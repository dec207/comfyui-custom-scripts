#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8188
DEFAULT_STARTUP_TIMEOUT = 120
DEFAULT_POLL_INTERVAL = 2.0
DEFAULT_BATCH_SIZE = 1
DEFAULT_REPEAT = 1
DEFAULT_SEED_STEP = 1
OPTION_GROUPS = ("poses", "outfits")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Start ComfyUI if needed, queue one or more workflows, and save images "
            "to a chosen output directory."
        )
    )
    parser.add_argument(
        "--repo-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Path to the comfyui-custom-scripts repository. Defaults to this file's directory.",
    )
    parser.add_argument(
        "--comfyui-dir",
        type=Path,
        default=None,
        help="Path to the ComfyUI directory. Defaults to ../comfyui relative to --repo-dir.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for generated images. Defaults to ../img_bank relative to --repo-dir.",
    )
    parser.add_argument(
        "--workflow",
        action="append",
        default=[],
        help=(
            "Workflow file or character name to run. Repeat for multiple values. "
            "Defaults to all JSON files in workflows/."
        ),
    )
    parser.add_argument(
        "--character",
        default=None,
        help="Character name to run from workflows/base. If omitted with no --workflow, an interactive menu is shown.",
    )
    parser.add_argument(
        "--pose",
        default=None,
        help="Pose option name from options/poses.",
    )
    parser.add_argument(
        "--outfit",
        default=None,
        help="Outfit option name from options/outfits.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Batch size applied to node 5 when present. Default: {DEFAULT_BATCH_SIZE}.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=DEFAULT_REPEAT,
        help=f"Sequential runs per workflow with incremented seeds. Default: {DEFAULT_REPEAT}.",
    )
    parser.add_argument(
        "--seed-step",
        type=int,
        default=DEFAULT_SEED_STEP,
        help=f"Seed increment between repeated runs. Default: {DEFAULT_SEED_STEP}.",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"ComfyUI host. Default: {DEFAULT_HOST}.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"ComfyUI port. Default: {DEFAULT_PORT}.",
    )
    parser.add_argument(
        "--startup-timeout",
        type=int,
        default=DEFAULT_STARTUP_TIMEOUT,
        help=f"Seconds to wait for ComfyUI startup. Default: {DEFAULT_STARTUP_TIMEOUT}.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL,
        help=f"Seconds between job status checks. Default: {DEFAULT_POLL_INTERVAL}.",
    )
    parser.add_argument(
        "--python",
        default=None,
        help="Python executable to use for ComfyUI. Auto-detected by default.",
    )
    parser.add_argument(
        "--use-local-models",
        action="store_true",
        help="Add this repository's models/ directory to ComfyUI model search paths.",
    )
    parser.add_argument(
        "--keep-server",
        action="store_true",
        help="Do not stop a ComfyUI server started by this script.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved paths and workflows without starting ComfyUI.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_dir = args.repo_dir.resolve()
    comfyui_dir = resolve_comfyui_dir(args.comfyui_dir, repo_dir)
    output_dir = resolve_output_dir(args.output_dir, repo_dir)
    workflow_paths, selected_options = resolve_run_request(repo_dir, args)
    python_executable = resolve_python_executable(args.python, comfyui_dir)
    accelerator = detect_accelerator(python_executable)
    runtime_args = get_runtime_args(accelerator)

    ensure_path(comfyui_dir, "ComfyUI directory")
    ensure_path(comfyui_dir / "main.py", "ComfyUI main.py")
    ensure_path(repo_dir / "workflows", "workflows directory")

    print(f"Repository: {repo_dir}")
    print(f"ComfyUI: {comfyui_dir}")
    print(f"Output: {output_dir}")
    print(f"Python: {python_executable}")
    print(f"Accelerator: {accelerator}")
    if runtime_args:
        print("Runtime args:")
        for runtime_arg in runtime_args:
            print(f"  - {runtime_arg}")
    print("Workflows:")
    for workflow_path in workflow_paths:
        print(f"  - {workflow_path.name}")

    if args.dry_run:
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    warn_missing_models(comfyui_dir, repo_dir, workflow_paths, args.use_local_models)

    extra_model_config = None
    process = None
    started_here = False
    base_url = f"http://{args.host}:{args.port}"

    try:
        if is_server_ready(base_url):
            print(f"Using existing ComfyUI server at {base_url}")
        else:
            extra_model_config = (
                create_extra_model_paths_yaml(repo_dir) if args.use_local_models else None
            )
            process = start_comfyui(
                python_executable=python_executable,
                comfyui_dir=comfyui_dir,
                output_dir=output_dir,
                host=args.host,
                port=args.port,
                extra_model_config=extra_model_config,
                runtime_args=runtime_args,
            )
            started_here = True
            wait_for_server(base_url, args.startup_timeout, process)
            print(f"ComfyUI server is ready at {base_url}")

        for workflow_path in workflow_paths:
            prompt = load_workflow(workflow_path)
            for repeat_index in range(args.repeat):
                prepared_prompt = prepare_prompt(
                    prompt=prompt,
                    workflow_path=workflow_path,
                    batch_size=args.batch_size,
                    seed_offset=selected_options.seed_offset + (repeat_index * args.seed_step),
                    selected_options=selected_options,
                )
                run_label = workflow_path.name
                if args.repeat > 1:
                    run_label = f"{workflow_path.name} ({repeat_index + 1}/{args.repeat})"
                prompt_id = queue_prompt(base_url, prepared_prompt)
                print(f"Queued {run_label} as prompt {prompt_id}")
                wait_for_prompt(base_url, prompt_id, run_label, args.poll_interval)
                print(f"Completed {run_label}")
    finally:
        if extra_model_config and extra_model_config.exists():
            extra_model_config.unlink(missing_ok=True)
        if process and started_here and not args.keep_server:
            stop_process(process)

    return 0


def resolve_comfyui_dir(comfyui_dir: Path | None, repo_dir: Path) -> Path:
    if comfyui_dir is not None:
        return comfyui_dir.expanduser().resolve()

    candidates = [
        repo_dir.parent / "comfyui",
        repo_dir / "ComfyUI",
        repo_dir / "comfyui",
    ]
    for candidate in candidates:
        if (candidate / "main.py").exists():
            return candidate.resolve()
    raise FileNotFoundError(
        "Could not find ComfyUI. Pass --comfyui-dir with the path to your ComfyUI checkout."
    )


def resolve_output_dir(output_dir: Path | None, repo_dir: Path) -> Path:
    if output_dir is not None:
        return output_dir.expanduser().resolve()
    return (repo_dir.parent / "img_bank").resolve()


class SelectedOptions:
    def __init__(self, options: list[dict[str, Any]] | None = None) -> None:
        self.options = options or []

    @property
    def seed_offset(self) -> int:
        return sum(int(option.get("seed_offset", 0)) for option in self.options)

    @property
    def filename_suffixes(self) -> list[str]:
        suffixes = []
        for option in self.options:
            suffix = option.get("filename_suffix")
            if isinstance(suffix, str) and suffix:
                suffixes.append(suffix)
        return suffixes


def resolve_run_request(repo_dir: Path, args: argparse.Namespace) -> tuple[list[Path], SelectedOptions]:
    if args.workflow:
        return resolve_workflows(repo_dir, args.workflow), load_cli_options(repo_dir, args)

    if args.character:
        workflow_path = resolve_character_workflow(repo_dir, args.character)
        return [workflow_path], load_cli_options(repo_dir, args)

    workflow_path, selected_options = interactive_selection(repo_dir)
    return [workflow_path], selected_options


def load_cli_options(repo_dir: Path, args: argparse.Namespace) -> SelectedOptions:
    options = []
    if args.pose:
        options.append(load_option(repo_dir, "poses", args.pose))
    if args.outfit:
        options.append(load_option(repo_dir, "outfits", args.outfit))
    return SelectedOptions(options)


def interactive_selection(repo_dir: Path) -> tuple[Path, SelectedOptions]:
    characters = list_characters(repo_dir)
    character = prompt_choice("Character", characters)
    pose = prompt_choice("Pose", list_options(repo_dir, "poses"))
    outfit = prompt_choice("Outfit", list_options(repo_dir, "outfits"))
    workflow_path = resolve_character_workflow(repo_dir, character["name"])
    return workflow_path, SelectedOptions([pose, outfit])


def prompt_choice(label: str, choices: list[dict[str, Any]]) -> dict[str, Any]:
    if not choices:
        raise FileNotFoundError(f"No choices available for {label}.")

    print(f"\n{label}:")
    for index, choice in enumerate(choices, start=1):
        print(f"  {index}. {choice['label']}")

    while True:
        raw = input("Choose number: ").strip()
        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(choices):
                return choices[index - 1]
        print(f"Enter a number from 1 to {len(choices)}.")


def list_characters(repo_dir: Path) -> list[dict[str, Any]]:
    base_dir = repo_dir / "workflows" / "base"
    characters = []
    for path in sorted(base_dir.glob("workflow_*_base.json")):
        name = path.stem.removeprefix("workflow_").removesuffix("_base")
        characters.append({"name": name, "label": name, "path": str(path)})
    return characters


def list_options(repo_dir: Path, group: str) -> list[dict[str, Any]]:
    options_dir = repo_dir / "options" / group
    options = []
    for path in sorted(options_dir.glob("*.json")):
        option = load_json(path)
        option["name"] = path.stem
        option["label"] = option.get("label", path.stem)
        options.append(option)
    return options


def load_option(repo_dir: Path, group: str, name: str) -> dict[str, Any]:
    option_path = repo_dir / "options" / group / f"{name}.json"
    if not option_path.exists():
        available = ", ".join(option["name"] for option in list_options(repo_dir, group))
        raise FileNotFoundError(f"Unknown {group} option '{name}'. Available: {available}")
    option = load_json(option_path)
    option["name"] = option_path.stem
    option["label"] = option.get("label", option_path.stem)
    return option


def resolve_character_workflow(repo_dir: Path, character: str) -> Path:
    normalized = character.strip()
    candidates = [
        repo_dir / "workflows" / "base" / f"workflow_{normalized}_base.json",
        repo_dir / "workflows" / "base" / f"workflow_{normalized}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"Base workflow not found for character: {character}")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def resolve_workflows(repo_dir: Path, requested: list[str]) -> list[Path]:
    workflows_dir = repo_dir / "workflows"
    if not requested:
        workflow_paths = sorted(workflows_dir.glob("*.json"))
    else:
        workflow_paths = [resolve_workflow_arg(workflows_dir, value) for value in requested]

    if not workflow_paths:
        raise FileNotFoundError(f"No workflow JSON files found in {workflows_dir}")
    return workflow_paths


def resolve_workflow_arg(workflows_dir: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    if candidate.exists():
        return candidate.resolve()

    normalized = value
    if not normalized.endswith(".json"):
        normalized = f"{normalized}.json"

    direct = workflows_dir / normalized
    if direct.exists():
        return direct.resolve()

    prefixed = workflows_dir / f"workflow_{normalized}"
    if prefixed.exists():
        return prefixed.resolve()

    raise FileNotFoundError(f"Workflow not found: {value}")


def ensure_path(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")


def resolve_python_executable(explicit: str | None, comfyui_dir: Path) -> str:
    if explicit:
        return explicit

    candidates = [
        comfyui_dir / "venv" / "Scripts" / "python.exe",
        comfyui_dir / "venv" / "bin" / "python",
        comfyui_dir / ".venv" / "Scripts" / "python.exe",
        comfyui_dir / ".venv" / "bin" / "python",
        comfyui_dir / "python_embeded" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    for command in ("python", "python3", sys.executable):
        resolved = shutil.which(command) if command != sys.executable else command
        if resolved:
            return resolved

    raise FileNotFoundError("Could not find a Python executable for ComfyUI.")


def detect_accelerator(python_executable: str) -> str:
    probe_script = """
import json
import platform
import subprocess

result = {
    "torch_available": False,
    "cuda_available": False,
    "cuda_device_name": None,
    "nvidia_smi": False,
    "platform_system": platform.system(),
    "platform_machine": platform.machine(),
    "mps_supported": False,
    "mps_available": False,
}
try:
    import torch
    result["torch_available"] = True
    result["cuda_available"] = bool(torch.cuda.is_available())
    if result["cuda_available"]:
        result["cuda_device_name"] = torch.cuda.get_device_name(0)
    mps_backend = getattr(torch.backends, "mps", None)
    if mps_backend is not None:
        result["mps_supported"] = bool(mps_backend.is_built())
        result["mps_available"] = bool(mps_backend.is_available())
except Exception:
    pass

try:
    completed = subprocess.run(
        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    result["nvidia_smi"] = completed.returncode == 0 and bool(completed.stdout.strip())
except Exception:
    pass

print(json.dumps(result))
"""
    completed = subprocess.run(
        [python_executable, "-c", probe_script],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    result = json.loads(completed.stdout)

    if result["cuda_available"]:
        device_name = result["cuda_device_name"] or "CUDA GPU"
        return f"GPU ({device_name})"
    if result["mps_available"]:
        return "GPU (Apple Silicon MPS)"
    if result["nvidia_smi"]:
        raise RuntimeError(
            "An NVIDIA GPU is present, but the selected Python environment cannot use CUDA. "
            "Refusing to continue with a CPU fallback."
        )
    if (
        result["platform_system"] == "Darwin"
        and result["platform_machine"] == "arm64"
        and result["torch_available"]
    ):
        raise RuntimeError(
            "Apple Silicon was detected, but the selected Python environment cannot use MPS. "
            "Refusing to continue with a CPU fallback."
        )
    if result["torch_available"]:
        return "CPU"
    return "Unknown"


def get_runtime_args(accelerator: str) -> list[str]:
    if accelerator == "GPU (Apple Silicon MPS)":
        return [
            "--force-non-blocking",
            "--force-channels-last",
            "--use-pytorch-cross-attention",
        ]
    return []


def create_extra_model_paths_yaml(repo_dir: Path) -> Path:
    models_dir = repo_dir / "models"
    if not models_dir.exists():
        raise FileNotFoundError(f"Local models directory not found: {models_dir}")

    config_text = (
        "custom_scripts:\n"
        f"  base_path: {to_posix_path(models_dir)}\n"
        "  checkpoints: checkpoints\n"
        "  loras: loras\n"
    )
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".yaml",
        prefix="comfyui-extra-model-paths-",
        delete=False,
    )
    try:
        handle.write(config_text)
        handle.flush()
    finally:
        handle.close()
    return Path(handle.name)


def to_posix_path(path: Path) -> str:
    return path.resolve().as_posix()


def start_comfyui(
    python_executable: str,
    comfyui_dir: Path,
    output_dir: Path,
    host: str,
    port: int,
    extra_model_config: Path | None,
    runtime_args: list[str],
) -> subprocess.Popen[str]:
    command = [
        python_executable,
        "main.py",
        "--listen",
        host,
        "--port",
        str(port),
        "--output-directory",
        str(output_dir),
    ]
    if extra_model_config:
        command.extend(["--extra-model-paths-config", str(extra_model_config)])
    command.extend(runtime_args)

    print("Starting ComfyUI:")
    print("  " + format_command(command))

    popen_kwargs: dict[str, Any] = {
        "cwd": str(comfyui_dir),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "text": True,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    return subprocess.Popen(command, **popen_kwargs)


def format_command(command: list[str]) -> str:
    return " ".join(shlex_quote(part) for part in command)


def shlex_quote(value: str) -> str:
    if os.name == "nt":
        if " " in value or "\t" in value:
            return f'"{value}"'
        return value
    return subprocess.list2cmdline([value]) if " " in value else value


def is_server_ready(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url}/object_info", timeout=3) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def wait_for_server(base_url: str, timeout_seconds: int, process: subprocess.Popen[str]) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("ComfyUI exited before it became ready.")
        if is_server_ready(base_url):
            return
        time.sleep(1)
    raise TimeoutError(f"Timed out waiting for ComfyUI at {base_url}")


def load_workflow(workflow_path: Path) -> dict[str, Any]:
    with workflow_path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def prepare_prompt(
    prompt: dict[str, Any],
    workflow_path: Path,
    batch_size: int,
    seed_offset: int = 0,
    selected_options: SelectedOptions | None = None,
) -> dict[str, Any]:
    prepared = json.loads(json.dumps(prompt))
    selected_options = selected_options or SelectedOptions()

    apply_prompt_options(prepared, selected_options)

    for sampler_node in sampler_nodes(prepared):
        inputs = sampler_node.setdefault("inputs", {})
        if "seed" in inputs and isinstance(inputs["seed"], int):
            inputs["seed"] = inputs["seed"] + seed_offset

    latent_node = prepared.get("5")
    if isinstance(latent_node, dict):
        inputs = latent_node.setdefault("inputs", {})
        if "batch_size" in inputs and batch_size > 0:
            inputs["batch_size"] = batch_size

    image_node = prepared.get("9")
    if isinstance(image_node, dict):
        inputs = image_node.setdefault("inputs", {})
        inputs["filename_prefix"] = workflow_name_to_prefix(
            workflow_path,
            selected_options.filename_suffixes,
        )

    return prepared


def apply_prompt_options(prompt: dict[str, Any], selected_options: SelectedOptions) -> None:
    positive_parts = []
    negative_parts = []
    for option in selected_options.options:
        positive = option.get("positive_addon")
        negative = option.get("negative_addon")
        if isinstance(positive, str) and positive:
            positive_parts.append(positive)
        if isinstance(negative, str) and negative:
            negative_parts.append(negative)

    if not positive_parts and not negative_parts:
        return

    positive_node_id, negative_node_id = find_conditioning_node_ids(prompt)
    append_text(prompt, positive_node_id, positive_parts)
    append_text(prompt, negative_node_id, negative_parts)


def find_conditioning_node_ids(prompt: dict[str, Any]) -> tuple[str | None, str | None]:
    for sampler_node in sampler_nodes(prompt):
        inputs = sampler_node.get("inputs", {})
        positive = inputs.get("positive")
        negative = inputs.get("negative")
        positive_id = positive[0] if isinstance(positive, list) and positive else None
        negative_id = negative[0] if isinstance(negative, list) and negative else None
        return positive_id, negative_id
    return None, None


def append_text(prompt: dict[str, Any], node_id: str | None, additions: list[str]) -> None:
    if not node_id or not additions:
        return
    node = prompt.get(node_id)
    if not isinstance(node, dict):
        return
    inputs = node.setdefault("inputs", {})
    existing = inputs.get("text", "")
    if not isinstance(existing, str):
        return
    inputs["text"] = ", ".join([existing, *additions])


def sampler_nodes(prompt: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = []
    for node in prompt.values():
        if not isinstance(node, dict):
            continue
        class_type = node.get("class_type")
        if isinstance(class_type, str) and "Sampler" in class_type:
            nodes.append(node)
    return nodes


def workflow_name_to_prefix(workflow_path: Path, suffixes: list[str] | None = None) -> str:
    name = workflow_path.stem
    if name.startswith("workflow_"):
        name = name[len("workflow_") :]
    if suffixes:
        name = "_".join([name, *suffixes])
    return f"{name}_v3"


def queue_prompt(base_url: str, prompt: dict[str, Any]) -> str:
    payload = json.dumps({"prompt": prompt}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    prompt_id = data.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"Unexpected response from ComfyUI /prompt: {data}")
    return str(prompt_id)


def wait_for_prompt(base_url: str, prompt_id: str, label: str, poll_interval: float) -> None:
    while True:
        history = get_history(base_url, prompt_id)
        if prompt_id in history:
            status = history[prompt_id].get("status", {})
            completed = status.get("completed")
            if completed is False:
                raise RuntimeError(f"ComfyUI reported an incomplete run for {label}: {status}")
            return
        print(f"Waiting for {label}...")
        time.sleep(poll_interval)


def get_history(base_url: str, prompt_id: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(f"{base_url}/history/{prompt_id}", timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Failed to fetch history for prompt {prompt_id}: {exc}") from exc


def warn_missing_models(
    comfyui_dir: Path,
    repo_dir: Path,
    workflow_paths: list[Path],
    use_local_models: bool,
) -> None:
    checkpoints = set(find_model_names(comfyui_dir / "models" / "checkpoints"))
    loras = set(find_model_names(comfyui_dir / "models" / "loras"))

    if use_local_models:
        checkpoints.update(find_model_names(repo_dir / "models" / "checkpoints"))
        loras.update(find_model_names(repo_dir / "models" / "loras"))

    required_checkpoints: set[str] = set()
    required_loras: set[str] = set()
    for workflow_path in workflow_paths:
        workflow = load_workflow(workflow_path)
        checkpoint_name = nested_get(workflow, "4", "inputs", "ckpt_name")
        lora_name = nested_get(workflow, "10", "inputs", "lora_name")
        if checkpoint_name:
            required_checkpoints.add(checkpoint_name)
        if lora_name:
            required_loras.add(lora_name)

    missing_checkpoints = sorted(required_checkpoints - checkpoints)
    missing_loras = sorted(required_loras - loras)

    if missing_checkpoints:
        print("Warning: missing checkpoints:", ", ".join(missing_checkpoints))
    if missing_loras:
        print("Warning: missing loras:", ", ".join(missing_loras))


def find_model_names(directory: Path) -> list[str]:
    if not directory.exists():
        return []
    return [path.name for path in directory.iterdir() if path.is_file()]


def nested_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def stop_process(process: subprocess.Popen[str]) -> None:
    print("Stopping ComfyUI server...")
    if os.name == "nt":
        process.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
    else:
        process.terminate()

    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
