import requests
import json
from datetime import datetime
import openai
import streamlit as st
from bs4 import BeautifulSoup
import re

class DestinationResearchAgent:
    """
    Agent responsible for researching destination information in real-time
    from various online sources using web searches.
    """
    
    def __init__(self, openai_client=None):
        """Initialize the destination research agent with API clients"""
        self.openai_client = openai_client
        self.search_results_cache = {}
        
    def get_destination_info(self, destination):
        """Main method to gather comprehensive information about a destination"""
        if destination in self.search_results_cache:
            return self.search_results_cache[destination]
            
        # Format current date for API calls
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Perform web search to gather information
        search_results = self._perform_web_search(destination)
        
        # Use the OpenAI client to analyze and synthesize the search results
        destination_data = self._analyze_search_results(destination, search_results)
        
        # Cache the results
        self.search_results_cache[destination] = destination_data
        
        return destination_data
    
    def _perform_web_search(self, destination):
        """Perform a web search to find information about the destination"""
        try:
            # Using Bing Search API (you would need to replace with your implementation)
            # This is a placeholder - you'd need to implement the actual API call
            search_query = f"travel guide {destination} tourist attractions weather best time to visit"
            
            # For demo purposes, we'll just create mock search results
            # In production, replace with actual API calls to search engines
            mock_results = [
                {
                    "title": f"Travel Guide for {destination}",
                    "snippet": f"Complete travel guide for {destination}. Find the best attractions, hotels, and restaurants.",
                    "url": f"https://example.com/travel/{destination.lower().replace(' ', '-')}"
                },
                {
                    "title": f"Best Time to Visit {destination}",
                    "snippet": f"Learn about the weather and best seasons to visit {destination}. Includes monthly temperature averages.",
                    "url": f"https://example.com/best-time/{destination.lower().replace(' ', '-')}"
                },
                {
                    "title": f"Top 10 Attractions in {destination}",
                    "snippet": f"Discover the must-visit attractions in {destination} including historical sites, natural wonders, and cultural experiences.",
                    "url": f"https://example.com/attractions/{destination.lower().replace(' ', '-')}"
                }
            ]
            
            return mock_results
        except Exception as e:
            print(f"Error performing web search: {str(e)}")
            return []
    
    def _analyze_search_results(self, destination, search_results):
        """Use LLM to analyze search results and extract useful information"""
        try:
            if not self.openai_client:
                # Mock analysis if no API client is available
                return self._create_mock_destination_data(destination)
                
            # Prepare the search results for the LLM
            search_context = "\n\n".join([
                f"Title: {result['title']}\nContent: {result['snippet']}\nURL: {result['url']}"
                for result in search_results
            ])
            
            # Prompt the LLM to analyze the search results
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": "You are a travel research assistant. Analyze the search results and extract key information about the destination."},
                    {"role": "user", "content": f"Based on these search results about {destination}, provide a structured analysis with the following sections: Overview, Best Time to Visit, Top Attractions, Local Cuisine, Cultural Tips, and Safety Information. If certain information is missing, indicate that it's not available.\n\nSearch Results:\n{search_context}"}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            # Extract the content
            destination_info = response.choices[0].message.content
            
            # Format the data for return
            return {
                "destination": destination,
                "research_date": datetime.now().strftime("%Y-%m-%d"),
                "info": destination_info,
                "sources": [result["url"] for result in search_results]
            }
            
        except Exception as e:
            print(f"Error analyzing search results: {str(e)}")
            return self._create_mock_destination_data(destination)
    
    def _create_mock_destination_data(self, destination):
        """Create mock destination data when API calls fail"""
        return {
            "destination": destination,
            "research_date": datetime.now().strftime("%Y-%m-%d"),
            "info": f"""
# {destination} Travel Guide

## Overview
{destination} is known for its unique blend of culture, history, and natural beauty. Visitors can explore historical sites, enjoy local cuisine, and experience the local traditions.

## Best Time to Visit
The ideal time to visit {destination} is typically during spring (April-June) and fall (September-November) when the weather is pleasant and tourist crowds are smaller.

## Top Attractions
1. Historical Downtown
2. National Museum
3. Central Park
4. Cultural District
5. Local Markets

## Local Cuisine
The local food scene features a variety of traditional dishes including regional specialties. Don't miss trying the local street food and visiting the food markets.

## Cultural Tips
Respect local customs by dressing modestly when visiting religious sites. Learning a few phrases in the local language is appreciated by residents.

## Safety Information
{destination} is generally safe for tourists, but standard precautions are advised. Keep valuables secure and be aware of your surroundings, especially in crowded areas.
            """,
            "sources": [
                f"https://example.com/travel/{destination.lower().replace(' ', '-')}",
                f"https://example.com/best-time/{destination.lower().replace(' ', '-')}",
                f"https://example.com/attractions/{destination.lower().replace(' ', '-')}"
            ]
        }
    
    def get_current_weather(self, destination):
        """Get current weather information for the destination"""
        try:
            # This is a placeholder - you'd need to implement the actual API call
            # to a weather service like OpenWeatherMap or AccuWeather
            
            # For demo purposes, creating mock weather data
            weather_data = {
                "temperature": "24°C",
                "condition": "Partly Cloudy",
                "humidity": "65%",
                "wind": "10 km/h",
                "forecast": [
                    {"day": "Today", "temp": "24°C", "condition": "Partly Cloudy"},
                    {"day": "Tomorrow", "temp": "26°C", "condition": "Sunny"},
                    {"day": "Day After", "temp": "22°C", "condition": "Light Rain"}
                ]
            }
            
            return weather_data
        except Exception as e:
            print(f"Error fetching weather data: {str(e)}")
            return None
    
    def get_local_events(self, destination, start_date, end_date):
        """Get local events happening during the visit period"""
        try:
            # This is a placeholder - you'd need to implement the actual API call
            # to an events service like Eventbrite, Ticketmaster, etc.
            
            # For demo purposes, creating mock events data
            events_data = [
                {
                    "name": f"Annual {destination} Festival",
                    "date": "2025-05-15",
                    "venue": "City Center",
                    "description": "A celebration of local culture with music, food, and art.",
                    "ticket_info": "Tickets from $20, available online"
                },
                {
                    "name": "Local Food Fair",
                    "date": "2025-05-18",
                    "venue": "Central Park",
                    "description": "Sample the best of local cuisine from top restaurants and food vendors.",
                    "ticket_info": "Free entry"
                },
                {
                    "name": "Historical Walking Tour",
                    "date": "Daily",
                    "venue": "Tourist Information Center",
                    "description": "Guided walking tour of historical sites in the city.",
                    "ticket_info": "$15 per person, book in advance"
                }
            ]
            
            return events_data
        except Exception as e:
            print(f"Error fetching events data: {str(e)}")
            return []
    
    def get_travel_advisories(self, destination):
        """Get travel advisories and safety information for the destination"""
        try:
            # This is a placeholder - you'd need to implement the actual API call
            # to a travel advisory service or government website
            
            # For demo purposes, creating mock advisory data
            advisory_data = {
                "level": "Exercise Normal Precautions",
                "last_updated": "2025-03-15",
                "details": "No current travel advisories for this destination. Exercise normal precautions and be aware of your surroundings.",
                "health_info": "No major health concerns. Tap water is safe to drink in most areas.",
                "emergency_contacts": {
                    "police": "911",
                    "ambulance": "911",
                    "us_embassy": "+1-555-123-4567"
                }
            }
            
            return advisory_data
        except Exception as e:
            print(f"Error fetching advisory data: {str(e)}")
            return None
    
    def get_visa_requirements(self, destination, citizenship="US"):
        """Get visa requirements for travelers based on citizenship"""
        try:
            # This is a placeholder - you'd need to implement the actual API call
            # to a visa information service
            
            # For demo purposes, creating mock visa data
            visa_data = {
                "required": "No Visa Required for stays up to 90 days",
                "processing_time": "N/A",
                "cost": "N/A",
                "additional_info": "Passport must be valid for at least 6 months beyond intended stay."
            }
            
            return visa_data
        except Exception as e:
            print(f"Error fetching visa data: {str(e)}")
            return None
            
    def generate_destination_summary(self, destination_data, max_length=500):
        """Generate a concise summary of the destination data"""
        try:
            if not self.openai_client:
                # Return a section of the mock data if no API client
                info = destination_data.get("info", "")
                return info[:max_length] + "..." if len(info) > max_length else info
            
            # Use OpenAI to generate a summary
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": "You are a travel assistant providing concise destination summaries."},
                    {"role": "user", "content": f"Create a concise summary (maximum {max_length} characters) of this destination information:\n\n{destination_data['info']}"}
                ],
                max_tokens=250,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            # Fall back to a simple truncation
            info = destination_data.get("info", "")
            return info[:max_length] + "..." if len(info) > max_length else info
