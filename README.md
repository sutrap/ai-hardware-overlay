# ai-hardware-overlay

Ein kleines, plattformübergreifendes (Windows + Linux) HUD-Overlay, das live
Hardware-Daten (CPU, RAM, GPU) und lokal geladene KI-Modelle (Ollama / LM Studio
/ llama.cpp / KoboldCpp) als immer im Vordergrund stehendes, rahmenloses und
halbtransparentes Fenster anzeigt.

**Merkmale:**

- Always-on-top, rahmenlos, halbtransparentes dunkles HUD mit weißer Monospace-Schrift
- Per linker Maustaste frei verschiebbar (draggable)
- Rechtsklick-Kontextmenü: **Beenden**, **Transparenz erhöhen**, **Transparenz verringern** sowie Aktualisierungsintervalle **500 ms / 1000 ms / 2000 ms**
- Fensterposition und Deckkraft werden in `config.json` gespeichert und beim nächsten Start wiederhergestellt
- Robust: Fehlt ein Tool, Treiber, eine API oder Datei, stürzt die Anwendung **nicht** ab — nicht verfügbare Werte werden als `n/a` angezeigt
- Keine Administratorrechte, keine Telemetrie, kein Internetzugriff außer auf localhost-APIs
- Datenabfrage läuft in einem Hintergrund-Thread (`MonitorThread`), die GUI bleibt dadurch reaktionsfähig

## Beispielanzeige

Die Ausgabe im Overlay sieht typischerweise so aus:

```
AI Hardware Overlay
-------------------
Models:
- llama3.1:8b [Ollama] 61%/39% CPU/GPU
    ctx 4k · Q4_K_M · 8.0B
- mistral-7b.Q4_K_M.gguf [llama.cpp]
    ctx 8k · Q4_K_M · 7B

CPU: 23%
RAM: 61% | 19.4 / 32.0 GB

GPU 1: NVIDIA GeForce RTX 4070
Load: 78%
VRAM: 8.6 / 12.0 GB
Temp: 67°C

GPU 2: AMD Radeon RX 7800 XT
Load: n/a
VRAM: n/a / 16.0 GB
Temp: n/a
```

Angezeigte Werte:

- **CPU-Auslastung** in Prozent
- **RAM-Auslastung** in Prozent + belegt/gesamt in GB
- **GPU-Hersteller** (NVIDIA / AMD / `n/a`)
- **GPU-Name**
- **GPU-Last** in Prozent
- **VRAM** belegt/gesamt in GB
- **GPU-Temperatur**
- **Modell-Aufteilung** (nur Ollama): wo das Modell geladen ist, z. B.
  `61%/39% CPU/GPU`, `100% GPU` oder `100% CPU`. Wird aus `size` und `size_vram`
  der Ollama-API (`/api/ps`) berechnet und nur angezeigt, wenn die Daten
  verfügbar sind (sonst keine Ergänzung).

### Modell-Detailzeile

Unter jedem Modell kann eine zweite, eingerückte Zeile mit weiteren Parametern
erscheinen. Welche Felder gezeigt werden, steuert der Konfigurationsschlüssel
`model_detail_fields` (Reihenfolge = Anzeigereihenfolge, leere Liste schaltet
die Zeile ab). Nicht verfügbare Werte werden einfach weggelassen.

| Feld | Bedeutung | Quelle |
|---|---|---|
| `ctx` | **Tatsächlich geladene** Kontextgröße (nicht das Modell-Maximum!). Wird kompakt als `4k`, `32k`, `128k` dargestellt | Ollama: `context_length` aus `/api/ps` (die Wahrheit, entspricht `ollama ps`); LM Studio: `loaded_context_length` aus `/api/v0/models`; llama.cpp/KoboldCpp: `-c`/`--ctx-size` aus der Prozess-Kommandozeile |
| `quant` | Quantisierung, z. B. `Q4_K_M`, `Q8_0` | Ollama `details.quantization_level`; LM Studio `quantization`; bei llama.cpp aus dem `.gguf`-Dateinamen |
| `params` | Parameteranzahl, z. B. `7.5B`, `70B` | Ollama `details.parameter_size`; bei llama.cpp aus dem `.gguf`-Dateinamen |
| `family` | Modellfamilie/-architektur, z. B. `gemma4`, `qwen2` | Ollama `details.family`; LM Studio `arch` |
| `ngl` | Anzahl auf die GPU ausgelagerter Layer | llama.cpp/KoboldCpp: `-ngl`/`--n-gpu-layers` aus der Kommandozeile |

Standard ist `["ctx", "quant", "params"]`.

Mehrere GPUs werden als Liste aufgeführt. Wird keine unterstützte GPU gefunden,
erscheint `GPU: n/a`. Wird kein Modell gefunden, erscheint `Model: kein Modell erkannt`.

## Voraussetzungen

- **Python 3.10 oder neuer**
- Betriebssystem: **Windows** oder **Linux**

## Projektstruktur

```
ai-hardware-overlay/
├── main.py
├── requirements.txt
├── README.md
├── config.json
├── app/
│   ├── __init__.py
│   ├── overlay.py
│   ├── config.py
│   ├── styles.py
│   └── formatter.py
├── monitors/
│   ├── __init__.py
│   ├── system_monitor.py
│   ├── gpu_detector.py
│   ├── nvidia_monitor.py
│   ├── amd_monitor.py
│   └── gpu_monitor.py
└── model_sources/
    ├── __init__.py
    ├── ollama.py
    ├── lmstudio.py
    ├── llamacpp_process.py
    └── detector.py
```

- `main.py` — Einstiegspunkt der Anwendung
- `app/` — Overlay-Fenster, Konfiguration, Styling und Text-Formatierung
- `monitors/` — System- und GPU-Erkennung/-Überwachung
- `model_sources/` — Erkennung lokal laufender KI-Modelle aus verschiedenen Quellen

## Installation (Windows)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

> Eine ausführliche Schritt-für-Schritt-Anleitung (inkl. Systembibliotheken und
> PyInstaller) steht in [INSTALL.md](INSTALL.md).

## Installation (Linux)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Auf minimalen Distributionen fehlen häufig die von Qt benötigten
Systembibliotheken. Je nach Distribution kann es notwendig sein, zusätzliche
Pakete in der Art von `libxcb-cursor0` bzw. `xcb-util`-Bibliotheken zu
installieren, damit PySide6 startet. Welche Pakete genau nötig sind, hängt von
der Distribution und der bereits installierten Paketbasis ab.

## Start

```bash
python main.py
```

Die Konfigurationsdatei `config.json` liegt neben `main.py`. Fensterposition und
Deckkraft werden beim Schließen dort gespeichert.

## NVIDIA-Hinweise

- Für NVIDIA-GPUs wird **NVML** über das Python-Paket **`nvidia-ml-py`** genutzt.
- Voraussetzung ist ein installierter **NVIDIA-Treiber** (die NVML-Bibliothek ist
  Teil des Treibers).
- NVML liefert: Name, GPU-Last, VRAM (belegt/gesamt), Temperatur und Anzahl der GPUs.
- Fehlt NVML oder ist keine NVIDIA-GPU vorhanden, läuft die Anwendung **still**
  weiter — die NVIDIA-Werte erscheinen als `n/a`.
- `nvidia-smi` ist **optional** und wird nur für die GPU-Erkennung
  (`gpu_detector.py`) verwendet, nicht für die Live-Messwerte.

## AMD-Hinweise (Linux)

- Zuerst wird **`rocm-smi`** verwendet (Erkennung über `shutil.which`) und per
  `subprocess` mit kurzen Timeouts und JSON-Ausgabe aufgerufen:
  ```
  rocm-smi --showuse --showmemuse --showtemp --showproductname --showmeminfo vram --json
  ```
  `rocm-smi` ist optional, aber **empfohlen**, da es die vollständigsten Werte liefert.
  Hinweis: `rocm-smi` gibt auf manchen Systemen eine `WARNING`-Zeile vor dem
  JSON aus. Der Parser überspringt alles bis zur ersten `{`.
- Ist `rocm-smi` nicht vorhanden oder schlägt es fehl, erfolgt ein Fallback auf
  direktes Lesen aus `/sys/class/drm/card*/device`:
  - Prüfung der Datei `vendor` (AMD-Vendor-ID `0x1002`)
  - Name abgeleitet aus `product_name` / `device` / `vendor`
  - VRAM aus `mem_info_vram_total` / `mem_info_vram_used`
  - Temperatur aus `hwmon`, sowie `gpu_busy_percent`, sofern diese Dateien existieren
- Fehlende Dateien oder fehlende Leserechte werden sauber behandelt (`n/a`).
- Ohne `rocm-smi` sind über sysfs also nur eingeschränkte Daten verfügbar.

## AMD-Hinweise (Windows)

- Unter Windows werden AMD-GPUs über **PowerShell/WMI** ermittelt:
  ```
  powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM | ConvertTo-Json"
  ```
- Die Erkennung erfolgt über Namens-Schlüsselwörter: **AMD, Radeon, RX, Vega, Ryzen**.
- Angezeigt werden Name und gesamter VRAM (`AdapterRAM`), sofern verfügbar.
- **Live-GPU-Last und der exakt aktuelle VRAM-Verbrauch sind unter Windows ohne
  zusätzliche Hersteller-APIs/-Tools in der Regel nicht zuverlässig verfügbar** und
  werden daher als `n/a` ausgegeben.
- Es werden **keine Adminrechte**, **keine externen Downloads** und **keine
  instabilen Hacks** verwendet.

## Wayland / X11 Hinweis

Das Always-on-top-Verhalten des Overlays funktioniert unter **X11 deutlich
zuverlässiger** als unter **Wayland**. Unter Wayland können Compositor-Richtlinien
das Immer-im-Vordergrund-Verhalten und die Positionierung des Fensters
einschränken: der Compositor bestimmt die Fensterposition, client-seitige
`move()`-Aufrufe werden ignoriert. Das **Verschieben per Maus** ist davon nicht
betroffen, weil es intern über `startSystemMove()` läuft (funktioniert unter
X11 und Wayland). Die **gespeicherte Startposition** (`window_x`/`window_y`)
kann unter Wayland jedoch vom Compositor überschrieben werden.

Ermitteln, welche Sitzung aktiv ist:

```bash
echo "$XDG_SESSION_TYPE"     # wayland | x11
echo "$WAYLAND_DISPLAY"      # gesetzt -> Wayland
loginctl show-session "$XDG_SESSION_ID" -p Type
```

Mögliche Abhilfen:

- Die Anwendung explizit über XWayland starten (benötigt die X11/xcb-Qt-Pakete):
  ```bash
  QT_QPA_PLATFORM=xcb python main.py
  ```
- Eine echte **X11-Session** wählen (z. B. „Plasma (X11)“ auf dem Login-Screen).
- Eine passende **Compositor-Regel** (z. B. in KDE/KWin, um ein Fenster in den
  Vordergrund zu zwingen) einrichten.

## Konfiguration

Die Datei `config.json` liegt neben `main.py` und wird beim Schließen
aktualisiert.

| Schlüssel | Standard | Bedeutung |
|---|---|---|
| `refresh_interval_ms` | `1000` | Aktualisierungsintervall der Daten in Millisekunden |
| `opacity` | `0.85` | Deckkraft des Overlay-Fensters (0.0 – 1.0) |
| `window_x` | `50` | X-Position des Fensters in Pixeln |
| `window_y` | `50` | Y-Position des Fensters in Pixeln |
| `font_size` | `13` | Schriftgröße der Monospace-Anzeige |
| `show_ollama` | `true` | Ollama-Modelle anzeigen |
| `show_lmstudio` | `true` | LM-Studio-Modelle anzeigen |
| `show_llamacpp_processes` | `true` | llama.cpp-/KoboldCpp-Prozesse anzeigen |
| `show_nvidia` | `true` | NVIDIA-GPUs anzeigen |
| `show_amd` | `true` | AMD-GPUs anzeigen |
| `max_model_name_length` | `60` | Maximale Länge eines angezeigten Modellnamens |
| `model_detail_fields` | `["ctx", "quant", "params"]` | Felder der optionalen Modell-Detailzeile (siehe oben); leere Liste `[]` schaltet sie ab |

## PyInstaller Build

### Windows

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

### Linux

```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

Die erzeugte `config.json` sollte **neben der ausführbaren Datei** liegen. Sie
wird dort automatisch erstellt bzw. beim Schließen aktualisiert, sofern der
Ablageort beschreibbar ist.

## Fehlerbehebung (Troubleshooting)

| Symptom | Mögliche Ursache | Lösung |
|---|---|---|
| `GPU: n/a` bei NVIDIA | Treiber/NVML fehlt oder keine NVIDIA-GPU vorhanden | NVIDIA-Treiber installieren, Paket `nvidia-ml-py` prüfen |
| AMD-Werte zeigen `n/a` | `rocm-smi` fehlt oder sysfs-Dateien fehlen/keine Leserechte | `rocm-smi` installieren (empfohlen); Leserechte auf `/sys/class/drm/card*/device` prüfen |
| AMD unter Windows: Load/VRAM `n/a` | Live-Werte ohne Hersteller-APIs nicht zuverlässig verfügbar | Name + Gesamt-VRAM werden angezeigt; Live-Werte sind erwartungsgemäß `n/a` |
| Overlay bleibt nicht im Vordergrund | Wayland-Compositor-Richtlinie | Unter X11 ausführen oder Compositor-Regel einrichten |
| Importfehler bei `PySide6` | Fehlende Qt-Systembibliotheken | Fehlende Systempakete installieren (z. B. `libxcb-cursor0` bzw. `xcb-util`-Bibliotheken, je nach Distribution) |
| Modelle werden nicht angezeigt | Server nicht gestartet / falscher Port / Firewall | Ollama (`localhost:11434`) bzw. LM Studio (`localhost:1234`) starten, Port prüfen |
| Hohe CPU-Auslastung | Zu kurzes Refresh-Intervall | `refresh_interval_ms` erhöhen (z. B. auf `2000`) |

## Datenschutz

- **Keine Telemetrie.** Die Anwendung sendet keinerlei Daten an externe Server.
- Es werden ausschließlich **lokale** Datenquellen gelesen:
  - localhost-APIs (Ollama auf `http://localhost:11434`, LM Studio auf `http://localhost:1234`),
  - lokale Systemdateien und -prozesse (z. B. `/sys/class/drm/*`, `psutil`-Prozessliste),
  - Systemwerkzeuge (`rocm-smi`, PowerShell/WMI) zur Hardware-Abfrage.
- Es besteht **kein Internetzugriff** außer dem Zugriff auf die genannten
  localhost-APIs.

## Lizenz

Veröffentlicht unter der **MIT-Lizenz** — siehe [LICENSE](LICENSE).
