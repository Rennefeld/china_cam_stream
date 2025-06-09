import os
import io
import time
import socket
import threading


import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageOps
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse
from kivy.core.image import Image as CoreImage

from settings import Settings
from webserver import WebServer

settings = Settings.load()
CAM_IP = settings.cam_ip
CAM_PORT = settings.cam_port
KEEPALIVE_PORTS = [8070, 8080]
KEEPALIVE_PAYLOADS = {8070: b"0f", 8080: b"Bv"}
STREAM_WIDTH = 640
STREAM_HEIGHT = 480
LOGFILE = "debug_udp_streamer.log"
BRIGHTNESS = settings.brightness
CONTRAST = settings.contrast
SATURATION = settings.saturation


def dummy_black_image():
    return Image.new("RGB", (STREAM_WIDTH, STREAM_HEIGHT), "black")


def log(msg, debug):
    if not debug:
        return
    print(msg)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")


class CameraStreamer:
    def __init__(self, debug=False):
        self.debug = debug
        self.sock = None
        self.keepalive_flag = {"running": False}
        self.running = False
        self.local_port = None
        self.current_img = dummy_black_image()
        self.last_frame_time = 0
        self.lock = threading.Lock()

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', 0))
        self.local_port = self.sock.getsockname()[1]
        log(f"[Streamer] listening on UDP {self.local_port}", self.debug)
        self.running = True
        self.keepalive_flag["running"] = True
        threading.Thread(target=self.keepalive_loop, daemon=True).start()
        threading.Thread(target=self.stream_loop, daemon=True).start()

    def stop(self):
        self.running = False
        self.keepalive_flag["running"] = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        log("[Streamer] stopped", self.debug)

    def restart(self):
        self.stop()
        self.start()

    def keepalive_loop(self):
        while self.keepalive_flag["running"]:
            for port in KEEPALIVE_PORTS:
                try:
                    self.sock.sendto(KEEPALIVE_PAYLOADS[port], (CAM_IP, port))
                    log(f"[KA] {KEEPALIVE_PAYLOADS[port]} -> {CAM_IP}:{port}", self.debug)
                except Exception as e:
                    log(f"[KA] error {e}", self.debug)
            time.sleep(1)

    def stream_loop(self):
        buffer = b""
        collecting = False
        pkt_counter = 0
        while self.running:
            try:
                data, _ = self.sock.recvfrom(65536)
                pkt_counter += 1
                if len(data) < 8:
                    log(f"pkt {pkt_counter} short", self.debug)
                    continue
                payload = data[8:]
                if payload.startswith(b"\xff\xd8"):
                    buffer = payload
                    collecting = True
                elif collecting:
                    buffer += payload
                if collecting and b"\xff\xd9" in payload:
                    end_idx = buffer.find(b"\xff\xd9")
                    if end_idx != -1:
                        frame = buffer[: end_idx + 2]
                        try:
                            img = Image.open(io.BytesIO(frame))
                            with self.lock:
                                self.current_img = img
                                self.last_frame_time = time.time()
                        except Exception as e:
                            log(f"decode err {e}", self.debug)
                        buffer = b""
                        collecting = False
            except Exception as ex:
                log(f"stream err {ex}", self.debug)

    def get_image(self):
        with self.lock:
            return self.current_img.copy()

    def alive(self, timeout=2.0):
        return time.time() - self.last_frame_time < timeout


class FileSavePopup(Popup):
    def __init__(self, title, callback, **kwargs):
        super().__init__(title=title, size_hint=(0.9, 0.9), **kwargs)
        self.callback = callback
        layout = BoxLayout(orientation='vertical')
        self.fc = FileChooserIconView(path=os.getcwd(), filters=["*.*"], size_hint=(1, 0.9))
        layout.add_widget(self.fc)
        btn = Button(text="Save", size_hint=(1, 0.1))
        btn.bind(on_release=self.do_save)
        layout.add_widget(btn)
        self.add_widget(layout)

    def do_save(self, *_):
        if self.fc.selection:
            self.callback(self.fc.selection[0])
            self.dismiss()


class CameraLayout(BoxLayout):
    def __init__(self, streamer: CameraStreamer, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.streamer = streamer
        self.debug_mode = False
        self.image_widget = KivyImage(size_hint=(1, 0.9))
        self.add_widget(self.image_widget)
        controls = BoxLayout(size_hint=(1, 0.1))
        self.record_btn = Button(text="Start Recording")
        self.record_btn.bind(on_release=self.toggle_record)
        self.snap_btn = Button(text="Snapshot")
        self.snap_btn.bind(on_release=self.snapshot)
        self.debug_btn = Button(text="Enable Debug")
        self.debug_btn.bind(on_release=self.toggle_debug)
        controls.add_widget(self.record_btn)
        controls.add_widget(self.snap_btn)
        controls.add_widget(self.debug_btn)
        self.add_widget(controls)
        self.video_writer = None
        self.record_temp = None
        self.blink_event = None
        Clock.schedule_interval(self.update_image, 1/10)
        Clock.schedule_interval(self.check_stream, 2)

    def toggle_debug(self, *_):
        self.debug_mode = not self.debug_mode
        self.debug_btn.text = "Disable Debug" if self.debug_mode else "Enable Debug"

    def toggle_record(self, *_):
        if not self.video_writer:
            self.record_temp = os.path.join(os.getcwd(), "record_temp.avi")
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            self.video_writer = cv2.VideoWriter(self.record_temp, fourcc, 10, (STREAM_WIDTH, STREAM_HEIGHT))
            self.record_btn.text = "Stop Recording"
            self.start_blink()
        else:
            self.record_btn.text = "Start Recording"
            self.stop_blink()
            self.video_writer.release()
            self.video_writer = None
            FileSavePopup("Save video", self.save_video).open()

    def save_video(self, path):
        if self.record_temp and os.path.exists(self.record_temp):
            os.replace(self.record_temp, path)
            log(f"video saved to {path}", self.debug_mode)

    def snapshot(self, *_):
        FileSavePopup("Save snapshot", self.save_snapshot).open()

    def save_snapshot(self, path):
        img = self.streamer.get_image()
        img = self.process_image(img)
        img.save(path)
        log(f"snapshot saved to {path}", self.debug_mode)

    def process_image(self, img):
        if BRIGHTNESS != 1.0:
            img = ImageEnhance.Brightness(img).enhance(BRIGHTNESS)
        if CONTRAST != 1.0:
            img = ImageEnhance.Contrast(img).enhance(CONTRAST)
        if SATURATION != 1.0:
            img = ImageEnhance.Color(img).enhance(SATURATION)
        return img

    def update_image(self, *_):
        img = self.streamer.get_image()
        img = self.process_image(img)
        data = io.BytesIO()
        img.save(data, format='PNG')
        tex = CoreImage(io.BytesIO(data.getvalue()), ext='png').texture
        self.image_widget.texture = tex
        if self.video_writer:
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            self.video_writer.write(frame)

    def start_blink(self):
        if self.blink_event:
            self.blink_event.cancel()
        with self.image_widget.canvas.after:
            self._color = Color(1, 0, 0, 1)
            self._ellipse = Ellipse(size=(20, 20), pos=(10, self.image_widget.height-30))
        self.blink_event = Clock.schedule_interval(self._toggle_indicator, 0.5)

    def stop_blink(self):
        if self.blink_event:
            self.blink_event.cancel()
            self.blink_event = None
        if hasattr(self, '_ellipse'):
            self.image_widget.canvas.after.remove(self._color)
            self.image_widget.canvas.after.remove(self._ellipse)

    def _toggle_indicator(self, *_):
        if self._color.a == 1:
            self._color.a = 0
        else:
            self._color.a = 1

    def check_stream(self, *_):
        if not self.streamer.alive():
            log("stream stalled, restarting", self.debug_mode)
            self.streamer.restart()


class CameraApp(App):
    def build(self):
        self.streamer = CameraStreamer()
        self.streamer.start()
        self.web = WebServer(self)
        self.web.start()
        self.layout = CameraLayout(self.streamer)
        return self.layout

    @property
    def settings(self):
        return settings

    def on_stop(self):
        self.streamer.stop()


if __name__ == "__main__":
    CameraApp().run()
