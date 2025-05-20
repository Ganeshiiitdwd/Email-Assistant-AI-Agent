"""
Configuration manager for Email Automation Agent

This module handles loading and validating configuration from config.ini
"""

import os
import configparser
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='email_agent.log'
)
logger = logging.getLogger(__name__)

def load_config(config_path: str = "config.ini") -> configparser.ConfigParser:
    """Load configuration from the config file"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file {config_path} not found")
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    logger.info(f"Configuration loaded from {config_path}")
    return config