from .base_agent import BaseAgent
import requests
from datetime import datetime, timedelta
import json
import re

class DestinationAgent(BaseAgent):
    """
    Agent responsible for researching destination information
    and providing relevant travel insights.
    """
    
    def __init__(self, openai_client=None):
        """Initialize the destination agent"""
        super().__init__(name="Destination Agent", openai_client=openai_client)
    
    def process(self, destination):
        """Process destination research request"""
        if not destination:
            return None
            
        # Normalize destination name
        destination = destination.strip()
        
        # Check cache first
        if destination in self.cache:
            self.log_activity("Cache Hit", f"Using cached data for {destination}")
            return self.cache[destination]
        
        self.log_activity("Research", f"Researching {destination}")
        
        # Gather destination information
        destination_data = self._research_destination(destination)
        weather_data = self._get_weather(destination)
        events_data = self._get_local_events(destination)
        advisory_data = self._get_travel_advisories(destination)
        
        # Compile all data
        full_data = {
            "destination": destination,
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "overview": destination_data,
            "weather": weather_data,
            "events": events_data,
            "advisories": advisory_data
        }
        
        # Save to cache
        self.cache[destination] = full_data
        
        return full_data
    
    def _research_destination(self, destination):
        """Research destination information using LLM"""
        system_prompt = """You are a travel research specialist with extensive knowledge about global destinations.
        Provide comprehensive, factual information about the requested destination.
        Structure your response in markdown format with these sections:
        1. Overview - Brief introduction to the destination
        2. Best Time to Visit - Seasonal information and weather patterns
        3. Top Attractions - Must-see places and experiences
        4. Local Cuisine - Notable food and dining recommendations
        5. Cultural Etiquette - Important customs and practices
        6. Transportation - How to get around the destination
        
        Keep your response factual, organized, and helpful for travelers planning a visit.
        """
        
        user_prompt = f"""Research the travel destination: {destination}
        
        Please provide detailed information that would help a traveler plan their trip.
        Include specific attractions, seasonal recommendations, and practical tips.
        """
        
        result = self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,  # Lower temperature for more factual responses
            max_tokens=1000
        )
        
        return result
    
    def _get_weather(self, destination):
        """Get weather information for the destination"""
        # In a production app, connect to a weather API
        # For now, using mock data and LLM
        
        system_prompt = """You are a weather information specialist.
        Create a realistic current weather report and 5-day forecast for the specified destination.
        Use plausible temperature ranges and weather conditions based on the destination's typical climate.
        Format your response as JSON with these fields:
        {
            "current": {"temp": "23°C", "condition": "Partly Cloudy", "humidity": "65%"},
            "forecast": [
                {"day": "Today", "temp_high": "24°C", "temp_low": "18°C", "condition": "Partly Cloudy"},
                {"day": "Tomorrow", "temp_high": "26°C", "temp_low": "19°C", "condition": "Sunny"},
                ...
            ]
        }
        """
        
        user_prompt = f"Create a realistic weather forecast for {destination} for today's date ({datetime.now().strftime('%Y-%m-%d')})."
        
        result = self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.4,
            max_tokens=500
        )
        
        # Extract JSON from the response
        try:
            # Find JSON in the response
            json_match = re.search(r'({[\s\S]*})', result)
            if json_match:
                weather_data = json.loads(json_match.group(1))
                return weather_data
            return {"error": "Could not parse weather data"}
        except Exception as e:
            self.log_activity("Error", f"Weather data parsing error: {str(e)}")
            return {"error": str(e)}
    
    def _get_local_events(self, destination):
        """Get local events for the destination"""
        # In a production app, connect to an events API
        # For now, using mock data and LLM
        
        # Calculate date range (next 30 days)
        today = datetime.now()
        end_date = today + timedelta(days=30)
        
        system_prompt = """You are an events research specialist.
        Create a list of realistic, plausible upcoming events for the specified destination.
        Include cultural festivals, concerts, exhibitions, and local celebrations that would be relevant for tourists.
        Format your response as JSON with an array of event objects:
        [
            {
                "name": "Annual Food Festival",
                "date": "2025-05-15",
                "venue": "City Center",
                "category": "Food",
                "description": "A celebration of local cuisine with food stalls and chef demonstrations",
                "ticket_info": "Free entry"
            },
            ...
        ]
        Include 3-5 realistic events with varied dates within the next month.
        """
        
        user_prompt = f"""Create a list of realistic upcoming events in {destination} between {today.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}.
        Focus on events that would interest tourists."""
        
        result = self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,  # Higher temperature for creative event ideas
            max_tokens=800
        )
        
        # Extract JSON from the response
        try:
            # Find JSON in the response
            json_match = re.search(r'(\[[\s\S]*\])', result)
            if json_match:
                events_data = json.loads(json_match.group(1))
                return events_data
            return []
        except Exception as e:
            self.log_activity("Error", f"Events data parsing error: {str(e)}")
            return []
    
    def _get_travel_advisories(self, destination):
        """Get travel advisories for the destination"""
        # In a production app, connect to a travel advisory API
        # For now, using mock data and LLM
        
        system_prompt = """You are a travel safety specialist.
        Create a realistic travel advisory for the specified destination.
        Include information about safety, health concerns, and entry requirements.
        Format your response as JSON with these fields:
        {
            "overall_risk": "Low/Medium/High",
            "safety_info": "...",
            "health_info": "...",
            "entry_requirements": "...",
            "emergency_contacts": {"police": "...", "ambulance": "...", "embassy": "..."}
        }
        Base your advisory on realistic conditions for the destination.
        """
        
        user_prompt = f"Create a realistic travel advisory for {destination} as of {datetime.now().strftime('%Y-%m-%d')}."
        
        result = self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.4,
            max_tokens=500
        )
        
        # Extract JSON from the response
        try:
            # Find JSON in the response
            json_match = re.search(r'({[\s\S]*})', result)
            if json_match:
                advisory_data = json.loads(json_match.group(1))
                return advisory_data
            return {"error": "Could not parse advisory data"}
        except Exception as e:
            self.log_activity("Error", f"Advisory data parsing error: {str(e)}")
            return {"error": str(e)}
    
    def get_destination_summary(self, destination_data, max_length=300):
        """Generate a concise summary of destination research"""
        if not destination_data:
            return ""
            
        if "overview" in destination_data:
            # Extract first paragraph or section from the overview
            overview = destination_data["overview"]
            # Find the first major section break
            first_section_end = overview.find("\n## ")
            if first_section_end > 0:
                summary = overview[:first_section_end].strip()
            else:
                # Just take the first few paragraphs
                paragraphs = overview.split("\n\n")
                summary = paragraphs[0]
                if len(paragraphs) > 1:
                    summary += "\n\n" + paragraphs[1]
            
            # Truncate if too long
            if len(summary) > max_length:
                summary = summary[:max_length] + "..."
                
            return summary
        
        return ""
