from huggingface_hub import hf_hub_download
import os
import shutil

repo_id = "KittyPrideUs/LoraXL"
filename = "anya_lora_sdxl_v1-000008.safetensors"
local_dir = "models/loras"
local_filename = "anya_forger_sdxl.safetensors"

print(f"Downloading {filename} from {repo_id}...")
downloaded_path = hf_hub_download(repo_id=repo_id, filename=filename, local_dir=local_dir)

# Rename to the desired filename
target_path = os.path.join(local_dir, local_filename)
if os.path.exists(target_path):
    os.remove(target_path)
shutil.move(downloaded_path, target_path)

print(f"Downloaded and moved to {target_path}")
