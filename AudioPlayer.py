import alsaaudio
import wave
import threading

class AudioPlayer:
    def __init__(self):
        self.output = None
        self.wave_file = None
        self.mixer = None
        self.is_playing = False
        self.playback_thread = None
        self.stop_signal = threading.Event()
        self.audio_lock = threading.Lock()
        self.audio_file_path = None

        self.playback_thread = threading.Thread(target=self.play_audio)
        self.playback_thread.daemon = True
        self.playback_thread.start()

        self.mixer = alsaaudio.Mixer('PCM')
    
    def start_audio(self, file_path, vol):
        with self.audio_lock:
            self.audio_file_path = file_path
            self.is_playing = True
            self.stop_signal.clear()

            # self.playback_thread.join() #

            self.mixer.setvolume(vol)
            print(f'Volume is {vol}')

            # self.playback_thread = threading.Thread(target=self.play_audio)
            # self.playback_thread.daemon = True
            # self.playback_thread.start()
    
    def play_audio(self):
        while True:
            if self.is_playing and self.audio_file_path:
                with self.audio_lock:
                    if self.wave_file:
                        self.wave_file.close()
                    try:
                        self.wave_file = wave.open(self.audio_file_path, 'rb')
                        self.output = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK)
                        self.output.setchannels(self.wave_file.getnchannels())
                        self.output.setrate(self.wave_file.getframerate())
                        self.output.setformat(alsaaudio.PCM_FORMAT_S16_LE)
                        self.output.setperiodsize(320)
                    except Exception as e:
                        print(f"Error opening audio file: {e}")
                        self.is_playing = False
            
                while self.is_playing and not self.stop_signal.is_set():
                    data = self.wave_file.readframes(320)
                    if not data:
                        self.wave_file.rewind()
                        data = self.wave_file.readframes(320)
                    
                    try:
                        self.output.write(data)
                    except alsaaudio.ALSAAudioError as e:
                        print(f"ALSA Audio error: {e}")
                        self.stop_audio()
                        break
            
            else:
                self.stop_signal.wait(0.1)

    
    def set_volume(self, vol):
        if self.mixer:
            self.mixer.setvolume(vol)
            print(f'Volume adjusted to {vol}')
        else:
            print("Audio is not playing.")
    
    def stop_audio(self):
        with self.audio_lock:
            self.is_playing = False
            self.stop_signal.set()
            if self.output:
                self.output.close()
                self.output = None
            if self.wave_file:
                self.wave_file.close()
                self.wave_file = None
            print("Audio stopped")

# class AudioPlayer:
#     def __init__(self):
#         self.output = None
#         self.wave_file = None
#         self.mixer = None
#         self.is_playing = False
#         self.playback_thread = None
#         self.stop_event = threading.Event()
    
#     def start_audio(self, file_path, vol):
#         print(file_path)
#         if self.is_playing:
#             print("Audio is already playing.")
#             return
        
#         #Create and set PCM
#         self.output = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK)
#         self.wave_file = wave.open(file_path, 'rb')
        
#         #Create Mixer and Set Volume
#         self.output.setchannels(self.wave_file.getnchannels())
#         self.output.setrate(self.wave_file.getframerate())
#         self.output.setformat(alsaaudio.PCM_FORMAT_S16_LE)
#         self.output.setperiodsize(320)
        
#         self.mixer = alsaaudio.Mixer('PCM')
#         self.mixer.setvolume(vol)
#         print(f'Volume is {vol}')
        
#         #Repeat read and write data
#         self.is_playing = True
#         self.stop_event.clear()
#         self.playback_thread = threading.Thread(target=self._play_audio)
#         self.playback_thread.start()
    
#     def _play_audio(self):
#         try:
#             while self.is_playing and not self.stop_event.is_set():
#                 data = self.wave_file.readframes(320)
                
#                 if not data:
#                     self.wave_file.rewind()
#                     data = self.wave_file.readframes(320)
                
#                 try:
#                     self.output.write(data)
#                 except alsaaudio.ALSAAudioError as e:
#                     print(f"ALSA Audio error: {e}")
#                     self.stop_audio()
#                     break
#             self.stop_audio()
#         except Exception as e:
#             print(f"Unexpected error: {e}")
#             self.stop_audio()
    
#     def set_volume(self, vol):
#         if self.mixer is not None:
#             self.mixer.setvolume(vol)
#             print(f'Volume adjusted to {vol}')
#         else:
#             print("Audio is not playing.")
    
#     def stop_audio(self):
#         print("Stopping Audio...")
#         if self.output is not None:
#             self.stop_event.set()

#             if self.playback_thread and self.playback_thread != threading.current_thread():
#                 self.playback_thread.join()
            
#             self.output.close()
#             self.output = None
#             self.mixer = None
#             self.is_playing = False
#             print("Audio stopped.")
#         else:
#             print("Audio is not playing.")