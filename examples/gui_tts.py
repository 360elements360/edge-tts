import tkinter as tk
from tkinter import ttk, filedialog
import edge_tts
import asyncio
from threading import Thread
import pygame
import os

class TTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Edge TTS GUI")
        self.root.geometry("500x350")
        
        # Text input
        self.text_label = tk.Label(root, text="Enter text:")
        self.text_label.pack(pady=5)
        
        self.text_entry = tk.Text(root, height=10, width=50)
        self.text_entry.pack(pady=5)
        
        # Voice selection
        self.voice_label = tk.Label(root, text="Select voice:")
        self.voice_label.pack(pady=5)
        
        self.voice_var = tk.StringVar()
        self.voice_combobox = ttk.Combobox(root, textvariable=self.voice_var)
        self.voice_combobox.pack(pady=5)
        
        # Status label
        self.status_label = tk.Label(root, text="", fg="blue")
        self.status_label.pack(pady=5)
        
        # Button frame
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=10)
        
        # Submit button
        self.submit_button = tk.Button(self.button_frame, text="Generate", command=self.generate_audio)
        self.submit_button.pack(side=tk.LEFT, padx=5)
        
        # Play controls
        self.play_button = tk.Button(self.button_frame, text="Play", command=self.play_audio, state=tk.DISABLED)
        self.play_button.pack(side=tk.LEFT, padx=5)
        
        self.pause_button = tk.Button(self.button_frame, text="Pause", command=self.pause_audio, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(self.button_frame, text="Stop", command=self.stop_audio, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Save button
        self.save_button = tk.Button(self.button_frame, text="Save", command=self.save_audio, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        # Get voices
        self.voices = asyncio.run(self.get_voices())
        self.voice_combobox['values'] = [v['ShortName'] for v in self.voices]
        if self.voices:
            self.voice_combobox.current(0)
            
        self.generated_file = None
    
    async def get_voices(self):
        voices = await edge_tts.VoicesManager.create()
        # Filter for English US voices only
        return [v for v in voices.voices if 'en-US' in v['ShortName']]
    
    def generate_audio(self):
        text = self.text_entry.get("1.0", tk.END).strip()
        voice = self.voice_var.get()
        
        if not text:
            self.status_label.config(text="Please enter some text", fg="red")
            return
            
        if len(text) > 5000:
            self.status_label.config(text="Text too long (max 5000 chars)", fg="red")
            return
            
        self.status_label.config(text="Generating audio...", fg="blue")
        self.submit_button.config(state=tk.DISABLED)
        self.play_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)
        
        def run_tts():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._generate_tts(text, voice))
            except Exception as e:
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Generation error: {str(e)}", fg="red"))
                self.root.after(0, lambda: self.submit_button.config(state=tk.NORMAL))
            finally:
                loop.close()
                
        Thread(target=run_tts, daemon=True).start()
    
    async def _generate_tts(self, text, voice):
        try:
            self.generated_file = "output.mp3"
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(self.generated_file)
            
            self.root.after(0, lambda: self.status_label.config(text="Audio generated", fg="green"))
            self.root.after(0, lambda: self.play_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.pause_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.save_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.submit_button.config(state=tk.NORMAL))
            
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Error: {str(e)}", fg="red"))
            self.root.after(0, lambda: self.submit_button.config(state=tk.NORMAL))
    
    def play_audio(self):
        if not self.generated_file or not os.path.exists(self.generated_file):
            self.status_label.config(text="No audio to play", fg="red")
            return
            
        try:
            self.status_label.config(text="Playing audio...", fg="green")
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
                
            # Clear any previous playback
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                
            pygame.mixer.music.load(self.generated_file)
            pygame.mixer.music.play()
            
            # Start monitoring playback
            self.monitor_playback()
            
        except Exception as e:
            self.status_label.config(text=f"Playback error: {str(e)}", fg="red")
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            self.disable_playback_controls()
            
    def monitor_playback(self):
        if pygame.mixer.music.get_busy():
            self.root.after(100, self.monitor_playback)
        else:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            self.status_label.config(text="Playback complete", fg="green")
            self.disable_playback_controls()
            
    def disable_playback_controls(self):
        self.pause_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.pause_button.config(text="Pause", command=self.pause_audio)
    
    def pause_audio(self):
        if pygame.mixer.music.get_busy():
            try:
                pygame.mixer.music.pause()
                self.status_label.config(text="Playback paused", fg="blue")
                self.pause_button.config(text="Resume", command=self.resume_audio)
            except Exception as e:
                self.status_label.config(text=f"Pause error: {str(e)}", fg="red")
            
    def resume_audio(self):
        try:
            pygame.mixer.music.unpause()
            self.status_label.config(text="Playback resumed", fg="blue")
            self.pause_button.config(text="Pause", command=self.pause_audio)
            self.monitor_playback()
        except Exception as e:
            self.status_label.config(text=f"Resume error: {str(e)}", fg="red")
        
    def stop_audio(self):
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                self.status_label.config(text="Playback stopped", fg="blue")
                self.pause_button.config(text="Pause", command=self.pause_audio)
                self.disable_playback_controls()
        except Exception as e:
            self.status_label.config(text=f"Stop error: {str(e)}", fg="red")
        
    def save_audio(self):
        if not self.generated_file or not os.path.exists(self.generated_file):
            self.status_label.config(text="No audio to save", fg="red")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 files", "*.mp3")],
            title="Save audio file"
        )
        
        if file_path:
            try:
                os.replace(self.generated_file, file_path)
                self.status_label.config(text=f"Audio saved to {file_path}", fg="green")
                self.generated_file = None
                self.play_button.config(state=tk.DISABLED)
                self.save_button.config(state=tk.DISABLED)
            except Exception as e:
                self.status_label.config(text=f"Save error: {str(e)}", fg="red")

if __name__ == "__main__":
    root = tk.Tk()
    app = TTSApp(root)
    root.mainloop()
