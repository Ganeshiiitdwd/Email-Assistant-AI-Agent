"""
Email Automation Agent - Main Application Runner

This script orchestrates the email automation workflow by integrating:
- Configuration management
- Email processing (Gmail or IMAP)
- AI-powered email assistant
- Interaction logging

Usage:
    python agent.py [--config CONFIG_PATH] [--single-run] [--interval SECONDS]
"""

import os
import time
import argparse
import logging
from typing import Dict, Optional

# Import modular components
from config_manager import load_config
from email_processors import GmailProcessor, ImapProcessor
from email_assistant import EmailAssistant
from logging_handlers import GoogleSheetsLogger, CsvLogger

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='email_agent.log'
)
logger = logging.getLogger(__name__)

class EmailAutomationAgent:
    """Main application class that orchestrates the email automation workflow"""
    
    def __init__(self, config_path: str = "config.ini"):
        """Initialize the agent with the specified configuration"""
        self.config = load_config(config_path)
        self.setup_components()
        
    def setup_components(self):
        """Initialize all components based on configuration"""
        # Set up email processor
        email_type = self.config["Email"]["type"].lower()
        if email_type == "gmail":
            self.email_processor = GmailProcessor(self.config)
        elif email_type == "imap":
            self.email_processor = ImapProcessor(self.config)
        else:
            raise ValueError(f"Unsupported email type: {email_type}")
            
        # Set up assistant
        self.assistant = EmailAssistant(self.config)
        
        # Set up logger
        logging_type = self.config["Logging"]["type"].lower()
        if logging_type == "googlesheets":
            self.logger = GoogleSheetsLogger(self.config)
        elif logging_type == "csv":
            self.logger = CsvLogger(self.config)
        else:
            raise ValueError(f"Unsupported logging type: {logging_type}")
    
    def process_single_email(self) -> bool:
        """Process just the latest unread email"""
        # Fetch the latest unread email
        email_data = self.email_processor.fetch_latest_unread_email()
        
        if not email_data:
            logger.info("No emails to process at this time")
            return False
            
        logger.info(f"Processing email: {email_data['subject']} from {email_data['sender']}")
        
        # Generate reply
        reply_text = self.assistant.generate_reply(email_data)
        
        # Send the reply
        if not self.email_processor.send_reply(email_data, reply_text):
            logger.error("Failed to send reply, aborting processing")
            return False
            
        # Generate summary
        summary = self.assistant.generate_summary(email_data, reply_text)
        
        # Log the interaction
        self.logger.log_interaction(email_data, reply_text, summary)
        
        logger.info("Email processed successfully")
        return True
    
    def run_once(self) -> bool:
        """Run the agent once to process a single email"""
        try:
            return self.process_single_email()
        except Exception as e:
            logger.error(f"Error in processing cycle: {str(e)}")
            return False
    
    def run(self, interval_seconds: int = 60, single_run: bool = False):
        """Run the agent in a loop or once based on configuration"""
        try:
            logger.info("Starting Email Automation Agent")
            
            if single_run:
                self.run_once()
                logger.info("Single run completed")
                return
                
            while True:
                logger.info(f"Checking for new emails...")
                self.run_once()
                logger.info(f"Sleeping for {interval_seconds} seconds...")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("Agent stopped by user")
        except Exception as e:
            logger.error(f"Unhandled error in main loop: {str(e)}")
        finally:
            # Clean up resources
            if hasattr(self.email_processor, 'disconnect'):
                self.email_processor.disconnect()
            logger.info("Email Automation Agent shut down")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Email Automation Agent")
    parser.add_argument("--config", default="config.ini", 
                        help="Path to configuration file (default: config.ini)")
    parser.add_argument("--single-run", action="store_true", 
                        help="Run once and exit (default: continuous run)")
    parser.add_argument("--interval", type=int, default=300, 
                        help="Check interval in seconds for continuous mode (default: 300)")
    return parser.parse_args()


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    try:
        # Create and run the agent
        agent = EmailAutomationAgent(args.config)
        agent.run(interval_seconds=args.interval, single_run=args.single_run)
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        print(f"Error: {str(e)}")
        exit(1)