# Llameros

A lightweight watchdog that monitors GPU VRAM, system RAM, and key processes to prevent OOM crashes.

## Purpose

Llameros runs in the background and polls GPU VRAM and system RAM usage every second.
When a configured threshold is exceeded, it kills the first matching process from the watchlist
and logs the event to `llameros.log`.

## How to Run

```bash
python src/main.py
```

## Configuration

Thresholds and watched processes are defined in `config/rules.yaml`:

```yaml
vram_limit_mb: 14000      # Kill trigger when VRAM used exceeds this value (MB)
ram_limit_mb: 30000       # Kill trigger when RAM used exceeds this value (MB)
processes:
  - ollama.exe            # First match in this list is killed on threshold breach
  - python.exe
  - VirtualBoxVM.exe
```

Adjust the limits to match your system's available VRAM and RAM.

## Requirements

- Python 3.8+
- NVIDIA GPU with `nvidia-smi` on PATH (for VRAM monitoring)
- Dependencies: `pip install -r requirements.txt`

## Log Output

Events are appended to `llameros.log` in the working directory.
simple system to monitor and schedule programs that take up ram and gpu, like ai agents on a pc...
