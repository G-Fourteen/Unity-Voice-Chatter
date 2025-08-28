import os
import re
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog
from io import BytesIO
import urllib.parse

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


class SimpleTooltip:
    def __init__(self, widget: tk.Widget):
        self.widget = widget
        self.tipwindow: tk.Toplevel | None = None

    def show(self, text: str, x: int, y: int):
        self.hide()
        if not text:
            return
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Segoe UI", 8),
        )
        label.pack(ipadx=1)

    def hide(self):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


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

        # Fetch available models
        try:
            self.models = self.client.fetch_models()
        except Exception:
            self.models = [{"name": self.config.default_model, "description": ""}]
        self.model_descriptions = {
            m.get("name", ""): m.get("description", "") for m in self.models
        }
        self.selected_model = tk.StringVar(value=self.config.default_model)

        self.listening = False
        self.listen_thread: threading.Thread | None = None

        # Keep references to images inserted in the chat to avoid garbage collection
        self._image_refs: list[ImageTk.PhotoImage] = []
        self.memories: list[str] = []

        # Audio control
        self.stop_audio = False
        self._current_audio_alias: str | None = None
        self.ignore_mic = False

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

        model_names = [m["name"] for m in self.models]
        if self.selected_model.get() not in model_names and model_names:
            self.selected_model.set(model_names[0])
        model_menu = ttk.Combobox(
            top_frame,
            textvariable=self.selected_model,
            values=model_names,
            state="readonly",
            width=25,
            style="Neon.TCombobox",
        )
        model_menu.pack(side=tk.LEFT, padx=5)
        model_menu.set(self.selected_model.get())
        self._add_model_tooltips(model_menu)

        self.start_button = ttk.Button(
            top_frame,
            text="Start Talking",
            command=self._toggle_listening,
            style="Neon.TButton",
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.mute_button = ttk.Button(
            top_frame,
            text="Mute",
            command=self._mute_audio,
            style="Neon.TButton",
        )
        self.mute_button.pack(side=tk.LEFT, padx=5)

        exit_button = ttk.Button(
            top_frame,
            text="Exit",
            command=self._exit_app,
            style="Neon.TButton",
        )
        exit_button.pack(side=tk.LEFT, padx=5)

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

        clear_button = ttk.Button(
            bottom_frame,
            text="Clear Chat",
            command=self._clear_chat,
            style="Neon.TButton",
        )
        clear_button.pack(side=tk.LEFT, padx=5)

    def _add_model_tooltips(self, combo: ttk.Combobox):
        def on_open(event):
            self.root.after(1, attach_tooltip)

        def attach_tooltip():
            try:
                popdown = combo.tk.eval(f"ttk::combobox::PopdownWindow {str(combo)}")
                popwin = self.root.nametowidget(popdown)
            except Exception:
                return
            listbox = None
            for child in popwin.winfo_children():
                if isinstance(child, tk.Listbox):
                    listbox = child
                    break
                for sub in child.winfo_children():
                    if isinstance(sub, tk.Listbox):
                        listbox = sub
                        break
                if listbox:
                    break
            if listbox is None:
                return
            tooltip = SimpleTooltip(listbox)

            def on_motion(e):
                idx = listbox.nearest(e.y)
                value = listbox.get(idx)
                desc = self.model_descriptions.get(value, "")
                tooltip.show(desc, e.x_root + 20, e.y_root + 10)

            def on_leave(e):
                tooltip.hide()

            listbox.bind("<Motion>", on_motion)
            listbox.bind("<Leave>", on_leave)

        combo.bind("<Button-1>", on_open)

    def _build_message(self, text: str):
        """Parse special tags from the AI response."""
        # Extract Markdown-style image tags without altering the URL
        md_image_pattern = r"!\[[^\]]*\]\((https?://[^\s)]+)\)"
        images = re.findall(md_image_pattern, text)
        text = re.sub(md_image_pattern, "", text)

        # Handle Pollinations image URLs that may contain spaces in the prompt.
        pollinations_urls: list[str] = []

        def _pollinations_repl(match: re.Match) -> str:
            prompt = urllib.parse.unquote(match.group(1).strip())
            query = match.group(2) or ""
            params = dict(urllib.parse.parse_qsl(query, keep_blank_values=True))
            if "model" not in params or not params["model"].strip():
                params["model"] = self.selected_model.get()
            encoded = urllib.parse.quote(prompt)
            new_query = urllib.parse.urlencode(params)
            pollinations_urls.append(
                f"https://image.pollinations.ai/prompt/{encoded}?{new_query}"
            )
            return ""

        poll_pattern = (
            r"https://image\.pollinations\.ai/prompt/([^?]+)(?:\?([^\s]+))?"
        )
        text = re.sub(poll_pattern, _pollinations_repl, text)
        images += pollinations_urls

        # Also capture any remaining bare URLs
        url_pattern = r"(https?://[^\s]+)"
        images += re.findall(url_pattern, text)
        text = re.sub(url_pattern, "", text)

        memory_pattern = r"\[memory\](.*?)\[/memory\]"
        memories = re.findall(memory_pattern, text, flags=re.DOTALL)
        text = re.sub(memory_pattern, "", text, flags=re.DOTALL)

        code_pattern = r"\[CODE\]\s*([\w#+-]*)\n(.*?)\n\[/CODE\]"
        codes = re.findall(code_pattern, text, flags=re.DOTALL)
        text = re.sub(code_pattern, "", text, flags=re.DOTALL)

        fence_pattern = r"```([\w#+-]*)\n(.*?)```"
        fence_codes = re.findall(fence_pattern, text, flags=re.DOTALL)
        text = re.sub(fence_pattern, "", text, flags=re.DOTALL)

        codes.extend(fence_codes)
        return text.strip(), images, codes, [m.strip() for m in memories]

    def _append_code_block(self, language: str, code: str):
        container = ttk.Frame(self.text_area.text, style="Neon.TFrame")

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
        yscroll.config(command=code_widget.yview)
        code_widget.insert("1.0", code)
        code_widget.configure(state=tk.DISABLED)
        code_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        text_widget = self.text_area.text
        text_widget.configure(state=tk.NORMAL)
        text_widget.window_create(tk.END, window=container)
        text_widget.insert(tk.END, "\n")
        text_widget.configure(state=tk.DISABLED)
        text_widget.see(tk.END)

    def _append_image(self, url: str):
        try:
            resp = requests.get(requests.utils.requote_uri(url), timeout=30)
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

    def _clear_chat(self):
        self.messages = [{"role": "system", "content": self.config.system_instructions}]
        text_widget = self.text_area.text
        text_widget.configure(state=tk.NORMAL)
        text_widget.delete("1.0", tk.END)
        text_widget.configure(state=tk.DISABLED)
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
        self._append_text("You", text)
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
                    self._append_text("You", text)
                    self.messages.append({"role": "user", "content": text})
                    self.ignore_mic = True
                    threading.Thread(target=self._get_response, args=(list(self.messages),)).start()
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    self._append_text("System", "Couldn't understand audio")
                except sr.RequestError as e:
                    self._append_text("System", f"Speech recognition error: {e}")

    def _get_response(self, messages):
        request_messages = (
            messages[:1]
            + [{"role": "system", "content": m} for m in self.memories]
            + messages[1:]
        )
        try:
            response = self.client.send_message(
                request_messages, self.selected_model.get()
            )
        except Exception as e:
            self._append_text("System", f"Error contacting API: {e}")
            self.ignore_mic = False
            return

        cleaned, image_urls, code_blocks, memories = self._build_message(response)
        self.messages.append({"role": "assistant", "content": cleaned})
        for mem in memories:
            self.memories.append(mem)
            self._append_text("System", f"Saved memory: {mem}")
        if cleaned:
            self._append_text("AI", cleaned)
            if self.voice_enabled.get():
                self._speak(cleaned)
            else:
                self.ignore_mic = False
        for lang, code in code_blocks:
            self._append_code_block(lang or "", code)
        for url in image_urls:
            self._append_image(url)
        if not cleaned or not self.voice_enabled.get():
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
                self._append_text("System", f"Audio playback failed: {e}")
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
