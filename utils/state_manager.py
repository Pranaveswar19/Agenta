"""
Session state management for the Travel Planner application
"""

import streamlit as st
from datetime import datetime

def initialize_session_state():
    """Initialize all session state variables needed for the application"""
    if "initialized" not in st.session_state:
        # Initialize conversation history
        st.session_state.conversation = []
        
        # Initialize trip details
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
        
        # Initialize itinerary state
        st.session_state.itinerary_generated = False
        st.session_state.generated_itinerary = None
        
        # Initialize agent data caches
        st.session_state.destination_data = {}
        st.session_state.agent_logs = []
        
        # Initialize debug mode
        st.session_state.debug_mode = False
        
        # Mark as initialized
        st.session_state.initialized = True

def log_activity(agent_name, action, details=""):
    """Add an entry to the agent activity log"""
    if "agent_logs" not in st.session_state:
        st.session_state.agent_logs = []
        
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "agent": agent_name,
        "action": action,
        "details": details
    }
    
    st.session_state.agent_logs.append(log_entry)
    return log_entry

def update_trip_details(new_details):
    """Update session state with new trip details"""
    if not isinstance(new_details, dict):
        return False
        
    modified = False
    for key, value in new_details.items():
        if key in st.session_state.trip_details and value.strip():
            if st.session_state.trip_details[key] != value:
                st.session_state.trip_details[key] = value
                modified = True
                log_activity("State Manager", f"Updated {key}", value)
    
    # If destination changed, reset itinerary
    if "Destination" in new_details and new_details["Destination"].strip() != st.session_state.trip_details.get("Destination", ""):
        st.session_state.itinerary_generated = False
        st.session_state.generated_itinerary = None
        log_activity("State Manager", "Reset itinerary", "Destination changed")
    
    return modified

def has_required_details():
    """Check if all required details are collected"""
    required_fields = [
        "Destination",
        "Duration",
        "Budget",
        "Dietary Preferences",
        "Mobility Concerns"
    ]
    return all(st.session_state.trip_details.get(field, "").strip() for field in required_fields)

def extract_json_from_response(response):
    """Carefully extract JSON from AI response."""
    try:
        import re
        import json
        json_matches = list(re.finditer(r'{[\s\S]*?}(?=\s*$)', response))
        if json_matches:
            json_str = json_matches[-1].group()
            parsed_json = json.loads(json_str)
            return parsed_json
    except Exception as e:
        log_activity("State Manager", "JSON extraction error", str(e))
    return None

def update_trip_details_from_response(response):
    """Extract and update trip details from an AI response"""
    json_data = extract_json_from_response(response)
    if json_data and "trip_details" in json_data:
        return update_trip_details(json_data["trip_details"])
    return False
