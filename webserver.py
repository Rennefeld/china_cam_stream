import io
import threading
from flask import Flask, Response, render_template_string, request, redirect

PAGE = """
<!doctype html>
<title>Cam Stream</title>
<h1>Cam Stream</h1>
<img src='/video_feed' width='{{ settings.width }}' height='{{ settings.height }}'>
<form method='post' action='/update'>
  IP: <input name='cam_ip' value='{{ settings.cam_ip }}'><br>
  Port: <input name='cam_port' value='{{ settings.cam_port }}'><br>
  Brightness: <input type='range' min='0' max='2' step='0.1' name='brightness' value='{{ settings.brightness }}'><br>
  Contrast: <input type='range' min='0' max='2' step='0.1' name='contrast' value='{{ settings.contrast }}'><br>
  Saturation: <input type='range' min='0' max='2' step='0.1' name='saturation' value='{{ settings.saturation }}'><br>
  Resolution:
  <select name='resolution'>
  {% for w,h in resolutions %}
    <option value='{{ w }}x{{ h }}' {% if w==settings.width and h==settings.height %}selected{% endif %}>{{ w }}x{{ h }}</option>
  {% endfor %}
  </select><br>
  <button type='submit'>Save</button>
</form>
"""


class WebServer:
    def __init__(self, gui):
        self.gui = gui
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        app = self.app

        @app.route('/')
        def index():
            return render_template_string(PAGE, settings=self.gui.settings, resolutions=self.gui.resolutions)

        @app.route('/video_feed')
        def video_feed():
            return Response(self.generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

        @app.route('/update', methods=['POST'])
        def update():
            form = request.form
            res = form.get('resolution')
            w, h = map(int, res.split('x'))
            self.gui.update_settings(
                cam_ip=form.get('cam_ip'),
                cam_port=int(form.get('cam_port')),
                brightness=float(form.get('brightness')),
                contrast=float(form.get('contrast')),
                saturation=float(form.get('saturation')),
                width=w,
                height=h,
            )
            return redirect('/')

    def generate(self):
        while True:
            img = self.gui.get_processed_image()
            buf = io.BytesIO()
            img.save(buf, format='JPEG')
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.getvalue() + b'\r\n')

    def start(self):
        threading.Thread(
            target=lambda: self.app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False),
            daemon=True,
        ).start()
