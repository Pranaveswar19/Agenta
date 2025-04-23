"""
Configuration settings for the Travel Planner application
"""

# OpenAI Model Configuration
DEFAULT_MODEL = "gpt-3.5-turbo-0125"  # Most cost-effective model
SUMMARY_MODEL = "gpt-3.5-turbo-0125"  # For generating summaries

# Temperature settings for different tasks
FACTUAL_TEMPERATURE = 0.2   # For fact extraction, lower creativity
CREATIVE_TEMPERATURE = 0.7  # For creative content like itineraries
BALANCED_TEMPERATURE = 0.5  # For general responses

# API Request Configurations
MAX_TOKENS_STANDARD = 800
MAX_TOKENS_LARGE = 1000
MAX_TOKENS_SMALL = 300

# Conversation History Settings
MAX_CONVERSATION_HISTORY = 10  # Number of messages to keep in memory

# Trip Details Configuration
REQUIRED_TRIP_DETAILS = [
    "Destination",
    "Duration",
    "Budget",
    "Dietary Preferences",
    "Mobility Concerns"
]

OPTIONAL_TRIP_DETAILS = [
    "Season",
    "Activity Preferences",
    "Accommodation Type"
]

# Agent System Prompts
TRAVEL_ASSISTANT_PROMPT = """
You are Pranav, a friendly and knowledgeable travel expert.

Your personality:
- Warm and engaging, using a conversational tone
- Enthusiastic about travel planning
- Helpful but not pushy
- Asks thoughtful follow-up questions but only one at a time
- Shares brief personal anecdotes about destinations

Your goal is to help users plan their perfect vacation by gathering key information
and providing personalized recommendations. You collaborate with specialized agents
that can research destinations, find accommodations, and plan transportation.

Always maintain a natural conversation flow while collecting the necessary information.
Respond to user queries directly, while gently guiding the conversation toward 
collecting the required trip details if they're still missing.
"""

# UI Elements
UI_THEME_COLOR = "#1E88E5"
TITLE_EMOJI = "✈️"
APP_TITLE = "AI Travel Planner"
