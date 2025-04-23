from .base_agent import BaseAgent
import json
import re

class DetailsAgent(BaseAgent):
    """
    Agent responsible for extracting and managing travel details
    from user conversations in a natural, unobtrusive way.
    """
    
    def __init__(self, openai_client=None):
        """Initialize the details gathering agent"""
        super().__init__(name="Details Agent", openai_client=openai_client)
        
        # Define the required trip details
        self.required_fields = [
            "Destination",
            "Duration",
            "Budget",
            "Dietary Preferences",
            "Mobility Concerns"
        ]
        
        # Define optional fields
        self.optional_fields = [
            "Season",
            "Activity Preferences",
            "Accommodation Type"
        ]
    
    def process(self, conversation_history, current_details=None):
        """
        Extract trip details from conversation history and
        determine the next questions to ask
        """
        if current_details is None:
            current_details = {field: "" for field in self.required_fields + self.optional_fields}
        
        # Extract details from conversation
        updated_details, confidence_scores = self._extract_details(conversation_history, current_details)
        
        # Determine what to ask next
        next_question, missing_fields = self._determine_next_question(updated_details)
        
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
    "Duration": "value",
    ...
  }},
  "confidence_scores": {{
    "Destination": 95,
    "Duration": 80,
    ...
  }}
}}
"""
        
        result = self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,  # Low temperature for factual extraction
            max_tokens=800
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
    
    def _determine_next_question(self, current_details):
        """Determine what information to ask for next"""
        # Check which required fields are missing
        missing_fields = [
            field for field in self.required_fields
            if not current_details.get(field, "").strip()
        ]
        
        if not missing_fields:
            # All required fields are filled
            return "All required information collected. You can say 'generate itinerary' whenever you're ready!", []
        
        # Get the first missing field
        next_field = missing_fields[0]
        
        # Create a question for the next field
        questions = {
            "Destination": "Where would you like to go for your trip?",
            "Duration": "How long are you planning to stay?",
            "Budget": "What's your budget for this trip? (e.g., economy, mid-range, luxury)",
            "Dietary Preferences": "Do you have any dietary preferences or restrictions I should know about?",
            "Mobility Concerns": "Do you have any mobility concerns or accessibility requirements?"
        }
        
        next_question = questions.get(next_field, f"Could you tell me about your {next_field.lower()}?")
        
        return next_question, missing_fields
    
    def _format_response(self, details, next_question, missing_fields):
        """Format a response with JSON data included"""
        # Create a friendly response
        if missing_fields:
            response_text = self._create_friendly_response(details, next_question)
        else:
            response_text = "Great! I now have all the essential information for your trip. Just say 'generate itinerary' whenever you're ready, and I'll create a detailed plan for your vacation! ✨"
        
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
        
        import random
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
