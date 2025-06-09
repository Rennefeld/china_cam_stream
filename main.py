import os
import io
import time
import socket
import threading
import logging


import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageOps
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
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
STREAM_WIDTH = settings.width
STREAM_HEIGHT = settings.height
RESOLUTIONS = [(640, 480), (800, 600), (1280, 720), (1920, 1080)]
LOGFILE = "debug_udp_streamer.log"
BRIGHTNESS = settings.brightness
CONTRAST = settings.contrast
SATURATION = settings.saturation


def dummy_black_image():
    return Image.new("RGB", (STREAM_WIDTH, STREAM_HEIGHT), "black")


logger = logging.getLogger("cam")
logger.setLevel(logging.DEBUG)
_handler = logging.FileHandler(LOGFILE, encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(_handler)

def log(msg, debug):
    if debug:
        logger.debug(msg)


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
        self.current_img = dummy_black_image()
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
    def __init__(self, title, default_name, callback, **kwargs):
        super().__init__(title=title, size_hint=(0.9, 0.9), **kwargs)
        self.callback = callback
        self.default_name = default_name
        layout = BoxLayout(orientation="vertical")
        self.fc = FileChooserIconView(path=os.getcwd(), dirselect=True, size_hint=(1, 0.9))
        layout.add_widget(self.fc)
        btn = Button(text="Save Here", size_hint=(1, 0.1))
        btn.bind(on_release=self.do_save)
        layout.add_widget(btn)
        self.add_widget(layout)

    def do_save(self, *_):
        if self.fc.path:
            dest = os.path.join(self.fc.path, self.default_name)
            self.callback(dest)
            self.dismiss()


class ConfigPopup(Popup):
    def __init__(self, apply_callback, **kwargs):
        super().__init__(title="Einstellungen", size_hint=(0.9, 0.9), **kwargs)
        self.apply_callback = apply_callback
        layout = BoxLayout(orientation="vertical")
        self.ip_input = TextInput(text=str(CAM_IP), size_hint=(1, 0.1))
        self.port_input = TextInput(text=str(CAM_PORT), size_hint=(1, 0.1))
        self.bright_input = TextInput(text=str(BRIGHTNESS), size_hint=(1, 0.1))
        self.contrast_input = TextInput(text=str(CONTRAST), size_hint=(1, 0.1))
        self.sat_input = TextInput(text=str(SATURATION), size_hint=(1, 0.1))
        self.res_spinner = Spinner(text=f"{STREAM_WIDTH}x{STREAM_HEIGHT}", values=[f"{w}x{h}" for w, h in RESOLUTIONS], size_hint=(1, 0.1))
        for widget, label in [
            (self.ip_input, "IP"),
            (self.port_input, "Port"),
            (self.bright_input, "Brightness"),
            (self.contrast_input, "Contrast"),
            (self.sat_input, "Saturation"),
            (self.res_spinner, "Resolution"),
        ]:
            row = BoxLayout(size_hint=(1, 0.1))
            row.add_widget(Label(text=label, size_hint=(0.4, 1)))
            row.add_widget(widget)
            layout.add_widget(row)
        btn = Button(text="Save", size_hint=(1, 0.1))
        btn.bind(on_release=self.do_save)
        layout.add_widget(btn)
        self.add_widget(layout)

    def do_save(self, *_):
        w, h = map(int, self.res_spinner.text.split("x"))
        self.apply_callback(
            cam_ip=self.ip_input.text,
            cam_port=int(self.port_input.text),
            brightness=float(self.bright_input.text),
            contrast=float(self.contrast_input.text),
            saturation=float(self.sat_input.text),
            width=w,
            height=h,
        )
        self.dismiss()


class CameraLayout(BoxLayout):
    def __init__(self, streamer: CameraStreamer, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.streamer = streamer
        self.debug_mode = False
        self.image_widget = KivyImage(size_hint=(1, 0.9))
        self.add_widget(self.image_widget)

        self.rotate_angle = 0
        self.flip_h = False
        self.flip_v = False
        self.gray = False

        row1 = BoxLayout(size_hint=(1, 0.1))
        self.record_btn = Button(text="Start Recording")
        self.record_btn.bind(on_release=self.toggle_record)
        self.snap_btn = Button(text="Snapshot")
        self.snap_btn.bind(on_release=self.snapshot)
        self.restart_btn = Button(text="Restart")
        self.restart_btn.bind(on_release=lambda *_: self.streamer.restart())
        self.debug_btn = Button(text="Enable Debug")
        self.debug_btn.bind(on_release=self.toggle_debug)
        self.config_btn = Button(text="Config")
        self.config_btn.bind(on_release=self.open_config)
        row1.add_widget(self.record_btn)
        row1.add_widget(self.snap_btn)
        row1.add_widget(self.restart_btn)
        row1.add_widget(self.debug_btn)
        row1.add_widget(self.config_btn)

        row2 = BoxLayout(size_hint=(1, 0.1))
        self.rotate_btn = Button(text="Rotate")
        self.rotate_btn.bind(on_release=lambda *_: self.rotate())
        self.flip_h_btn = Button(text="Flip H")
        self.flip_h_btn.bind(on_release=lambda *_: self.flip_horizontal())
        self.flip_v_btn = Button(text="Flip V")
        self.flip_v_btn.bind(on_release=lambda *_: self.flip_vertical())
        self.gray_btn = Button(text="B/W")
        self.gray_btn.bind(on_release=lambda *_: self.toggle_gray())
        row2.add_widget(self.rotate_btn)
        row2.add_widget(self.flip_h_btn)
        row2.add_widget(self.flip_v_btn)
        row2.add_widget(self.gray_btn)

        self.add_widget(row1)
        self.add_widget(row2)

        self.video_writer = None
        self.record_temp = None
        self.blink_event = None
        Clock.schedule_interval(self.update_image, 1/10)
        Clock.schedule_interval(self.check_stream, 2)

    def toggle_debug(self, *_):
        self.debug_mode = not self.debug_mode
        self.debug_btn.text = "Disable Debug" if self.debug_mode else "Enable Debug"
        self.streamer.debug = self.debug_mode
        
    def open_config(self, *_):
        ConfigPopup(self.apply_config).open()

    def apply_config(
        self,
        cam_ip=None,
        cam_port=None,
        brightness=None,
        contrast=None,
        saturation=None,
        width=None,
        height=None,
    ):
        global CAM_IP, CAM_PORT, BRIGHTNESS, CONTRAST, SATURATION, STREAM_WIDTH, STREAM_HEIGHT
        if cam_ip is not None:
            CAM_IP = cam_ip
            settings.cam_ip = cam_ip
        if cam_port is not None:
            CAM_PORT = cam_port
            settings.cam_port = cam_port
        if brightness is not None:
            BRIGHTNESS = brightness
            settings.brightness = brightness
        if contrast is not None:
            CONTRAST = contrast
            settings.contrast = contrast
        if saturation is not None:
            SATURATION = saturation
            settings.saturation = saturation
        if width is not None and height is not None:
            STREAM_WIDTH = width
            STREAM_HEIGHT = height
            settings.width = width
            settings.height = height
        settings.save()
        self.streamer.restart()

    def toggle_record(self, *_):
        if not self.video_writer:
            self.record_temp = os.path.join(os.getcwd(), "record_temp.mpg")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.video_writer = cv2.VideoWriter(self.record_temp, fourcc, 10, (STREAM_WIDTH, STREAM_HEIGHT))
            self.record_btn.text = "Stop Recording"
            self.start_blink()
        else:
            self.record_btn.text = "Start Recording"
            self.stop_blink()
            self.video_writer.release()
            self.video_writer = None
            name = time.strftime("%Y%m%d_%H%M%S_h4r1_cam_streamer.mpg")
            FileSavePopup("Save video", name, self.save_video).open()

    def save_video(self, path):
        if self.record_temp and os.path.exists(self.record_temp):
            os.replace(self.record_temp, path)
            log(f"video saved to {path}", self.debug_mode)

    def snapshot(self, *_):
        name = time.strftime("%Y%m%d_%H%M%S_h4r1_cam_streamer.jpg")
        FileSavePopup("Save snapshot", name, self.save_snapshot).open()

    def save_snapshot(self, path):
        img = self.streamer.get_image()
        img = self.process_image(img)
        img.save(path)
        log(f"snapshot saved to {path}", self.debug_mode)

    def rotate(self):
        self.rotate_angle = (self.rotate_angle + 90) % 360

    def flip_horizontal(self):
        self.flip_h = not self.flip_h

    def flip_vertical(self):
        self.flip_v = not self.flip_v

    def toggle_gray(self):
        self.gray = not self.gray

    def process_image(self, img):
        if self.flip_h:
            img = ImageOps.mirror(img)
        if self.flip_v:
            img = ImageOps.flip(img)
        if self.rotate_angle:
            img = img.rotate(self.rotate_angle, expand=True)
            img = img.resize((STREAM_WIDTH, STREAM_HEIGHT))
        if self.gray:
            img = ImageOps.grayscale(img).convert("RGB")
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

    @property
    def resolutions(self):
        return RESOLUTIONS

    def update_settings(self, **kwargs):
        self.layout.apply_config(**kwargs)

    def get_processed_image(self):
        img = self.streamer.get_image()
        return self.layout.process_image(img)

    def on_stop(self):
        self.streamer.stop()


if __name__ == "__main__":
    CameraApp().run()
