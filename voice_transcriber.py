import pyaudio
import wave
import keyboard
import openai
import pyperclip
import pyautogui
import os
import threading
import time
from datetime import datetime

# Set your OpenAI API key here
openai.api_key = ""  # Key removed for security - use Bunny Transcriber GUI instead

# Audio recording settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class VoiceTranscriber:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        self.frames = []
        self.stream = None
        self.recording_thread = None
        self.auto_paste = True  # Toggle for auto-paste feature
        
    def record_audio(self):
        """Record audio in a separate thread"""
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        while self.is_recording:
            try:
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                self.frames.append(data)
            except:
                break
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            
    def start_recording(self):
        """Start recording audio"""
        if self.is_recording:
            return
            
        print("🎤 Recording started... Press F9 again to stop")
        self.is_recording = True
        self.frames = []
        
        # Start recording in a separate thread
        self.recording_thread = threading.Thread(target=self.record_audio)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
    def stop_recording(self):
        """Stop recording and save audio file"""
        if not self.is_recording:
            return
            
        print("⏹️ Recording stopped. Processing...")
        self.is_recording = False
        
        # Wait for recording thread to finish
        if self.recording_thread:
            self.recording_thread.join(timeout=1)
        
        if not self.frames:
            print("❌ No audio recorded")
            return
        
        # Save the recorded audio to a file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"temp_audio_{timestamp}.wav"
        
        try:
            wf = wave.open(filename, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(self.frames))
            wf.close()
            
            # Transcribe the audio
            self.transcribe_audio(filename)
            
            # Clean up - delete the temporary audio file
            os.remove(filename)
            
        except Exception as e:
            print(f"❌ Error saving audio: {str(e)}")
        
    def transcribe_audio(self, audio_file):
        """Send audio to OpenAI for transcription"""
        try:
            print("🤖 Transcribing...")
            with open(audio_file, "rb") as file:
                response = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=file,
                    response_format="text"
                )
                
            transcribed_text = response.strip()
            
            if transcribed_text:
                print("✅ Transcription completed!")
                print(f"📝 Text: {transcribed_text}")
                
                # Copy to clipboard
                pyperclip.copy(transcribed_text)
                print("📋 Text copied to clipboard!")
                
                # Auto-paste if enabled
                if self.auto_paste:
                    # Small delay to ensure the user can switch windows if needed
                    time.sleep(0.5)
                    pyautogui.write(transcribed_text)
                    print("⌨️ Text auto-pasted!")
                
                print("-" * 40)
                
            else:
                print("❌ No speech detected. Try speaking louder or closer to the microphone.")
                
        except Exception as e:
            print(f"❌ Error during transcription: {str(e)}")
    
    def toggle_auto_paste(self):
        """Toggle auto-paste feature on/off"""
        self.auto_paste = not self.auto_paste
        status = "ON" if self.auto_paste else "OFF"
        print(f"🔄 Auto-paste is now {status}")
    
    def toggle_recording(self):
        """Toggle between start and stop recording"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def cleanup(self):
        """Clean up audio resources"""
        self.is_recording = False
        if self.stream:
            self.stream.close()
        self.audio.terminate()

def main():
    print("🎙️ Voice-to-Text Transcriber Ready!")
    print("Press F9 to start/stop recording")
    print("Press F10 to toggle auto-paste ON/OFF")
    print("Press ESC to quit")
    print("-" * 40)
    
    transcriber = VoiceTranscriber()
    
    # Set up hotkeys
    keyboard.add_hotkey('f9', transcriber.toggle_recording)
    keyboard.add_hotkey('f10', transcriber.toggle_auto_paste)
    
    try:
        # Keep the program running and check for ESC key
        while True:
            if keyboard.is_pressed('esc'):
                break
            time.sleep(0.1)  # Small delay to prevent high CPU usage
            
    except KeyboardInterrupt:
        pass
    finally:
        transcriber.cleanup()
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error starting program: {str(e)}")
        print("Press any key to close...")
        input()