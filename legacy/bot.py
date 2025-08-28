import discord
from discord.ext import commands
import asyncio
import os
import logging
import aiofiles
from config import Config
from api_client import APIClient
from message_handler import MessageHandler
from memory_manager import MemoryManager
from commands import setup_commands
from data_manager import DataManager

if not os.path.exists("logs"):
    os.makedirs("logs")
logging.basicConfig(filename="logs/application.log", level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logging.getLogger("").addHandler(console)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

config = Config()
api_client = APIClient(config)
memory_manager = MemoryManager()
data_manager = DataManager("logs/chat_data.json")
bot.data_manager = data_manager
message_handler = MessageHandler(api_client, memory_manager, config, data_manager, bot)
memory_manager.api_client = api_client
bot.memory_manager = memory_manager

async def setup_bot():
    await bot.wait_until_ready()
    models = await api_client.fetch_models()
    if not models:
        models = [{"name": "unity", "description": "Default unity model"}]
        logging.info("No models loaded from API, defaulting to 'unity'.")
    memory_manager.set_models(models)
    config.default_model = "unity"
    data_manager.load_data(memory_manager)
    setup_commands(bot, models)
    print(f"Loaded {len(models)} models: {[m['name'] for m in models]}")

@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    logging.info("Bot is ready and connected.")
    await setup_bot()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    channel_id = str(message.channel.id)
    guild_id = str(message.guild.id) if message.guild else "DM"
    user_id = str(message.author.id)
    logging.info(f"Received message from {user_id} in channel {channel_id} (guild: {guild_id}): {message.content}")

    memory_manager.initialize_channel(channel_id)
    user_model = memory_manager.get_user_model(guild_id, user_id)
    logging.info(f"User {user_id} using model: {user_model} in guild {guild_id}")

    try:
        await bot.process_commands(message)
        await message_handler.handle_message(message)
        await data_manager.save_data_async(memory_manager)
    except Exception as e:
        logging.error(f"Error handling message for user {user_id}: {e}")
        try:
            await message.channel.send(f"<@{user_id}> Something went wrong - please try again.")
        except Exception as send_error:
            logging.error(f"Failed to send error message to user {user_id}: {send_error}")

    if len(memory_manager.channel_histories.get(channel_id, [])) > config.max_history:
        memory_manager.channel_histories[channel_id] = memory_manager.channel_histories[channel_id][-config.max_history:]

@bot.command(name="wipe")
async def wipe(ctx):
    try:
        channel_id = str(ctx.channel.id)
        guild_id = str(ctx.guild.id) if ctx.guild else "DM"
        user_id = str(ctx.author.id)
        logging.info(f"Wipe command initiated by {user_id} in channel {channel_id}")

        bot.memory_manager.channel_histories[channel_id] = []
        if guild_id in bot.memory_manager.user_histories:
            if user_id in bot.memory_manager.user_histories[guild_id]:
                bot.memory_manager.user_histories[guild_id][user_id] = []
        if guild_id in bot.memory_manager.user_model_histories:
            if user_id in bot.memory_manager.user_model_histories[guild_id]:
                for model in bot.memory_manager.user_model_histories[guild_id][user_id]:
                    bot.memory_manager.user_model_histories[guild_id][user_id][model] = []

        await bot.data_manager.save_data_async(bot.memory_manager)
        await ctx.send(f"<@{user_id}> Chat history wiped for this server.")
        logging.info(f"Chat history wiped for user {user_id} in channel {channel_id}")
    except Exception as e:
        logging.error(f"Error in wipe command for user {user_id}: {e}")
        await ctx.send(f"<@{user_id}> Error wiping chat history: {str(e)}")

async def wipe_logs_periodically():
    while True:
        try:
            await asyncio.sleep(3600)
            async with aiofiles.open("logs/application.log", "w") as f:
                await f.write("")
            logging.info("Logs wiped successfully.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"Error wiping logs: {e}")

@bot.event
async def on_connect():
    await api_client.initialize()
    print("Bot connected to Discord")

@bot.event
async def on_disconnect():
    await api_client.close()
    print("Bot disconnected from Discord")

async def main():
    try:
        await bot.start(config.discord_token)
    except discord.errors.LoginFailure as e:
        logging.error(f"Failed to login: {e}")
        print("Login failed. Please check your Discord token in the .env file (key: DISCORD_TOKEN). Ensure it's valid and not revoked. Visit https://discord.com/developers/applications to reset it.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")
    finally:
        await api_client.close()
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    asyncio.run(main())