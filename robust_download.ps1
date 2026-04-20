$checkpoint_url = "https://huggingface.co/cagliostrolab/animagine-xl-3.1/resolve/main/animagine-xl-3.1.safetensors"
$checkpoint_path = "models/checkpoints/animagine-xl-3.1.safetensors"
$checkpoint_expected_size = 6938325776

$vae_url = "https://huggingface.co/cagliostrolab/animagine-xl-3.1/resolve/main/vae/diffusion_pytorch_model.safetensors"
$vae_path = "models/vae/animagine-xl-3.1.vae.safetensors"
$vae_expected_size = 167335342

$log_path = "download_progress.log"

function Log-Message($message) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $message" | Out-File -FilePath $log_path -Append
    Write-Host "$timestamp - $message"
}

# Ensure directories exist
if (!(Test-Path "models/checkpoints")) { New-Item -ItemType Directory -Force -Path "models/checkpoints" }
if (!(Test-Path "models/vae")) { New-Item -ItemType Directory -Force -Path "models/vae" }

Log-Message "Starting robust downloads..."

# VAE Download
if (Test-Path $vae_path) {
    $vae_size = (Get-Item $vae_path).Length
    if ($vae_size -eq $vae_expected_size) {
        Log-Message "VAE already downloaded and size matches."
    } else {
        Log-Message "VAE size mismatch ($vae_size vs $vae_expected_size). Restarting download..."
        Remove-Item $vae_path
        curl.exe -L -o $vae_path $vae_url 2>&1 | Out-File -FilePath $log_path -Append
    }
} else {
    Log-Message "Downloading VAE..."
    curl.exe -L -o $vae_path $vae_url 2>&1 | Out-File -FilePath $log_path -Append
}

# Checkpoint Download
if (Test-Path $checkpoint_path) {
    $checkpoint_size = (Get-Item $checkpoint_path).Length
    if ($checkpoint_size -eq $checkpoint_expected_size) {
        Log-Message "Checkpoint already downloaded and size matches."
    } else {
        Log-Message "Checkpoint size mismatch or incomplete ($checkpoint_size vs $checkpoint_expected_size). Resuming..."
        curl.exe -L -C - -o $checkpoint_path $checkpoint_url 2>&1 | Out-File -FilePath $log_path -Append
    }
} else {
    Log-Message "Downloading Checkpoint..."
    curl.exe -L -o $checkpoint_path $checkpoint_url 2>&1 | Out-File -FilePath $log_path -Append
}

# Final Verification
$checkpoint_final_size = (Get-Item $checkpoint_path).Length
$vae_final_size = (Get-Item $vae_path).Length

Log-Message "Final Checkpoint size: $checkpoint_final_size bytes"
Log-Message "Final VAE size: $vae_final_size bytes"

if ($checkpoint_final_size -eq $checkpoint_expected_size -and $vae_final_size -eq $vae_expected_size) {
    Log-Message "All downloads successful and verified."
} else {
    Log-Message "Verification failed. Check log for details."
}
