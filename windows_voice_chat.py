import asyncio
import os
import re
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext

from gtts import gTTS
from playsound import playsound
import speech_recognition as sr

from app_config import Config
from api_client import APIClient


class VoiceChatApp:
    """Simple Windows voice chat application using Pollinations AI."""

    def __init__(self):
        self.config = Config()
        self.client = APIClient(self.config)
        self.root = tk.Tk()
        self.root.title("Unity Voice Chat")
        self.root.configure(bg="#1a0000")

        self.voice_enabled = tk.BooleanVar(value=True)
        self.selected_voice = tk.StringVar(value="en")
        self.messages = [
            {"role": "system", "content": self.config.system_instructions}
        ]

        self._build_ui()

    def _build_ui(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        voice_check = ttk.Checkbutton(
            top_frame, text="Voice Output", variable=self.voice_enabled
        )
        voice_check.pack(side=tk.LEFT)

        voices = self._available_voices()
        voice_menu = ttk.OptionMenu(
            top_frame, self.selected_voice, self.selected_voice.get(), *voices
        )
        voice_menu.pack(side=tk.LEFT, padx=5)

        speak_button = ttk.Button(top_frame, text="Speak", command=self._voice_input)
        speak_button.pack(side=tk.LEFT, padx=5)

        self.text_area = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, state=tk.DISABLED, bg="#330000", fg="#FFFFFF"
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)

        self.entry = ttk.Entry(bottom_frame)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", lambda event: self._send_text())

        send_button = ttk.Button(bottom_frame, text="Send", command=self._send_text)
        send_button.pack(side=tk.LEFT, padx=5)

    def _available_voices(self):
        from gtts.lang import tts_langs

        langs = tts_langs()
        return sorted(langs.keys())

    def _append_text(self, speaker: str, text: str):
        self.text_area.configure(state=tk.NORMAL)
        self.text_area.insert(tk.END, f"{speaker}: {text}\n")
        self.text_area.configure(state=tk.DISABLED)
        self.text_area.see(tk.END)

    def _send_text(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        self._append_text("You", text)
        self.messages.append({"role": "user", "content": text})
        threading.Thread(target=self._get_response, args=(list(self.messages),)).start()

    def _voice_input(self):
        threading.Thread(target=self._listen_and_send).start()

    def _listen_and_send(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            audio = r.listen(source)
        try:
            text = r.recognize_google(audio, language=self.selected_voice.get())
            self._append_text("You", text)
            self.messages.append({"role": "user", "content": text})
            self._get_response(list(self.messages))
        except sr.UnknownValueError:
            self._append_text("System", "Could not understand audio")
        except sr.RequestError as e:
            self._append_text("System", f"Speech recognition error: {e}")

    def _get_response(self, messages):
        try:
            response = asyncio.run(self.client.send_message(messages, None))
        except Exception as e:
            self._append_text("System", f"Error contacting API: {e}")
            return
        self.messages.append({"role": "assistant", "content": response})
        self._append_text("AI", response)
        if self.voice_enabled.get():
            self._speak(response)

    def _speak(self, text: str):
        sentences = [s.strip() for s in re.split(r"(?<=[.!?]) +", text) if s.strip()]
        for sentence in sentences:
            tts = gTTS(sentence, lang=self.selected_voice.get())
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_name = fp.name
            tts.save(temp_name)
            playsound(temp_name)
            try:
                os.remove(temp_name)
            except OSError:
                pass

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = VoiceChatApp()
    app.run()
