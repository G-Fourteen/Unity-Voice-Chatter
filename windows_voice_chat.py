import asyncio
import os
import re
import tempfile
import threading
import tkinter as tk
from io import BytesIO

import requests
import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledText
from gtts import gTTS
from gtts.lang import tts_langs
from PIL import Image, ImageTk
from playsound import playsound
import speech_recognition as sr

from app_config import Config
from api_client import APIClient


class VoiceChatApp:
    """Simple Windows voice chat application using Pollinations AI."""

    def __init__(self):
        self.config = Config()
        self.client = APIClient(self.config)
        self.root = ttk.Window(themename="darkly")
        self.root.title("Unity Voice Chat")
        self.root.option_add("*Font", ("Segoe UI", 10))
        self.root.configure(bg="black")

        # Set application icon if available
        app_dir = os.path.dirname(os.path.abspath(__file__))
        ico_path = os.path.join(app_dir, "unity.ico")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass

        self._style = ttk.Style()
        neon = "#39FF14"
        self._style.configure("Neon.TFrame", background="black")
        self._style.configure("Neon.TCheckbutton", background="black", foreground=neon)
        self._style.configure("Neon.TButton", background="black", foreground=neon)
        self._style.configure(
            "Neon.TEntry", fieldbackground="black", foreground=neon, insertcolor=neon
        )
        self._style.configure(
            "Neon.TCombobox", fieldbackground="black", foreground=neon, background="black"
        )
        self._style.configure("Neon.TLabel", background="black", foreground=neon)
        self.neon = neon

        self.voice_enabled = tk.BooleanVar(value=True)
        self.selected_voice = tk.StringVar()
        self.messages = [
            {"role": "system", "content": self.config.system_instructions}
        ]

        self.listening = False
        self.listen_thread: threading.Thread | None = None

        # Keep references to images inserted in the chat to avoid garbage collection
        self._image_refs: list[ImageTk.PhotoImage] = []

        self._build_ui()

    def _build_ui(self):
        # Header with title
        header = ttk.Frame(self.root, padding=5, style="Neon.TFrame")
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text="Unity Voice Chat",
            style="Neon.TLabel",
            font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT, padx=5)

        top_frame = ttk.Frame(self.root, padding=5, style="Neon.TFrame")
        top_frame.pack(fill=tk.X)

        voice_check = ttk.Checkbutton(
            top_frame,
            text="Voice Output",
            variable=self.voice_enabled,
            style="Neon.TCheckbutton",
        )
        voice_check.pack(side=tk.LEFT)

        voices = self._available_voices()
        self.voice_map = {display: name for name, display in voices}
        self.selected_voice.set(voices[0][0])
        self.voice_display = tk.StringVar(value=voices[0][1])
        voice_menu = ttk.Combobox(
            top_frame,
            textvariable=self.voice_display,
            values=list(self.voice_map.keys()),
            state="readonly",
            width=35,
            style="Neon.TCombobox",
        )
        voice_menu.pack(side=tk.LEFT, padx=5)
        voice_menu.bind(
            "<<ComboboxSelected>>",
            lambda e: self.selected_voice.set(self.voice_map[self.voice_display.get()]),
        )

        self.start_button = ttk.Button(
            top_frame,
            text="Start Talking",
            command=self._toggle_listening,
            style="Neon.TButton",
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.text_area = ScrolledText(
            self.root,
            wrap=tk.WORD,
            state=tk.DISABLED,
            padding=5,
        )
        self.text_area.configure(style="Neon.TFrame")
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.text_area.text.configure(
            bg="black", fg=self.neon, insertbackground=self.neon
        )

        bottom_frame = ttk.Frame(self.root, padding=5, style="Neon.TFrame")
        bottom_frame.pack(fill=tk.X)

        self.entry = ttk.Entry(bottom_frame, style="Neon.TEntry")
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entry.bind("<Return>", lambda event: self._send_text())

        send_button = ttk.Button(
            bottom_frame,
            text="Send",
            command=self._send_text,
            style="Neon.TButton",
        )
        send_button.pack(side=tk.LEFT)

    def _process_pollinations(self, text: str):
        """Remove pollinations image URLs from text and return list of URLs."""
        pattern = r"https?://\S*pollinations\.ai\S*"
        urls = re.findall(pattern, text)
        cleaned = re.sub(pattern, "", text).strip()
        return cleaned, urls

    def _append_image(self, url: str):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            image_data = BytesIO(resp.content)
            img = Image.open(image_data)
            photo = ImageTk.PhotoImage(img)
            text_widget = self.text_area.text
            text_widget.configure(state=tk.NORMAL)
            text_widget.image_create(tk.END, image=photo)
            text_widget.insert(tk.END, "\n")
            text_widget.configure(state=tk.DISABLED)
            text_widget.see(tk.END)
            self._image_refs.append(photo)
        except Exception as e:
            self._append_text("System", f"Failed to load image: {e}")

    def _available_voices(self):
        """Return available common voices using gTTS languages."""
        voices: list[tuple[str, str]] = []
        try:
            languages = tts_langs()
            common_codes = {
                "en",  # English
                "es",  # Spanish
                "fr",  # French
                "de",  # German
                "it",  # Italian
                "pt",  # Portuguese
                "ru",  # Russian
            }
            for code, name in languages.items():
                if code in common_codes:
                    voices.append((code, f"{name} ({code})"))
            voices.sort(key=lambda x: x[1])
        except Exception:
            pass
        if voices:
            return voices
        return [("en", "English (en)")]

    def _language_from_voice(self) -> str:
        return self.selected_voice.get()

    def _append_text(self, speaker: str, text: str):
        text_widget = self.text_area.text
        text_widget.configure(state=tk.NORMAL)
        text_widget.insert(tk.END, f"{speaker}: {text}\n")
        text_widget.configure(state=tk.DISABLED)
        text_widget.see(tk.END)

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
            r.adjust_for_ambient_noise(source, duration=0.5)
            while self.listening:
                try:
                    audio = r.listen(source, timeout=1, phrase_time_limit=8)
                    text = r.recognize_google(audio, language=self._language_from_voice())
                    self._append_text("You", text)
                    self.messages.append({"role": "user", "content": text})
                    threading.Thread(target=self._get_response, args=(list(self.messages),)).start()
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    self._append_text("System", "Couldn't understand audio")
                except sr.RequestError as e:
                    self._append_text("System", f"Speech recognition error: {e}")

    def _get_response(self, messages):
        try:
            response = asyncio.run(self.client.send_message(messages, None))
        except Exception as e:
            self._append_text("System", f"Error contacting API: {e}")
            return

        cleaned, image_urls = self._process_pollinations(response)
        self.messages.append({"role": "assistant", "content": response})
        if cleaned:
            self._append_text("AI", cleaned)
            if self.voice_enabled.get():
                self._speak(cleaned)
        for url in image_urls:
            self._append_image(url)

    def _play_audio(self, path: str):
        if os.name == "nt":
            import ctypes

            alias = f"vc{threading.get_ident()}"
            mci = ctypes.windll.winmm.mciSendStringW
            mci(f'open "{path}" type mpegvideo alias {alias}', None, 0, None)
            mci(f'play {alias} wait', None, 0, None)
            mci(f'close {alias}', None, 0, None)
        else:
            playsound(path)

    def _speak(self, text: str):
        sentences = [s.strip() for s in re.split(r"(?<=[.!?]) +", text) if s.strip()]
        for sentence in sentences:
            temp_name = None
            try:
                tts = gTTS(text=sentence, lang=self._language_from_voice())
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                    temp_name = fp.name
                    tts.write_to_fp(fp)
                self._play_audio(temp_name)
            except Exception as e:
                self._append_text("System", f"Audio playback failed: {e}")
            finally:
                if temp_name:
                    try:
                        os.remove(temp_name)
                    except OSError:
                        pass

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = VoiceChatApp()
    app.run()
