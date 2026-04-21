# ComfyUI Game Character Generation

This repository contains custom workflows for generating 6 unique game characters with high-quality settings.

## Characters Included

1. **Kim Da-on (\uae40\ub2e4\uc628)**: Tomboyish charm, pixie cut, oversized hoodie.
2. **Park Ha-neul (\ubc15\ud558\ub298)**: Radiant grin, light-brown wavy hair, street fashion.
3. **Seo Yun-ah (\uc11c\uc724\uc544)**: Intellectual vibe, high half-pony, designer blouse.
4. **Han So-hee (\ud55c\uc18c\ud76c)**: Cat-like eyes, long layered black hair, elegant black dress.
5. **Park Seo-yoon (\ubc15\uc11c\uc724)**: Innocent look, school uniform, sunny classroom.
6. **Lee Chae-won (\uc774\ucc44\uc6d0)**: High cheekbones, leather jacket, urban neon vibes.

## Repository Structure

- workflows/: Contains separate JSON workflows for each character.
- prompt.json: Default API prompt configuration.
- older_paths.py: Configured to output to C:\workspace\img_back.

## Requirements

- **Base Model**: strangeThingMixToon_v3.safetensors
- **LoRA**: perfection style.safetensors (Weight: 0.7)
- **Resolution**: 832 x 1024 (Optimized for SDXL)
