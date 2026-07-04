# KREA 2 ROCm Test — Status

## Current status

KREA2 itself can produce coherent images on this machine, but **the GGUF/ComfyUI-GGUF path is not validated** and produced severe RGB/banding artifacts in API tests.

## Visual findings

### Failed artifacts
The first generated files using `krea2_turbo-Q5_K_M.gguf` through `UnetLoaderGGUF` / generic API workflows were visually broken:

- repeated RGB blocks
- horizontal/rectangular neon banding
- no recognizable subject
- no usable prompt adherence

These files were removed from the repo and must not be used as success proof.

### Coherent existing KREA2 reference
A prior local KREA2 output exists at:

```text
~/SD/ComfyUI/output/krea2_sexy_elfe_anime.png
```

It is visually coherent: anime elf, pointed ears, silver hair, green/gold fantasy outfit, clean face. It has some overexposed glow and typical AI detail issues, but no decoder/latent RGB glitch.

A copy is stored in this repo as:

```text
krea2_reference_good_existing.png
```

This is a **visual reference**, not proof that the current GGUF workflow is valid.

## Root cause hypothesis

The broken outputs are most likely caused by one of these:

1. GGUF KREA2 Turbo model incompatibility with current `ComfyUI-GGUF`
2. Incorrect latent/scheduler behavior for the GGUF path
3. Using community GGUF conversion where the official ComfyUI workflow expects FP8 safetensors

The official installed ComfyUI workflow template for KREA2 Turbo uses:

```text
UNETLoader -> krea2_turbo_fp8_scaled.safetensors
CLIPLoader(type="krea2") -> qwen3vl_4b_fp8_scaled.safetensors / qwen3vl_4b_clean.safetensors
VAELoader -> qwen_image_vae.safetensors
KSampler -> 8 steps, cfg 1, euler, simple
ConditioningZeroOut for negative
```

## Correct model path from official template

Download the official KREA2 FP8 UNet:

```bash
mkdir -p ~/SD/ComfyUI/models/diffusion_models
cd ~/SD/ComfyUI/models/diffusion_models
curl -L -C - -o krea2_turbo_fp8_scaled.safetensors \
  https://huggingface.co/Comfy-Org/Krea-2/resolve/main/diffusion_models/krea2_turbo_fp8_scaled.safetensors
```

The file is ~13.1 GB.

## Runtime command

Use ComfyUI's ROCm venv, not system Python:

```bash
cd ~/SD/ComfyUI
HSA_OVERRIDE_GFX_VERSION=11.0.0 HIP_VISIBLE_DEVICES=0 PYTORCH_HIP_ALLOC_CONF=expandable_segments:True \
  .venv/bin/python main.py --listen --port 8188 --bf16-vae --bf16-unet --bf16-text-enc
```

## Text encoder note

For local testing, `qwen3vl_4b_clean.safetensors` works because it uses the correct `model.` prefix. `krea/model.safetensors` has `language_model.` keys and can be misdetected as CLIP-L in some paths.

## Validation rule

A KREA2 run is only considered valid when:

- output file exists on disk
- PNG dimensions and size are plausible
- visual inspection shows a recognizable subject
- no RGB block/banding artifacts dominate the image
- prompt adherence is acceptable

Do not mark a run successful merely because ComfyUI returned a PNG.