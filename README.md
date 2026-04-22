# ComfyUI Game Character Generation

This repository contains API-format workflows for generating 6 character images with ComfyUI.

## Characters Included

1. **Kim Da-on (\uae40\ub2e4\uc628)**: Tomboyish charm, pixie cut, oversized hoodie.
2. **Park Ha-neul (\ubc15\ud558\ub298)**: Radiant grin, light-brown wavy hair, street fashion.
3. **Seo Yun-ah (\uc11c\uc724\uc544)**: Intellectual vibe, high half-pony, designer blouse.
4. **Han So-hee (\ud55c\uc18c\ud76c)**: Cat-like eyes, long layered black hair, elegant black dress.
5. **Park Seo-yoon (\ubc15\uc11c\uc724)**: Innocent look, school uniform, sunny classroom.
6. **Lee Chae-won (\uc774\ucc44\uc6d0)**: High cheekbones, leather jacket, urban neon vibes.

## Repository Structure

- `workflows/`: Per-character ComfyUI API workflows.
- `prompt.json`: Single-workflow API prompt example.
- `run_generation.py`: Cross-platform runner for starting ComfyUI and queueing workflows.
- `models/`: Optional local model directory for checkpoints and LoRAs.
- `download_models.ps1`, `robust_download.ps1`: Windows-focused model download helpers.

## Requirements

- A working ComfyUI checkout
- Python that can run your ComfyUI installation
- Base model: `strangeThingMixToon_v3.safetensors`
- LoRA: `perfection style.safetensors`

## Quick Start

### macOS / Linux

```bash
python3 run_generation.py --comfyui-dir ../comfyui
```

### Windows

```powershell
python run_generation.py --comfyui-dir ..\comfyui
```

If your ComfyUI uses a dedicated Python executable, pass it explicitly:

```powershell
python run_generation.py --comfyui-dir ..\ComfyUI --python ..\ComfyUI\venv\Scripts\python.exe
```

## Useful Options

- Run only one workflow:

```bash
python3 run_generation.py --workflow Da-un
```

- Use this repository's `models/` folder as an extra ComfyUI model search path:

```bash
python3 run_generation.py --use-local-models
```

- Keep an existing or newly started ComfyUI server running:

```bash
python3 run_generation.py --keep-server
```

- Preview resolved paths without starting ComfyUI:

```bash
python3 run_generation.py --dry-run
```

## Notes

- Generated files are renamed from the workflow filename, such as `Da-un_v3_00001_.png`.
- If a ComfyUI server is already running on `127.0.0.1:8188`, the runner reuses it instead of starting a second one.
- The default output directory is `../img_bank` relative to this repository, and it is created automatically if missing.
- `folder_paths.py` is kept as a reference file, but `run_generation.py` is the recommended way to run these workflows across macOS and Windows.
