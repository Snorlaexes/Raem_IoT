from pydub import AudioSegment
import simpleaudio as sa
import threading
import time

class AudioPlayer:
    _instance = None

    @staticmethod
    def getInstance():
        if AudioPlayer._instance is None:
            AudioPlayer._instance = AudioPlayer()
        return AudioPlayer._instance

    def __init__(self):
        if AudioPlayer._instance is not None:
            raise Exception("This is a Singleton Class")
        
        # Attributes for audio playback
        self.audio_file_path = None
        self.is_playing = False
        self.playback_thread = None
        self.stop_signal = threading.Event()
        self.audio_lock = threading.Lock()
        self.play_obj = None

    def start_audio(self, file_path, volume):
        with self.audio_lock:
            self.audio_file_path = file_path
            self.is_playing = True
            self.stop_signal.clear()

            # Load the audio file with pydub
            self.audio = AudioSegment.from_file(file_path)
            self.audio = self.audio + volume  # Adjust volume

            # If playback thread is not running, start it
            if not self.playback_thread or not self.playback_thread.is_alive():
                self.playback_thread = threading.Thread(target=self.play_audio)
                self.playback_thread.daemon = True
                self.playback_thread.start()

    def play_audio(self):
        while self.is_playing:
            with self.audio_lock:
                # Convert the pydub AudioSegment to raw audio data for simpleaudio
                raw_data = self.audio.raw_data
                sample_rate = self.audio.frame_rate
                num_channels = self.audio.channels
                bytes_per_sample = self.audio.sample_width

                try:
                    # Start playback
                    self.play_obj = sa.play_buffer(raw_data, num_channels, bytes_per_sample, sample_rate)
                    self.play_obj.wait_done()  # Wait until playback is done
                except Exception as e:
                    print(f"Error during playback: {e}")
                    self.stop_audio()

                # Rewind if needed
                if not self.stop_signal.is_set():
                    self.play_obj = None  # Reset play_obj for next playback if looping

    def stop_audio(self):
        with self.audio_lock:
            self.is_playing = False
            self.stop_signal.set()
            if self.play_obj:
                self.play_obj.stop()
                self.play_obj = None
            print("Audio stopped")

    def set_volume(self, volume):
        with self.audio_lock:
            if self.audio:
                # Adjust the volume by reloading the file with new volume
                self.audio = AudioSegment.from_file(self.audio_file_path)
                self.audio = volume
                print(f"Volume set to {volume}")

# # Usage example
# player = AudioPlayer.getInstance()
# player.start_audio('path/to/audio/file.mp3', volume=10)  # Adjust the volume as desired
# time.sleep(5)  # Let the audio play for a bit
# player.stop_audio()
