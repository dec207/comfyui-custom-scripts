# ComfyUI Game Character Generation

This repository contains custom workflows and configurations for generating game characters (e.g., Kim Da-on).

## Contents

### Workflows
- `game_character_workflow.json`: Optimized workflow for the game character "Kim Da-on".
- `prompt.json`: Direct API prompt configuration.

### Model Requirements
- **Base Model**: `strangeThingMixToon_v3.safetensors`
- **LoRA**: `perfection style.safetensors` (Weight: 0.7)

### Custom Configuration
- `folder_paths.py`: Modified to output images directly to `C:\workspace\img_back`.

### Images
The `images/` directory contains sample outputs of the game characters.
