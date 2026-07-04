# KREA 2 ROCm Test — Verified Working

## Setup
- **GPU:** AMD Radeon RX 7800 XT (gfx1101, 16GB VRAM)
- **ROCm:** 7.2.4
- **PyTorch:** 2.6.0+rocm6.1 (in ComfyUI `.venv`)
- **ComfyUI:** v0.26.0
- **Env:** `HSA_OVERRIDE_GFX_VERSION=11.0.0 HIP_VISIBLE_DEVICES=0`

## Models Used
| Component | File | Size |
|-----------|------|------|
| UNet (GGUF) | `krea2_turbo-Q5_K_M.gguf` | 8.3 GB |
| Text Encoder | `qwen3vl_4b_clean.safetensors` | 4.9 GB |
| VAE | `qwen_image_vae.safetensors` | Wan 2.1 VAE |

## Critical Fix: Text Encoder Key Prefix
The `krea/model.safetensors` file uses key prefix `language_model.layers.0...` but
ComfyUI's `detect_te_model()` expects `model.language_model.layers.0...`. This causes
the model to be misdetected as `TEModel.CLIP_L` (768-dim) instead of Qwen3-VL-4B (2560-dim),
resulting in `mat1 and mat2 shapes cannot be multiplied (77x768 and 3072x768)`.

**Solution:** Use `qwen3vl_4b_clean.safetensors` from `models/text_encoders/` which has
the correct `model.` prefix. Symlink it into `models/clip/`:

```bash
cd ComfyUI/models/clip
ln -sf ../text_encoders/qwen3vl_4b_clean.safetensors qwen3vl_4b_clean.safetensors
```

## Workflow
See `examples/krea2_txt2img_workflow.json` for the working ComfyUI API workflow.

### Node Graph
```
UnetLoaderGGUF → KSampler → VAEDecode → SaveImage
CLIPLoader ─────→ TextEncodeKrea2 (positive) → KSampler
CLIPLoader ─────→ TextEncodeKrea2 (negative) → KSampler
VAELoader ──────→ VAEDecode
EmptyLatentImage → KSampler
```

## Test Result
- **Prompt:** "beautiful anime elf girl, pointed ears, green eyes, flowing silver hair, fantasy dress, detailed face, masterpiece, best quality"
- **Negative:** "blurry, deformed, low quality, bad anatomy, extra fingers"
- **Steps:** 20, CFG: 7, Sampler: euler, Size: 512×768
- **Generation time:** ~120 seconds (including model loading)
- **Output:** `test_output_krea2_elf.png` (512×768, 362 KB)

## Custom Nodes Required
- `ComfyUI-GGUF` — for `.gguf` model loading
- `ComfyUI-Krea2TexTEncoder` — for `TextEncodeKrea2` and `Krea2SystemPrompt` nodes
- `ComfyUI-Conditioning-Rebalance` — for `ConditioningKrea2Rebalance` (optional)