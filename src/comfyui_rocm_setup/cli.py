#!/usr/bin/env python3
"""comfyui-rocm-setup — One-click ComfyUI+ROCm installer for AMD GPUs."""

import argparse
import json
import os
import sys
from pathlib import Path

from .gpu_db import GPU_DATABASE, FALLBACK_GFX, TORCH_VERSIONS
from .detector import detect_gpu, get_rocm_version, get_vram_info
from .installer import install_comfyui, download_models
from .config_gen import generate_startup_script, generate_config
from .health import health_check, diagnose


def cmd_detect(args):
    gpu = detect_gpu()
    if gpu is None:
        print("\u274c No AMD GPU detected.")
        print("\n   Make sure you have an AMD Radeon GPU installed.")
        print("   Run: lspci -d ::0300 -nn")
        sys.exit(1)

    print(f"\u2705 GPU detected: {gpu['name']}")
    print(f"   PCI ID:     {gpu['pci_id']}")
    print(f"   GFX arch:   {gpu['arch']}")
    print(f"   VRAM:       {gpu['vram_gb']} GB")
    print(f"   ROCm min:   {gpu['rocm_min']}")

    rocm_ver = get_rocm_version()
    if rocm_ver:
        print(f"\n\u2705 ROCm installed: {rocm_ver}")
    else:
        print(f"\n\u26a0\ufe0f  ROCm not found in PATH")
        print(f"   Recommended: ROCm {gpu['rocm_min']}+")

    env = get_recommended_env(gpu, rocm_ver)
    print(f"\n\U0001f527 Recommended environment:")
    for k, v in env.items():
        print(f"   {k}={v}")

    torch_pkg = TORCH_VERSIONS.get(rocm_ver or gpu['rocm_min'], f"torch (ROCm {gpu['rocm_min']})")
    print(f"\n\U0001f4e6 Recommended PyTorch: {torch_pkg}")

    if args.json:
        print(json.dumps({
            "gpu": gpu,
            "rocm_version": rocm_ver,
            "env": env,
            "torch": torch_pkg,
        }, indent=2))


def cmd_install(args):
    gpu = detect_gpu()
    if gpu is None:
        print("\u274c No AMD GPU detected. Run 'comfy-rocm detect' first.")
        sys.exit(1)

    print(f"\U0001f680 Installing ComfyUI for {gpu['name']} ({gpu['arch']})\n")

    target = Path(args.path).expanduser()
    rocm_ver = get_rocm_version() or gpu['rocm_min']

    result = install_comfyui(
        target=target,
        gpu=gpu,
        rocm_version=rocm_ver,
        skip_models=args.no_models,
        python_bin=args.python,
    )

    if result["success"]:
        print(f"\n\u2705 Installation complete!")
        print(f"   Path: {target}")
        print(f"   Start: {result['start_cmd']}")
    else:
        print(f"\n\u274c Installation failed: {result['error']}")
        sys.exit(1)


def cmd_config(args):
    gpu = detect_gpu()
    if gpu is None:
        print("\u274c No AMD GPU detected.")
        sys.exit(1)

    target = Path(args.path).expanduser()
    if not (target / "main.py").exists():
        print(f"\u274c ComfyUI not found at {target}")
        print(f"   Run 'comfy-rocm install' first.")
        sys.exit(1)

    rocm_ver = get_rocm_version() or gpu['rocm_min']
    env = get_recommended_env(gpu, rocm_ver)

    generate_startup_script(target, env, port=args.port)
    generate_config(target, gpu, rocm_ver)

    print(f"\u2705 Config generated at {target}")
    print(f"   startup.sh  — launch ComfyUI with correct env")
    print(f"   config.yaml — ComfyUI extra config")
    if args.systemd:
        from .config_gen import generate_systemd_unit
        generate_systemd_unit(target, env, user=os.environ.get("USER", "torben"))
        print(f"   comfyui.service — systemd user unit")


def cmd_health(args):
    results = health_check()
    print("\U0001f50d ComfyUI ROCm Health Check\n")
    for category, items in results.items():
        print(f"  {category}:")
        for item in items:
            status = item["status"]
            icon = "\u2705" if status == "ok" else "\u274c" if status == "fail" else "\u26a0\ufe0f"
            print(f"    {icon} {item['name']}: {item['detail']}")
        print()

    if args.json:
        print(json.dumps(results, indent=2))


def cmd_start(args):
    gpu = detect_gpu()
    if gpu is None:
        print("\u274c No AMD GPU detected.")
        sys.exit(1)

    target = Path(args.path).expanduser()
    if not (target / "main.py").exists():
        print(f"\u274c ComfyUI not found at {target}")
        sys.exit(1)

    rocm_ver = get_rocm_version() or gpu['rocm_min']
    env = os.environ.copy()
    env.update(get_recommended_env(gpu, rocm_ver))

    port = args.port
    cmd = [
        str(target / ".venv" / "bin" / "python3"),
        "main.py",
        "--port", str(port),
        "--listen", args.listen,
    ]

    print(f"\U0001f680 Starting ComfyUI on port {port}...")
    print(f"   GPU: {gpu['name']} ({gpu['arch']})")
    print(f"   URL: http://{args.listen}:{port}\n")

    os.execvpe(cmd[0], cmd, env)


def cmd_models(args):
    gpu = detect_gpu()
    if gpu is None:
        print("\u274c No AMD GPU detected.")
        sys.exit(1)

    target = Path(args.path).expanduser()
    result = download_models(target, gpu, model_type=args.type)
    print(result)


def cmd_doctor(args):
    print("\U0001f50d ComfyUI ROCm Doctor\n")
    issues = diagnose()
    if not issues:
        print("\u2705 No issues detected. Everything looks healthy!")
    else:
        for issue in issues:
            print(f"\u26a0\ufe0f  {issue['title']}")
            print(f"   {issue['description']}")
            print(f"   Fix: {issue['fix']}")
            print()


def get_recommended_env(gpu, rocm_version):
    env = {
        "HSA_OVERRIDE_GFX_VERSION": gpu["gfx_version"],
        "HIP_VISIBLE_DEVICES": "0",
    }
    if gpu["arch"] in ("gfx1101", "gfx1102", "gfx1031"):
        env["HSA_OVERRIDE_GFX_VERSION"] = "11.0.0" if gpu["arch"].startswith("gfx110") else "10.3.0"
    return env


def main():
    parser = argparse.ArgumentParser(
        prog="comfy-rocm",
        description="One-click ComfyUI+ROCm installer for AMD GPUs",
    )
    sub = parser.add_subparsers(dest="command")

    p_detect = sub.add_parser("detect", help="Detect GPU and show recommended config")
    p_detect.add_argument("--json", action="store_true", help="Output as JSON")

    p_install = sub.add_parser("install", help="Full install: ROCm, ComfyUI, models")
    p_install.add_argument("--path", default="~/comfy/ComfyUI", help="Install path")
    p_install.add_argument("--no-models", action="store_true", help="Skip model download")
    p_install.add_argument("--python", default="python3", help="Python binary")

    p_config = sub.add_parser("config", help="Generate config files")
    p_config.add_argument("--path", default="~/comfy/ComfyUI", help="ComfyUI path")
    p_config.add_argument("--port", type=int, default=8188, help="ComfyUI port")
    p_config.add_argument("--systemd", action="store_true", help="Also generate systemd unit")

    p_health = sub.add_parser("health", help="Health check")
    p_health.add_argument("--json", action="store_true")

    p_start = sub.add_parser("start", help="Start ComfyUI with correct env")
    p_start.add_argument("--path", default="~/comfy/ComfyUI", help="ComfyUI path")
    p_start.add_argument("--port", type=int, default=8188)
    p_start.add_argument("--listen", default="127.0.0.1")

    p_models = sub.add_parser("models", help="Download recommended models")
    p_models.add_argument("--path", default="~/comfy/ComfyUI", help="ComfyUI path")
    p_models.add_argument("--type", default="sdxl", choices=["sdxl", "sd15", "flux", "all"])

    sub.add_parser("doctor", help="Diagnose common issues")

    args = parser.parse_args()

    commands = {
        "detect": cmd_detect,
        "install": cmd_install,
        "config": cmd_config,
        "health": cmd_health,
        "start": cmd_start,
        "models": cmd_models,
        "doctor": cmd_doctor,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()