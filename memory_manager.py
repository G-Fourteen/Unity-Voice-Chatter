import datetime
import logging

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self):
        self.channel_memories = {}
        self.channel_histories = {}
        self.user_histories = {}
        self.user_models = {}
        self.user_model_histories = {}
        self.models = []
        self.api_client = None

    def set_models(self, models):
        self.models = models
        logger.info(f"Set {len(models)} models")

    def initialize_channel(self, channel_id):
        channel_id = str(channel_id)
        self.channel_memories.setdefault(channel_id, [])
        self.channel_histories.setdefault(channel_id, [])

    def initialize_user(self, guild_id, user_id):
        guild_id = str(guild_id)
        user_id = str(user_id)
        self.user_histories.setdefault(guild_id, {}).setdefault(user_id, [])
        self.user_models.setdefault(guild_id, {}).setdefault(user_id, None)
        self.user_model_histories.setdefault(guild_id, {}).setdefault(user_id, {})

    def add_memory(self, channel_id, memory):
        channel_id = str(channel_id)
        self.initialize_channel(channel_id)
        memory = memory.strip()
        if memory and memory not in self.channel_memories[channel_id]:
            self.channel_memories[channel_id].append(memory)
            if len(self.channel_memories[channel_id]) > 5:
                self.channel_memories[channel_id] = self.channel_memories[channel_id][-5:]

    def get_memories(self, channel_id):
        channel_id = str(channel_id)
        self.initialize_channel(channel_id)
        return list(self.channel_memories[channel_id])

    def get_user_model_history(self, guild_id, user_id, model_name):
        guild_id = str(guild_id)
        user_id = str(user_id)
        model_name = str(model_name)
        self.user_model_histories.setdefault(guild_id, {}).setdefault(user_id, {}).setdefault(model_name, [])
        return self.user_model_histories[guild_id][user_id][model_name]

    def add_user_message(self, channel_id, guild_id, user_id, message_content):
        channel_id = str(channel_id)
        guild_id = str(guild_id)
        user_id = str(user_id)
        self.initialize_channel(channel_id)
        self.initialize_user(guild_id, user_id)
        model = self.get_user_model(guild_id, user_id)
        user_model_history = self.get_user_model_history(guild_id, user_id, model)
        user_model_history.append({
            "role": "user",
            "content": message_content,
            "timestamp": str(datetime.datetime.now()),
            "status": "active"
        })
        if len(user_model_history) > 20:
            user_model_history[:] = user_model_history[-20:]
        self.channel_histories[channel_id].append({
            "role": "user",
            "content": message_content,
            "user_id": user_id,
            "timestamp": str(datetime.datetime.now()),
            "status": "active"
        })
        if len(self.channel_histories[channel_id]) > 20:
            self.channel_histories[channel_id] = self.channel_histories[channel_id][-20:]
        self.user_histories[guild_id][user_id].append({
            "role": "user",
            "content": message_content,
            "timestamp": str(datetime.datetime.now()),
            "status": "active"
        })
        if len(self.user_histories[guild_id][user_id]) > 20:
            self.user_histories[guild_id][user_id] = self.user_histories[guild_id][user_id][-20:]

    def add_ai_message(self, channel_id, guild_id, user_id, message_content):
        channel_id = str(channel_id)
        guild_id = str(guild_id)
        user_id = str(user_id)
        self.initialize_channel(channel_id)
        self.initialize_user(guild_id, user_id)
        model = self.get_user_model(guild_id, user_id)
        user_model_history = self.get_user_model_history(guild_id, user_id, model)
        user_model_history.append({
            "role": "ai",
            "content": message_content,
            "timestamp": str(datetime.datetime.now()),
            "status": "active"
        })
        if len(user_model_history) > 20:
            user_model_history[:] = user_model_history[-20:]
        self.channel_histories[channel_id].append({
            "role": "ai",
            "content": message_content,
            "user_id": user_id,
            "timestamp": str(datetime.datetime.now()),
            "status": "active"
        })
        if len(self.channel_histories[channel_id]) > 20:
            self.channel_histories[channel_id] = self.channel_histories[channel_id][-20:]
        self.user_histories[guild_id][user_id].append({
            "role": "ai",
            "content": message_content,
            "timestamp": str(datetime.datetime.now()),
            "status": "active"
        })
        if len(self.user_histories[guild_id][user_id]) > 20:
            self.user_histories[guild_id][user_id] = self.user_histories[guild_id][user_id][-20:]

    def get_user_history(self, guild_id, user_id):
        guild_id = str(guild_id)
        user_id = str(user_id)
        self.initialize_user(guild_id, user_id)
        return list(self.user_histories.get(guild_id, {}).get(user_id, []))

    def get_channel_history(self, channel_id):
        channel_id = str(channel_id)
        self.initialize_channel(channel_id)
        return [msg for msg in self.channel_histories[channel_id] if msg["status"] == "active"]

    def set_user_model(self, guild_id, user_id, model_name):
        guild_id = str(guild_id)
        user_id = str(user_id)
        self.initialize_user(guild_id, user_id)
        model_name_lower = model_name.lower()
        for m in self.models:
            if m["name"].lower() == model_name_lower:
                self.user_models[guild_id][user_id] = m["name"]
                logger.info(f"Set model for user {user_id} in guild {guild_id} to {m['name']}")
                return True
        logger.warning(f"Model {model_name} not found for user {user_id} in guild {guild_id}")
        return False

    def get_user_model(self, guild_id, user_id):
        guild_id = str(guild_id)
        user_id = str(user_id)
        self.initialize_user(guild_id, user_id)
        model = self.user_models.get(guild_id, {}).get(user_id)
        if model is None:
            model = "unity"
            self.user_models[guild_id][user_id] = model
            logger.info(f"Assigned default model {model} for user {user_id} in guild {guild_id}")
        return model