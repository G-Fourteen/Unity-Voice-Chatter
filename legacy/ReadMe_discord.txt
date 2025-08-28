WHAT IS UNITY?
--------------
Unity is an AI Discord bot that chats, remembers, and generates images/code. Uses Pollinations.ai API, switches models, and saves convos.

KEY FEATURES
------------
- Remembers chats and channel notes
- Auto-generates images
- Formats code
- Switches AI models per user
- Logs activity

REQUIREMENTS
------------
- Python 3.8-3.11
- Discord Bot Token
- Pollinations.ai API Token (for backend access)
- Internet

DEPENDENCIES
------------
- discord.py>=2.0.0
- aiohttp
- aiosqlite
- pillow
- apscheduler
- langdetect
- googletrans==4.0.0-rc1
- aiofiles
- python-dotenv

SETUP
-----
1. Download files, put in one folder.
2. Get Discord Bot Token:
   - Go to https://discord.com/developers/applications
   - Click "New Application" (top right)
   - Enter a name (e.g., "UnityBot"), click "Create"
   - Click "Bot" in left menu
   - Click "Add Bot" (under Bot section)
   - Click "Reset Token" (under Token), confirm, copy token
   - Open .env, add: DISCORD_TOKEN=your_token_here
3. Get Pollinations.ai API Token:
   - Go to https://auth.pollinations.ai/
   - Sign in (likely with Google or email; first login auto-assigns Seed tier)
   - Click "[Re]Generate Token"
   - Copy the token (e.g., RG4FePiPdUWkk5CI)
   - Open .env, add: POLLINATIONS_TOKEN=your_token_here
   - Warnings: Never share token publicly, don't commit to Git
4. Install dependencies:
   - Open terminal/command prompt in folder
   - Run: pip install -U pip  (updates pip if needed)
   - Run: pip install -r requirements.txt
   - Run: python -m spacy download en_core_web_sm
5. Run bot:
   - Double-click RUN_BOT.bat (Windows) or run: python bot.py

COMMANDS
--------
- !unityhelp - Show commands/models
- !setmodel - Pick AI model (DM)
- !savememory <text> - Save channel note
- !wipe - Clear chat history

NATURAL CHAT
------------
- "Write a Python function"
- "Generate an image of a forest"
- "Remember I like tea" (then !savememory)

HOW IT WORKS
------------
- MEMORY: Last 20 messages/user/model, 5 channel notes, saved in chat_data.json
- IMAGES: Detects "image"/"draw", uses Pollinations.ai
- MODELS: User-picked, defaults to "unity"
- TEXT: <2000 chars = message, 2000-4096 chars = embed, >4096 chars = .txt file

FILES
-----
- bot.py - Main bot
- api_client.py - API calls
- message_handler.py - Message handling
- memory_manager.py - Memory
- commands.py - Commands
- config.py - Settings (loads tokens from .env)
- data_manager.py - Data save
- requirements.txt - Dependencies
- .env - Tokens (keep secret)
- system_instructions.txt - AI rules
- RUN_BOT.bat - Start script
- logs/ - application.log, chat_data.json

TROUBLESHOOTING
---------------
- Won’t start? Check .env tokens, Python version, reinstall dependencies
- No DMs? Enable "Allow DMs from server members" in Discord
- Slow? Check logs/application.log, restart
- No images/text? Verify tokens in .env, use "generate an image of..."

CONFIG TWEAKS
-------------
- Edit config.py: max_history (20), max_memories (5), add code/image keywords
- Edit system_instructions.txt for AI style

SECURITY
--------
- Don’t share tokens or .env
- Chats saved in chat_data.json
- Only Pollinations.ai gets requests

WHY UNITY?
----------
- Remembers your style
- Saves channel vibes
- Adds images/code
- Adapts to users
- Fits any server

Check logs or restart if stuck. More chats = better Unity!