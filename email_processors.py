"""
Email Processors for Email Automation Agent

This module contains classes for processing emails through different providers:
- EmailProcessor: Base class with common functionality
- GmailProcessor: Gmail API specific implementation
- ImapProcessor: Generic IMAP/SMTP implementation
"""

import os
import base64
import re
import pickle
import logging
from typing import Dict, List, Optional, Tuple, Any
import configparser

# Email Libraries
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header

# Google API Libraries
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as GoogleCredentials

# Set up logging
logger = logging.getLogger(__name__)

class EmailProcessor:
    """Base class for email processing functionality"""
    
    def __init__(self, config: configparser.ConfigParser):
        self.config = config
        self.processed_emails = set()  # Track processed emails to avoid loops
        
    def mark_as_processed(self, email_id: str):
        """Mark an email as processed to prevent reply loops"""
        self.processed_emails.add(email_id)
        
    def is_processed(self, email_id: str) -> bool:
        """Check if an email has already been processed"""
        return email_id in self.processed_emails
        
    def should_process_email(self, email_data: Dict) -> bool:
        """Determine if an email should be processed based on filtering rules"""
        # Skip emails from no-reply addresses
        if "no-reply" in email_data["sender"].lower() or "noreply" in email_data["sender"].lower():
            return False
            
        # Skip if this is already a reply (contains Re: or FWD:)
        if re.match(r'^(re:|fwd:)', email_data["subject"].lower()):
            # Check if it's not from us (avoid reply loops)
            if self.config["Email"]["email_address"] not in email_data["sender"]:
                # It's a reply but not from us, so we can process it
                pass
            else:
                # It's a reply from us, don't process
                return False
                
        # Skip mailing lists (often have List-Id header)
        if email_data.get("list_id"):
            return False
            
        # Skip if "no-auto-reply" or similar is in the subject
        if any(x in email_data["subject"].lower() for x in ["no-auto-reply", "no-auto", "human-only"]):
            return False
            
        return True


class GmailProcessor(EmailProcessor):
    """Gmail-specific email processing using the Gmail API"""
    
    def __init__(self, config: configparser.ConfigParser):
        super().__init__(config)
        self.setup_gmail_api()
        
    def setup_gmail_api(self):
        """Set up the Gmail API client"""
        SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
        creds = None
        token_path = self.config["Gmail"]["token_path"]
        credentials_path = self.config["Gmail"]["credentials_path"]
        
        # Check for existing token
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
                
        # If no valid credentials are available, ask the user to log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                
            # Save the credentials for the next run
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
                
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API initialized successfully")
        
    def fetch_latest_unread_email(self) -> Optional[Dict]:
        """Fetch only the latest unread email from Gmail"""
        try:
            # Query for unread messages in the inbox
            results = self.service.users().messages().list(
                userId='me', 
                labelIds=['INBOX', 'UNREAD'],
                maxResults=1  # Just get the latest email
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                logger.info("No new emails found")
                return None
                
            # Get the latest message
            message = messages[0]
            msg_id = message['id']
            
            # Skip if already processed
            if self.is_processed(msg_id):
                logger.info(f"Email {msg_id} already processed, skipping")
                return None
                
            # Get the message details
            msg = self.service.users().messages().get(userId='me', id=msg_id).execute()
            
            email_data = {
                "id": msg_id,
                "threadId": msg['threadId'],
                "sender": "",
                "recipient": self.config["Email"]["email_address"],
                "subject": "",
                "body": "",
                "date": "",
                "list_id": None
            }
            
            # Extract headers (From, Subject, Date)
            headers = msg['payload']['headers']
            for header in headers:
                name = header['name'].lower()
                if name == 'from':
                    email_data["sender"] = header['value']
                elif name == 'subject':
                    email_data["subject"] = header['value']
                elif name == 'date':
                    email_data["date"] = header['value']
                elif name == 'list-id':
                    email_data["list_id"] = header['value']
            
            # Extract message body
            if 'parts' in msg['payload']:
                for part in msg['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = part['body'].get('data', '')
                        if body:
                            decoded_bytes = base64.urlsafe_b64decode(body)
                            email_data["body"] = decoded_bytes.decode('utf-8')
                            break
            elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                body = msg['payload']['body']['data']
                decoded_bytes = base64.urlsafe_b64decode(body)
                email_data["body"] = decoded_bytes.decode('utf-8')
            
            # Apply filtering logic
            if self.should_process_email(email_data):
                return email_data
            else:
                logger.info(f"Email {msg_id} filtered out based on rules")
                self.mark_as_processed(msg_id)  # Mark as processed to skip next time
                return None
                
        except Exception as e:
            logger.error(f"Error fetching email: {str(e)}")
            return None
            
    def send_reply(self, email_data: Dict, reply_text: str) -> bool:
        """Send a reply to an email using the Gmail API"""
        try:
            message = MIMEMultipart()
            message['to'] = email_data["sender"]
            message['subject'] = f"Re: {email_data['subject']}"
            message['In-Reply-To'] = email_data["id"]
            message['References'] = email_data["threadId"]
            message.attach(MIMEText(reply_text, 'plain'))
            
            # Encode the message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Create the message
            created_message = self.service.users().messages().send(
                userId='me',
                body={'raw': encoded_message, 'threadId': email_data["threadId"]}
            ).execute()
            
            # Mark the original email as read
            self.service.users().messages().modify(
                userId='me', 
                id=email_data["id"],
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            # Mark as processed to prevent loops
            self.mark_as_processed(email_data["id"])
            
            logger.info(f"Reply sent successfully: {created_message['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending reply: {str(e)}")
            return False


class ImapProcessor(EmailProcessor):
    """IMAP-based email processing for generic email servers"""
    
    def __init__(self, config: configparser.ConfigParser):
        super().__init__(config)
        self.imap_server = None
        self.smtp_server = None
        self.connect_to_servers()
        
    def connect_to_servers(self):
        """Connect to IMAP and SMTP servers"""
        try:
            # Connect to IMAP server
            self.imap_server = imaplib.IMAP4_SSL(
                self.config["IMAP"]["host"], 
                int(self.config["IMAP"]["port"])
            )
            self.imap_server.login(
                self.config["Email"]["email_address"], 
                self.config["Email"]["password"]
            )
            logger.info("Connected to IMAP server")
            
            # Connect to SMTP server
            self.smtp_server = smtplib.SMTP_SSL(
                self.config["SMTP"]["host"], 
                int(self.config["SMTP"]["port"])
            )
            self.smtp_server.login(
                self.config["Email"]["email_address"], 
                self.config["Email"]["password"]
            )
            logger.info("Connected to SMTP server")
            
        except Exception as e:
            logger.error(f"Error connecting to email servers: {str(e)}")
            raise
    
    def fetch_latest_unread_email(self) -> Optional[Dict]:
        """Fetch only the latest unread email from the IMAP server"""
        try:
            # Select the inbox
            self.imap_server.select('INBOX')
            
            # Search for unread emails
            status, messages = self.imap_server.search(None, 'UNSEEN')
            
            if status != 'OK':
                logger.warning("Failed to search for emails")
                return None
            
            email_ids = messages[0].split()
            
            if not email_ids:
                logger.info("No unread emails found")
                return None
            
            # Get the latest email (last in the list)
            latest_email_id = email_ids[-1]
            email_id_str = latest_email_id.decode('utf-8')
            
            # Skip if already processed
            if self.is_processed(email_id_str):
                logger.info(f"Email {email_id_str} already processed, skipping")
                return None
            
            # Fetch the email
            status, msg_data = self.imap_server.fetch(latest_email_id, '(RFC822)')
            
            if status != 'OK':
                logger.warning(f"Failed to fetch email {email_id_str}")
                return None
                
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Extract email data
            email_data = {
                "id": email_id_str,
                "threadId": email_id_str,  # No threading in IMAP, use email_id
                "sender": email.utils.parseaddr(email_message['From'])[1],
                "recipient": self.config["Email"]["email_address"],
                "subject": self._decode_header(email_message['Subject']),
                "body": "",
                "date": email_message['Date'],
                "list_id": email_message.get('List-Id')
            }
            
            # Extract the body
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    # Get plain text body
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        email_data["body"] = part.get_payload(decode=True).decode()
                        break
            else:
                email_data["body"] = email_message.get_payload(decode=True).decode()
            
            # Apply filtering logic
            if self.should_process_email(email_data):
                return email_data
            else:
                logger.info(f"Email {email_id_str} filtered out based on rules")
                self.mark_as_processed(email_id_str)  # Mark as processed to skip next time
                return None
            
        except Exception as e:
            logger.error(f"Error fetching email via IMAP: {str(e)}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """Decode email header properly"""
        if not header:
            return ""
            
        decoded_header = decode_header(header)
        header_parts = []
        
        for part, encoding in decoded_header:
            if isinstance(part, bytes):
                if encoding:
                    header_parts.append(part.decode(encoding or 'utf-8', errors='replace'))
                else:
                    header_parts.append(part.decode('utf-8', errors='replace'))
            else:
                header_parts.append(part)
                
        return ''.join(header_parts)
    
    def send_reply(self, email_data: Dict, reply_text: str) -> bool:
        """Send a reply to an email using SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config["Email"]["email_address"]
            msg['To'] = email_data["sender"]
            msg['Subject'] = f"Re: {email_data['subject']}"
            msg['In-Reply-To'] = email_data["id"]
            msg['References'] = email_data["id"]
            msg.attach(MIMEText(reply_text, 'plain'))
            
            # Send the message
            self.smtp_server.send_message(msg)
            
            # Mark the email as read
            self.imap_server.store(email_data["id"].encode(), '+FLAGS', '\\Seen')
            
            # Mark as processed to prevent loops
            self.mark_as_processed(email_data["id"])
            
            logger.info(f"Reply sent to {email_data['sender']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending reply via SMTP: {str(e)}")
            return False
    
    def disconnect(self):
        """Close connections to IMAP and SMTP servers"""
        try:
            if self.imap_server:
                self.imap_server.close()
                self.imap_server.logout()
            
            if self.smtp_server:
                self.smtp_server.quit()
                
            logger.info("Disconnected from email servers")
        
        except Exception as e:
            logger.error(f"Error disconnecting from servers: {str(e)}")