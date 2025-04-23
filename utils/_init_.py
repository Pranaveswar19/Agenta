"""
Utility Functions Package for Travel Planner

This package contains utility modules for state management,
UI components, and prompt templates used throughout the application.
"""

# Import key functions for easy access
from .state_manager import (
    initialize_session_state,
    update_trip_details,
    has_required_details,
    log_activity
)

from .ui_components import (
    create_sidebar,
    display_chat_history,
    display_destination_info
)

__all__ = [
    'initialize_session_state',
    'update_trip_details',
    'has_required_details',
    'log_activity',
    'create_sidebar',
    'display_chat_history',
    'display_destination_info'
]
