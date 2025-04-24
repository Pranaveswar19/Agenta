from .base_agent import BaseAgent
import json
import re
import random

class DetailsAgent(BaseAgent):
    """
    Agent responsible for extracting and managing travel details
    from user conversations in a natural, unobtrusive way.
    Using chain prompts for dynamic question generation.
    """
    
    def __init__(self, openai_client=None):
        """Initialize the details gathering agent"""
        super().__init__(name="Details Agent", openai_client=openai_client)
        
        # Define the required trip details
        self.required_fields = [
            "Destination",
            "Origin",
            "Duration",
            "Travel_Dates",
            "Travelers_Count",
            "Travelers_Type",
            "Budget",
            "Dietary_Preferences",
            "Mobility_Concerns"
        ]
        
        # Define optional fields
        self.optional_fields = [
            "Season",
            "Activity_Preferences",
            "Accommodation_Type",
            "Transportation_Preferences",
            "Purpose_Of_Trip",
            "Must_See_Attractions",
            "Weather_Preferences",
            "Previous_Travel_Experience",
            "Shopping_Interests",
            "Special_Occasions",
            "Language_Assistance_Needs"
        ]
        
        # Define tiers for information gathering
        self.tier1_fields = ["Destination", "Origin", "Duration", "Travel_Dates", "Travelers_Count", "Budget"]
        self.tier2_fields = ["Travelers_Type", "Dietary_Preferences", "Mobility_Concerns", "Accommodation_Type"]
        self.tier3_fields = ["Purpose_Of_Trip", "Must_See_Attractions", "Transportation_Preferences", 
                            "Special_Occasions", "Weather_Preferences"]
        self.tier4_fields = ["Previous_Travel_Experience", "Shopping_Interests", "Language_Assistance_Needs", "Season"]
    
    def process(self, conversation_history, current_details=None):
        """
        Extract trip details from conversation history and
        determine the next questions to ask
        """
        if current_details is None:
            current_details = {field: "" for field in self.required_fields + self.optional_fields}
        
        # Extract details from conversation
        updated_details, confidence_scores = self._extract_details(conversation_history, current_details)
        
        # Determine what to ask next using chain prompts
        next_question, missing_fields = self._determine_next_question(updated_details, conversation_history)
        
        # Format response with JSON
        response_with_json = self._format_response(updated_details, next_question, missing_fields)
        
        return {
            "updated_details": updated_details,
            "next_question": next_question,
            "missing_fields": missing_fields,
            "response_with_json": response_with_json,
            "confidence_scores": confidence_scores
        }
    
    def _extract_details(self, conversation_history, current_details):
        """Extract trip details from the conversation history"""
        # Convert conversation history to string format for the LLM
        conversation_text = "\n".join([
            f"{message['role'].upper()}: {message['content']}"
            for message in conversation_history
            if message['role'] in ['user', 'assistant']
        ])
        
        # Prepare the current details as JSON
        current_details_json = json.dumps(current_details, indent=2)
        
        system_prompt = """You are a detail extraction specialist for travel planning.
        Analyze the conversation history and extract travel planning details.
        Only update values when you have high confidence in the information.
        For each detail, provide a confidence score (0-100).
        If information is not mentioned or unclear, do not update the field.
        
        Pay special attention to:
        1. Dates (format as YYYY-MM-DD)
        2. Number of travelers and their relationships (family, couple, friends, solo)
        3. Specific preferences about accommodations, transportation, and activities
        4. Any mentioned special requirements or celebrations
        5. Both explicit and implicit mentions of budget level
        """
        
        user_prompt = f"""Current trip details:
{current_details_json}

Conversation history:
{conversation_text}

Extract any new or updated travel details from this conversation.
Return your findings as valid JSON with two objects:
1. "updated_details" - The trip details with any new information
2. "confidence_scores" - Your confidence level (0-100) for each field

Format:
{{
  "updated_details": {{
    "Destination": "value",
    "Origin": "value",
    "Duration": "value",
    "Travel_Dates": "value",
    "Travelers_Count": "value",
    "Travelers_Type": "value",
    "Budget": "value",
    "Dietary_Preferences": "value",
    "Mobility_Concerns": "value",
    "Season": "value",
    "Activity_Preferences": "value",
    "Accommodation_Type": "value",
    "Transportation_Preferences": "value",
    "Purpose_Of_Trip": "value",
    "Must_See_Attractions": "value",
    "Weather_Preferences": "value",
    "Previous_Travel_Experience": "value",
    "Shopping_Interests": "value",
    "Special_Occasions": "value",
    "Language_Assistance_Needs": "value"
  }},
  "confidence_scores": {{
    "Destination": 95,
    "Origin": 90,
    ...other fields
  }}
}}
"""
        
        result = self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,  # Low temperature for factual extraction
            max_tokens=1000
        )
        
        # Extract JSON from the response
        try:
            # Find JSON in the response
            json_match = re.search(r'({[\s\S]*})', result)
            if json_match:
                extracted_data = json.loads(json_match.group(1))
                updated_details = extracted_data.get("updated_details", {})
                confidence_scores = extracted_data.get("confidence_scores", {})
                
                # Merge with current details, only updating fields that were extracted
                for field in current_details:
                    if field in updated_details and updated_details[field] and confidence_scores.get(field, 0) > 50:
                        current_details[field] = updated_details[field]
                
                return current_details, confidence_scores
            
            return current_details, {}
        except Exception as e:
            self.log_activity("Error", f"Details extraction error: {str(e)}")
            return current_details, {}
    
    def _determine_next_question(self, current_details, conversation_history):
        """
        Determine what information to ask for next using a dynamic chain prompt approach
        """
        # Check if all required fields are filled
        missing_required = [field for field in self.required_fields if not current_details.get(field, "").strip()]
        
        # If all required fields are filled, we can encourage itinerary generation
        if not missing_required:
            return "Great! I have all the essential information I need to create your personalized itinerary. Just say 'generate itinerary' and I'll create a detailed plan for your trip! ✨", []
        
        # Determine which tier to focus on
        missing_tier1 = [field for field in self.tier1_fields if not current_details.get(field, "").strip()]
        missing_tier2 = [field for field in self.tier2_fields if not current_details.get(field, "").strip()]
        
        # Convert conversation history to string format for the LLM
        conversation_text = "\n".join([
            f"{message['role'].upper()}: {message['content']}"
            for message in conversation_history[-5:] # Using last 5 messages for context
            if message['role'] in ['user', 'assistant']
        ])
        
        # Current date and time
        current_datetime = "2025-04-24 08:50:28"  # This should be dynamically updated
        
        # Prepare the current details as JSON
        current_details_json = json.dumps(current_details, indent=2)
        
        # Prepare the system prompt for chain prompting
        system_prompt = """You are a travel planning expert who excels at gathering information in a conversational way.
        Your goal is to formulate the next best question to ask the user to gather essential travel information.
        The question should flow naturally from the conversation and not feel like a generic form question.
        Make your questions engaging, personalized, and contextually relevant.
        
        For questions about dates, ask for specific dates if possible.
        For questions about travelers, try to understand the group dynamics.
        For questions about budget, help users understand the options available.
        
        NEVER ask for multiple pieces of information in a single question.
        NEVER list all the missing information - focus on one question at a time.
        ALWAYS phrase questions in a friendly, conversational tone.
        """
        
        # Determine which missing field to focus on
        if missing_tier1:
            target_field = missing_tier1[0]
            field_importance = "essential"
        else:
            target_field = missing_tier2[0] if missing_tier2 else self.tier3_fields[0]
            field_importance = "important" if missing_tier2 else "helpful"
        
        # Prepare the user prompt for chain prompting
        user_prompt = f"""Current date and time: {current_datetime}
        
Current trip details:
{current_details_json}

Recent conversation:
{conversation_text}

Your next task is to ask about the user's "{target_field.replace('_', ' ')}".
This information is {field_importance} for planning their trip.

Generate a single, natural-sounding question to ask about this topic.
Consider what we already know about their trip and make the question flow naturally.
Avoid sounding like a form or survey. Make it conversational and friendly.

Return only the question you would ask the user, nothing else.
"""
        
        # Call the LLM to generate the next question
        next_question = self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,  # Higher temperature for more varied, natural responses
            max_tokens=150
        )
        
        # Clean up the response if needed
        next_question = next_question.strip()
        
        # Return the next question and list of all missing required fields
        return next_question, missing_required
    
    def _format_response(self, details, next_question, missing_fields):
        """Format a response with JSON data included"""
        # Create a friendly response
        if missing_fields:
            response_text = self._create_friendly_response(details, next_question)
        else:
            # Make the generate itinerary prompt more obvious
            response_text = "Great! I now have all the essential information for your trip. 🎉 Just say 'generate itinerary' whenever you're ready, and I'll create a detailed plan for your vacation!"
        
        # Add JSON data
        response_with_json = f"{response_text}\n\n{{\n    \"trip_details\": {json.dumps(details, indent=8)}\n}}"
        
        return response_with_json
    
    def _create_friendly_response(self, details, next_question):
        """Create a conversational response based on collected details"""
        # Check what we already know
        destination = details.get("Destination", "").strip()
        
        responses = [
            "I'm excited to help plan your perfect trip! 🌟",
            "Let's make this an amazing vacation! ✨",
            "I can't wait to help you plan this adventure! 🧳",
            "This trip is going to be fantastic! 🗺️",
            "I'm thrilled to help with your travel plans! 🌈"
        ]
        
        base_response = random.choice(responses)
        
        # Personalize based on destination if we have it
        if destination:
            destination_responses = [
                f"{destination} is a wonderful choice! ",
                f"I love {destination}! ",
                f"{destination} is one of my favorite places! ",
                f"Great choice with {destination}! ",
                f"I think you'll love visiting {destination}! "
            ]
            base_response = random.choice(destination_responses)
        
        # Add the next question
        full_response = f"{base_response}{next_question}"
        
        return full_response
    
    def has_required_details(self, details):
        """Check if all required details are collected"""
        return all(details.get(field, "").strip() for field in self.required_fields)
