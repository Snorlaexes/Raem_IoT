import alsaaudio
import wave
import threading
import time

class AudioPlayer:
    _instance = None

    @staticmethod
    def getInstance():
        if AudioPlayer._instance is None:
            return AudioPlayer()
        else:
            return AudioPlayer._instance

    def __init__(self):
        if AudioPlayer._instance is not None:
            raise Exception("AudioPlayer is a Singleton Class")
        else:
            self.output = None
            self.wave_file = None
            self.mixer = alsaaudio.Mixer('PCM')
            self.is_playing = False
            self.playback_thread = None
            self.update_event = threading.Event()
            self.audio_lock = threading.Lock()
            self.audio_file_path = None
            self.volume = 0

    def start(self):
        if not self.is_playing:
            self.is_playing = True
            self.playback_thread = threading.Thread(target=self.run)
            self.playback_thread.daemon = True
            self.playback_thread.start()
    
    def run(self):
        while self.is_playing:
            self.update_event.wait()
            with self.audio_lock:
                self.play(self.audio_file_path, self.volume)
            self.update_event.clear()

    def update_music(self, music_path, volume):
        with self.audio_lock:
            self.audio_file_path = music_path
            self.volume = volume
        self.update_event.set()

    def play(self, music_path, volume):
        # 오디오 파일 열기
        try:
            self.wave_file = wave.open(music_path, 'rb')
            self.output = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, device='sysdefault:CARD=Audio')
            self.output.setchannels(self.wave_file.getnchannels())
            self.output.setrate(self.wave_file.getframerate())
            self.output.setformat(alsaaudio.PCM_FORMAT_S16_LE)
            self.output.setperiodsize(2048)
        except Exception as e:
            print(f"Error opening audio file: {e}")
            self.is_playing = False
            return  # 함수 종료

        self.mixer.setvolume(volume)  # 볼륨 설정

        while self.is_playing:
            data = self.wave_file.readframes(2048)
            if not data:
                print("End of audio file reached. Rewinding...")
                self.wave_file.rewind()  # 파일의 처음으로 되돌리기
                continue  # 루프를 계속하여 다시 재생

            try:
                if not self.is_playing:
                    break
                self.output.write(data)
            except alsaaudio.ALSAAudioError as e:
                print(f"ALSA Audio error: {e}")
                self.stop()
                break

        # 재생 종료 후 자원 정리
        self.stop()

    def set_volume(self, vol):
        if self.mixer:
            self.mixer.setvolume(vol)
            print(f'Volume adjusted to {vol}')
        else:
            print("Audio is not playing.")

    def stop(self):
        if self.is_playing:
            self.is_playing = False
            self.update_event.set()

            if self.output is not None:
                print("Closing PCM output")
                self.output.close()
                time.sleep(0.2)
                self.output = None

            if self.wave_file is not None:
                print("Closing wave file")
                self.wave_file.close()
                time.sleep(0.2)
                self.wave_file = None
            
            if self.playback_thread is not None:
                self.playback_thread.join()
                self.playback_thread = None

            print("Audio stopped")