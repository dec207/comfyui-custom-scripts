$urls = @(
    @{url="https://huggingface.co/cagliostrolab/animagine-xl-3.1/resolve/main/animagine-xl-3.1.safetensors"; path="models\checkpoints\animagine-xl-3.1.safetensors"},
    @{url="https://huggingface.co/cagliostrolab/animagine-xl-3.1/resolve/main/vae/diffusion_pytorch_model.safetensors"; path="models\vae\animagine-xl-3.1.vae.safetensors"},
    @{url="https://huggingface.co/Linaqruf/animagine-xl-v3-style-lora/resolve/main/anya_forger_sdxl.safetensors"; path="models\loras\anya_forger_sdxl.safetensors"}
)

if (!(Test-Path "models\checkpoints")) { New-Item -ItemType Directory -Force -Path "models\checkpoints" }
if (!(Test-Path "models\vae")) { New-Item -ItemType Directory -Force -Path "models\vae" }
if (!(Test-Path "models\loras")) { New-Item -ItemType Directory -Force -Path "models\loras" }

foreach ($item in $urls) {
    $path = $item.path
    $url = $item.url
    Write-Output "Downloading $url to $path"
    & curl.exe -L -C - -o $path $url
}

