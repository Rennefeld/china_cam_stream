import os
import io
import time
import socket
import threading
import logging
from typing import Tuple

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageOps
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
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

settings = Settings.load()
CAM_IP = settings.cam_ip
CAM_PORT = settings.cam_port
KEEPALIVE_PORTS = [8070, 8080]
KEEPALIVE_PAYLOADS = {8070: b"0f", 8080: b"Bv"}
STREAM_WIDTH = 640
STREAM_HEIGHT = 480
LOGFILE = "debug_udp_streamer.log"
VIDEO_CODEC = "XVID"
VIDEO_FPS = 30

BRIGHTNESS = settings.brightness
CONTRAST = settings.contrast
SATURATION = settings.saturation

logger = logging.getLogger("cam")
logger.setLevel(logging.INFO)
_handler = logging.FileHandler(LOGFILE, encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(_handler)

def log(msg: str) -> None:
    if not logger.disabled:
        logger.info(msg)
    print(msg)

def dummy_black_image() -> Image.Image:
    return Image.new("RGB", (STREAM_WIDTH, STREAM_HEIGHT), "black")

class CameraStreamer:
    """Receive MJPEG frames over UDP."""

    def __init__(self) -> None:
        self.sock: socket.socket | None = None
        self.keepalive_flag = {"running": False}
        self.running = False
        self.local_port: int | None = None
        self.current_img: Image.Image = dummy_black_image()
        self.last_frame_time = 0.0
        self.lock = threading.Lock()

    def start(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 0))
        self.local_port = self.sock.getsockname()[1]
        log(f"[Streamer] listening on UDP {self.local_port}")
        self.running = True
        self.keepalive_flag["running"] = True
        threading.Thread(target=self.keepalive_loop, daemon=True).start()
        threading.Thread(target=self.stream_loop, daemon=True).start()

    def stop(self) -> None:
        self.running = False
        self.keepalive_flag["running"] = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        log("[Streamer] stopped")

    def restart(self) -> None:
        self.stop()
        self.current_img = dummy_black_image()
        self.start()

    def keepalive_loop(self) -> None:
        while self.keepalive_flag["running"]:
            for port in KEEPALIVE_PORTS:
                try:
                    assert self.sock is not None
                    self.sock.sendto(KEEPALIVE_PAYLOADS[port], (CAM_IP, port))
                    log(f"[KA] {KEEPALIVE_PAYLOADS[port]} -> {CAM_IP}:{port}")
                except Exception as exc:
                    log(f"[KA] error {exc}")
            time.sleep(1)

    def stream_loop(self) -> None:
        buffer = b""
        collecting = False
        pkt_counter = 0
        while self.running:
            try:
                assert self.sock is not None
                data, _ = self.sock.recvfrom(65536)
                pkt_counter += 1
                if len(data) < 8:
                    log(f"pkt {pkt_counter} short")
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
                            img = img.convert("RGB")
                            with self.lock:
                                self.current_img = img
                                self.last_frame_time = time.time()
                        except Exception as e:
                            log(f"decode err {e}")
                        buffer = b""
                        collecting = False
            except Exception as ex:
                log(f"stream err {ex}")

    def get_image(self) -> Image.Image:
        with self.lock:
            try:
                return self.current_img.copy()
            except Exception:
                return dummy_black_image()

    def alive(self, timeout: float = 2.0) -> bool:
        return time.time() - self.last_frame_time < timeout

class FileSavePopup(Popup):
    def __init__(self, title: str, default_name: str, callback, **kwargs) -> None:
        super().__init__(title=title, size_hint=(0.9, 0.9), **kwargs)
        self.callback = callback
        layout = BoxLayout(orientation="vertical")
        self.fc = FileChooserIconView(path=os.getcwd(), dirselect=True, size_hint=(1, 0.8))
        layout.add_widget(self.fc)
        self.name_input = TextInput(text=default_name, multiline=False, size_hint=(1, 0.1))
        layout.add_widget(self.name_input)
        btn = Button(text="Save", size_hint=(1, 0.1))
        btn.bind(on_release=self.do_save)
        layout.add_widget(btn)
        self.add_widget(layout)

    def do_save(self, *_args) -> None:
        if self.fc.path:
            dest = os.path.join(self.fc.path, self.name_input.text)
            self.callback(dest)
            self.dismiss()

class ConfigPopup(Popup):
    def __init__(self, apply_cb, **kwargs) -> None:
        super().__init__(title="Settings", size_hint=(0.9, 0.9), **kwargs)
        self.apply_cb = apply_cb
        layout = GridLayout(cols=2)
        layout.add_widget(Label(text="Cam IP"))
        self.ip_in = TextInput(text=CAM_IP, multiline=False)
        layout.add_widget(self.ip_in)
        layout.add_widget(Label(text="Cam Port"))
        self.port_in = TextInput(text=str(CAM_PORT), multiline=False)
        layout.add_widget(self.port_in)
        layout.add_widget(Label(text="Brightness"))
        self.bright_in = TextInput(text=str(BRIGHTNESS), multiline=False)
        layout.add_widget(self.bright_in)
        layout.add_widget(Label(text="Contrast"))
        self.contrast_in = TextInput(text=str(CONTRAST), multiline=False)
        layout.add_widget(self.contrast_in)
        layout.add_widget(Label(text="Saturation"))
        self.sat_in = TextInput(text=str(SATURATION), multiline=False)
        layout.add_widget(self.sat_in)
        layout.add_widget(Label(text="Resolution"))
        self.res_spin = Spinner(values=["640x480", "800x600", "1280x720", "1920x1080"], text=f"{STREAM_WIDTH}x{STREAM_HEIGHT}")
        layout.add_widget(self.res_spin)
        btn = Button(text="Save", size_hint=(1, None), height=40)
        btn.bind(on_release=self.on_save)
        layout.add_widget(btn)
        self.add_widget(layout)

    def on_save(self, *_args) -> None:
        res = self.res_spin.text.split("x")
        width, height = int(res[0]), int(res[1])
        self.apply_cb(
            cam_ip=self.ip_in.text,
            cam_port=int(self.port_in.text),
            brightness=float(self.bright_in.text),
            contrast=float(self.contrast_in.text),
            saturation=float(self.sat_in.text),
            resolution=(width, height),
        )
        self.dismiss()

class CameraLayout(BoxLayout):
    def __init__(self, streamer: CameraStreamer, **kwargs) -> None:
        super().__init__(orientation="vertical", **kwargs)
        self.streamer = streamer
        self.image_widget = KivyImage(size_hint=(1, 0.9))
        self.add_widget(self.image_widget)

        self.record_btn = Button(text="Start Recording")
        self.record_btn.bind(on_release=self.toggle_record)
        self.snap_btn = Button(text="Snapshot")
        self.snap_btn.bind(on_release=self.snapshot)
        self.restart_btn = Button(text="Restart")
        self.restart_btn.bind(on_release=lambda *_: self.streamer.restart())
        self.config_btn = Button(text="Config")
        self.config_btn.bind(on_release=self.show_config)
        self.log_btn = Button(text="Enable Log")
        self.log_btn.bind(on_release=self.toggle_log)

        row1 = GridLayout(cols=5, size_hint=(1, 0.1))
        for w in [self.record_btn, self.snap_btn, self.restart_btn, self.config_btn, self.log_btn]:
            row1.add_widget(w)
        self.add_widget(row1)

        row2 = GridLayout(cols=4, size_hint=(1, 0.1))
        self.rotate_btn = Button(text="Rotate")
        self.rotate_btn.bind(on_release=lambda *_: self.rotate())
        self.fliph_btn = Button(text="Flip H")
        self.fliph_btn.bind(on_release=lambda *_: self.flip_horizontal())
        self.flipv_btn = Button(text="Flip V")
        self.flipv_btn.bind(on_release=lambda *_: self.flip_vertical())
        self.gray_btn = Button(text="B/W")
        self.gray_btn.bind(on_release=lambda *_: self.toggle_gray())
        for w in [self.rotate_btn, self.fliph_btn, self.flipv_btn, self.gray_btn]:
            row2.add_widget(w)
        self.add_widget(row2)

        self.video_writer: cv2.VideoWriter | None = None
        self.recording = False
        self.record_temp: str | None = None
        self.rotate_angle = 0
        self.flip_h = False
        self.flip_v = False
        self.gray = False

        Clock.schedule_interval(self.update_image, 1 / 10)
        Clock.schedule_interval(self.check_stream, 2)
        self.blink_state = False

    def show_config(self, *_args) -> None:
        ConfigPopup(self.apply_settings).open()

    def apply_settings(
        self,
        cam_ip: str,
        cam_port: int,
        brightness: float,
        contrast: float,
        saturation: float,
        resolution: Tuple[int, int],
    ) -> None:
        global CAM_IP, CAM_PORT, BRIGHTNESS, CONTRAST, SATURATION, STREAM_WIDTH, STREAM_HEIGHT
        CAM_IP = cam_ip
        CAM_PORT = cam_port
        BRIGHTNESS = brightness
        CONTRAST = contrast
        SATURATION = saturation
        STREAM_WIDTH, STREAM_HEIGHT = resolution
        settings.cam_ip = cam_ip
        settings.cam_port = cam_port
        settings.brightness = brightness
        settings.contrast = contrast
        settings.saturation = saturation
        settings.save()
        self.streamer.restart()

    def toggle_log(self, *_args) -> None:
        logger.disabled = not logger.disabled
        self.log_btn.text = "Disable Log" if not logger.disabled else "Enable Log"

    def rotate(self) -> None:
        self.rotate_angle = (self.rotate_angle + 90) % 360

    def flip_horizontal(self) -> None:
        self.flip_h = not self.flip_h

    def flip_vertical(self) -> None:
        self.flip_v = not self.flip_v

    def toggle_gray(self) -> None:
        self.gray = not self.gray

    def get_processed_image(self) -> Image.Image:
        img = self.streamer.get_image()
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

    def toggle_record(self, *_args) -> None:
        if not self.recording:
            fname = time.strftime("%Y%m%d_%H%M%S_h4r1_cam_recording.avi")
            self.record_temp = os.path.join(os.getcwd(), fname)
            fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
            self.video_writer = cv2.VideoWriter(self.record_temp, fourcc, VIDEO_FPS, (STREAM_WIDTH, STREAM_HEIGHT))
            self.recording = True
            self.record_btn.text = "Stop Recording"
            log(f"Recording started: {self.record_temp}")
        else:
            self.record_btn.text = "Start Recording"
            if self.video_writer:
                self.video_writer.release()
            self.video_writer = None
            self.recording = False
            log(f"Recording stopped. Saved as: {self.record_temp}")
            if self.record_temp:
                FileSavePopup("Save video", os.path.basename(self.record_temp), self.save_video).open()

    def save_video(self, path: str) -> None:
        if self.record_temp and os.path.exists(self.record_temp):
            try:
                os.replace(self.record_temp, path)
                log(f"Video saved to {path}")
            except Exception as e:
                log(f"Could not save video: {e}")
            finally:
                self.record_temp = None

    def snapshot(self, *_args) -> None:
        name = time.strftime("%Y%m%d_%H%M%S_h4r1_cam_streamer.jpg")
        FileSavePopup("Save snapshot", name, self.save_snapshot).open()

    def save_snapshot(self, path: str) -> None:
        img = self.get_processed_image()
        try:
            img.save(path)
            log(f"Snapshot saved to {path}")
        except Exception as e:
            log(f"Could not save snapshot: {e}")

    def update_image(self, *_args) -> None:
        img = self.get_processed_image()
        data = io.BytesIO()
        img.save(data, format="PNG")
        tex = CoreImage(io.BytesIO(data.getvalue()), ext="png").texture
        self.image_widget.texture = tex
        if self.recording and self.video_writer:
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            self.video_writer.write(frame)
        self._draw_rec_indicator()

    def _draw_rec_indicator(self) -> None:
        self.image_widget.canvas.after.clear()
        if self.recording:
            with self.image_widget.canvas.after:
                self.blink_state = not self.blink_state
                if self.blink_state:
                    Color(1, 0, 0)
                else:
                    Color(1, 0, 0, 0.2)
                Ellipse(pos=(10, self.image_widget.height - 20), size=(10, 10))

    def check_stream(self, *_args) -> None:
        if not self.streamer.alive():
            log("stream stalled, restarting")
            self.streamer.restart()

class CameraApp(App):
    def build(self):
        self.title = "H4R1 Cam Streamer"
        self.streamer = CameraStreamer()
        self.streamer.start()
        self.layout = CameraLayout(self.streamer)
        return self.layout

    def on_stop(self) -> None:
        self.streamer.stop()

if __name__ == "__main__":
    CameraApp().run()
