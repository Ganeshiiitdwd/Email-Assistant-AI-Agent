# Email-Assistant-AI-Agent
An intelligent email automation system powered by Google's Gemini AI that monitors your inbox, generates personalized responses, and logs all interactions to Google Sheets or CSV.

## ✨ Features
- **🤖 AI-Powered Responses**: Generates contextual replies using Google's Gemini AI models
- **📧 Multi-Provider Support**: Works with Gmail API and standard IMAP/SMTP servers
- **📊 Interaction Tracking**: Logs all email interactions in Google Sheets or local CSV
- **🔍 Smart Filtering**: Avoids reply loops and automatically skips newsletters/no-reply emails
- **⏱️ Flexible Scheduling**: Run continuously with customizable check intervals or as a one-time process
- **🔐 Secure Authentication**: Uses OAuth for Gmail and service accounts for Google Sheets

## 📂 Project Structure
gemini-email-assistant/
├── agent.py # Main application entry point
├── config_manager.py # Configuration manager
├── email_assistant.py # AI response generation using Gemini
├── email_processor.py # Email fetching and sending
├── logging_handlers.py # Interaction logging implementations
├── spreadsheet.py # Google Sheets integration
├── requirements.txt # Python dependencies
├── config.ini # Configuration file (template)
├── .env # Environment variables (optional)
└── README.md # Documentation


## 🛠️ Setup Guide

### Prerequisites
- Python 3.8 or higher
- A Google account
- Google Cloud Platform project access

### 1. Clone the Repository
git clone https://github.com/your-username/gemini-email-assistant.git
cd gemini-email-assistant

### 2. Install Dependencies

### 3. Set Up API Access
Gmail API Setup
Go to the Google Cloud Console

Create a new project (or select an existing one)

Enable the Gmail API

Go to "Credentials" and create an OAuth client ID

Application type: Desktop app

Name: Gemini Email Assistant

Download credentials JSON file as credentials.json

Google Sheets API Setup
In the same Google Cloud project, enable Google Sheets API and Drive API

Create Service Account and download JSON key as service_account.json

Share your Google Sheet with the service account email

Gemini API Setup
Go to Google AI Studio

Get API key from the API keys section

Save this key for configuration

### 4. Configure the Application
Create config.ini:
[Email]
type = gmail
email_address = your-email@gmail.com
password = your-app-password

[Gmail]
credentials_path = credentials.json
token_path = token.pickle

[LLM]
provider = google
api_key = your-gemini-api-key
model_name = gemini-2.0-flash

[Assistant]
persona = Professional assistant representing [Your Company]

[Logging]
type = googlesheets

[GoogleSheets]
credentials_path = service_account.json
spreadsheet_id = your-sheet-id

🚀 Running the Assistant
# Run once
python agent.py --single

# Run continuously
python agent.py --interval 300

# Custom config
python agent.py --config my_custom_config.ini

🔒 Security
Keep credentials files secure

Never commit secrets to version control

Use App Passwords instead of real passwords
