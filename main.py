import socket
import threading
import time
from tkinter import (
    Tk,
    Canvas,
    NW,
    Button,
    Menu,
    Toplevel,
    Label,
    Entry,
    Scale,
    HORIZONTAL,
    Frame,
)
from PIL import Image, ImageTk, ImageEnhance, ImageOps
import io
import binascii
import json
import os
import cv2
import numpy as np
from settings import Settings
from webserver import WebServer

settings = Settings.load()
CAM_IP = settings.cam_ip
CAM_PORT = settings.cam_port
LOCAL_PORT = 0  # Ephemeral
KEEPALIVE_PORTS = [8070, 8080]
KEEPALIVE_PAYLOADS = {8070: b"0f", 8080: b"Bv"}
STREAM_WIDTH = 640
STREAM_HEIGHT = 480
LOGFILE = "debug_udp_streamer.log"
BRIGHTNESS = settings.brightness
CONTRAST = settings.contrast
SATURATION = settings.saturation

def log(msg):
    print(msg)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")

def keepalive_loop(sock, flag, local_port):
    while flag["running"]:
        for port in KEEPALIVE_PORTS:
            try:
                sock.sendto(KEEPALIVE_PAYLOADS[port], (CAM_IP, port))
                log(f"[Keepalive] gesendet: {KEEPALIVE_PAYLOADS[port]} an {CAM_IP}:{port} von local port {local_port}")
            except Exception as e:
                log(f"[Keepalive] Fehler an {port}: {e}")
        time.sleep(1)

def dummy_black_image():
    return Image.new("RGB", (STREAM_WIDTH, STREAM_HEIGHT), "black")


def save_settings():
    settings.cam_ip = CAM_IP
    settings.cam_port = CAM_PORT
    settings.brightness = BRIGHTNESS
    settings.contrast = CONTRAST
    settings.saturation = SATURATION
    settings.save()

class MJPEGNetworkGuiDemo:
    def __init__(self):
        self.root = Tk()
        self.root.title("UDP Debug MJPEG Streamer")
        self.canvas = Canvas(self.root, width=STREAM_WIDTH, height=STREAM_HEIGHT, bg="black")
        self.canvas.pack()
        self.controls = Frame(self.root)
        self.controls.pack()
        self._build_menu()
        self._build_controls()
        self.rotate_angle = 0
        self.flip_h = False
        self.flip_v = False
        self.gray = False
        self.recording = False
        self.video_writer = None
        self.tk_img = None
        self.current_img = dummy_black_image()
        self.draw_image(self.current_img)
        self.running = True

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', LOCAL_PORT))
        self.local_port = self.sock.getsockname()[1]

        log(f"[Streamer] Höre auf UDP {self.local_port}… (Keepalive 8070+8080)")

        self.ka_flag = {"running": True}
        threading.Thread(target=keepalive_loop, args=(self.sock, self.ka_flag, self.local_port), daemon=True).start()
        threading.Thread(target=self.stream_loop, daemon=True).start()

        self.web = WebServer(self)
        self.web.start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def _build_menu(self):
        menu_bar = Menu(self.root)
        self.root.config(menu=menu_bar)
        settings_menu = Menu(menu_bar, tearoff=0)
        settings_menu.add_command(label="Einstellungen", command=self.show_settings_dialog)
        menu_bar.add_cascade(label="Menü", menu=settings_menu)

    def _build_controls(self):
        Button(self.controls, text="Aufnahme", command=self.toggle_record).grid(row=0, column=0)
        Button(self.controls, text="Snapshot", command=self.snapshot).grid(row=0, column=1)
        Button(self.controls, text="Rotate", command=self.rotate).grid(row=0, column=2)
        Button(self.controls, text="Flip H", command=self.flip_horizontal).grid(row=0, column=3)
        Button(self.controls, text="Flip V", command=self.flip_vertical).grid(row=0, column=4)
        Button(self.controls, text="B/W", command=self.toggle_gray).grid(row=0, column=5)

    def show_settings_dialog(self):
        dlg = Toplevel(self.root)
        dlg.title("Einstellungen")
        Label(dlg, text="Cam IP").grid(row=0, column=0)
        ip_entry = Entry(dlg)
        ip_entry.insert(0, CAM_IP)
        ip_entry.grid(row=0, column=1)

        Label(dlg, text="Cam Port").grid(row=1, column=0)
        port_entry = Entry(dlg)
        port_entry.insert(0, str(CAM_PORT))
        port_entry.grid(row=1, column=1)

        Label(dlg, text="Helligkeit").grid(row=2, column=0)
        bright_scale = Scale(dlg, from_=0, to=2, resolution=0.1, orient=HORIZONTAL)
        bright_scale.set(BRIGHTNESS)
        bright_scale.grid(row=2, column=1)

        Label(dlg, text="Kontrast").grid(row=3, column=0)
        contrast_scale = Scale(dlg, from_=0, to=2, resolution=0.1, orient=HORIZONTAL)
        contrast_scale.set(CONTRAST)
        contrast_scale.grid(row=3, column=1)

        Label(dlg, text="Sättigung").grid(row=4, column=0)
        sat_scale = Scale(dlg, from_=0, to=2, resolution=0.1, orient=HORIZONTAL)
        sat_scale.set(SATURATION)
        sat_scale.grid(row=4, column=1)

        def apply_and_close():
            self.update_settings(
                cam_ip=ip_entry.get(),
                cam_port=int(port_entry.get()),
                brightness=float(bright_scale.get()),
                contrast=float(contrast_scale.get()),
                saturation=float(sat_scale.get()),
            )
            dlg.destroy()

        Button(dlg, text="Speichern", command=apply_and_close).grid(row=5, column=0, columnspan=2)

    def update_settings(self, cam_ip=None, cam_port=None, brightness=None, contrast=None, saturation=None):
        global CAM_IP, CAM_PORT, BRIGHTNESS, CONTRAST, SATURATION
        if cam_ip is not None:
            CAM_IP = cam_ip
        if cam_port is not None:
            CAM_PORT = cam_port
        if brightness is not None:
            BRIGHTNESS = brightness
        if contrast is not None:
            CONTRAST = contrast
        if saturation is not None:
            SATURATION = saturation
        save_settings()

    def toggle_record(self):
        if not self.recording:
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            fname = time.strftime("record_%Y%m%d_%H%M%S.avi")
            self.video_writer = cv2.VideoWriter(fname, fourcc, 10, (STREAM_WIDTH, STREAM_HEIGHT))
            self.recording = True
        else:
            self.recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None

    def snapshot(self):
        fname = time.strftime("snapshot_%Y%m%d_%H%M%S.jpg")
        self.get_processed_image().save(fname)

    def rotate(self):
        self.rotate_angle = (self.rotate_angle + 90) % 360

    def flip_horizontal(self):
        self.flip_h = not self.flip_h

    def flip_vertical(self):
        self.flip_v = not self.flip_v

    def toggle_gray(self):
        self.gray = not self.gray

    def get_processed_image(self):
        img = self.current_img.copy()
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

    def draw_image(self, pil_img):
        processed = self.get_processed_image() if pil_img is self.current_img else pil_img
        if self.recording and self.video_writer:
            frame = cv2.cvtColor(np.array(processed), cv2.COLOR_RGB2BGR)
            self.video_writer.write(frame)
        self.tk_img = ImageTk.PhotoImage(processed)
        self.canvas.create_image(0, 0, anchor=NW, image=self.tk_img)

    def stream_loop(self):
        log("[Streamer] Starte Debug-Bildzusammenbau...")
        buffer = b""
        pkt_counter = 0
        collecting = False
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65536)
                pkt_counter += 1
                if len(data) < 8:
                    log(f"Pkt {pkt_counter}: Zu kurz! Daten: {binascii.hexlify(data)}")
                    continue

                header = data[:8]
                payload = data[8:]
                log(f"Pkt {pkt_counter}: Header: {binascii.hexlify(header)}, Payload[0:8]: {binascii.hexlify(payload[:8])} ...")

                # --- FIX: Wenn FFD8 erkannt, immer ein neues JPEG starten ---
                if payload.startswith(b'\xff\xd8'):
                    if buffer:
                        log(f"Pkt {pkt_counter}: Buffer war noch da (vermutlich Frame zu groß oder Endekennung gefehlt) – verworfen!")
                    buffer = payload
                    collecting = True
                    log(f"Pkt {pkt_counter}: Start JPEG erkannt!")
                elif collecting:
                    buffer += payload

                # Option 1: JPEG-Ende suchen
                if collecting and b'\xff\xd9' in payload:
                    # bis inkl. FF D9 übernehmen
                    end_idx = buffer.find(b'\xff\xd9')
                    if end_idx != -1:
                        frame = buffer[:end_idx+2]
                        log(f"Pkt {pkt_counter}: JPEG vollständig (bis FF D9), Größe {len(frame)} Bytes. Versuche anzuzeigen…")
                        try:
                            img = Image.open(io.BytesIO(frame))
                            self.current_img = img
                            self.root.after(0, self.draw_image, self.current_img)
                            log(f"Pkt {pkt_counter}: Bild angezeigt!")
                        except Exception as e:
                            log(f"Pkt {pkt_counter}: JPEG Decode fehlgeschlagen: {e}")
                        buffer = b""
                        collecting = False

            except Exception as ex:
                log(f"[Streamer] Fehler: {ex}")

    def on_close(self):
        self.running = False
        self.ka_flag["running"] = False
        if self.video_writer:
            self.video_writer.release()
        try:
            self.root.destroy()
        except Exception:
            pass
        log("[GUI] Beendet.")

if __name__ == "__main__":
    MJPEGNetworkGuiDemo()
