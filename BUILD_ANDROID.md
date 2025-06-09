# Android-Build mit Buildozer

Diese Anleitung erklaert, wie du aus dem vorhandenen Projekt eine Android-App baust. Die Schritte beruhen auf Best Practices, um ein wartbares, modulares Ergebnis zu erreichen.

## Vorbereitung

1. **WSL2 und Python**  
   Unter Windows empfiehlt sich die Nutzung von WSL2 mit Ubuntu. Dort installierst du Python 3 und Buildozer:
   ```bash
   sudo apt update && sudo apt install python3 python3-pip -y
   pip install buildozer
   ```
   Buildozer kuemmert sich spaeter um alle weiteren Abhaengigkeiten, sofern sie korrekt im `buildozer.spec` gelistet sind.

2. **Projektstruktur beibehalten**  
   Das Repository nutzt eine klare Trennung:
   - `main.py` – GUI und Bildverarbeitung
   - `webserver.py` – Flask-basierter Webserver
   - `settings.py` – Konfiguration ueber eine `dataclass`

   Diese modulare Aufteilung erleichtert Wartung und Erweiterung.

## Buildozer initialisieren

1. Wechsle ins Projektverzeichnis und fuehre aus:
   ```bash
   buildozer init
   ```
   Dadurch wird eine Vorlage `buildozer.spec` erstellt.

2. Oeffne die Datei und passe mindestens diese Felder an:

   | Einstellung              | Beispielwert/Empfehlung                                               |
   |--------------------------|-----------------------------------------------------------------------|
   | `title`                  | `China Cam Stream`                                                    |
   | `package.name`           | `chinacamstream` (nur Kleinbuchstaben)                                |
   | `package.domain`         | z. B. `org.example`                                                   |
   | `source.include_exts`    | `py,json`                                                             |
   | `requirements`           | `kivy,flask,pillow,opencv-python,numpy`                               |
   | `android.permissions`    | `INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE`               |
   | `orientation`            | `portrait`                                                           |

   Alle Bibliotheken, die im Code verwendet werden (z. B. Flask, OpenCV, Pillow), muessen in `requirements` stehen, damit Buildozer sie automatisch installiert.

3. Optional kannst du Werte wie `icon`, `presplash` oder `fullscreen` ergaenzen – halte die Konfiguration aber schlank (KISS).

## APK erzeugen

Fuehre anschliessend im selben Verzeichnis aus:
```bash
buildozer -v android debug
```
Das erstellte APK findest du danach im Ordner `bin/`.

## Best Practices

- **Dependencies in der Spec**  
  Jede importierte Bibliothek muss in `requirements` auftauchen, damit sie beim Build installiert wird.

- **KISS und Modularitaet**  
  Die getrennten Module (`main.py`, `webserver.py`, `settings.py`) folgen dem KISS-Prinzip und vermeiden Monolithen. Anpassungen an den Settings werden zentral ueber die Dataclass vorgenommen.

- **Erweiterbarkeit**  
  Durch diese Struktur lassen sich neue Features (z. B. zusaetzliche Bildfilter oder Web-Routen) leicht ergaenzen, ohne den Kern zu verkomplizieren.

Damit steht dem Erstellen einer Android-App mit Buildozer nichts mehr im Weg.
