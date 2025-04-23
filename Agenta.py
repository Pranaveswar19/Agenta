import streamlit as st
import openai
import json
import re
from datetime import datetime, timedelta

# Import configuration
from config import *

# Import utilities
from utils.state_manager import (
    initialize_session_state, 
    update_trip_details, 
    has_required_details,
    extract_json_from_response,
    update_trip_details_from_response,
    log_activity
)
from utils.ui_components import (
    create_sidebar,
    display_chat_history,
    display_destination_info,
    display_debug_panel
)
from utils.prompt_templates import TRAVEL_ASSISTANT_PROMPT

# Import agents
from agents.destination_agent import DestinationAgent
from agents.details_agent import DetailsAgent
from agents.itinerary_agent import ItineraryAgent

# Setup OpenAI client
if "ai_planner_api_key" in st.secrets:
    client = openai.OpenAI(api_key=st.secrets["ai_planner_api_key"])
else:
    client = None
    st.error("OpenAI API key not found in secrets. Some features may not work.")

# Initialize agents
destination_agent = DestinationAgent(openai_client=client)
details_agent = DetailsAgent(openai_client=client)
itinerary_agent = ItineraryAgent(openai_client=client)

# Initialize session state
initialize_session_state()

# Update current user info (using the information provided)
st.session_state.current_user = "Pranaveswar19"
st.session_state.current_datetime = "2025-04-23 18:14:31"

# Set page title and configuration
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=TITLE_EMOJI,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main application UI
st.title(f"{TITLE_EMOJI} {APP_TITLE}")
st.markdown("""
    <style>
    .travel-header {
        color: #1E88E5;
        font-size: 20px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)
st.markdown('<p class="travel-header">Hi! I\'m Pranav, your personal travel expert. Let\'s plan your dream vacation! 🌎</p>', unsafe_allow_html=True)

# Create sidebar with trip details form
update_button, reset_button, modified, new_values = create_sidebar(st.session_state.trip_details)

if update_button and modified:
    # Update trip details from form
    update_trip_details(new_values)
    st.rerun()

if reset_button:
    # Reset trip details
    for key in st.session_state.trip_details:
        st.session_state.trip_details[key] = ""
    st.session_state.itinerary_generated = False
    st.session_state.generated_itinerary = None
    # Clear destination data to avoid showing old research
    if "destination_data" in st.session_state:
        st.session_state.destination_data = {}
    st.rerun()

# Add debug mode toggle to sidebar
with st.sidebar:
    st.markdown("---")
    debug_toggle = st.checkbox("Debug Mode", value=st.session_state.debug_mode)
    if debug_toggle != st.session_state.debug_mode:
        st.session_state.debug_mode = debug_toggle
        st.rerun()
    
    if st.session_state.debug_mode:
        # Add current date/time and user info
        st.markdown(f"**Current Date/Time:** {st.session_state.current_datetime}")
        st.markdown(f"**User:** {st.session_state.current_user}")

# Display debug panel if enabled
display_debug_panel()

# Display destination information in sidebar ONLY, not in main chat area
# This fixes the issue of destination info appearing at the top of chat
destination = st.session_state.trip_details.get("Destination", "")
if destination:
    with st.sidebar:
        st.markdown("---")
        with st.expander("Destination Information", expanded=False):
            if "destination_data" not in st.session_state:
                st.session_state.destination_data = {}
                
            if destination in st.session_state.destination_data:
                st.markdown(f"## {destination}")
                
                # Extract just key facts for sidebar display
                dest_data = st.session_state.destination_data[destination]
                
                # Show brief overview
                if "overview" in dest_data:
                    overview = dest_data["overview"]
                    first_section_end = overview.find("\n## ")
                    if first_section_end > 0:
                        brief_overview = overview[:first_section_end].strip()
                    else:
                        brief_overview = overview.split("\n\n")[0]
                    st.markdown(brief_overview)
                
                # Show current weather
                if "weather" in dest_data and "current" in dest_data["weather"]:
                    weather = dest_data["weather"]
                    st.markdown(f"**Current Weather:** {weather['current'].get('temp', 'N/A')}, {weather['current'].get('condition', 'N/A')}")
                
                # Show advisory level if available
                if "advisories" in dest_data and "overall_risk" in dest_data["advisories"]:
                    st.markdown(f"**Advisory Level:** {dest_data['advisories'].get('overall_risk', 'Not available')}")
            else:
                # Don't show a spinner here to avoid cluttering the UI
                st.markdown(f"Researching {destination}...")

# Initialize conversation if needed
if len(st.session_state.conversation) == 0:
    greeting = "Hi! I'm so excited to help you plan your next adventure! ✈️ Where would you like to go? Tell me about your dream destination! 🌟"
    st.session_state.conversation.append({"role": "assistant", "content": greeting})

# Display chat history
display_chat_history(st.session_state.conversation)

# Chat input
user_input = st.chat_input("Tell me about your travel plans...")

if user_input:
    # Add user message to conversation
    user_input = user_input.strip()
    st.chat_message("user").write(user_input)
    st.session_state.conversation.append({"role": "user", "content": user_input})
    
    # Check for destination mentions to trigger research
    current_destination = st.session_state.trip_details.get("Destination", "")
    
    # Process with the details agent
    details_result = details_agent.process(st.session_state.conversation, st.session_state.trip_details)
    
    # Update trip details from agent results
    update_trip_details(details_result["updated_details"])
    
    # Check if destination has changed
    new_destination = details_result["updated_details"].get("Destination", "")
    if new_destination and new_destination != current_destination:
        # Trigger destination research for new destination
        if "destination_data" not in st.session_state:
            st.session_state.destination_data = {}
            
        if new_destination not in st.session_state.destination_data:
            with st.spinner(f"Researching {new_destination}..."):
                destination_data = destination_agent.process(new_destination)
                if destination_data:
                    st.session_state.destination_data[new_destination] = destination_data
    
    # Check for itinerary generation request
    # FIX: More robust detection of itinerary generation triggers
    generate_triggers = [
        "generate itinerary", "create itinerary", "make itinerary", 
        "plan my trip", "create a plan", "make a plan", 
        "generate my trip", "plan", "generate", "itinerary"
    ]
    should_generate = any(trigger in user_input.lower() for trigger in generate_triggers)
    
    # FIX: If all details are collected and user says anything that might be a generation request,
    # we should generate the itinerary
    if has_required_details() and should_generate:
        if not st.session_state.itinerary_generated:
            # Show generation message
            generation_message = "Perfect! I'll create your personalized itinerary now... ✨"
            st.chat_message("assistant").write(generation_message)
            st.session_state.conversation.append({
                "role": "assistant",
                "content": generation_message
            })
            
            with st.spinner("Generating your personalized itinerary... This might take a minute!"):
                # Get destination data if available
                destination = st.session_state.trip_details.get("Destination", "")
                destination_data = st.session_state.destination_data.get(destination, None)
                
                # Generate itinerary
                itinerary = itinerary_agent.process(
                    st.session_state.trip_details,
                    destination_data
                )
                
                if itinerary:
                    st.session_state.itinerary_generated = True
                    st.session_state.generated_itinerary = itinerary
                    
                    # Display the generated itinerary
                    st.markdown("---")
                    st.subheader("🗺️ Your Personalized Itinerary")
                    st.markdown(itinerary)
                    
                    # Add a download button for the itinerary
                    st.download_button(
                        label="Download Itinerary",
                        data=itinerary,
                        file_name=f"{destination.replace(' ', '_')}_itinerary.md",
                        mime="text/markdown"
                    )
                else:
                    st.error("There was a problem generating your itinerary. Please try again.")
        else:
            # If itinerary already generated, just let the user know
            st.chat_message("assistant").write("I've already created your itinerary! You can find it below. Would you like me to regenerate it with any changes?")
            st.session_state.conversation.append({
                "role": "assistant",
                "content": "I've already created your itinerary! You can find it below. Would you like me to regenerate it with any changes?"
            })
            
        # Exit early to avoid adding another assistant response
        st.rerun()
    
    # Generate response if not generating itinerary
    if client:
        # Prepare destination information if available
        destination_info = ""
        if new_destination and new_destination in st.session_state.destination_data:
            destination_data = st.session_state.destination_data[new_destination]
            overview = destination_data.get("overview", "")
            # Get a brief summary of the destination
            first_section_end = overview.find("\n## ")
            if first_section_end > 0:
                destination_info = overview[:first_section_end].strip()
            else:
                destination_info = overview.split("\n\n")[0]
        
        # Prepare conversation history for the API
        conversation_history = [{"role": "system", "content": TRAVEL_ASSISTANT_PROMPT}]
        
        # Add the last 10 messages (or fewer if there aren't 10)
        recent_messages = st.session_state.conversation[-min(10, len(st.session_state.conversation)):]
        conversation_history.extend(recent_messages)
        
        # Add system guidance based on current state
        # FIX: Explicitly tell the assistant not to repeat destination information
        # and instead focus on gathering missing details or prompting for itinerary generation
        system_guidance = f"""
        Current trip details: {json.dumps(st.session_state.trip_details)}
        
        Next question to ask: {details_result["next_question"]}
        Missing required fields: {", ".join(details_result["missing_fields"]) if details_result["missing_fields"] else "None"}
        
        Guidelines:
        1. Maintain a natural, friendly conversation
        2. DO NOT repeat destination information that's already been researched
        3. If all details are collected, remind the user they can say "generate itinerary"
        4. Always include the trip details JSON object at the end of your response
        5. If the user asks about their destination, provide brief insights but focus on collecting missing details
        
        Important: 
        - The destination information is already displayed in the sidebar
        - If all required details are collected, strongly encourage the user to generate an itinerary
        """
        
        conversation_history.append({"role": "system", "content": system_guidance})
        
        # Call the API
        try:
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[{"role": m["role"], "content": m["content"]} for m in conversation_history],
                max_tokens=MAX_TOKENS_STANDARD,
                temperature=BALANCED_TEMPERATURE
            )
            
            # Get response text
            response_text = response.choices[0].message.content
            
            # Update trip details from response
            update_trip_details_from_response(response_text)
            
            # Display response
            cleaned_response = re.sub(r'{[\s\S]*?}(?=\s*$)', '', response_text).strip()
            st.chat_message("assistant").write(cleaned_response)
            
            # Add to conversation history
            st.session_state.conversation.append({
                "role": "assistant",
                "content": response_text
            })
            
            # FIX: Check if all details are collected and add a "Generate Itinerary" button for convenience
            if has_required_details() and not st.session_state.itinerary_generated:
                st.button("Generate Itinerary", on_click=lambda: st.session_state.update({
                    'manual_generate': True
                }))
                
                # Handle button click
                if st.session_state.get('manual_generate', False):
                    st.session_state.manual_generate = False  # Reset flag
                    
                    # Add a user message about generating itinerary
                    generate_message = "generate itinerary"
                    st.session_state.conversation.append({
                        "role": "user",
                        "content": generate_message
                    })
                    
                    # Rerun to process the generate request
                    st.rerun()
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            log_activity("Main App", "API Error", str(e))
    else:
        # Fallback if no API client
        st.error("Cannot generate response: OpenAI API client not initialized")
    
    # Rerun if destination changed to update UI
    if new_destination and new_destination != current_destination:
        st.rerun()

# Display previously generated itinerary if available
if st.session_state.generated_itinerary and st.session_state.itinerary_generated:
    st.markdown("---")
    st.subheader("🗺️ Your Personalized Itinerary")
    st.markdown(st.session_state.generated_itinerary)
    
    # Add a download button for the itinerary
    destination = st.session_state.trip_details.get("Destination", "My_Trip")
    st.download_button(
        label="Download Itinerary",
        data=st.session_state.generated_itinerary,
        file_name=f"{destination.replace(' ', '_')}_itinerary.md",
        mime="text/markdown"
    )

    # Add button to regenerate itinerary
    if st.button("Regenerate Itinerary"):
        st.session_state.itinerary_generated = False
        st.session_state.generated_itinerary = None
        st.rerun()

# Footer
st.markdown("---")
st.markdown("Created with ❤️ by Pranav")
