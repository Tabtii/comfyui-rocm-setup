# ComfyUI ROCm Auto-Setup

**One-click installer for ComfyUI with ROCm support on AMD RX 7000/6000 GPUs.**

Detects your AMD GPU, configures the correct ROCm environment variables, installs ComfyUI with PyTorch+ROCm, and generates startup scripts — all from a single command.

## Why

AMD GPU users struggle with ROCm setup. The `HSA_OVERRIDE_GFX_VERSION` requirement, PyTorch wheel selection, and ComfyUI configuration are constant pain points. This tool automates all of it.

## Install

```bash
pip install comfyui-rocm-setup
```

Or from source:

```bash
git clone https://github.com/Tabtii/comfyui-rocm-setup.git
cd comfyui-rocm-setup
pip install -e .
```

## Usage

```bash
# Detect your GPU and show recommended config
comfy-rocm detect

# Full install: ComfyUI + PyTorch+ROCm + models
comfy-rocm install --path ~/comfy/ComfyUI

# Generate startup script + config
comfy-rocm config --path ~/comfy/ComfyUI --systemd

# Start ComfyUI with correct ROCm environment
comfy-rocm start --port 8188

# Health check (GPU, ROCm, PyTorch, ComfyUI, VRAM)
comfy-rocm health

# Download models for your GPU
comfy-rocm models --type sdxl

# Diagnose common issues
comfy-rocm doctor
```

## Supported GPUs

| GPU | Architecture | VRAM | ROCm Min | Override Needed |
|-----|------------|------|----------|-----------------|
| RX 7900 XTX | gfx1100 | 24 GB | 5.4 | No |
| RX 7900 XT | gfx1100 | 20 GB | 5.4 | No |
| RX 7800 XT | gfx1101 | 16 GB | 5.4 | Yes (11.0.0) |
| RX 7700 XT | gfx1101 | 12 GB | 5.4 | Yes (11.0.0) |
| RX 6900 XT | gfx1030 | 16 GB | 5.0 | No |
| RX 6800 XT | gfx1030 | 16 GB | 5.0 | No |
| RX 6700 XT | gfx1031 | 12 GB | 5.4 | Yes (10.3.0) |
| RX 5700 XT | gfx1010 | 8 GB | 5.4 | Yes (10.1.0) |

Unknown AMD GPUs get a best-guess fallback based on the GPU name.

## What it does

1. **Detects** your AMD GPU via `lspci` and maps PCI ID to GFX architecture
2. **Checks** ROCm installation (pacman, dpkg, /opt/rocm)
3. **Sets** `HSA_OVERRIDE_GFX_VERSION` automatically for Navi 3x GPUs
4. **Installs** ComfyUI + PyTorch with the correct ROCm wheel index
5. **Downloads** recommended models (SDXL, SD1.5, FLUX) sized for your VRAM
6. **Generates** `startup.sh`, `config.yaml`, and optional systemd unit
7. **Verifies** GPU access via `torch.cuda.is_available()`

## KREA2 ROCm validation

This repo includes a visually validated KREA2 test workflow for RX 7800 XT / ROCm:

- [`docs/KREA2_TEST.md`](docs/KREA2_TEST.md) — validated stack, known-good/known-bad paths, visual validation rules
- [`docs/KREA2_TEST_STRATEGY.md`](docs/KREA2_TEST_STRATEGY.md) — benchmark-character, diversity, and style test strategy
- [`examples/krea2_gguf_fp8_text_encoder_validated_workflow.json`](examples/krea2_gguf_fp8_text_encoder_validated_workflow.json) — known-good ComfyUI workflow
- [`examples/krea2_prompt_presets.json`](examples/krea2_prompt_presets.json) — public benchmark, cinematic, armor-detail, and diversity prompt presets

Important: KREA2 runs are only considered valid after visual inspection. A generated PNG alone is not proof that the workflow is correct.

## Zero Dependencies

Python stdlib only. No npm, no Rust, no system packages required beyond `lspci` (pre-installed on all Linux distros).

## Requirements

- Linux (ROCm is Linux-only)
- AMD Radeon RX 6000/7000 series GPU
- ROCm 5.4+ installed
- Python 3.10+

## License

MIT — see [LICENSE](LICENSE)
