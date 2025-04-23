"""
Reusable UI components for the Travel Planner application
"""

import streamlit as st
from datetime import datetime
import json

def create_sidebar(trip_details):
    """Create sidebar with trip details form"""
    with st.sidebar:
        st.title("📋 Trip Overview")
        st.markdown("Edit your trip details below")
        
        with st.form("trip_details_form"):
            modified = False
            new_values = {}
            
            for key in trip_details.keys():
                current_value = trip_details[key]
                new_value = st.text_input(f"{key}:", value=current_value, placeholder=f"Enter {key.lower()}", key=f"sidebar_{key}")
                new_values[key] = new_value
                
                if new_value != current_value:
                    modified = True
            
            col1, col2 = st.columns([1, 1])
            with col1:
                update_button = st.form_submit_button("Update Details")
            with col2:
                reset_button = st.form_submit_button("Reset")
            
            return update_button, reset_button, modified, new_values

def display_chat_history(conversation):
    """Display chat message history"""
    for message in conversation: 
        if message["role"] in ["user", "assistant"]:
            content = message["content"]
            
            # Remove JSON from assistant messages
            if message["role"] == "assistant":
                import re
                content = re.sub(r'{[\s\S]*?}(?=\s*$)', '', content).strip()
            
            st.chat_message(message["role"]).write(content)

def display_destination_info(destination_data):
    """Display destination information"""
    if not destination_data:
        return
        
    destination = destination_data.get("destination", "")
    
    with st.expander("Destination Research", expanded=True):
        # Display a summary of the destination
        st.markdown(f"## About {destination}")
        
        # Extract and display overview
        info = destination_data.get("overview", "")
        st.markdown(info)
        
        # Display weather information if available
        weather = destination_data.get("weather", {})
        if weather and "current" in weather:
            st.markdown("### Current Weather")
            current = weather["current"]
            st.markdown(f"**Temperature:** {current.get('temp', 'N/A')} | **Conditions:** {current.get('condition', 'N/A')}")
            
            if "forecast" in weather:
                st.markdown("### Weather Forecast")
                forecast_data = []
                for day in weather.get('forecast', [])[:5]:  # Show up to 5 days
                    forecast_data.append([
                        day.get('day', 'N/A'), 
                        f"{day.get('temp_high', 'N/A')}/{day.get('temp_low', 'N/A')}", 
                        day.get('condition', 'N/A')
                    ])
                
                st.table({
                    "Day": [d[0] for d in forecast_data],
                    "Temperature (High/Low)": [d[1] for d in forecast_data],
                    "Conditions": [d[2] for d in forecast_data]
                })
        
        # Display events if available
        events = destination_data.get("events", [])
        if events:
            st.markdown("### Upcoming Events")
            for event in events[:5]:  # Show up to 5 events
                st.markdown(f"**{event.get('name', 'Event')}**")
                st.markdown(f"*{event.get('date', 'Date TBD')} at {event.get('venue', 'Venue TBD')}*")
                st.markdown(f"{event.get('description', '')}")
                st.markdown("---")
        
        # Display travel advisories if available
        advisory = destination_data.get("advisories", {})
        if advisory:
            st.markdown("### Travel Advisory")
            st.markdown(f"**Risk Level:** {advisory.get('overall_risk', 'No data')}")
            st.markdown(advisory.get('safety_info', 'No safety information available.'))

def display_debug_panel():
    """Display debug information panel"""
    if not st.session_state.get("debug_mode", False):
        return
        
    with st.expander("Debug Information", expanded=False):
        st.write("### Application State")
        
        # Show trip details
        st.json(st.session_state.trip_details)
        
        st.write("### Agent Logs")
        
        # Show log of agent activities
        if "agent_logs" not in st.session_state:
            st.session_state.agent_logs = []
            
        for log in st.session_state.agent_logs[-10:]:  # Show last 10 logs
            st.write(f"**{log['timestamp']}** - {log['agent']}: {log['action']}")
            if log.get('details'):
                st.write(f"  *{log['details']}*")
        
        # Add system information
        st.write("### System Information")
        st.write(f"**Current Date/Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"**User:** {st.session_state.get('current_user', 'Unknown')}")
