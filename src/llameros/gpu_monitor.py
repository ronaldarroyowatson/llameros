"""gpu_monitor.py – Query NVIDIA VRAM usage via nvidia-smi."""
import subprocess


def get_gpu_memory() -> float:
    """Return used VRAM in MB for the first GPU, or 0.0 if unavailable."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return float(result.stdout.strip().splitlines()[0])
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    return 0.0
