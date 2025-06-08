import socket
import threading
import time
from tkinter import Tk, Canvas, NW
from PIL import Image, ImageTk
import io
import binascii

CAM_IP = "192.168.4.153"
CAM_PORT = 8080
LOCAL_PORT = 0  # Ephemeral
KEEPALIVE_PORTS = [8070, 8080]
KEEPALIVE_PAYLOADS = {8070: b"0f", 8080: b"Bv"}
STREAM_WIDTH = 640
STREAM_HEIGHT = 480
LOGFILE = "debug_udp_streamer.log"

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

class MJPEGNetworkGuiDemo:
    def __init__(self):
        self.root = Tk()
        self.root.title("UDP Debug MJPEG Streamer")
        self.canvas = Canvas(self.root, width=STREAM_WIDTH, height=STREAM_HEIGHT, bg="black")
        self.canvas.pack()
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

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def draw_image(self, pil_img):
        self.tk_img = ImageTk.PhotoImage(pil_img)
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
                            self.root.after(0, self.draw_image, img)
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
        try:
            self.root.destroy()
        except Exception:
            pass
        log("[GUI] Beendet.")

if __name__ == "__main__":
    MJPEGNetworkGuiDemo()
