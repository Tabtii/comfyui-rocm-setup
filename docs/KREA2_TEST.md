# KREA 2 ROCm Test — Validated Workflow

## Final status: validated

KREA2 has been validated locally on the RX 7800 XT with ROCm. The first attempts failed because the wrong text encoder / workflow path was used. The working path is **not** the official FP8 `UNETLoader` workflow in this setup; the validated path is the existing GGUF UNet with the FP8 Qwen3-VL text encoder.

## Validated output

```text
krea2_validated_elf.png
```

Generated output characteristics:

- 768×1024 PNG
- coherent anime elf woman
- pointed ears
- silver hair
- green/gold fantasy outfit
- clean face and eyes
- no RGB block/banding glitch
- no dominant decoder artifacts

Minor limitations: hands are mostly out of frame / hidden; there is some typical AI line-art glow/overexposure, but the image is visually usable.

## Validated workflow

```text
examples/krea2_gguf_fp8_text_encoder_validated_workflow.json
```

### Working stack

```text
UnetLoaderGGUF -> krea2_turbo-Q5_K_M.gguf
CLIPLoader(type="krea2") -> qwen3vl_4b_fp8_scaled.safetensors
TextEncodeKrea2 -> positive prompt
TextEncodeKrea2 -> negative prompt
KSampler -> 8 steps, CFG 3.0, euler, simple
VAELoader -> qwen_image_vae.safetensors
VAEDecode -> SaveImage
```

### Runtime command

Use ComfyUI's ROCm venv, not system Python:

```bash
cd ~/SD/ComfyUI
HSA_OVERRIDE_GFX_VERSION=11.0.0 HIP_VISIBLE_DEVICES=0 PYTORCH_HIP_ALLOC_CONF=expandable_segments:True \
  .venv/bin/python main.py --listen --port 8188 --lowvram --bf16-vae --bf16-unet --bf16-text-enc
```

## Critical lessons learned

### 1. `qwen3vl_4b_clean.safetensors` loads but produced RGB glitches here

Earlier reasoning assumed the cleaned text encoder was safer because it has a nicer `model.` prefix. In practice, KREA2 output quality was broken with that setup: severe RGB/banding artifacts and no recognizable subject.

For this local KREA2 GGUF workflow, use:

```text
qwen3vl_4b_fp8_scaled.safetensors
```

### 2. Official FP8 `UNETLoader` workflow also glitched in this environment

The official template points to:

```text
models/diffusion_models/krea2_turbo_fp8_scaled.safetensors
```

It downloaded correctly and safetensors opened successfully, but the test output still produced RGB block artifacts with the local workflow. Keep it available for future debugging, but do not treat it as validated.

### 3. PNG creation is not enough

A ComfyUI run is valid only after visual inspection. The broken workflows all produced valid PNG files, but the images were unusable.

## Validation rule

A KREA2 run is only considered successful when:

- output file exists on disk
- PNG dimensions and size are plausible
- visual inspection shows a recognizable subject
- no RGB block/banding artifacts dominate the image
- prompt adherence is acceptable

Do not mark a run successful merely because ComfyUI returned a PNG.

## Known-bad paths

These produced RGB/block artifacts and should not be used as proof:

- `qwen3vl_4b_clean.safetensors` with KREA2 GGUF
- official FP8 `UNETLoader` workflow as currently wired
- generic `KSampler` workflow using wrong text encoder assumptions

## Known-good path

Use the workflow in:

```text
examples/krea2_gguf_fp8_text_encoder_validated_workflow.json
```

and inspect the reference output:

```text
krea2_validated_elf.png
```

## Repeatable test improvements

The chat-discovered improvements were turned into project assets:

```text
docs/KREA2_TEST_STRATEGY.md
examples/krea2_prompt_presets.json
```

The strategy separates two complementary test modes:

- **Benchmark character** — same silver-haired emerald-eyed elf, useful for regression testing CFG/steps/sampler/VAE/text-encoder changes.
- **Character diversity** — moon/forest/dark/fire/ice elf archetypes, useful for robustness testing and checking whether KREA2 collapses to one character.

The prompt presets include public benchmark, cinematic, armor-detail, and diversity variants. Private robustness prompts are intentionally not included as public defaults.
