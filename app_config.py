import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    logger.warning(".env file not found; ensure POLLINATIONS_TOKEN is set in environment")

class Config:
    """Configuration for the Windows voice chat application."""
    def __init__(self):
        self.pollinations_token = os.getenv("POLLINATIONS_TOKEN", "").strip()
        if not self.pollinations_token:
            raise ValueError("POLLINATIONS_TOKEN not found in environment variables")
        try:
            with open("system_instructions.txt", "r", encoding="utf-8") as f:
                self.system_instructions = f.read().strip()
        except FileNotFoundError:
            logger.warning("system_instructions.txt not found; proceeding without system instructions")
            self.system_instructions = ""
        self.api_url = "https://text.pollinations.ai/openai"
        self.models_url = "https://text.pollinations.ai/models"
        self.default_model = "unity"
