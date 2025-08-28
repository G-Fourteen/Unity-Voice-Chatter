import os
import re
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog
from io import BytesIO
import urllib.request
import ttkbootstrap as ttk
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
        self.root.option_add("*Foreground", "#39FF14")
        self.root.option_add("*Background", "black")
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
        border_opts = {
            "bordercolor": neon,
            "lightcolor": neon,
            "darkcolor": neon,
            "focuscolor": neon,
            "focusthickness": 1,
        }
        self._style.configure("Neon.TFrame", background="black", **border_opts)
        self._style.configure(
            "Neon.TCheckbutton", background="black", foreground=neon, **border_opts
        )
        self._style.configure(
            "Neon.TButton", background="black", foreground=neon, **border_opts
        )
        self._style.configure(
            "Neon.TEntry",
            fieldbackground="black",
            foreground=neon,
            insertcolor=neon,
            **border_opts,
        )
        self._style.configure(
            "Neon.TCombobox",
            fieldbackground="black",
            foreground=neon,
            background="black",
            **border_opts,
        )
        self._style.configure("Neon.TLabel", background="black", foreground=neon)
        self.neon = neon

        self.voice_enabled = tk.BooleanVar(value=True)
        self.selected_voice = tk.StringVar()
        self.models = self.client.fetch_models()
        if self.config.default_model not in self.models:
            self.models.insert(0, self.config.default_model)
        self.selected_model = tk.StringVar(value=self.config.default_model)
        self.messages = [
            {"role": "system", "content": self.config.system_instructions}
        ]

        self.listening = False
        self.listen_thread: threading.Thread | None = None

        # Keep references to images inserted in the chat to avoid garbage collection
        self._image_refs: list[ImageTk.PhotoImage] = []

        # Audio control
        self.stop_audio = False
        self._current_audio_alias: str | None = None
        self.ignore_mic = False

        self._build_ui()

    def _apply_highlight(self, widget) -> None:
        """Safely apply neon highlight to a widget if supported."""
        try:
            widget.configure(
                highlightthickness=1,
                highlightbackground=self.neon,
                highlightcolor=self.neon,
            )
        except tk.TclError:
            pass

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
        self._apply_highlight(voice_check)
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
        self._apply_highlight(voice_menu)
        voice_menu.pack(side=tk.LEFT, padx=5)
        voice_menu.bind(
            "<<ComboboxSelected>>",
            lambda e: self.selected_voice.set(self.voice_map[self.voice_display.get()]),
        )

        model_menu = ttk.Combobox(
            top_frame,
            textvariable=self.selected_model,
            values=self.models,
            state="readonly",
            width=35,
            style="Neon.TCombobox",
        )
        self._apply_highlight(model_menu)
        model_menu.pack(side=tk.LEFT, padx=5)

        self.start_button = ttk.Button(
            top_frame,
            text="Start Talking",
            command=self._toggle_listening,
            style="Neon.TButton",
        )
        self._apply_highlight(self.start_button)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.mute_button = ttk.Button(
            top_frame,
            text="Mute",
            command=self._mute_audio,
            style="Neon.TButton",
        )
        self._apply_highlight(self.mute_button)
        self.mute_button.pack(side=tk.LEFT, padx=5)

        exit_button = ttk.Button(
            top_frame,
            text="Exit",
            command=self._exit_app,
            style="Neon.TButton",
        )
        self._apply_highlight(exit_button)
        exit_button.pack(side=tk.LEFT, padx=5)

        chat_container = ttk.Frame(self.root, style="Neon.TFrame")
        chat_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas = tk.Canvas(chat_container, bg="black", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar = ttk.Scrollbar(
            chat_container, orient=tk.VERTICAL, command=self.canvas.yview
        )
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.chat_frame = ttk.Frame(self.canvas, style="Neon.TFrame")
        self.chat_window = self.canvas.create_window(
            (0, 0), window=self.chat_frame, anchor="nw"
        )
        self.chat_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self.chat_window, width=e.width),
        )

        bottom_frame = ttk.Frame(self.root, padding=5, style="Neon.TFrame")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.entry = tk.Entry(
            bottom_frame,
            bg="black",
            fg=self.neon,
            insertbackground=self.neon,
        )
        self._apply_highlight(self.entry)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entry.bind("<Return>", lambda event: self._send_text())

        send_button = ttk.Button(
            bottom_frame,
            text="Send",
            command=self._send_text,
            style="Neon.TButton",
        )
        self._apply_highlight(send_button)
        send_button.pack(side=tk.LEFT)

        clear_button = ttk.Button(
            bottom_frame,
            text="Clear Chat",
            command=self._clear_chat,
            style="Neon.TButton",
        )
        self._apply_highlight(clear_button)
        clear_button.pack(side=tk.LEFT, padx=5)

    def _build_message(self, content):
        """Parse message content and extract text and image URLs."""

        text = ""
        image_urls: list[str] = []
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        parts.append(item.get("text", ""))
                    elif item.get("type") == "image_url":
                        url = item.get("image_url", {}).get("url")
                        if url:
                            image_urls.append(url)
            text = "\n".join(parts)
        else:
            text = "" if content is None else str(content)

        # Extract [IMAGE](url) tags from the text
        for url in re.findall(r"\[IMAGE\]\(([^)]+)\)", text):
            image_urls.append(url)
        text = re.sub(r"\[IMAGE\]\([^)]+\)", "", text).strip()

        return text, image_urls, [], []

    def _append_code_block(self, language: str, code: str):
        container = ttk.Frame(self.chat_frame, style="Neon.TFrame")

        header = ttk.Frame(container, style="Neon.TFrame")
        header.pack(fill=tk.X)

        def copy_code():
            self.root.clipboard_clear()
            self.root.clipboard_append(code)

        def download_code():
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            )
            if filename:
                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(code)
                except OSError:
                    pass

        ttk.Button(header, text="Copy", command=copy_code, style="Neon.TButton").pack(
            side=tk.RIGHT
        )
        ttk.Button(
            header, text="Download", command=download_code, style="Neon.TButton"
        ).pack(side=tk.RIGHT)

        text_frame = ttk.Frame(container, style="Neon.TFrame")
        text_frame.pack(fill=tk.BOTH, expand=True)

        yscroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        code_widget = tk.Text(
            text_frame,
            height=max(1, code.count("\n") + 1),
            width=60,
            wrap=tk.NONE,
            yscrollcommand=yscroll.set,
            bg="black",
            fg=self.neon,
            insertbackground=self.neon,
        )
        self._apply_highlight(code_widget)
        yscroll.config(command=code_widget.yview)
        code_widget.insert("1.0", code)
        code_widget.configure(state=tk.DISABLED)
        code_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        container.pack(anchor="w", fill=tk.X, padx=10, pady=4)
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def _append_image(self, url: str, speaker: str | None = "AI"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                image_data = BytesIO(resp.read())
            img = Image.open(image_data)
            photo = ImageTk.PhotoImage(img)
            bubble = ttk.Frame(self.chat_frame, style="Neon.TFrame")
            if speaker:
                tag_label = tk.Label(
                    bubble,
                    text=speaker,
                    font=("Segoe UI", 12, "bold"),
                    bg="black",
                    fg=self.neon,
                )
                self._apply_highlight(tag_label)
                tag_label.pack(anchor="w")
            label = tk.Label(
                bubble,
                image=photo,
                bg="black",
            )
            self._apply_highlight(label)
            label.image = photo
            label.pack(anchor="w")
            bubble.pack(anchor="w", padx=10, pady=4)
            self._image_refs.append(photo)
            self.canvas.update_idletasks()
            self.canvas.yview_moveto(1.0)
        except Exception as e:
            self._append_text("System", f"Failed to load image: {e}", role="system")

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

    def _append_text(self, speaker: str, text: str, role: str = "system"):
        bubble = ttk.Frame(self.chat_frame, style="Neon.TFrame")
        tag_label = tk.Label(
            bubble,
            text=speaker,
            font=("Segoe UI", 12, "bold"),
            bg="black",
            fg=self.neon,
        )
        self._apply_highlight(tag_label)
        tag_label.pack(anchor="e" if role == "user" else "w")
        msg_label = tk.Label(
            bubble,
            text=text,
            wraplength=400,
            justify=tk.RIGHT if role == "user" else tk.LEFT,
            bg="black",
            fg=self.neon,
            padx=10,
            pady=6,
            font=("Segoe UI", 10),
        )
        self._apply_highlight(msg_label)
        msg_label.pack(anchor="e" if role == "user" else "w")
        bubble.pack(anchor="e" if role == "user" else "w", padx=10, pady=4, fill=tk.X)
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def _clear_chat(self):
        self.messages = [{"role": "system", "content": self.config.system_instructions}]
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        self.stop_audio = True
        self.ignore_mic = False

    def _mute_audio(self):
        self.stop_audio = True
        self.ignore_mic = False
        if os.name == "nt" and self._current_audio_alias:
            import ctypes

            mci = ctypes.windll.winmm.mciSendStringW
            mci(f"stop {self._current_audio_alias}", None, 0, None)
            mci(f"close {self._current_audio_alias}", None, 0, None)
            self._current_audio_alias = None

    def _exit_app(self):
        self.listening = False
        self.root.destroy()

    def _send_text(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        self._append_text("You", text, role="user")
        self.messages.append({"role": "user", "content": text})
        self.ignore_mic = True
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
                if self.ignore_mic:
                    time.sleep(0.1)
                    continue
                try:
                    audio = r.listen(source, timeout=1, phrase_time_limit=8)
                    text = r.recognize_google(audio, language=self._language_from_voice())
                    self._append_text("You", text, role="user")
                    self.messages.append({"role": "user", "content": text})
                    self.ignore_mic = True
                    threading.Thread(target=self._get_response, args=(list(self.messages),)).start()
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    self._append_text("System", "Couldn't understand audio", role="system")
                except sr.RequestError as e:
                    self._append_text("System", f"Speech recognition error: {e}", role="system")

    def _get_response(self, messages):
        try:
            response = self.client.send_message(
                messages, self.selected_model.get()
            )
        except Exception as e:
            self._append_text("System", f"Error contacting API: {e}", role="system")
            self.ignore_mic = False
            return

        text, image_urls, code_blocks, memories = self._build_message(response)
        assistant_content = text if text else "[No content]"
        self.messages.append({"role": "assistant", "content": assistant_content})
        for mem in memories:
            self.messages.append({"role": "system", "content": mem})
            self._append_text("System", f"Saved memory: {mem}", role="system")
        if text:
            self._append_text("AI", text, role="assistant")
            if self.voice_enabled.get():
                self._speak(text)
            else:
                self.ignore_mic = False
        for lang, code in code_blocks:
            self._append_code_block(lang or "", code)
        for url in image_urls:
            self._append_image(url, speaker=None if text else "AI")
        if not text or not self.voice_enabled.get():
            self.ignore_mic = False

    def _play_audio(self, path: str):
        if os.name == "nt":
            import ctypes

            alias = "vc_audio"
            self._current_audio_alias = alias
            mci = ctypes.windll.winmm.mciSendStringW
            mci(f'open "{path}" type mpegvideo alias {alias}', None, 0, None)
            mci(f'play {alias}', None, 0, None)
            while True:
                if self.stop_audio:
                    mci(f'stop {alias}', None, 0, None)
                    break
                status_buf = ctypes.create_unicode_buffer(32)
                mci(f'status {alias} mode', status_buf, 32, None)
                if status_buf.value == "stopped":
                    break
                time.sleep(0.1)
            mci(f'close {alias}', None, 0, None)
            self._current_audio_alias = None
        else:
            playsound(path)

    def _speak(self, text: str):
        self.ignore_mic = True
        sentences = [s.strip() for s in re.split(r"(?<=[.!?]) +", text) if s.strip()]
        self.stop_audio = False
        for sentence in sentences:
            if self.stop_audio:
                break
            temp_name = None
            try:
                tts = gTTS(text=sentence, lang=self._language_from_voice())
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                    temp_name = fp.name
                    tts.write_to_fp(fp)
                self._play_audio(temp_name)
            except Exception as e:
                self._append_text("System", f"Audio playback failed: {e}", role="system")
            finally:
                if temp_name:
                    try:
                        os.remove(temp_name)
                    except OSError:
                        pass
        self.stop_audio = False
        self.ignore_mic = False

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = VoiceChatApp()
    app.run()
