"""
Email Assistant for Email Automation Agent

This module handles the AI-powered email response generation using Google Gemini
"""

import logging
from typing import Dict
import configparser
from google import genai

# Set up logging
logger = logging.getLogger(__name__)

class EmailAssistant:
    """Core class for email processing using Google Gemini"""

    def __init__(self, config: configparser.ConfigParser):
        self.config = config
        self.setup_llm()

    def setup_llm(self):
        """Initialize the Google Gemini API with client approach"""
        llm_provider = self.config["LLM"]["provider"].lower()

        if llm_provider == "google":
            api_key = self.config["LLM"]["api_key"]
            self.model_name = self.config["LLM"]["model_name"]

            # Initialize the client
            self.client = genai.Client(api_key=api_key)

            logger.info(f"Initialized {self.model_name} from Google Gemini")

        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

    def generate_reply(self, email_data: Dict) -> str:
        """Generate a reply to the email using Google Gemini client"""
        try:
            # Extract the persona from config or use default
            assistant_persona = self.config.get("Assistant", "persona", fallback="A helpful, professional assistant")

            # Create prompt
            prompt = f"""
            You are an AI assistant managing emails with the following persona: {assistant_persona}

            You've received the following email:
            From: {email_data["sender"]}
            Subject: {email_data["subject"]}

            Body:
            {email_data["body"]}

            Draft a polite and helpful reply that addresses the content of the email.
            If it's a simple query you can answer, do so thoroughly.
            If it's complex or requires human intervention, politely acknowledge the email and state that it will be forwarded to the appropriate person.
            Be concise but friendly in your response.
            """

            # Generate content using correct parameter format
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )

            logger.info("Generated reply using Google Gemini")
            return response.text

        except Exception as e:
            logger.error(f"Error generating reply: {str(e)}")
            return (
                "Thank you for your email. I'm experiencing technical difficulties processing your request at the moment. "
                "A team member will review your message and respond as soon as possible."
            )

    def generate_summary(self, email_data: Dict, reply_text: str) -> str:
        """Generate a summary of the email interaction"""
        try:
            # Create summary prompt
            prompt = f"""
            Summarize this email interaction concisely. Extract key points only.

            Original Email Subject: {email_data["subject"]}
            Original Email: {email_data["body"]}

            Reply Sent: {reply_text}

            Summary:
            """

            # Generate summary with correct parameter format
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )

            logger.info("Generated summary using Google Gemini")
            return response.text

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return f"Interaction regarding: {email_data['subject']}"