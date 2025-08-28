import os
from dotenv import load_dotenv
import re
import logging

logger = logging.getLogger(__name__)

# Load .env file
env_path = os.path.join(os.path.dirname(__file__), '.env')
if not os.path.exists(env_path):
    logger.error(f".env file not found at {env_path}")
    raise FileNotFoundError(f".env file not found at {env_path}")
load_dotenv(env_path)
logger.info(f"Loaded .env file from {env_path}")

class Config:
    def __init__(self):
        # Load and validate Discord token
        self.discord_token = os.getenv("DISCORD_TOKEN")
        if self.discord_token:
            self.discord_token = self.discord_token.strip()  # Remove whitespace
            logger.debug(f"Discord token length: {len(self.discord_token)}, first 10 chars: {self.discord_token[:10]}")
            # Discord tokens are base64-like, ~59-100 chars
            if not re.match(r'^[A-Za-z0-9._-]{50,100}$', self.discord_token):
                logger.error(f"Invalid Discord token format: {self.discord_token[:10]}... (truncated)")
                raise ValueError("Invalid Discord token format. Ensure no spaces, quotes, or invalid characters.")
        else:
            logger.error("DISCORD_TOKEN not found in environment variables")
            raise ValueError("DISCORD_TOKEN not found in environment variables")
        logger.info(f"Successfully loaded discord token: {self.discord_token[:10]}... (truncated for security)")

        # Load and validate Pollinations token
        self.pollinations_token = os.getenv("POLLINATIONS_TOKEN")
        if self.pollinations_token:
            self.pollinations_token = self.pollinations_token.strip()
            logger.debug(f"Pollinations token length: {len(self.pollinations_token)}, first 10 chars: {self.pollinations_token[:10]}")
            if not re.match(r'^[A-Za-z0-9]{16}$', self.pollinations_token):  # Assuming 16-char alphanumeric format from example
                logger.error(f"Invalid Pollinations token format: {self.pollinations_token[:10]}... (truncated)")
                raise ValueError("Invalid Pollinations token format. Ensure it's correct and no invalid characters.")
        else:
            logger.error("POLLINATIONS_TOKEN not found in environment variables")
            raise ValueError("POLLINATIONS_TOKEN not found in environment variables")
        logger.info(f"Successfully loaded pollinations token: {self.pollinations_token[:10]}... (truncated for security)")

        # Bot configuration
        self.default_model = "unity"
        try:
            with open("system_instructions.txt", "r") as f:
                self.system_instructions = f.read().strip()
        except FileNotFoundError:
            logger.error("system_instructions.txt not found")
            raise FileNotFoundError("system_instructions.txt not found")
        self.api_url = f"https://text.pollinations.ai/openai?token={self.pollinations_token}"
        self.models_url = "https://text.pollinations.ai/models"
        self.max_history = 20
        self.max_memories = 5
        self.code_keywords = [
            "code", "script", "program", "function", "class",
            "method", "javascript", "python", "java", "html", "css"
        ]
        self.image_keywords = [
            "image", "picture", "photo", "generate", "create", "draw", "art"
        ]
        self.memory_regex = r"\$\$ memory \$\$([\s\S]*?)\$\$ \/memory \$\$"
        self.code_block_regex = r"```(\w*)\n([\s\S]*?)\n```"
        self.url_regex = r"https?://[^\s>]+"

    def is_image_request(self, message: str) -> bool:
        return any(keyword in message.lower() for keyword in self.image_keywords)

    def is_code_request(self, message: str) -> bool:
        return any(keyword in message.lower() for keyword in self.code_keywords)

    def extract_image_prompt(self, message: str) -> str:
        return message.strip()