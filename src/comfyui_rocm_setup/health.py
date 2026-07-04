"""Health check and diagnostics module."""

import re
import subprocess
from pathlib import Path
from typing import Optional

from .detector import detect_gpu, get_rocm_version, get_rocm_path, get_vram_info


def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "", -1


def health_check() -> dict:
    """Run comprehensive health check and return structured results."""
    results = {
        "GPU": [],
        "ROCm": [],
        "PyTorch": [],
        "ComfyUI": [],
    }

    # --- GPU ---
    gpu = detect_gpu()
    if gpu:
        results["GPU"].append({
            "name": gpu["name"],
            "status": "ok",
            "detail": f"{gpu['name']} ({gpu['arch']}, {gpu['vram_gb']}GB VRAM)",
        })
    else:
        results["GPU"].append({
            "name": "AMD GPU",
            "status": "fail",
            "detail": "No AMD GPU detected via lspci",
        })

    # VRAM info
    vram = get_vram_info()
    if vram["total_bytes"] > 0:
        results["GPU"].append({
            "name": "VRAM",
            "status": "ok" if vram["free_gb"] > 1 else "warn",
            "detail": f"{vram['used_gb']:.1f}/{vram['total_gb']:.1f} GB used ({vram['free_gb']:.1f} GB free)",
        })
    else:
        results["GPU"].append({
            "name": "VRAM",
            "status": "warn",
            "detail": "Could not read VRAM (rocm-smi not in PATH?)",
        })

    # --- ROCm ---
    rocm_ver = get_rocm_version()
    if rocm_ver:
        results["ROCm"].append({
            "name": "ROCm version",
            "status": "ok",
            "detail": f"ROCm {rocm_ver}",
        })
    else:
        results["ROCm"].append({
            "name": "ROCm version",
            "status": "fail",
            "detail": "ROCm not detected. Install from https://rocm.docs.amd.com/",
        })

    rocm_path = get_rocm_path()
    if rocm_path:
        results["ROCm"].append({
            "name": "ROCm path",
            "status": "ok",
            "detail": rocm_path,
        })

    # Check HSA_OVERRIDE_GFX_VERSION
    env_override = __import__("os").environ.get("HSA_OVERRIDE_GFX_VERSION")
    if gpu and gpu.get("arch", "").startswith("gfx110"):
        if env_override:
            results["ROCm"].append({
                "name": "HSA_OVERRIDE_GFX_VERSION",
                "status": "ok",
                "detail": f"Set to {env_override}",
            })
        else:
            results["ROCm"].append({
                "name": "HSA_OVERRIDE_GFX_VERSION",
                "status": "warn",
                "detail": f"Not set — Navi 3x GPUs need HSA_OVERRIDE_GFX_VERSION={gpu['gfx_version']}",
            })

    # --- PyTorch ---
    # Find ComfyUI venv
    comfy_paths = [
        Path.home() / "comfy" / "ComfyUI",
        Path.home() / "SD" / "ComfyUI",
        Path.home() / "ComfyUI",
    ]

    venv_python = None
    comfy_path = None
    for p in comfy_paths:
        venv_p = p / ".venv" / "bin" / "python3"
        if venv_p.exists() and (p / "main.py").exists():
            venv_python = str(venv_p)
            comfy_path = p
            break

    if venv_python:
        out, rc = _run([
            venv_python, "-c",
            "import torch; print(torch.__version__); print(torch.version.hip); print(torch.cuda.is_available())"
        ])
        if rc == 0 and out:
            lines = out.strip().split("\n")
            torch_ver = lines[0] if lines else "unknown"
            hip_ver = lines[1] if len(lines) > 1 else "None"
            cuda_ok = "True" in (lines[2] if len(lines) > 2 else "")

            results["PyTorch"].append({
                "name": "PyTorch version",
                "status": "ok" if "rocm" in torch_ver.lower() or hip_ver != "None" else "warn",
                "detail": f"{torch_ver} (HIP: {hip_ver})",
            })

            results["PyTorch"].append({
                "name": "GPU access",
                "status": "ok" if cuda_ok else "fail",
                "detail": "torch.cuda.is_available() = " + ("True" if cuda_ok else "False"),
            })
        else:
            results["PyTorch"].append({
                "name": "PyTorch",
                "status": "fail",
                "detail": "Could not import torch in venv",
            })
    else:
        # Try system python
        out, rc = _run([
            "python3", "-c",
            "import torch; print(torch.__version__); print(torch.version.hip); print(torch.cuda.is_available())"
        ])
        if rc == 0 and out:
            lines = out.strip().split("\n")
            torch_ver = lines[0] if lines else "unknown"
            hip_ver = lines[1] if len(lines) > 1 else "None"
            cuda_ok = "True" in (lines[2] if len(lines) > 2 else "")

            results["PyTorch"].append({
                "name": "PyTorch (system)",
                "status": "ok" if cuda_ok else "warn",
                "detail": f"{torch_ver} (HIP: {hip_ver}, CUDA: {cuda_ok})",
            })
        else:
            results["PyTorch"].append({
                "name": "PyTorch",
                "status": "fail",
                "detail": "torch not importable",
            })

    # --- ComfyUI ---
    if comfy_path:
        results["ComfyUI"].append({
            "name": "ComfyUI path",
            "status": "ok",
            "detail": str(comfy_path),
        })

        # Check if running
        out, rc = _run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                       "http://127.0.0.1:8188/system_stats"])
        if out == "200":
            results["ComfyUI"].append({
                "name": "ComfyUI running",
                "status": "ok",
                "detail": "Responding on http://127.0.0.1:8188",
            })
        else:
            results["ComfyUI"].append({
                "name": "ComfyUI running",
                "status": "warn",
                "detail": "Not responding on port 8188 (may not be started)",
            })

        # Check models
        checkpoints = comfy_path / "models" / "checkpoints"
        if checkpoints.exists():
            safetensors = list(checkpoints.glob("*.safetensors"))
            if safetensors:
                results["ComfyUI"].append({
                    "name": "Models",
                    "status": "ok",
                    "detail": f"{len(safetensors)} checkpoint(s) found",
                })
            else:
                results["ComfyUI"].append({
                    "name": "Models",
                    "status": "warn",
                    "detail": "No .safetensors in models/checkpoints/",
                })
        else:
            results["ComfyUI"].append({
                "name": "Models",
                "status": "warn",
                "detail": "models/checkpoints/ directory not found",
            })
    else:
        results["ComfyUI"].append({
            "name": "ComfyUI",
            "status": "fail",
            "detail": "ComfyUI installation not found",
        })

    return results


def diagnose() -> list:
    """Diagnose common ROCm/ComfyUI issues and return actionable fixes."""
    issues = []

    gpu = detect_gpu()
    rocm_ver = get_rocm_version()

    # Issue: No ROCm
    if not rocm_ver:
        issues.append({
            "title": "ROCm not installed",
            "description": "No ROCm installation detected. PyTorch cannot use your AMD GPU.",
            "fix": "Install ROCm from https://rocm.docs.amd.com/ or your distro's package manager",
        })

    # Issue: Navi 3x without HSA_OVERRIDE
    if gpu and gpu.get("arch", "").startswith("gfx110"):
        env_override = __import__("os").environ.get("HSA_OVERRIDE_GFX_VERSION")
        if not env_override:
            issues.append({
                "title": "HSA_OVERRIDE_GFX_VERSION not set",
                "description": f"Your {gpu['name']} ({gpu['arch']}) requires HSA_OVERRIDE_GFX_VERSION to work with ROCm.",
                "fix": f"export HSA_OVERRIDE_GFX_VERSION={gpu['gfx_version']} or use 'comfy-rocm start' which sets it automatically",
            })

    # Issue: GPU in low-power state
    rocm_smi = "/opt/rocm/bin/rocm-smi" if Path("/opt/rocm/bin/rocm-smi").exists() else "rocm-smi"
    out, _ = _run([rocm_smi])
    if "low-power state" in out:
        issues.append({
            "title": "GPU in low-power state",
            "description": "AMD GPU is in a low-power/runtime-suspended state, which can cause inference failures.",
            "fix": "Run: echo on | sudo tee /sys/bus/pci/devices/0000:03:00.0/power/control (adjust PCI address)",
        })

    # Issue: PyTorch CUDA not available
    comfy_paths = [
        Path.home() / "comfy" / "ComfyUI",
        Path.home() / "SD" / "ComfyUI",
    ]
    for p in comfy_paths:
        venv_p = p / ".venv" / "bin" / "python3"
        if venv_p.exists():
            out, rc = _run([str(venv_p), "-c", "import torch; print(torch.cuda.is_available())"])
            if rc == 0 and "False" in out:
                issues.append({
                    "title": "PyTorch cannot see GPU",
                    "description": f"torch.cuda.is_available() returns False in {p.name} venv.",
                    "fix": f"Check: (1) ROCm installed, (2) HSA_OVERRIDE_GFX_VERSION set, (3) PyTorch built with ROCm support",
                })
            break

    # Issue: No ComfyUI
    comfy_found = any((p / "main.py").exists() for p in comfy_paths)
    if not comfy_found:
        issues.append({
            "title": "ComfyUI not installed",
            "description": "No ComfyUI installation found in common paths.",
            "fix": "Run: comfy-rocm install",
        })

    # Issue: No models
    for p in comfy_paths:
        ckpt_dir = p / "models" / "checkpoints"
        if ckpt_dir.exists():
            if not list(ckpt_dir.glob("*.safetensors")):
                issues.append({
                    "title": "No model checkpoints",
                    "description": f"No .safetensors files in {ckpt_dir}",
                    "fix": "Run: comfy-rocm models --type sdxl",
                })
            break

    return issues