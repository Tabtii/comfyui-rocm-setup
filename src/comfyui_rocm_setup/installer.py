"""ComfyUI installer module — clone, venv, pip install, model download."""

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

from .gpu_db import TORCH_VERSIONS


def _run(cmd, cwd=None, env=None, timeout=300, check=True):
    """Run a command, stream output, return (success, output)."""
    try:
        r = subprocess.run(
            cmd, cwd=cwd, env=env, timeout=timeout,
            capture_output=True, text=True,
        )
        success = r.returncode == 0
        output = (r.stdout or "") + (r.stderr or "")
        if check and not success:
            return False, output
        return success, output
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return False, str(e)


def install_comfyui(target: Path, gpu: dict, rocm_version: str,
                    skip_models: bool = False, python_bin: str = "python3") -> dict:
    """Full ComfyUI installation with ROCm support.

    Args:
        target: Installation directory
        gpu: GPU info dict from detect_gpu()
        rocm_version: ROCm version string (e.g., "6.3")
        skip_models: Skip model download
        python_bin: Python binary to use for venv

    Returns:
        dict with success, error, start_cmd
    """
    target = Path(target).expanduser()
    target.mkdir(parents=True, exist_ok=True)

    steps = []

    # Step 1: Clone ComfyUI if not present
    if not (target / "main.py").exists():
        print("  [1/5] Cloning ComfyUI...")
        ok, out = _run([
            "git", "clone", "https://github.com/comfyanonymous/ComfyUI.git", str(target)
        ], timeout=120)
        if not ok:
            return {"success": False, "error": f"git clone failed: {out[:200]}"}
        steps.append("cloned ComfyUI")
    else:
        print("  [1/5] ComfyUI already present, skipping clone")
        steps.append("ComfyUI already existed")

    # Step 2: Create venv
    venv_path = target / ".venv"
    if not venv_path.exists():
        print("  [2/5] Creating virtual environment...")
        try:
            venv.create(venv_path, with_pip=True, python=python_bin)
        except Exception as e:
            return {"success": False, "error": f"venv creation failed: {e}"}
        steps.append("venv created")
    else:
        print("  [2/5] venv already exists")
        steps.append("venv existed")

    venv_python = str(venv_path / "bin" / "python3")

    # Step 3: Install PyTorch with ROCm
    print(f"  [3/5] Installing PyTorch+ROCm ({rocm_version})...")
    torch_pkg = TORCH_VERSIONS.get(rocm_version, f"torch==2.6.0+rocm{rocm_version}")
    pip_index_url = f"https://download.pytorch.org/whl/rocm{rocm_version}"

    ok, out = _run([
        venv_python, "-m", "pip", "install",
        torch_pkg,
        "--index-url", pip_index_url,
    ], timeout=600)
    if not ok:
        # Fallback: try without explicit index (system PyTorch might have ROCm)
        print(f"  [3/5] Fallback: installing torch from default index...")
        ok, out = _run([
            venv_python, "-m", "pip", "install", "torch", "torchvision", "torchaudio"
        ], timeout=600)
        if not ok:
            return {"success": False, "error": f"PyTorch install failed: {out[:300]}"}
    steps.append(f"PyTorch {torch_pkg} installed")

    # Step 4: Install ComfyUI requirements
    req_file = target / "requirements.txt"
    if req_file.exists():
        print("  [4/5] Installing ComfyUI requirements...")
        ok, out = _run([
            venv_python, "-m", "pip", "install", "-r", str(req_file)
        ], timeout=600)
        if not ok:
            return {"success": False, "error": f"requirements.txt install failed: {out[:300]}"}
        steps.append("requirements installed")

    # Step 5: Verify PyTorch can see GPU
    print("  [5/5] Verifying GPU access...")
    verify_script = (
        "import torch\\n"
        f"print('torch', torch.__version__)\\n"
        f"print('hip', torch.version.hip)\\n"
        f"print('cuda available', torch.cuda.is_available())\\n"
        f"if torch.cuda.is_available():\\n"
        f"    print('device', torch.cuda.get_device_name(0))\\n"
        f"    print('vram', torch.cuda.get_device_properties(0).total_memory // (1024**3), 'GB')\\n"
    )
    ok, out = _run([venv_python, "-c", verify_script], timeout=30, check=False)
    if "cuda available True" in out or "device" in out:
        steps.append("GPU verified")
        print(f"  [5/5] GPU access confirmed!")
    else:
        print(f"  [5/5] Warning: GPU not detected by PyTorch")
        print(f"         You may need HSA_OVERRIDE_GFX_VERSION={gpu['gfx_version']}")
        steps.append("GPU not verified (check HSA_OVERRIDE)")

    # Download models
    if not skip_models:
        print("\\n  Downloading recommended models...")
        download_models(target, gpu)

    # Generate startup script
    from .config_gen import generate_startup_script
    env_vars = {
        "HSA_OVERRIDE_GFX_VERSION": gpu["gfx_version"],
        "HIP_VISIBLE_DEVICES": "0",
    }
    generate_startup_script(target, env_vars)

    start_cmd = f"cd {target} && bash startup.sh"
    return {
        "success": True,
        "steps": steps,
        "start_cmd": start_cmd,
    }


def download_models(target: Path, gpu: dict, model_type: str = "sdxl") -> str:
    """Download recommended models for the GPU.

    Downloads to ComfyUI's model directories.
    """
    target = Path(target).expanduser()
    models_dir = target / "models"

    # Model URLs
    models = {
        "sdxl": [
            {
                "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
                "path": models_dir / "checkpoints" / "sd_xl_base_1.0.safetensors",
                "size_gb": 6.9,
                "name": "SDXL Base 1.0",
            },
        ],
        "sd15": [
            {
                "url": "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors",
                "path": models_dir / "checkpoints" / "v1-5-pruned-emaonly.safetensors",
                "size_gb": 4.0,
                "name": "SD 1.5 Pruned",
            },
        ],
        "flux": [
            {
                "url": "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/flux1-schnell.safetensors",
                "path": models_dir / "checkpoints" / "flux1-schnell.safetensors",
                "size_gb": 11.9,
                "name": "FLUX.1 Schnell",
            },
        ],
    }

    if model_type == "all":
        to_download = models["sdxl"] + models["sd15"] + models["flux"]
    else:
        to_download = models.get(model_type, models["sdxl"])

    # Check VRAM — warn if model is larger than VRAM
    vram_gb = gpu.get("vram_gb", 8)
    results = []
    for m in to_download:
        if m["size_gb"] > vram_gb:
            results.append(f"  ⚠️  {m['name']} ({m['size_gb']}GB) exceeds VRAM ({vram_gb}GB) — may OOM")
            continue

        dest = m["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists():
            results.append(f"  ✅ {m['name']} already exists ({dest})")
            continue

        print(f"  Downloading {m['name']} ({m['size_gb']}GB)...")
        ok, out = _run([
            "wget", "-q", "--show-progress", "-O", str(dest), m["url"]
        ], timeout=1800)
        if ok:
            results.append(f"  ✅ {m['name']} downloaded")
        else:
            results.append(f"  ❌ {m['name']} download failed")

    return "\n".join(results)