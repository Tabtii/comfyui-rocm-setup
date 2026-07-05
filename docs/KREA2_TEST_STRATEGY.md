# KREA2 Test Strategy for ComfyUI ROCm

This document turns the KREA2 debugging findings into a repeatable test strategy for the ComfyUI ROCm setup project.

## Goal

Validate that ComfyUI + ROCm + KREA2 can generate visually usable images, not just technically valid PNG files.

A run is successful only when the output passes **both** technical and visual checks.

## Validated baseline stack

```text
GPU: RX 7800 XT / gfx1101 / 16GB VRAM
Runtime: ComfyUI `.venv/bin/python` with ROCm torch
UNet: krea2_turbo-Q5_K_M.gguf
Text encoder: qwen3vl_4b_fp8_scaled.safetensors
Prompt node: TextEncodeKrea2
VAE: qwen_image_vae.safetensors
Sampler: euler
Scheduler: simple
Steps: 8
CFG: 3.0
Resolution: 768×1024
```

Runtime command:

```bash
cd ~/SD/ComfyUI
HSA_OVERRIDE_GFX_VERSION=11.0.0 HIP_VISIBLE_DEVICES=0 PYTORCH_HIP_ALLOC_CONF=expandable_segments:True \
  .venv/bin/python main.py --listen --port 8188 --lowvram --bf16-vae --bf16-unet --bf16-text-enc
```

## Test layers

### 1. Technical health test

Purpose: verify the stack can load and generate an output file.

Checks:

- ComfyUI starts on `http://127.0.0.1:8188`
- `/system_stats` responds
- workflow POST to `/prompt` succeeds
- output PNG is retrieved through `/view`
- PNG is valid RGB and expected size

This is necessary but **not sufficient**.

### 2. Visual validation test

Purpose: catch latent/VAE/text-encoder mismatches.

Reject outputs with:

- RGB block glitches
- horizontal neon/banding artifacts
- no recognizable subject
- melted face/chest/outfit
- obvious wrong prompt adherence
- severe anatomy deformation

Accept outputs with:

- recognizable subject
- coherent face/eyes
- no dominant RGB/banding glitch
- plausible outfit and silhouette
- acceptable prompt adherence

### 3. Benchmark-character test

Purpose: detect regressions across workflow changes.

Use one stable character:

```text
adult elven woman, silver-white hair, emerald green eyes,
pointed ears, emerald-and-gold fantasy outfit
```

This makes it easier to compare:

- text encoders
- VAE paths
- samplers
- CFG values
- LoRAs
- scheduler changes

Recommended fixed seeds:

```text
26070401, 26070402, 26070406, 26070407
```

Known-good seed from batch:

```text
26070407
```

### 4. Character-diversity test

Purpose: test robustness beyond one character attractor.

Generate several distinct adult elf archetypes:

| Archetype | Core attributes |
|---|---|
| Moon elf | silver hair, blue eyes, white/silver outfit |
| Forest elf | auburn hair, green eyes, leather/leaf outfit |
| Dark elf | dark skin, white hair, violet eyes, black/silver armor |
| Fire elf | copper-red hair, amber eyes, crimson/gold outfit |
| Ice elf | platinum hair, icy blue eyes, crystal outfit |

Use this to catch overfitting to the benchmark character and to evaluate style robustness.

### 5. Style test

Purpose: test how stable KREA2 is across style changes.

Current style presets:

- polished anime fantasy
- adult spicy but non-explicit anime pin-up
- realistic/semi-realistic cinematic fantasy portrait

Safety constraints for adult/spicy presets:

```text
adult, non-explicit, no nudity, no visible nipples, no visible genitals, no sex act
```

Negative prompt must include:

```text
child, loli, teen, underage, young-looking, explicit sexual content, pornographic
```

## Known-good and known-bad paths

### Known-good

```text
UnetLoaderGGUF -> krea2_turbo-Q5_K_M.gguf
CLIPLoader(type="krea2") -> qwen3vl_4b_fp8_scaled.safetensors
TextEncodeKrea2 -> positive/negative prompts
KSampler -> 8 steps, CFG 3, euler/simple
VAELoader -> qwen_image_vae.safetensors
```

### Known-bad / not validated

```text
qwen3vl_4b_clean.safetensors with KREA2 GGUF
Official FP8 UNETLoader workflow as currently wired
Any workflow considered successful only because a PNG exists
```

## Output review checklist

For every test batch, produce:

1. `results.json` — seed, path, size, elapsed time
2. contact sheet — all outputs labeled by seed
3. top-3 selection — best files copied into a `best/` folder
4. notes — bad outputs and likely failure mode

## Suggested next automation

Add a CLI command later:

```bash
comfy-rocm krea2-test --preset benchmark --seeds 26070401,26070402 --out /tmp/krea2_test
comfy-rocm krea2-test --preset diversity --count 10 --out /tmp/krea2_diversity
```

The command should generate workflow JSONs, submit them to ComfyUI, collect outputs, and build a contact sheet.

Visual quality still requires human/vision-model inspection.
