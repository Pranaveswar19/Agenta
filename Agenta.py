import streamlit as st
import openai
import json
import re
from datetime import datetime, timedelta

from destination_agent import DestinationResearchAgent

client = openai.OpenAI(api_key=st.secrets["ai_planner_api_key"])

# Create instances of our agents
destination_agent = DestinationResearchAgent(openai_client=client)

SYSTEM_PROMPT = """
You are Agenta, a warm and enthusiastic travel expert who loves helping people plan their dream vacations. 
Your personality traits:
- Friendly and engaging, using casual language
- Asks ONE thoughtful follow-up question at a time
- Shares personal travel anecdotes (fictional but realistic)
- Shows genuine excitement about travel planning
- Uses appropriate emojis and expressive language

REQUIRED information (collect in this exact order):
1. Destination (ask first)
2. Duration (ask only after destination is known)
3. Budget (ask only after duration is known)
4. Dietary preferences (ask only after budget is known)
5. Mobility concerns (ask only after dietary preferences are known)

IMPORTANT: Do NOT ask about the optional information below unless the user mentions it first:
- Season
- Activity preferences
- Accommodation type

You now have access to real-time destination research. When a user mentions a destination, use this information to provide insightful facts about their destination. Include weather forecasts, local events, and travel tips based on the destination research.

When ALL REQUIRED information is collected (destination, duration, budget, dietary, mobility):
1. Let the user know you have all necessary information
2. Tell them they can say "generate itinerary" whenever they're ready
3. Only generate the itinerary when they specifically request it

After every user message, analyze their response and extract travel details while maintaining natural conversation.
Include a JSON object at the end of your message with ALL gathered details.

Example response when waiting for duration:
"That's fantastic! I absolutely love Goa - I was just there last season and the beaches are incredible! 🌊 
Now, could you tell me how long you're planning to stay? This will help me suggest the perfect activities for your trip! ✨"

Example response when all required info is collected:
"Great! I now have all the essential information for your trip. Just say 'generate itinerary' whenever you're ready, and I'll create a detailed plan for your vacation! ✨"

{
    "trip_details": {
        "Destination": "Goa, India",
        "Duration": "",
        "Budget": "",
        "Dietary Preferences": "",
        "Mobility Concerns": "",
        "Season": "",
        "Activity Preferences": "",
        "Accommodation Type": ""
    }
}
"""

def extract_json_from_response(response):
    """Carefully extract JSON from AI response."""
    try:
        json_matches = list(re.finditer(r'{[\s\S]*?}(?=\s*$)', response))
        if json_matches:
            json_str = json_matches[-1].group()
            parsed_json = json.loads(json_str)
            return parsed_json
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"JSON extraction error: {e}")
    return None

def update_trip_details_from_json(json_data):
    """Update session state with new trip details."""
    if json_data and "trip_details" in json_data:
        details = json_data["trip_details"]
        for key, value in details.items():
            if value and value.strip():
                formatted_key = key.strip()
                if formatted_key in st.session_state.trip_details:
                    st.session_state.trip_details[formatted_key] = value.strip()
                    print(f"Updated {formatted_key}: {value.strip()}")

def has_required_details():
    """Check if all required details are collected."""
    required_fields = [
        "Destination",
        "Duration",
        "Budget",
        "Dietary Preferences",
        "Mobility Concerns"
    ]
    return all(st.session_state.trip_details[field].strip() for field in required_fields)

# Modified to use our destination agent
def generate_detailed_itinerary():
    """Generate a detailed day-by-day itinerary using GPT-3.5-turbo and destination research."""
    try:
        days = int(st.session_state.trip_details['Duration'].split()[0])
        itinerary_parts = []
        
        # Get destination information from our agent
        destination = st.session_state.trip_details['Destination']
        destination_data = destination_agent.get_destination_info(destination)
        
        # Include destination research in our prompt
        destination_info = destination_data.get("info", "")
        destination_summary = destination_agent.generate_destination_summary(destination_data)
        
        summary_prompt = f"""
        Create an extremely detailed {st.session_state.trip_details['Duration']} itinerary for {st.session_state.trip_details['Destination']}.
        
        Trip Details:
        - Budget Level: {st.session_state.trip_details['Budget']}
        - Dietary Preferences: {st.session_state.trip_details['Dietary Preferences']}
        - Mobility Concerns: {st.session_state.trip_details['Mobility Concerns']}
        - Activity Preferences: {st.session_state.trip_details.get('Activity Preferences', 'Not specified')}
        - Accommodation Type: {st.session_state.trip_details.get('Accommodation Type', 'Not specified')}
        - Season: {st.session_state.trip_details.get('Season', 'Not specified')}

        Destination Information:
        {destination_summary}

        Create a day-by-day luxury itinerary with the following detailed breakdown for each day:

        1. Start each day with:
           "Day X: [Theme/Highlight of the day]"

        2. Morning Schedule (6 AM - 12 PM):
           - Wake-up call time
           - Breakfast venue with exact restaurant name
           - Recommended breakfast dishes with prices
           - Morning activity schedule with precise timings
           - Tips for best photo opportunities
           - Transportation details between locations

        3. Afternoon Schedule (12 PM - 5 PM):
           - Lunch spot with restaurant name and signature dishes
           - Price range for lunch
           - Post-lunch activities with duration
           - Indoor backup plans for weather
           - Local authentic experiences
           - Cultural insights for each location

        4. Evening Schedule (5 PM - 11 PM):
           - Sunset viewing spots if applicable
           - Pre-dinner activities
           - Restaurant recommendation for dinner
           - Must-try dishes and specialties
           - Evening entertainment options
           - Nightlife suggestions if relevant

        For EVERY venue mentioned, include:
        - Full name and exact location
        - Price range ($$$ scale)
        - Opening hours
        - Reservation requirements
        - Dress code if any
        - Local tips and secrets
        - Accessibility information
        - Contact numbers for reservations

        Additional Requirements:
        1. Include alternative options for each meal
        2. Specify travel time between locations
        3. Add local transportation tips
        4. Mention best photo spots
        5. Include cultural etiquette tips
        6. Add weather-specific advice
        7. Include estimated costs for all activities
        8. Mention booking requirements and links
        9. Add insider tips for each location
        10. Include safety tips when relevant

        Format the itinerary with clear headings, emojis, and bulleted lists for easy reading.
        Make it detailed enough that travelers can follow it without additional research.
        """
        
        summary = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You are a travel expert creating trip summaries."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=500,
            temperature=0.7
        ).choices[0].message.content

        for day in range(1, days + 1):
            # Get any local events for this day (for a more dynamic itinerary)
            start_date = (datetime.now() + timedelta(days=day)).strftime("%Y-%m-%d")
            local_events = destination_agent.get_local_events(destination, start_date, start_date)
            
            # Include events in the day's itinerary if available
            events_info = ""
            if local_events:
                events_info = "\n\nLocal Events Today:\n" + "\n".join([
                    f"- {event['name']} at {event['venue']}: {event['description']}" 
                    for event in local_events
                ])
            
            day_prompt = f"""
            Create Day {day} itinerary for {st.session_state.trip_details['Destination']}.
            Budget: {st.session_state.trip_details['Budget']}
            Diet: {st.session_state.trip_details['Dietary Preferences']}
            Mobility: {st.session_state.trip_details['Mobility Concerns']}

            Destination Information:
            {destination_summary}
            {events_info}

            Format:
            - Morning (breakfast, activities)
            - Afternoon (lunch, sightseeing)
            - Evening (dinner, entertainment)

            For each place include:
            - Name and location
            - Price range ($-$$$)
            - Opening hours
            - Key tips
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": "You are a travel expert creating detailed daily itineraries."},
                    {"role": "user", "content": day_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            ).choices[0].message.content
            
            itinerary_parts.append(f"## Day {day}\n\n{response}")
        
        # Get travel advisory information to include in the itinerary
        travel_advisory = destination_agent.get_travel_advisories(destination)
        visa_info = destination_agent.get_visa_requirements(destination)
        weather_info = destination_agent.get_current_weather(destination)
        
        # Add helpful sections at the end of the itinerary
        additional_sections = """
## Important Travel Information

### Weather Forecast
"""
        if weather_info:
            additional_sections += f"""
Current Temperature: {weather_info['temperature']}
Conditions: {weather_info['condition']}
Humidity: {weather_info['humidity']}
Wind: {weather_info['wind']}

3-Day Forecast:
"""
            for day in weather_info.get('forecast', []):
                additional_sections += f"- {day['day']}: {day['temp']}, {day['condition']}\n"
        else:
            additional_sections += "Weather information unavailable. Check local forecast before your trip.\n"
            
        additional_sections += "\n### Travel Advisories\n"
        if travel_advisory:
            additional_sections += f"""
Advisory Level: {travel_advisory['level']}
Last Updated: {travel_advisory['last_updated']}

{travel_advisory['details']}

Health Information: {travel_advisory['health_info']}

Emergency Contacts:
- Police: {travel_advisory['emergency_contacts']['police']}
- Ambulance: {travel_advisory['emergency_contacts']['ambulance']}
- US Embassy: {travel_advisory['emergency_contacts']['us_embassy']}
"""
        else:
            additional_sections += "Travel advisory information unavailable. Check with your country's foreign office for current advisories.\n"
            
        additional_sections += "\n### Visa Requirements\n"
        if visa_info:
            additional_sections += f"""
Visa Status: {visa_info['required']}
Processing Time: {visa_info['processing_time']}
Cost: {visa_info['cost']}
Additional Information: {visa_info['additional_info']}
"""
        else:
            additional_sections += "Visa information unavailable. Check with the embassy or consulate of your destination country.\n"
            
        full_itinerary = f"""
# Your {days}-Day Adventure in {st.session_state.trip_details['Destination']} ✈️

## Trip Overview
{summary}

---

{"---\n\n".join(itinerary_parts)}

---

{additional_sections}

---

### Data Sources
Information in this itinerary was compiled from:
- {' '.join(destination_data.get('sources', ['Travel research sources']))}
- Weather and travel advisory information current as of {datetime.now().strftime("%Y-%m-%d")}
"""
        
        return full_itinerary
    except Exception as e:
        print(f"Itinerary generation error: {e}")
        return None

def create_sidebar():
    """Create sidebar with trip details form."""
    with st.sidebar:
        st.title("📋 Trip Overview")
        st.markdown("Edit your trip details below")
        
        with st.form("trip_details_form"):
            modified = False
            new_values = {}
            
            for key in st.session_state.trip_details.keys():
                current_value = st.session_state.trip_details[key]
                new_value = st.text_input(f"{key}:", value=current_value, placeholder=f"Enter {key.lower()}", key=f"sidebar_{key}")
                new_values[key] = new_value
                
                if new_value != current_value:
                    modified = True
            
            col1, col2 = st.columns([1, 1])
            with col1:
                update_button = st.form_submit_button("Update Details")
            with col2:
                reset_button = st.form_submit_button("Reset")
            
            if update_button and modified:
                for key, value in new_values.items():
                    st.session_state.trip_details[key] = value
                st.session_state.itinerary_generated = False
                st.session_state.generated_itinerary = None
                st.rerun()
            
            if reset_button:
                for key in st.session_state.trip_details:
                    st.session_state.trip_details[key] = ""
                st.session_state.itinerary_generated = False
                st.session_state.generated_itinerary = None
                st.rerun()

# New function to display destination info
def display_destination_info():
    """Display destination information when available"""
    if st.session_state.trip_details["Destination"]:
        destination = st.session_state.trip_details["Destination"]
        
        # Show a loading message
        with st.expander("Destination Research", expanded=True):
            with st.spinner(f"Researching {destination}..."):
                destination_data = destination_agent.get_destination_info(destination)
                
                # Display a summary of the destination
                st.markdown(f"## About {destination}")
                
                # Extract and display sections from the destination info
                info = destination_data.get("info", "")
                st.markdown(info)
                
                # Show the sources
                sources = destination_data.get("sources", [])
                if sources:
                    st.markdown("### Sources")
                    for source in sources:
                        st.markdown(f"- [{source}]({source})")
                
                # Get and display current weather
                weather = destination_agent.get_current_weather(destination)
                if weather:
                    st.markdown("### Current Weather")
                    st.markdown(f"**Temperature:** {weather['temperature']} | **Conditions:** {weather['condition']}")
                    
                    st.markdown("### 3-Day Forecast")
                    forecast_data = []
                    for day in weather.get('forecast', []):
                        forecast_data.append([day['day'], day['temp'], day['condition']])
                    
                    st.table({"Day": [d[0] for d in forecast_data],
                             "Temperature": [d[1] for d in forecast_data],
                             "Conditions": [d[2] for d in forecast_data]})
                
                # Get and display travel advisories
                advisory = destination_agent.get_travel_advisories(destination)
                if advisory:
                    st.markdown("### Travel Advisory")
                    st.markdown(f"**Level:** {advisory['level']} | **Last Updated:** {advisory['last_updated']}")
                    st.markdown(advisory['details'])

if "initialized" not in st.session_state:
    st.session_state.conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
    st.session_state.trip_details = {
        "Destination": "",
        "Duration": "",
        "Budget": "",
        "Dietary Preferences": "",
        "Mobility Concerns": "",
        "Season": "",
        "Activity Preferences": "",
        "Accommodation Type": ""
    }
    st.session_state.itinerary_generated = False
    st.session_state.generated_itinerary = None
    st.session_state.initialized = True

st.title("✈️ AI Travel Planner")
st.markdown("""
    <style>
    .travel-header {
        color: #1E88E5;
        font-size: 20px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)
st.markdown('<p class="travel-header">Hi! I\'m Agenta, your personal travel expert. Let\'s plan your dream vacation! 🌎</p>', unsafe_allow_html=True)

create_sidebar()

# Display destination info if available
if st.session_state.trip_details["Destination"]:
    display_destination_info()

for message in st.session_state.conversation[1:]: 
    if message["role"] in ["user", "assistant"]:
        content = message["content"]
        
        if message["role"] == "assistant":
            content = re.sub(r'{[\s\S]*?}(?=\s*$)', '', content).strip()
        
        st.chat_message(message["role"]).write(content)

if len(st.session_state.conversation) == 1:
    greeting = "Hi! I'm so excited to help you plan your next adventure! ✈️ Where would you like to go? Tell me about your dream destination! 🌟"
    st.chat_message("assistant").write(greeting)
    st.session_state.conversation.append({"role": "assistant", "content": greeting})

user_input = st.chat_input("Tell me about your travel plans...")

if user_input:
    user_input = user_input.strip()
    st.chat_message("user").write(user_input)
    st.session_state.conversation.append({"role": "user", "content": user_input})
    
    # Check if destination has been updated in this message
    # and update destination research if needed
    prev_destination = st.session_state.trip_details.get("Destination", "")
    destination_mentioned = False
    
    # Basic destination extraction (in a real app, use NER or the LLM to extract this)
    potential_destinations = re.findall(r"(?:going to|visit|traveling to|planning for|vacation in|trip to) ([A-Z][a-z]+(?: [A-Z][a-z]+)*)", user_input)
    if potential_destinations:
        potential_destination = potential_destinations[0]
        if potential_destination != prev_destination:
            destination_mentioned = True
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(st.session_state.conversation[-10:])
    
    # If destination was mentioned, get research data
    destination_info = ""
    if destination_mentioned:
        destination_data = destination_agent.get_destination_info(potential_destination)
        destination_info = destination_agent.generate_destination_summary(destination_data)

    messages.append({"role": "system", "content": f"""
        Current trip details: {json.dumps(st.session_state.trip_details)}
        Remember: Only ask about season/activities/accommodation if user mentions them first.
        If all required details are collected, remind user to say "generate itinerary".
        
        New destination research:
        {destination_info}
    """})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[{"role": m["role"], "content": m["content"]} for m in messages],
            max_tokens=800,
            temperature=0.7
        ).choices[0].message.content

        json_data = extract_json_from_response(response)
        if json_data:
            update_trip_details_from_json(json_data)

        display_response = re.sub(r'{[\s\S]*?}(?=\s*$)', '', response).strip()
        st.chat_message("assistant").write(display_response)

        st.session_state.conversation.append({
            "role": "assistant",
            "content": response
        })

        generate_triggers = ["generate itinerary", "generate my itinerary", "create itinerary", "make itinerary", "plan my trip"]
        should_generate = any(trigger in user_input.lower() for trigger in generate_triggers)

        if has_required_details() and should_generate:
            if not st.session_state.itinerary_generated:
                st.chat_message("assistant").write("Perfect! I'll create your personalized itinerary now... ✨")
                with st.spinner("Generating your personalized itinerary... This might take a minute!"):
                    itinerary = generate_detailed_itinerary()
                if itinerary:
                    st.session_state.itinerary_generated = True
                    st.session_state.generated_itinerary = itinerary
                    st.markdown("---")
                    st.subheader("🗺️ Your Personalized Itinerary")
                    st.markdown(itinerary)

        # If destination has been updated, trigger the UI to refresh and show the destination info
        if "Destination" in st.session_state.trip_details and st.session_state.trip_details["Destination"] != prev_destination:
            st.rerun()
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

if st.session_state.generated_itinerary:
    st.markdown("---")
    st.subheader("🗺️ Your Personalized Itinerary")
    st.markdown(st.session_state.generated_itinerary)

st.markdown("---")
st.markdown("Created by Pranav")
