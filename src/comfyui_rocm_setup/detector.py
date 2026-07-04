"""GPU detection module — lspci + ROCm SMI parsing for AMD GPUs."""

import re
import subprocess
from pathlib import Path
from typing import Optional

from .gpu_db import GPU_DATABASE, FALLBACK_GFX


def _run(cmd, timeout=10):
    """Run a command, return stdout or empty string."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.SubprocessError):
        return ""


def get_pci_gpu() -> Optional[dict]:
    """Get AMD GPU PCI info via lspci."""
    out = _run(["lspci", "-nn", "-d", "::0300"])
    if not out:
        out = _run(["lspci", "-nn"])  # fallback to full list
        if not out:
            return None

    for line in out.split("\n"):
        if "AMD" not in line and "ATI" not in line and "Advanced Micro" not in line:
            continue
        if "VGA" not in line and "Display" not in line:
            continue

        # Extract PCI ID: [1002:747e]
        m = re.search(r"\[(1002:[0-9a-fA-F]{4})\]", line)
        if m:
            pci_id = m.group(1)
            name = line.split(":")[-1].strip()
            # Clean up name: remove PCI IDs and extra text
            name = re.sub(r"\[.*?\]", "", name)
            name = re.sub(r"\(rev.*?\)", "", name)
            name = " ".join(name.split()).strip()
            return {"pci_id": pci_id, "raw_name": name, "lspci_line": line}

    return None


def detect_gpu() -> Optional[dict]:
    """Detect AMD GPU and return its configuration from the database."""
    pci = get_pci_gpu()
    if pci is None:
        return None

    pci_id = pci["pci_id"]
    if pci_id in GPU_DATABASE:
        gpu = dict(GPU_DATABASE[pci_id])
        gpu["pci_id"] = pci_id
        gpu["raw_name"] = pci["raw_name"]
        gpu["lspci_line"] = pci["lspci_line"]
        return gpu

    # Unknown AMD GPU — try to guess architecture from name
    raw_name = pci["raw_name"].lower()
    if "7900" in raw_name or "7950" in raw_name:
        fallback = FALLBACK_GFX["navi3"]
    elif "7800" in raw_name or "7700" in raw_name or "7600" in raw_name:
        fallback = FALLBACK_GFX["navi3"]
    elif "6900" in raw_name or "6800" in raw_name or "6700" in raw_name:
        fallback = FALLBACK_GFX["navi2"]
    elif "5700" in raw_name or "5600" in raw_name:
        fallback = FALLBACK_GFX["navi1"]
    else:
        fallback = FALLBACK_GFX["unknown"]

    return {
        "name": pci["raw_name"],
        "pci_id": pci_id,
        "gfx_version": fallback["gfx_version"],
        "arch": fallback["arch"],
        "vram_gb": _get_vram_from_lspci(pci["lspci_line"]) or 8,
        "rocm_min": fallback["rocm_min"],
        "raw_name": pci["raw_name"],
        "lspci_line": pci["lspci_line"],
        "fallback": True,
    }


def _get_vram_from_lspci(line: str) -> Optional[int]:
    """Try to extract VRAM from lspci line (not always available)."""
    # Some lspci outputs include VRAM info, but usually not. Return None.
    return None


def get_rocm_version() -> Optional[str]:
    """Detect installed ROCm version."""
    # Try rocm-smi first (most reliable)
    rocm_smi = _run(["/opt/rocm/bin/rocm-smi", "--version"])
    if not rocm_smi:
        rocm_smi = _run(["rocm-smi", "--version"])

    if rocm_smi:
        # Parse version from output like "ROCkN version: 6.3.0"
        m = re.search(r"ROC[kmN]+\s+version:\s*([\d.]+)", rocm_smi)
        if m:
            return m.group(1)

    # Try /opt/rocm/.info/version file
    version_file = Path("/opt/rocm/.info/version")
    if version_file.exists():
        ver = version_file.read_text().strip()
        if ver:
            return ver

    # Try pacman (Arch)
    pacman = _run(["pacman", "-Q", "rocm-core"])
    if pacman:
        m = re.search(r"rocm-core\s+([\d.]+)", pacman)
        if m:
            return m.group(1)

    # Try dpkg (Ubuntu)
    dpkg = _run(["dpkg", "-l", "rocm-core"])
    if dpkg:
        m = re.search(r"rocm-core\s+([\d.]+)", dpkg)
        if m:
            return m.group(1)

    return None


def get_rocm_path() -> Optional[str]:
    """Find ROCm installation path."""
    candidates = ["/opt/rocm", "/opt/rocm-6.3.0", "/opt/rocm-6.1.0"]
    for c in candidates:
        if Path(c).exists():
            return c
    # Check PATH
    which = _run(["which", "rocm-smi"])
    if which:
        return str(Path(which).resolve().parent.parent)
    return None


def get_vram_info() -> dict:
    """Get VRAM info from rocm-smi."""
    rocm_smi = "/opt/rocm/bin/rocm-smi"
    if not Path(rocm_smi).exists():
        which = _run(["which", "rocm-smi"])
        rocm_smi = which or "rocm-smi"

    out = _run([rocm_smi, "--showmeminfo", "vram"])
    if not out:
        return {"total_bytes": 0, "used_bytes": 0, "free_bytes": 0}

    total = 0
    used = 0
    for line in out.split("\n"):
        m = re.search(r"VRAM Total Memory \(B\):\s*(\d+)", line)
        if m:
            total = int(m.group(1))
        m = re.search(r"VRAM Total Used Memory \(B\):\s*(\d+)", line)
        if m:
            used = int(m.group(1))

    return {
        "total_bytes": total,
        "used_bytes": used,
        "free_bytes": total - used,
        "total_gb": round(total / (1024**3), 1) if total else 0,
        "used_gb": round(used / (1024**3), 1) if used else 0,
        "free_gb": round((total - used) / (1024**3), 1) if total else 0,
    }


def get_gpu_gfx_from_rocm_smi() -> Optional[str]:
    """Get GFX architecture directly from rocm-smi."""
    rocm_smi = "/opt/rocm/bin/rocm-smi"
    if not Path(rocm_smi).exists():
        which = _run(["which", "rocm-smi"])
        rocm_smi = which or "rocm-smi"

    out = _run([rocm_smi, "--showproductname"])
    if not out:
        return None

    m = re.search(r"GFX Version:\s*(gfx\d+)", out)
    if m:
        return m.group(1)
    return None


def get_gpu_model_from_rocm_smi() -> Optional[str]:
    """Get GPU model name from rocm-smi."""
    rocm_smi = "/opt/rocm/bin/rocm-smi"
    if not Path(rocm_smi).exists():
        which = _run(["which", "rocm-smi"])
        rocm_smi = which or "rocm-smi"

    out = _run([rocm_smi, "--showproductname"])
    if not out:
        return None

    m = re.search(r"Card Series:\s*(.+)", out)
    if m:
        return m.group(1).strip()
    return None