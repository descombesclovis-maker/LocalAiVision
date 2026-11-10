"""Deploy the private LocalAiStudio diagnostic Space using the local HF login.

Never prints or writes the Hugging Face token. This script intentionally does
not install model weights or change LocalAiStudio's application UI.
"""
from __future__ import annotations

from pathlib import Path

from huggingface_hub import HfApi, get_token
from huggingface_hub.utils import RepositoryNotFoundError

SPACE_NAME = "LocalAiStudio-VideoEngine"
SPACE_HARDWARE = "zero-a10g"  # Hub ZeroGPU allocation; 48 GB default tier.
ROOT = Path(__file__).resolve().parents[1]
SPACE_DIR = ROOT / "spaces" / SPACE_NAME


def main() -> None:
    token = get_token()
    if not token:
        raise SystemExit("No Hugging Face login found. Run `hf auth login` and retry.")

    api = HfApi(token=token)
    owner = api.whoami(token=token)["name"]
    repo_id = f"{owner}/{SPACE_NAME}"

    try:
        api.repo_info(repo_id=repo_id, repo_type="space", token=token)
    except RepositoryNotFoundError:
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="gradio",
            space_hardware=SPACE_HARDWARE,
            private=True,
            token=token,
        )

    api.upload_folder(
        repo_id=repo_id,
        repo_type="space",
        folder_path=str(SPACE_DIR),
        ignore_patterns=["tests/**", "__pycache__/**", "*.pyc"],
        commit_message="Deploy LocalAiStudio remote GPU diagnostic Space",
        token=token,
    )
    runtime = api.get_space_runtime(repo_id=repo_id, token=token)
    print(f"Space: https://huggingface.co/spaces/{repo_id}")
    print(f"Runtime stage: {runtime.stage}")
    print(f"Requested hardware: {runtime.requested_hardware}")
    print("Generation readiness: not enabled; no model weights were downloaded.")


if __name__ == "__main__":
    main()
