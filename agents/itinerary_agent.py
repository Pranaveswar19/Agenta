from .base_agent import BaseAgent
import json
from datetime import datetime, timedelta

class ItineraryAgent(BaseAgent):
    """
    Agent responsible for creating the overall structure and flow
    of a travel itinerary based on destination research and user preferences.
    """
    
    def __init__(self, openai_client=None):
        """Initialize the itinerary structure agent"""
        super().__init__(name="Itinerary Agent", openai_client=openai_client)
    
    def process(self, trip_details, destination_data=None):
        """Generate a structured itinerary based on trip details and destination data"""
        if not self._validate_input(trip_details):
            return "Insufficient details to generate an itinerary."
            
        self.log_activity("Generating", f"Creating itinerary for {trip_details.get('Destination', 'unknown')}")
        
        # Extract key details
        destination = trip_details.get("Destination", "")
        duration_text = trip_details.get("Duration", "")
        budget = trip_details.get("Budget", "")
        dietary = trip_details.get("Dietary Preferences", "")
        mobility = trip_details.get("Mobility Concerns", "")
        
        # Parse duration to get number of days
        days = self._parse_duration(duration_text)
        if days <= 0:
            days = 3  # Default if parsing fails
        
        # Generate itinerary overview
        overview = self._generate_overview(trip_details, destination_data)
        
        # Generate day-by-day structure
        day_plans = self._generate_day_plans(trip_details, destination_data, days)
        
        # Generate practical information section
        practical_info = self._generate_practical_info(trip_details, destination_data)
        
        # Assemble full itinerary
        full_itinerary = f"""
# Your {days}-Day Adventure in {destination} ✈️

## Trip Overview
{overview}

---

{day_plans}

---

{practical_info}

---

*This itinerary was created on {datetime.now().strftime('%Y-%m-%d')} based on current travel information.*
"""
        
        return full_itinerary
    
    def _validate_input(self, trip_details):
        """Validate that we have enough information to create an itinerary"""
        required_fields = ["Destination", "Duration"]
        return all(trip_details.get(field, "").strip() for field in required_fields)
    
    def _parse_duration(self, duration_text):
        """Parse duration text to extract number of days"""
        if not duration_text:
            return 3  # Default value
            
        # Try to extract a number from the text
        import re
        numbers = re.findall(r'\d+', duration_text)
        if numbers:
            return int(numbers[0])
            
        # Handle text-based durations
        duration_lower = duration_text.lower()
        if "week" in duration_lower:
            # Handle "a week", "one week", etc.
            if any(x in duration_lower for x in ["a", "one", "1"]):
                return 7
            # Handle "two weeks", "2 weeks"
            if any(x in duration_lower for x in ["two", "2"]):
                return 14
            # Handle "three weeks", "3 weeks"
            if any(x in duration_lower for x in ["three", "3"]):
                return 21
        
        # Handle "weekend", "long weekend"
        if "weekend" in duration_lower:
            if "long" in duration_lower:
                return 3
            return 2
            
        return 3  # Default value
    
    def _generate_overview(self, trip_details, destination_data):
        """Generate an overview of the trip"""
        destination = trip_details.get("Destination", "")
        duration = trip_details.get("Duration", "")
        budget = trip_details.get("Budget", "")
        
        # Use destination data if available
        destination_summary = ""
        if destination_data and "overview" in destination_data:
            # Get just the first section
            overview = destination_data["overview"]
            first_section_end = overview.find("\n## ")
            if first_section_end > 0:
                destination_summary = overview[:first_section_end].strip()
        
        system_prompt = """You are a travel planner creating an engaging overview section for a trip itinerary.
        Write a concise but informative summary of the trip, highlighting what makes this destination special.
        Include practical information based on the budget level and duration.
        Format your response in markdown with appropriate styling.
        """
        
        destination_info = f"Destination Information:\n{destination_summary}" if destination_summary else ""
        
        user_prompt = f"""Create an overview section for a {duration} trip to {destination} with a {budget} budget.
        
        {destination_info}
        
        Keep it concise (200-300 words) but exciting and informative, highlighting the key experiences and what makes this trip special.
        """
        
        overview = self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=500
        )
        
        return overview
    
    def _generate_day_plans(self, trip_details, destination_data, days):
        """Generate day-by-day structure for the itinerary"""
        destination = trip_details.get("Destination", "")
        budget = trip_details.get("Budget", "")
        dietary = trip_details.get("Dietary Preferences", "")
        mobility = trip_details.get("Mobility Concerns", "")
        
        # Extract top attractions if available
        attractions = []
        if destination_data and "overview" in destination_data:
            overview = destination_data["overview"]
            attractions_section = self._extract_section(overview, "Top Attractions")
            if attractions_section:
                # Simple extraction of list items
                import re
                attractions = re.findall(r'\d+\.\s+(.*?)(?=\n|$)', attractions_section)
        
        attractions_text = "\n".join([f"- {attraction}" for attraction in attractions]) if attractions else ""
        
        # Create individual day plans
        day_plans = []
        
        for day in range(1, days + 1):
            # Create a theme for each day
            if day == 1:
                theme = "Orientation & Key Highlights"
            elif day == days:
                theme = "Final Explorations & Favorites"
            else:
                # For middle days, create themed days
                themes = [
                    "Cultural Immersion",
                    "Natural Beauty",
                    "Local Experiences",
                    "Historical Discovery",
                    "Culinary Adventure",
                    "Relaxation & Leisure",
                    "Off the Beaten Path"
                ]
                import random
                theme = themes[(day + hash(destination)) % len(themes)]
            
            system_prompt = """You are a travel planner creating a detailed day plan for a vacation itinerary.
            Structure your response with Morning, Afternoon, and Evening sections.
            Include specific venues with realistic names, times, and practical details.
            Format in markdown with clear headings and bullet points.
            Ensure activities flow logically with appropriate travel time between locations.
            """
            
            user_prompt = f"""Create a detailed Day {day} itinerary for a trip to {destination} with theme: "{theme}".
            
            Trip details:
            - Budget level: {budget}
            - Dietary preferences: {dietary}
            - Mobility concerns: {mobility}
            
            Suggested attractions:
            {attractions_text}
            
            Include:
            1. A morning activity with breakfast recommendation
            2. Lunch at a specific venue appropriate to the budget level
            3. Afternoon activities
            4. Dinner recommendation
            5. Evening activity or relaxation
            
            For each place mentioned, include:
            - Name and brief description
            - Approximate timings
            - Price range indicator ($ to $$$)
            - Any special notes or tips
            """
            
            day_plan = self.call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=1000
            )
            
            day_plans.append(f"## Day {day}: {theme}\n\n{day_plan}")
        
        return "\n\n---\n\n".join(day_plans)
    
    def _generate_practical_info(self, trip_details, destination_data):
        """Generate practical information section"""
        destination = trip_details.get("Destination", "")
        
        # Extract relevant data from destination research
        weather_info = ""
        if destination_data and "weather" in destination_data:
            weather = destination_data["weather"]
            if isinstance(weather, dict) and "current" in weather and "forecast" in weather:
                weather_info = f"""
### Weather Forecast
Current: {weather['current'].get('temp', 'N/A')}, {weather['current'].get('condition', 'N/A')}
                
Forecast:
"""
                for day in weather['forecast'][:3]:
                    weather_info += f"- {day.get('day', 'N/A')}: {day.get('temp_high', 'N/A')}/{day.get('temp_low', 'N/A')}, {day.get('condition', 'N/A')}\n"
        
        # Extract advisory information
        advisory_info = ""
        if destination_data and "advisories" in destination_data:
            advisory = destination_data["advisories"]
            if isinstance(advisory, dict):
                advisory_info = f"""
### Travel Advisory
Risk Level: {advisory.get('overall_risk', 'No data')}

{advisory.get('safety_info', 'No safety information available.')}

Health Information:
{advisory.get('health_info', 'No health information available.')}

Entry Requirements:
{advisory.get('entry_requirements', 'Check with local embassy for entry requirements.')}
"""
        
        # Generate transportation and packing information
        system_prompt = """You are a travel planning assistant providing practical information for a trip.
        Create a concise section with essential practical tips including:
        1. Local transportation options
        2. Packing recommendations
        3. Money and tipping customs
        4. Essential phrases if applicable
        5. Emergency contacts and safety tips
        
        Format your response in clear markdown with appropriate headings and bullet points.
        """
        
        user_prompt = f"""Create a practical information section for a trip to {destination}.
        Include transportation options, packing tips, money handling advice, useful phrases,
        and any other practical information travelers should know.
        Keep it concise but comprehensive.
        """
        
        practical_tips = self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=800
        )
        
        # Combine all practical information
        practical_info = f"""
## Practical Information

{weather_info}

{advisory_info}

{practical_tips}
"""
        
        return practical_info
    
    def _extract_section(self, text, section_title):
        """Extract a specific section from markdown text"""
        import re
        pattern = rf"## {section_title}(.*?)(?=\n## |$)"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
