#!/usr/bin/env python3
"""
       /)  /)
      ( ^.^ )    Bunny Transcriber
      (")_(")    Voice-to-Text with Whisper

A cute and adorable voice-to-text transcriber with a bunny theme!
"""

import json
import os
import sys
import threading
import time
import wave
from datetime import datetime
from pathlib import Path

import pyaudio
import pyperclip

# Try importing openai
try:
    import openai
except ImportError:
    print("Please install openai: pip install openai")
    sys.exit(1)

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)

# ── Config ────────────────────────────────────────────────────────────

APP_NAME = "BunnyTranscriber"
CONFIG_FILENAME = "config.json"

def _get_config_path() -> Path:
    config_dir = Path.home() / ".config" / APP_NAME.lower()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / CONFIG_FILENAME

def load_config() -> dict:
    path = _get_config_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def save_config(config: dict):
    path = _get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

def get_api_key() -> str:
    return load_config().get("api_key", "")

def set_api_key(key: str):
    config = load_config()
    config["api_key"] = key
    save_config(config)

# ── Audio Recording ──────────────────────────────────────────────────

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100


class TranscriberSignals(QObject):
    """Signals emitted by the transcriber for GUI updates."""
    status_update = pyqtSignal(str)
    transcription_done = pyqtSignal(str)
    error = pyqtSignal(str)
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()


class VoiceTranscriber:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        self.frames = []
        self.stream = None
        self.recording_thread = None
        self.auto_paste = True
        self.signals = TranscriberSignals()

    def record_audio(self):
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )
        while self.is_recording:
            try:
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                self.frames.append(data)
            except Exception:
                break
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

    def start_recording(self):
        if self.is_recording:
            return
        self.is_recording = True
        self.frames = []
        self.signals.recording_started.emit()
        self.signals.status_update.emit("*wiggles ears* Listening...")
        self.recording_thread = threading.Thread(target=self.record_audio)
        self.recording_thread.daemon = True
        self.recording_thread.start()

    def stop_recording(self):
        if not self.is_recording:
            return
        self.is_recording = False
        self.signals.recording_stopped.emit()
        self.signals.status_update.emit("*nibble nibble* Processing your words...")

        if self.recording_thread:
            self.recording_thread.join(timeout=2)

        if not self.frames:
            self.signals.error.emit("No audio recorded! Try speaking louder, little one.")
            return

        # Save and transcribe in a background thread
        threading.Thread(target=self._save_and_transcribe, daemon=True).start()

    def _save_and_transcribe(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/tmp/bunny_audio_{timestamp}.wav"

        try:
            wf = wave.open(filename, "wb")
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b"".join(self.frames))
            wf.close()

            self._transcribe(filename)
        except Exception as e:
            self.signals.error.emit(f"Error saving audio: {e}")
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    def _transcribe(self, audio_file: str):
        api_key = get_api_key()
        if not api_key:
            self.signals.error.emit("No API key set! Please enter your OpenAI API key above.")
            return

        try:
            client = openai.OpenAI(api_key=api_key)
            with open(audio_file, "rb") as f:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="text",
                )

            text = response.strip()
            if text:
                pyperclip.copy(text)
                self.signals.transcription_done.emit(text)

                if self.auto_paste:
                    time.sleep(0.3)
                    try:
                        import pyautogui
                        pyautogui.typewrite(text, interval=0.01) if text.isascii() else None
                    except Exception:
                        pass
            else:
                self.signals.error.emit("No speech detected. Try speaking closer to the mic!")
        except openai.AuthenticationError:
            self.signals.error.emit("Invalid API key! Please check your key and try again.")
        except Exception as e:
            self.signals.error.emit(f"Transcription error: {e}")

    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def cleanup(self):
        self.is_recording = False
        if self.stream:
            try:
                self.stream.close()
            except Exception:
                pass
        self.audio.terminate()


# ── Bunny Theme Colors ───────────────────────────────────────────────

COLORS = {
    "bg": "#FFF5F5",
    "frame_bg": "#FFE4E6",
    "button": "#F9A8D4",
    "button_hover": "#F472B6",
    "button_pressed": "#EC4899",
    "accent": "#FDA4AF",
    "text": "#831843",
    "text_light": "#BE185D",
    "white": "#FFFFFF",
    "success": "#86EFAC",
    "success_text": "#065F46",
    "error": "#FCA5A5",
    "error_text": "#991B1B",
    "recording": "#F87171",
    "recording_pulse": "#EF4444",
}

BUNNY_IDLE = r"""   /)  /)
  ( ^.^ )
  (")_(")"""

BUNNY_HAPPY = r"""   /)  /)
  ( ^w^ )
  (")_(")"""

BUNNY_LISTENING = r"""   /)  /)
  ( o.o )
  (")_(")"""

BUNNY_WORKING = r"""   /)  /)
  ( >.<)
  (")_(")"""

BUNNY_SLEEPY = r"""   /)  /)
  ( -.- )
  (")_(")"""

import random

IDLE_MESSAGES = [
    "Hop hop! Ready to listen!",
    "Welcome to my cozy transcription burrow!",
    "*wiggles nose* What shall we transcribe?",
    "Your friendly neighborhood transcription bunny!",
    "Ready to nibble through your words!",
]

SUCCESS_MESSAGES = [
    "Yay! Got it! *happy bunny dance*",
    "Your words are ready! *wiggles tail*",
    "Transcription complete! Time for a carrot break!",
    "*happy nose wiggles* All done!",
    "Hop-pily transcribed!",
]


# ── Main Window ──────────────────────────────────────────────────────

class BunnyTranscriberWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bunny Transcriber")
        self.resize(550, 680)
        self.setMinimumSize(450, 580)

        self.transcriber = VoiceTranscriber()
        self.transcriber.signals.status_update.connect(self._on_status)
        self.transcriber.signals.transcription_done.connect(self._on_transcription)
        self.transcriber.signals.error.connect(self._on_error)
        self.transcriber.signals.recording_started.connect(self._on_recording_start)
        self.transcriber.signals.recording_stopped.connect(self._on_recording_stop)

        self._recording_blink = False
        self._blink_timer = QTimer()
        self._blink_timer.timeout.connect(self._blink_record)

        self._build_ui()
        self._apply_theme()
        self._load_api_key()
        self._set_idle()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 15, 20, 15)

        # ── Bunny Header ──
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)

        self._bunny_label = QLabel(BUNNY_IDLE)
        self._bunny_label.setFont(QFont("Courier", 16, QFont.Weight.Bold))
        self._bunny_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self._bunny_label)

        title = QLabel("Bunny Transcriber")
        title.setFont(QFont("Georgia", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)

        subtitle = QLabel("Voice-to-Text with Whisper")
        subtitle.setFont(QFont("Georgia", 11))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setProperty("class", "subtitle")
        header_layout.addWidget(subtitle)

        self._message_label = QLabel("")
        self._message_label.setFont(QFont("Georgia", 10))
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setProperty("class", "cute-message")
        self._message_label.setWordWrap(True)
        header_layout.addWidget(self._message_label)

        layout.addWidget(header)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(2)
        layout.addWidget(sep)

        # ── API Key Section ──
        api_frame = QWidget()
        api_frame.setProperty("class", "section-frame")
        api_layout = QVBoxLayout(api_frame)
        api_layout.setContentsMargins(12, 10, 12, 10)
        api_layout.setSpacing(6)

        api_header = QHBoxLayout()
        api_title = QLabel("OpenAI API Key")
        api_title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        api_header.addWidget(api_title)

        api_header.addStretch()

        self._show_key_btn = QPushButton("Show")
        self._show_key_btn.setFixedWidth(60)
        self._show_key_btn.setProperty("class", "small-btn")
        self._show_key_btn.clicked.connect(self._toggle_key_visibility)
        api_header.addWidget(self._show_key_btn)

        api_layout.addLayout(api_header)

        key_row = QHBoxLayout()
        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText("sk-... (paste your API key here)")
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setFont(QFont("Consolas", 10))
        key_row.addWidget(self._api_key_input)

        self._save_key_btn = QPushButton("Save")
        self._save_key_btn.setFixedWidth(70)
        self._save_key_btn.setProperty("class", "accent-btn")
        self._save_key_btn.clicked.connect(self._save_api_key)
        key_row.addWidget(self._save_key_btn)

        api_layout.addLayout(key_row)

        layout.addWidget(api_frame)

        # ── Record Button ──
        self._record_btn = QPushButton("Start Recording")
        self._record_btn.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
        self._record_btn.setMinimumHeight(70)
        self._record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._record_btn.setProperty("class", "record-btn")
        self._record_btn.clicked.connect(self._on_record_toggle)
        layout.addWidget(self._record_btn)

        # ── Status ──
        self._status_label = QLabel("")
        self._status_label.setFont(QFont("Georgia", 10))
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setWordWrap(True)
        self._status_label.setProperty("class", "status")
        layout.addWidget(self._status_label)

        # ── Transcript Log ──
        log_title = QLabel("Transcription Log")
        log_title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        layout.addWidget(log_title)

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setFont(QFont("Georgia", 10))
        self._log_view.setPlaceholderText(
            "*sniff sniff* No transcriptions yet...\n"
            "Click the big pink button and start talking!"
        )
        layout.addWidget(self._log_view, 1)

        # ── Options Row ──
        opts = QHBoxLayout()

        self._auto_paste_cb = QCheckBox("Auto-paste text")
        self._auto_paste_cb.setFont(QFont("Georgia", 10))
        self._auto_paste_cb.setChecked(True)
        self._auto_paste_cb.toggled.connect(self._toggle_auto_paste)
        opts.addWidget(self._auto_paste_cb)

        opts.addStretch()

        self._clear_btn = QPushButton("Clear Log")
        self._clear_btn.setProperty("class", "small-btn")
        self._clear_btn.clicked.connect(lambda: self._log_view.clear())
        opts.addWidget(self._clear_btn)

        layout.addLayout(opts)

        # ── Footer ──
        footer = QLabel("Made with love and carrots")
        footer.setFont(QFont("Georgia", 8))
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setProperty("class", "footer")
        layout.addWidget(footer)

    def _apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {COLORS['bg']};
                color: {COLORS['text']};
            }}
            QLabel {{
                color: {COLORS['text']};
                background: transparent;
            }}
            QLabel[class="subtitle"] {{
                color: {COLORS['text_light']};
                font-style: italic;
            }}
            QLabel[class="cute-message"] {{
                color: {COLORS['accent']};
            }}
            QLabel[class="footer"] {{
                color: {COLORS['accent']};
                font-style: italic;
            }}
            QLabel[class="status"] {{
                color: {COLORS['text_light']};
                padding: 4px;
            }}

            QWidget[class="section-frame"] {{
                background-color: {COLORS['frame_bg']};
                border-radius: 8px;
            }}

            QFrame {{
                background-color: {COLORS['accent']};
                border: none;
            }}

            QLineEdit {{
                background-color: {COLORS['white']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['accent']};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 10pt;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['button_hover']};
            }}

            QPushButton {{
                background-color: {COLORS['button']};
                color: {COLORS['text']};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-family: Georgia;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS['button_hover']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['button_pressed']};
            }}

            QPushButton[class="accent-btn"] {{
                background-color: {COLORS['button']};
                font-weight: bold;
            }}

            QPushButton[class="small-btn"] {{
                background-color: {COLORS['white']};
                border: 1px solid {COLORS['accent']};
                padding: 4px 10px;
                font-size: 9pt;
            }}
            QPushButton[class="small-btn"]:hover {{
                background-color: {COLORS['frame_bg']};
            }}

            QPushButton[class="record-btn"] {{
                background-color: {COLORS['button']};
                border: 3px solid {COLORS['button_hover']};
                border-radius: 12px;
                font-size: 16pt;
            }}
            QPushButton[class="record-btn"]:hover {{
                background-color: {COLORS['button_hover']};
            }}
            QPushButton[class="record-btn"]:pressed {{
                background-color: {COLORS['recording']};
                border-color: {COLORS['recording_pulse']};
            }}

            QTextEdit {{
                background-color: {COLORS['white']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['accent']};
                border-radius: 8px;
                padding: 8px;
                font-family: Georgia;
                font-size: 10pt;
            }}

            QCheckBox {{
                color: {COLORS['text']};
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {COLORS['accent']};
                border-radius: 4px;
                background-color: {COLORS['white']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['button']};
                border-color: {COLORS['button_hover']};
            }}
        """)

    # ── API Key ───────────────────────────────────────────────────────

    def _load_api_key(self):
        key = get_api_key()
        if key:
            self._api_key_input.setText(key)

    def _save_api_key(self):
        key = self._api_key_input.text().strip()
        if not key:
            self._on_error("Please enter an API key first!")
            return
        set_api_key(key)
        self._status_label.setText("API key saved! *happy hop*")
        self._status_label.setStyleSheet(f"color: {COLORS['success_text']};")

    def _toggle_key_visibility(self):
        if self._api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_key_btn.setText("Hide")
        else:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_key_btn.setText("Show")

    # ── Recording ─────────────────────────────────────────────────────

    def _on_record_toggle(self):
        if self.transcriber.is_recording:
            self.transcriber.stop_recording()
            return
        if not get_api_key() and not self._api_key_input.text().strip():
            self._on_error("Please set your API key first!")
            return
        # Auto-save key if entered but not yet saved
        if self._api_key_input.text().strip() and not get_api_key():
            self._save_api_key()
        self.transcriber.start_recording()

    def _on_recording_start(self):
        self._bunny_label.setText(BUNNY_LISTENING)
        self._record_btn.setText("Listening...")
        self._record_btn.setStyleSheet(
            f"background-color: {COLORS['recording']};"
            f"border: 3px solid {COLORS['recording_pulse']};"
            f"border-radius: 12px; font-size: 16pt; font-weight: bold;"
            f"color: white;"
        )
        self._blink_timer.start(500)

    def _on_recording_stop(self):
        self._blink_timer.stop()
        self._record_btn.setText("Start Recording")
        self._record_btn.setStyleSheet("")  # Reset to theme default
        self._bunny_label.setText(BUNNY_WORKING)

    def _blink_record(self):
        self._recording_blink = not self._recording_blink
        if self._recording_blink:
            self._record_btn.setText("Listening...")
        else:
            self._record_btn.setText("* Recording *")

    # ── Signals ───────────────────────────────────────────────────────

    def _on_status(self, msg: str):
        self._status_label.setText(msg)
        self._status_label.setStyleSheet(f"color: {COLORS['text_light']};")

    def _on_transcription(self, text: str):
        self._bunny_label.setText(BUNNY_HAPPY)
        msg = random.choice(SUCCESS_MESSAGES)
        self._message_label.setText(msg)
        self._status_label.setText("Copied to clipboard!")
        self._status_label.setStyleSheet(f"color: {COLORS['success_text']};")

        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_view.append(f"[{timestamp}] {text}\n")

        # Reset bunny after a moment
        QTimer.singleShot(3000, self._set_idle)

    def _on_error(self, msg: str):
        self._bunny_label.setText(BUNNY_SLEEPY)
        self._message_label.setText("*sad bunny noises*")
        self._status_label.setText(msg)
        self._status_label.setStyleSheet(f"color: {COLORS['error_text']};")
        QTimer.singleShot(5000, self._set_idle)

    def _set_idle(self):
        self._bunny_label.setText(BUNNY_IDLE)
        self._message_label.setText(random.choice(IDLE_MESSAGES))
        self._status_label.setText("")

    # ── Options ───────────────────────────────────────────────────────

    def _toggle_auto_paste(self, checked: bool):
        self.transcriber.auto_paste = checked

    # ── Cleanup ───────────────────────────────────────────────────────

    def closeEvent(self, event):
        self.transcriber.cleanup()
        super().closeEvent(event)


def main():
    print(r"""
       /)  /)
      ( ^.^ )    Starting Bunny Transcriber...
      (")_(")
    """)

    app = QApplication(sys.argv)
    app.setApplicationName("Bunny Transcriber")
    app.setStyle("Fusion")

    window = BunnyTranscriberWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
