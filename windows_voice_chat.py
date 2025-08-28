import asyncio
import os
import re
import tempfile
import threading
import tkinter as tk
from tkinter import scrolledtext

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
        self.root.configure(bg="#000000")

        self.voice_enabled = tk.BooleanVar(value=True)
        self.selected_voice = tk.StringVar(value="en")
        self.messages = [
            {"role": "system", "content": self.config.system_instructions}
        ]

        self.listening = False
        self.listen_thread: threading.Thread | None = None

        self._build_ui()

    def _build_ui(self):
        top_frame = tk.Frame(self.root, bg="#000000")
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        voice_check = tk.Checkbutton(
            top_frame,
            text="Voice Output",
            variable=self.voice_enabled,
            bg="#000000",
            fg="#FF0000",
            selectcolor="#000000",
            activebackground="#000000",
            activeforeground="#FF0000",
        )
        voice_check.pack(side=tk.LEFT)

        voices = self._available_voices()
        voice_menu = tk.OptionMenu(
            top_frame, self.selected_voice, self.selected_voice.get(), *voices
        )
        voice_menu.configure(
            bg="#330000",
            fg="#FF0000",
            activebackground="#660000",
            activeforeground="#FF0000",
            highlightthickness=0,
        )
        voice_menu.pack(side=tk.LEFT, padx=5)
        voice_menu["menu"].config(bg="#000000", fg="#FF0000")

        self.start_button = tk.Button(
            top_frame,
            text="Start Talking",
            command=self._toggle_listening,
            bg="#330000",
            fg="#FF0000",
            activebackground="#660000",
            activeforeground="#FF0000",
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.text_area = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#000000",
            fg="#FF0000",
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        bottom_frame = tk.Frame(self.root, bg="#000000")
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)

        self.entry = tk.Entry(
            bottom_frame,
            bg="#000000",
            fg="#FF0000",
            insertbackground="#FF0000",
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", lambda event: self._send_text())

        send_button = tk.Button(
            bottom_frame,
            text="Send",
            command=self._send_text,
            bg="#330000",
            fg="#FF0000",
            activebackground="#660000",
            activeforeground="#FF0000",
        )
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

    def _toggle_listening(self):
        if not self.listening:
            self.listening = True
            self.start_button.config(text="Stop Talking")
            self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listen_thread.start()
        else:
            self.listening = False
            self.start_button.config(text="Start Talking")

    def _listen_loop(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            while self.listening:
                try:
                    audio = r.listen(source, timeout=1, phrase_time_limit=5)
                    text = r.recognize_google(audio, language=self.selected_voice.get())
                    self._append_text("You", text)
                    self.messages.append({"role": "user", "content": text})
                    threading.Thread(target=self._get_response, args=(list(self.messages),)).start()
                except sr.WaitTimeoutError:
                    continue
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
