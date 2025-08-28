# Unity Voice Chat

This project provides a simple Windows 11 application for conversing with an AI assistant using both text and speech.
It reuses the API and response formatting logic from the original Unity Discord bot, but exposes a desktop interface
with optional text-to-speech and speech-to-text capabilities.

## Features
- Modern Windows 11 style interface built with `ttkbootstrap`
- Toggleable voice output using Google Text-to-Speech
- Speech recognition input using the default microphone
- Sentence-by-sentence speech synthesis to avoid cut-off on long replies
- Dropdown with full language names for all Google TTS languages
- Basic chat log and memory of the current session
- Code blocks rendered with copy and download buttons
- Model selector populated dynamically from `text.pollinations.ai/models`

## Getting Started
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Ensure `POLLINATIONS_TOKEN` is set in a `.env` file or environment variable.
3. Run the application:
   ```bash
   python windows_voice_chat.py
   ```

The previous Discord bot implementation is preserved in the `legacy/` folder for reference.
