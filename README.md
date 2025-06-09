# China Cam Stream

Die Anwendung trägt in der Titelleiste den Namen **H4R1 Cam Streamer** und richtet sich mit ihrer vertikalen Kivy-Oberfläche besonders an Android-Geräte.

Dieses Programm zeigt einen MJPEG Stream über UDP an und nutzt eine moderne Kivy-Oberfläche, die sich besonders für Android im Hochformat eignet. Zusätzlich steht ein integrierter Webserver bereit. Neben dem reinen Anzeigen können verschiedene Bildoperationen angewendet und Aufnahmen erstellt werden.

## Funktionen

- **MJPEG Anzeige** aus einem UDP Stream
- **Konfigurationsmenü** für Kamera-IP, Kamera-Port, Helligkeit, Kontrast und Sättigung
- **Bildoperationen**: Drehung in 90°-Schritten, horizontales/vertikales Spiegeln, Schwarz/Weiß
- **Snapshot und Videoaufnahme** mit individuellem Speicherort
- **Individuelle Dateinamen** beim Speichern von Videos und Bildern
- **Weboberfläche** mit denselben Funktionen

## Bedienung

Nach dem Start erscheint die Hauptoberfläche mit dem Videofenster und den Steuerbuttons. 
Über das Menü `Einstellungen` lassen sich die Kameradaten sowie Bildparameter anpassen. 
Alle Änderungen werden sofort angewendet und in `settings.json` gespeichert.

### Steuerbuttons

 - **Aufnahme**: Startet bzw. beendet die Videoaufnahme und speichert als MP4-Datei.
- **Snapshot**: Speichert das aktuelle Bild als JPEG.
- **Debug**: Schaltet eine Protokollierung ein oder aus.
- **Restart**: Startet den Stream manuell neu.
- **Rotate**: Rotiert das Bild um 90°.
- **Flip H/V**: Spiegelt das Bild horizontal bzw. vertikal.
- **B/W**: Schaltet zwischen Farbe und Graustufen um.
- **Auflösung**: Vordefinierte Werte bis 1920x1080 wählbar.

### Webserver

Parallel zur Desktop-GUI startet automatisch ein Webserver auf Port `5000`.
Rufen Sie `http://<IP>:5000` im Browser auf, um die gleichen Bedienelemente per Web zu nutzen.
Wenn keine Bilder empfangen werden, versucht die Anwendung den Stream erneut zu starten.

## Installation

Führe zunächst die Installation der benötigten Bibliotheken aus,
bevor du das Programm startest. Dazu gehören Python-Pakete und **FFmpeg**:

```bash
pip install opencv-python pillow numpy flask kivy
sudo apt install ffmpeg
```
FFmpeg wird zum Konvertieren aufgezeichneter Videos in das MP4-Format
verwendet. Ist es nicht installiert, speichert die Anwendung die Aufnahme
als AVI-Datei.


## Android-Build unter Windows 10

1. Installieren Sie **WSL2** sowie ein aktuelles Ubuntu.
2. Innerhalb von WSL Python 3, `pip` und `buildozer` installieren:
   ```bash
   sudo apt update && sudo apt install python3 python3-pip -y
   pip install buildozer
   ```
3. Erstellen Sie eine Kivy-App-Hülle für `main.py` und passen Sie die `buildozer.spec` an.
4. Führen Sie `buildozer -v android debug` innerhalb von WSL aus. 
   Das erzeugte APK finden Sie danach im Unterordner `bin/`.
5. Übertragen Sie das APK auf Ihr Android-Gerät und installieren Sie es.

