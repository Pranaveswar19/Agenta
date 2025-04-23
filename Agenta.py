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

# Update current user info (in this case from the prompt)
st.session_state.current_user = "Pranaveswar19"

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
        st.markdown(f"**Current Date/Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.markdown(f"**User:** {st.session_state.current_user}")

# Display debug panel if enabled
display_debug_panel()

# Display destination information if available
destination = st.session_state.trip_details.get("Destination", "")
if destination:
    if destination in st.session_state.destination_data:
        display_destination_info(st.session_state.destination_data[destination])
    else:
        with st.spinner(f"Researching {destination}..."):
            destination_data = destination_agent.process(destination)
            if destination_data:
                st.session_state.destination_data[destination] = destination_data
                display_destination_info(destination_data)

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
        if new_destination not in st.session_state.destination_data:
            with st.spinner(f"Researching {new_destination}..."):
                destination_data = destination_agent.process(new_destination)
                if destination_data:
                    st.session_state.destination_data[new_destination] = destination_data
    
    # Generate response
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
        system_guidance = f"""
        Current trip details: {json.dumps(st.session_state.trip_details)}
        Next question to ask: {details_result["next_question"]}
        Missing required fields: {", ".join(details_result["missing_fields"]) if details_result["missing_fields"] else "None"}
        
        Destination information: {destination_info}
        
        Guidelines:
        1. Maintain a natural, friendly conversation
        2. If all details are collected, remind the user they can say "generate itinerary"
        3. Always include the trip details JSON object at the end of your response
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
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            log_activity("Main App", "API Error", str(e))
    else:
        # Fallback if no API client
        st.error("Cannot generate response: OpenAI API client not initialized")
    
    # Check for itinerary generation request
    generate_triggers = ["generate itinerary", "generate my itinerary", "create itinerary", "make itinerary", "plan my trip"]
    should_generate = any(trigger in user_input.lower() for trigger in generate_triggers)
    
    if has_required_details() and should_generate:
        if not st.session_state.itinerary_generated:
            st.chat_message("assistant").write("Perfect! I'll create your personalized itinerary now... ✨")
            
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
    
    # Rerun if destination changed to update UI
    if new_destination and new_destination != current_destination:
        st.rerun()

# Display previously generated itinerary if available
if st.session_state.generated_itinerary and not st.session_state.itinerary_generated:
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

# Footer
st.markdown("---")
st.markdown("Created with ❤️ by Pranav")
