"""
Logging Handlers for Email Automation Agent

This module contains classes for logging email interactions:
- LoggingHandler: Base class with common functionality
- GoogleSheetsLogger: For logging to Google Sheets
- CsvLogger: For logging to CSV files
"""

import os
import csv
import datetime
import logging
from typing import Dict
import configparser

# Google API Libraries
import gspread
from google.oauth2.service_account import Credentials

# Set up logging
logger = logging.getLogger(__name__)

class LoggingHandler:
    """Base class for logging email interactions"""
    
    def __init__(self, config: configparser.ConfigParser):
        self.config = config
    
    def log_interaction(self, email_data: Dict, reply_text: str, summary: str) -> bool:
        """Log the email interaction (to be implemented by subclasses)"""
        raise NotImplementedError("Subclasses must implement log_interaction")


class GoogleSheetsLogger(LoggingHandler):
    """Logger that appends interactions to a Google Sheet"""
    
    def __init__(self, config: configparser.ConfigParser):
        super().__init__(config)
        self.setup_sheets_api()
        
    def setup_sheets_api(self):
        """Set up the Google Sheets API client"""
        try:
            # Load credentials from the service account file
            credentials_path = self.config["GoogleSheets"]["credentials_path"]
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            
            credentials = Credentials.from_service_account_file(credentials_path, scopes=scope)
            self.client = gspread.authorize(credentials)
            
            # Open the spreadsheet
            spreadsheet_id = self.config["GoogleSheets"]["spreadsheet_id"]
            self.sheet = self.client.open_by_key(spreadsheet_id).sheet1
            
            logger.info("Google Sheets API initialized successfully")
            
            # Check if headers exist, if not add them
            if not self.sheet.row_values(1):
                headers = [
                    "Timestamp", "Sender", "Recipient", "Subject", 
                    "Original Email Snippet", "Generated Reply Snippet", 
                    "Full Summary of Interaction"
                ]
                self.sheet.append_row(headers)
                logger.info("Added headers to the Google Sheet")
                
        except Exception as e:
            logger.error(f"Error setting up Google Sheets API: {str(e)}")
            raise
    
    def log_interaction(self, email_data: Dict, reply_text: str, summary: str) -> bool:
        """Log the email interaction to Google Sheets"""
        try:
            # Prepare the row data
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            original_snippet = email_data["body"][:200] + "..." if len(email_data["body"]) > 200 else email_data["body"]
            reply_snippet = reply_text[:200] + "..." if len(reply_text) > 200 else reply_text
            
            row_data = [
                timestamp,
                email_data["sender"],
                email_data["recipient"],
                email_data["subject"],
                original_snippet,
                reply_snippet,
                summary
            ]
            
            # Append the row
            self.sheet.append_row(row_data)
            logger.info("Logged interaction to Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"Error logging to Google Sheets: {str(e)}")
            return False


class CsvLogger(LoggingHandler):
    """Logger that appends interactions to a CSV file"""
    
    def __init__(self, config: configparser.ConfigParser):
        super().__init__(config)
        self.csv_path = self.config["CSV"]["file_path"]
        
        # Create the file with headers if it doesn't exist
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                headers = [
                    "Timestamp", "Sender", "Recipient", "Subject", 
                    "Original Email Snippet", "Generated Reply Snippet", 
                    "Full Summary of Interaction"
                ]
                writer.writerow(headers)
                logger.info(f"Created new CSV log file at {self.csv_path}")
    
    def log_interaction(self, email_data: Dict, reply_text: str, summary: str) -> bool:
        """Log the email interaction to a CSV file"""
        try:
            # Prepare the row data
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            original_snippet = email_data["body"][:200] + "..." if len(email_data["body"]) > 200 else email_data["body"]
            reply_snippet = reply_text[:200] + "..." if len(reply_text) > 200 else reply_text
            
            row_data = [
                timestamp,
                email_data["sender"],
                email_data["recipient"],
                email_data["subject"],
                original_snippet,
                reply_snippet,
                summary
            ]
            
            # Append to the CSV file
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(row_data)
                
            logger.info(f"Logged interaction to CSV file: {self.csv_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging to CSV: {str(e)}")
            return False