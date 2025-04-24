def _determine_next_question(self, current_details, conversation_history):
    """
    Determine what information to ask for next using a dynamic chain prompt approach.
    Generates contextually appropriate, natural-sounding questions based on:
    - Current conversation flow
    - Already collected information
    - The specific information still needed
    - Current date and time
    - User's profile
    """
    # Check if all required fields are filled
    missing_required = [field for field in self.required_fields if not current_details.get(field, "").strip()]
    
    # If all required fields are filled, we can encourage itinerary generation
    if not missing_required:
        return "Great! I have all the essential information I need to create your personalized itinerary. Just say 'generate itinerary' and I'll create a detailed plan for your trip! ✨", []
    
    # Determine which tier to focus on
    missing_tier1 = [field for field in self.tier1_fields if not current_details.get(field, "").strip()]
    missing_tier2 = [field for field in self.tier2_fields if not current_details.get(field, "").strip()]
    missing_tier3 = [field for field in self.tier3_fields if not current_details.get(field, "").strip()]
    
    # Convert conversation history to string format for the LLM
    # Focus on recent messages for better context
    recent_messages = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
    conversation_text = "\n".join([
        f"{message['role'].upper()}: {message['content']}"
        for message in recent_messages
        if message['role'] in ['user', 'assistant']
    ])
    
    # Current date and time - use the provided value
    current_datetime = "2025-04-24 08:53:45"  
    
    # Current user information
    current_user = "Pranaveswar19"
    
    # Prepare the current details as JSON with better formatting for readability
    current_details_pretty = {}
    for key, value in current_details.items():
        if value.strip():  # Only include non-empty values
            current_details_pretty[key] = value
    
    current_details_json = json.dumps(current_details_pretty, indent=2)
    
    # Determine which missing field to focus on
    if missing_tier1:
        target_field = missing_tier1[0]
        field_importance = "essential"
        priority_level = "high"
    elif missing_tier2:
        target_field = missing_tier2[0]
        field_importance = "important"
        priority_level = "medium"
    elif missing_tier3:
        target_field = missing_tier3[0]
        field_importance = "helpful"
        priority_level = "low"
    else:
        # If we've covered tiers 1-3, move to tier 4 or pick a random missing optional field
        remaining_missing = [field for field in self.optional_fields 
                            if field not in self.tier1_fields + self.tier2_fields + self.tier3_fields 
                            and not current_details.get(field, "").strip()]
        if remaining_missing:
            target_field = remaining_missing[0]
            field_importance = "additional"
            priority_level = "very low"
        else:
            # Fallback - shouldn't reach here if all required fields check worked
            return "I think we have all the information we need! Would you like me to generate your itinerary now?", []
    
    # Prepare the system prompt for chain prompting
    system_prompt = f"""You are a travel planning expert named Pranav who excels at gathering information in a conversational way.
    Your goal is to formulate the next best question to ask the user to gather essential travel information.
    The question should flow naturally from the conversation and not feel like a generic form question.
    Make your questions engaging, personalized, and contextually relevant.
    
    You're currently helping user: {current_user}
    Current date and time: {current_datetime}
    
    The next information you need is the user's "{target_field.replace('_', ' ')}".
    This is {field_importance} information with {priority_level} priority.
    
    Guidelines for your question:
    - Make it sound natural and conversational, not like a form field
    - Reference previously collected information when relevant
    - Ask for only ONE piece of information at a time
    - Be specific but friendly
    - If asking about dates, encourage specific dates rather than vague timeframes
    - If asking about travelers, try to understand the group composition
    - If asking about budget, help users understand their options clearly
    
    Your tone should be:
    - Friendly and enthusiastic
    - Helpful not pushy
    - Knowledgeable but accessible
    - Personalized to what you know about the trip so far
    """
    
    # Prepare the user prompt for chain prompting
    user_prompt = f"""Current trip details:
{current_details_json}

Recent conversation:
{conversation_text}

Generate a single, natural-sounding question to ask about the user's "{target_field.replace('_', ' ')}".
The question must fit naturally into the conversation flow and not feel like a survey.
Use what you already know about their trip to personalize the question.

Return ONLY the question you would ask the user, nothing else.
"""
    
    # Call the LLM to generate the next question
    next_question = self.call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.7,  # Higher temperature for more varied, natural responses
        max_tokens=150
    )
    
    # Clean up the response - remove any explanation text, quotation marks, etc.
    next_question = re.sub(r'^("|\')', '', next_question.strip())
    next_question = re.sub(r'("|\')\s*$', '', next_question.strip())
    
    # Check if the response is a proper question
    if not next_question.endswith('?'):
        # Attempt to extract just the question if there's explanation text
        question_match = re.search(r'([^.!?]+\?)', next_question)
        if question_match:
            next_question = question_match.group(1).strip()
    
    # Add contextual emojis for a friendly touch if the question doesn't already have one
    if not any(emoji in next_question for emoji in ['🌍', '✈️', '🏨', '🍽️', '🧳', '🗺️', '🌴', '🏖️', '🎭', '🚗']):
        field_emojis = {
            'Destination': '🌍',
            'Origin': '🏙️',
            'Duration': '📅',
            'Travel_Dates': '🗓️',
            'Travelers_Count': '👥',
            'Travelers_Type': '👨‍👩‍👧‍👦',
            'Budget': '💰',
            'Dietary_Preferences': '🍽️',
            'Mobility_Concerns': '♿',
            'Transportation_Preferences': '🚗',
            'Accommodation_Type': '🏨',
            'Purpose_Of_Trip': '🎯',
            'Must_See_Attractions': '🗿',
            'Weather_Preferences': '☀️',
            'Shopping_Interests': '🛍️',
            'Special_Occasions': '🎉'
        }
        
        emoji = field_emojis.get(target_field, '✨')
        next_question = f"{next_question} {emoji}"
    
    # Return the next question and list of all missing required fields
    return next_question, missing_required
