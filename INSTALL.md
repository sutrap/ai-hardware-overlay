# Installation

Ausführliche Schritt-für-Schritt-Anleitung. Eine Kurzfassung steht im
[README](README.md).

## 1. Voraussetzungen

- **Python 3.10 oder neuer** (`python --version`)
- Betriebssystem: **Windows** oder **Linux**
- Optional, je nach Hardware/Quelle:
  - **NVIDIA-Treiber** (für Live-GPU-Werte; NVML ist Teil des Treibers)
  - **`rocm-smi`** (für vollständige AMD-Werte unter Linux)
  - laufende lokale KI-Server: **Ollama** (`localhost:11434`) und/oder
    **LM Studio** (`localhost:1234`)

## 2. Repository klonen

```bash
git clone git@github.com:sutrap/ai-hardware-overlay.git
cd ai-hardware-overlay
```

## 3. Virtuelle Umgebung anlegen

**Linux / macOS**

```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

## 4. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

Enthalten: `PySide6` (GUI), `psutil` (CPU/RAM/Prozesse), `nvidia-ml-py`
(NVML) und `requests` (localhost-APIs).

### Systembibliotheken für PySide6 (Linux)

Auf minimalen Distributionen fehlen häufig die von Qt benötigten
Systembibliotheken. Beispielhaft (Debian/Ubuntu):

```bash
sudo apt install libxcb-cursor0 libxcb-xinerama0 libxkbcommon-x11-0
```

Welche Pakete genau nötig sind, hängt von Distribution und bereits
installierter Paketbasis ab. Bei einem Importfehler von `PySide6` die
Fehlermeldung lesen — sie nennt die fehlende Bibliothek.

## 5. Starten

```bash
python main.py
```

Beim ersten Start wird `config.json` neben `main.py` angelegt, falls sie noch
nicht existiert. Fensterposition und Deckkraft werden beim Schließen dort
gespeichert.

## 6. Bedienung

- **Verschieben:** linke Maustaste gedrückt halten und ziehen
- **Rechtsklick-Kontextmenü:** Beenden, Transparenz erhöhen/verringern,
  Aktualisierungsintervall (500 / 1000 / 2000 ms)

## 7. Optional: eigenständige ausführbare Datei (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

Die erzeugte `config.json` sollte **neben der ausführbaren Datei** liegen; sie
wird dort automatisch erstellt bzw. aktualisiert, sofern der Ablageort
beschreibbar ist.

## Fehlerbehebung

Weitere Hinweise zu NVIDIA, AMD, Wayland/X11 und bekannten Symptomen stehen im
Abschnitt **Troubleshooting** des [README](README.md#fehlerbehebung-troubleshooting).
