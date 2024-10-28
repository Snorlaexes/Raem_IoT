import threading
import time
import board
import neopixel

class LEDController:
    _instance = None

    @staticmethod
    def getInstance() :
        if LEDController._instance is None:
            return LEDController()
        else :
            return LEDController._instance
        
    def __init__(self):
        if LEDController._instance is not None:
            raise Exception("LEDController is a Singleton Class")
        else:
            self.red = 0.0
            self.green = 0.0
            self.blue = 0.0
            self.steps = 0
            self.is_running = False
            self.light_thread = None
            self.update_event = threading.Event()
            self.light_lock = threading.Lock()
    
    def start(self):
        if not self.is_running:
            self.is_running = True
            self.light_thread = threading.Thread(target=self.run)
            self.light_thread.daemon = True
            self.light_thread.start()
    
    def run(self):
        while self.is_running:
            self.update_event.wait()
            with self.light_lock:
                self.controllerLED(self.red, self.green, self.blue, self.steps)
            self.update_event.clear()

    def controllerLED(self, r, g, b, steps):
        if steps > -1 : # -1이 아니면 점진적으로 켜짐
            stepRed = r/steps
            stepGreen = g/steps
            stepBlue = b/steps

            currentRed, currentGreen, currentBlue = 0.0000, 0.0000, 0.0000
            for _ in range(steps):
                currentRed += stepRed
                currentGreen += stepGreen
                currentBlue += stepBlue

                pixels=neopixel.NeoPixel(board.D18, 30)
                pixels.fill((currentRed, currentGreen, currentBlue))
                pixels.show()

                time.sleep(0.1)

        else: # -1이면 바로 켜짐
            pixels=neopixel.NeoPixel(board.D18, 30)
            pixels.fill((r, g, b))
            pixels.show()
    

    def update_color(self, r, g, b, steps):
        with self.light_lock:
            self.red = r
            self.green = g
            self.blue = b
            self.steps = steps
        self.update_event.set()  # 색상이 업데이트되었음을 알림

    def stop(self):
        self.update_color(0,0,0,-1) # 먼저 불 끄기
        self.is_running = False
        self.update_event.set()  # 스레드를 종료하기 위해 이벤트 설정
        if self.light_thread:
            self.light_thread.join()
            self.light_thread = None