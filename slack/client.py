import os
from slack_sdk import WebClient
from dotenv import load_dotenv
from utils import setup_logger  

load_dotenv()  # Load env vars from .env
logger = setup_logger("SlackClient")

class SlackClient:
    def __init__(self, token: str = None):
        self.token = token or os.getenv("SLACK_BOT_TOKEN")

        if not self.token:
            logger.error("SLACK_BOT_TOKEN not found")
            raise ValueError("Slack token is missing")

        self.client = WebClient(token=self.token)
        logger.info("Slack client initialized successfully")

    def get_client(self):
        logger.debug("Slack WebClient instance returned")
        return self.client
    
    def list_channels(self):
        """Fetch and return all channels visible to the bot"""
        try:
            logger.info("Fetching list of Slack channels")
            response = self.client.conversations_list(limit=1000)
            channels = response.get("channels", [])
            for ch in channels:
                logger.info(f"Channel: {ch['name']} => ID: {ch['id']}")
            return channels
        except Exception as e:
            logger.error(f"Failed to list channels: {e}")
            return []
