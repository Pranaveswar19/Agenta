import openai
from abc import ABC, abstractmethod
from datetime import datetime
import streamlit as st

class BaseAgent(ABC):
    """
    Base class for all agents in the travel planner system.
    Provides common functionality and enforces an interface.
    """
    
    def __init__(self, name, openai_client=None):
        """Initialize the base agent"""
        self.name = name
        self.openai_client = openai_client
        self.cache = {}
        
    def log_activity(self, action, details=""):
        """Log agent activity for debugging and monitoring"""
        if "agent_logs" not in st.session_state:
            st.session_state.agent_logs = []
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "agent": self.name,
            "action": action,
            "details": details
        }
        
        st.session_state.agent_logs.append(log_entry)
        return log_entry
    
    def call_llm(self, system_prompt, user_prompt, model="gpt-3.5-turbo-0125", temperature=0.7, max_tokens=800):
        """Standardized method to call the OpenAI API"""
        if not self.openai_client:
            self.log_activity("Error", "No OpenAI client available")
            return "I'm unable to process this request without an API connection."
        
        try:
            self.log_activity("LLM Call", f"Using model: {model}")
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            content = response.choices[0].message.content
            return content
            
        except Exception as e:
            error_msg = str(e)
            self.log_activity("API Error", error_msg)
            return f"I encountered an error: {error_msg}"
    
    @abstractmethod
    def process(self, input_data):
        """
        Process the input data and return results.
        This method must be implemented by all agent subclasses.
        """
        pass
