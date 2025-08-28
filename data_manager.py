import json
import os
import logging
import aiofiles

logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self, filename):
        self.filename = filename
        self.data = {"channels": {}, "user_models": {}, "user_histories": {}}
        if not os.path.exists(filename):
            try:
                with open(filename, "w") as f:
                    json.dump(self.data, f, indent=4)
                logger.info(f"Created new data file at {filename}")
            except Exception as e:
                logger.error(f"Failed to create data file {filename}: {e}")
                raise

    def load_data(self, memory_manager):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r") as f:
                    self.data = json.loads(f.read())
                for channel_id, channel_data in self.data.get("channels", {}).items():
                    memory_manager.channel_memories[channel_id] = channel_data.get("memories", [])
                    memory_manager.channel_histories[channel_id] = channel_data.get("history", [])
                for guild_id, models in self.data.get("user_models", {}).items():
                    memory_manager.user_models[guild_id] = models
                for guild_id, histories in self.data.get("user_histories", {}).items():
                    memory_manager.user_histories[guild_id] = histories
                logger.info("Data loaded successfully from chat_data.json")
            except Exception as e:
                logger.error(f"Error loading data from {self.filename}: {e}")
                self.data = {"channels": {}, "user_models": {}, "user_histories": {}}

    async def save_data_async(self, memory_manager):
        try:
            data = {
                "channels": {},
                "user_models": memory_manager.user_models.copy(),
                "user_histories": memory_manager.user_histories.copy()
            }
            for channel_id, mems in memory_manager.channel_memories.items():
                data["channels"][channel_id] = {
                    "memories": mems,
                    "history": memory_manager.channel_histories.get(channel_id, [])
                }

            async with aiofiles.open(self.filename, "w") as f:
                await f.write(json.dumps(data, indent=4))
            logger.debug("Data saved successfully to chat_data.json")
        except Exception as e:
            logger.error(f"Error saving data to {self.filename}: {e}")

    def save_data(self, memory_manager):
        try:
            data = {
                "channels": {},
                "user_models": memory_manager.user_models.copy(),
                "user_histories": memory_manager.user_histories.copy()
            }
            for channel_id, mems in memory_manager.channel_memories.items():
                data["channels"][channel_id] = {
                    "memories": mems,
                    "history": memory_manager.channel_histories.get(channel_id, [])
                }
            with open(self.filename, "w") as f:
                json.dump(data, f, indent=4)
            logger.debug("Data saved successfully to chat_data.json")
        except Exception as e:
            logger.error(f"Error saving data to {self.filename}: {e}")