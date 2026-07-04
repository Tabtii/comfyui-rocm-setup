"""AMD GPU database — PCI device IDs mapped to GFX architecture codes.

Maps AMD Radeon GPU PCI IDs to their GFX architecture name and recommended
HSA_OVERRIDE_GFX_VERSION for ROCm.
"""

# Format: (vendor_id:device_id) -> {name, gfx_version, architecture, vram_gb, rocm_min}
GPU_DATABASE = {
    # Navi 31 — RX 7900 series (gfx1100)
    "1002:744c": {"name": "RX 7900 XTX", "gfx_version": "11.0.0", "arch": "gfx1100", "vram_gb": 24, "rocm_min": "5.4"},
    "1002:7448": {"name": "RX 7900 XT", "gfx_version": "11.0.0", "arch": "gfx1100", "vram_gb": 20, "rocm_min": "5.4"},
    "1002:744a": {"name": "RX 7900 GRE", "gfx_version": "11.0.0", "arch": "gfx1100", "vram_gb": 16, "rocm_min": "5.4"},

    # Navi 32 — RX 7700/7800 series (gfx1101)
    "1002:747e": {"name": "RX 7800 XT", "gfx_version": "11.0.0", "arch": "gfx1101", "vram_gb": 16, "rocm_min": "5.4"},
    "1002:7480": {"name": "RX 7700 XT", "gfx_version": "11.0.0", "arch": "gfx1101", "vram_gb": 12, "rocm_min": "5.4"},

    # Navi 33 — RX 7600 series (gfx1102) — not officially supported by ROCm, use override
    "1002:7480_alt": {"name": "RX 7600", "gfx_version": "11.0.0", "arch": "gfx1102", "vram_gb": 8, "rocm_min": "5.7"},

    # Navi 21 — RX 6800/6900 series (gfx1030) — officially supported
    "1002:73bf": {"name": "RX 6900 XT", "gfx_version": "10.3.0", "arch": "gfx1030", "vram_gb": 16, "rocm_min": "5.0"},
    "1002:73a5": {"name": "RX 6800 XT", "gfx_version": "10.3.0", "arch": "gfx1030", "vram_gb": 16, "rocm_min": "5.0"},
    "1002:73a4": {"name": "RX 6800", "gfx_version": "10.3.0", "arch": "gfx1030", "vram_gb": 16, "rocm_min": "5.0"},

    # Navi 22 — RX 6700/6750 series (gfx1031) — uses override
    "1002:73df": {"name": "RX 6700 XT", "gfx_version": "10.3.0", "arch": "gfx1031", "vram_gb": 12, "rocm_min": "5.4"},
    "1002:73e0": {"name": "RX 6750 XT", "gfx_version": "10.3.0", "arch": "gfx1031", "vram_gb": 12, "rocm_min": "5.4"},

    # Navi 10 — RX 5700 series (gfx1010) — uses override, limited support
    "1002:731f": {"name": "RX 5700 XT", "gfx_version": "10.1.0", "arch": "gfx1010", "vram_gb": 8, "rocm_min": "5.4"},
}

# Fallback for unknown AMD GPUs: try gfx1100 (most common Navi 3x)
# or gfx1030 (most common Navi 2x) based on PCI generation
FALLBACK_GFX = {
    "navi3": {"gfx_version": "11.0.0", "arch": "gfx1100", "rocm_min": "5.4"},
    "navi2": {"gfx_version": "10.3.0", "arch": "gfx1030", "rocm_min": "5.0"},
    "navi1": {"gfx_version": "10.1.0", "arch": "gfx1010", "rocm_min": "5.4"},
    "unknown": {"gfx_version": "11.0.0", "arch": "gfx1100", "rocm_min": "5.4"},
}

# Known ROCm versions and their minimum supported GPUs
ROCM_VERSIONS = {
    "5.4": {"min_gfx": "gfx1030", "notes": "Last version with Navi 21 official support"},
    "5.5": {"min_gfx": "gfx1030", "notes": "Performance improvements for Navi 2x"},
    "5.6": {"min_gfx": "gfx1030", "notes": "Better Navi 3x override support"},
    "5.7": {"min_gfx": "gfx1030", "notes": "Navi 33 experimental"},
    "6.0": {"min_gfx": "gfx1030", "notes": "ROCm 6.x — Navi 3x via override only"},
    "6.1": {"min_gfx": "gfx1030", "notes": "Stable Navi 3x support via HSA_OVERRIDE"},
    "6.2": {"min_gfx": "gfx1030", "notes": "Performance + memory improvements"},
    "6.3": {"min_gfx": "gfx1030", "notes": "PyTorch 2.9+rocm6.3 baseline"},
    "7.2": {"min_gfx": "gfx1030", "notes": "ROCm 7.x — latest series"},
}

# Recommended PyTorch versions per ROCm version
TORCH_VERSIONS = {
    "5.4": "torch==2.1.0+rocm5.4",
    "5.5": "torch==2.1.0+rocm5.5",
    "5.6": "torch==2.2.0+rocm5.6",
    "5.7": "torch==2.2.0+rocm5.7",
    "6.0": "torch==2.3.0+rocm6.0",
    "6.1": "torch==2.4.0+rocm6.1",
    "6.2": "torch==2.5.0+rocm6.2",
    "6.3": "torch==2.6.0+rocm6.3",
    "7.2": "torch==2.12.0+rocm7.2",
}
