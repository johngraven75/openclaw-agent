from __future__ import annotations

import base64
import json
import os
import re
import stat
import shutil
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
import zipfile
from urllib.parse import quote, urlsplit
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request, send_from_directory


APP_NAME = "OpenClaw"
VERSION = "1.0.10"
BUILD_LABEL = "Build 1.0.10"
if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent
    ASSET_ROOT = Path(getattr(sys, "_MEIPASS", ROOT))
else:
    ROOT = Path(__file__).resolve().parent
    ASSET_ROOT = ROOT
CONFIG_PATH = ROOT / "openclaw_config.json"
WORKSPACE = ROOT / "workspace"
GENERATED = ROOT / "generated"
PLUGIN_ROOT = ROOT / "plugins"
VSCODE_PLUGIN_ROOT = PLUGIN_ROOT / "vscode"

for folder in (WORKSPACE, GENERATED, PLUGIN_ROOT, VSCODE_PLUGIN_ROOT):
    folder.mkdir(parents=True, exist_ok=True)


DEFAULT_CONFIG: dict[str, Any] = {
    "provider": "local",
    "model": "openclaw-local",
    "openai_api_key": "",
    "anthropic_api_key": "",
    "gemini_api_key": "",
    "huggingface_api_key": "",
    "huggingface_provider_policy": "fastest",
    "dormant_huggingface_model": "",
    "stability_api_key": "",
    "custom_endpoint": "",
    "custom_api_key": "",
    "ollama_endpoint": "http://localhost:11434",
    "reasoning_style": "plan-act-check",
    "vscode_host_enabled": True,
    "workspace": str(WORKSPACE),
}

HF_TOKEN_CACHE: dict[str, dict[str, Any]] = {}
HF_TOKEN_CACHE_SECONDS = 300
MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
OPENVSX_ALLOWED_HOSTS = frozenset({"open-vsx.org"})
MAX_VSIX_FILES = 20_000
MAX_VSIX_DOWNLOAD_BYTES = 256 * 1024 * 1024
MAX_VSIX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024


def env_huggingface_token() -> str:
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY") or ""


def huggingface_credential_status(token: str) -> dict[str, Any]:
    token = (token or "").strip()
    if not token:
        return {
            "state": "missing",
            "active": False,
            "message": "No Hugging Face token is configured. Hugging Face models stay dormant and Chat uses local reasoning.",
        }
    if not token.startswith("hf_"):
        return {
            "state": "invalid-format",
            "active": False,
            "message": "The configured Hugging Face token does not look like an hf_ token.",
        }

    cached = HF_TOKEN_CACHE.get(token)
    now = time.time()
    if cached and now - float(cached.get("checked_at", 0)) < HF_TOKEN_CACHE_SECONDS:
        return dict(cached["status"])

    status: dict[str, Any]
    try:
        response = requests.get(
            "https://huggingface.co/api/whoami-v2",
            headers={"Authorization": f"Bearer {token}", "User-Agent": "OpenClaw/1.0"},
            timeout=8,
        )
        if response.ok:
            status = {
                "state": "verified",
                "active": True,
                "message": "Hugging Face token verified. Hugging Face chat can be activated.",
            }
        elif response.status_code in {401, 403}:
            status = {
                "state": "rejected",
                "active": False,
                "message": "Hugging Face rejected the configured token. Hugging Face models stay dormant.",
            }
        else:
            status = {
                "state": "unverified",
                "active": False,
                "message": f"Hugging Face token could not be verified right now ({response.status_code}). Chat will stay local until verification succeeds.",
            }
    except Exception as exc:
        status = {
            "state": "unverified",
            "active": False,
            "message": f"Hugging Face token verification failed: {exc}. Chat will stay local until verification succeeds.",
        }

    HF_TOKEN_CACHE[token] = {"checked_at": now, "status": status}
    return dict(status)


def resolve_provider_state(config: dict[str, Any], provider: str | None = None, model: str | None = None) -> dict[str, Any]:
    resolved = {**DEFAULT_CONFIG, **config}
    if not resolved.get("huggingface_api_key"):
        resolved["huggingface_api_key"] = env_huggingface_token()

    requested_provider = (provider or resolved.get("provider") or "local").strip().lower()
    requested_model = (model or resolved.get("model") or "").strip()
    hf_status = huggingface_credential_status(resolved.get("huggingface_api_key", ""))
    dormant_model = (resolved.get("dormant_huggingface_model") or "").strip()

    if requested_provider == "huggingface":
        dormant_model = requested_model or dormant_model
        if not hf_status["active"]:
            resolved["provider"] = "local"
            resolved["model"] = "openclaw-local"
        else:
            resolved["provider"] = "huggingface"
            resolved["model"] = requested_model or dormant_model or "deepseek-ai/DeepSeek-V4-Pro"
    else:
        resolved["provider"] = requested_provider or "local"
        resolved["model"] = requested_model or resolved.get("model") or "openclaw-local"

    resolved["dormant_huggingface_model"] = dormant_model
    resolved["huggingface_credential_state"] = hf_status["state"]
    resolved["huggingface_credential_message"] = hf_status["message"]
    resolved["huggingface_active"] = bool(hf_status["active"] and resolved.get("provider") == "huggingface")
    return resolved

OPEN_LICENSE_TAGS = {
    "license:apache-2.0",
    "license:mit",
    "license:bsd-3-clause",
    "license:bsd-2-clause",
    "license:cc-by-4.0",
    "license:cc-by-sa-4.0",
    "license:cc0-1.0",
    "license:openrail",
    "license:bigscience-openrail-m",
    "license:creativeml-openrail-m",
}


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            config = {**DEFAULT_CONFIG, **data}
            if not config.get("huggingface_api_key"):
                config["huggingface_api_key"] = env_huggingface_token()
            return resolve_provider_state(config)
        except Exception:
            config = DEFAULT_CONFIG.copy()
            config["huggingface_api_key"] = env_huggingface_token()
            return resolve_provider_state(config)
    config = DEFAULT_CONFIG.copy()
    config["huggingface_api_key"] = env_huggingface_token()
    return resolve_provider_state(config)


def save_config(config: dict[str, Any]) -> None:
    clean = resolve_provider_state({**DEFAULT_CONFIG, **config})
    CONFIG_PATH.write_text(json.dumps(clean, indent=2), encoding="utf-8")


def public_config(config: dict[str, Any]) -> dict[str, Any]:
    masked = resolve_provider_state(config)
    for key in list(masked):
        if key.endswith("_api_key") and masked[key]:
            masked[key] = "set"
    if config.get("huggingface_api_key") and not CONFIG_PATH.exists():
        masked["huggingface_api_key_source"] = "environment"
    return masked


def safe_json_error(message: str, status: int = 400, **extra: Any):
    payload = {"ok": False, "error": message, **extra}
    return jsonify(payload), status


@dataclass
class ProviderResult:
    text: str
    provider: str
    model: str
    raw: Any = None


class HuggingFaceCredentialError(ValueError):
    pass


def mark_huggingface_token_inactive(token: str, state: str, message: str) -> None:
    token = (token or "").strip()
    if not token:
        return
    HF_TOKEN_CACHE[token] = {
        "checked_at": time.time(),
        "status": {"state": state, "active": False, "message": message},
    }


def local_reasoning_reply(prompt: str, messages: list[dict[str, str]] | None = None) -> ProviderResult:
    history = messages or []
    recent = " ".join(m.get("content", "") for m in history[-4:])
    combined = (recent + " " + prompt).strip()
    needs_code = any(word in combined.lower() for word in ["code", "script", "bug", "function", "app", "program"])
    needs_web = any(word in combined.lower() for word in ["search", "internet", "latest", "web", "download"])
    needs_media = any(word in combined.lower() for word in ["image", "photo", "video", "voice", "audio"])
    steps = [
        "I can break the request into a plan, gather context, run tools, and verify the result.",
        "For model-grade answers, add an API key in Settings for OpenAI, Hugging Face, Ollama, or another OpenAI-compatible endpoint.",
    ]
    if needs_code:
        steps.append("For code work, use the Code tab or ask me to write/run a script in the workspace.")
    if needs_web:
        steps.append("For internet-backed answers, use the Web Search tool so sources are fetched live.")
    if needs_media:
        steps.append("For image/video generation, configure the matching provider key or endpoint in Settings.")
    text = "OpenClaw local reasoning mode:\n\n" + "\n".join(f"{i + 1}. {step}" for i, step in enumerate(steps))
    return ProviderResult(text=text, provider="local", model="openclaw-local")


def call_openai_compatible(endpoint: str, api_key: str, model: str, messages: list[dict[str, str]]) -> ProviderResult:
    url = endpoint.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {"model": model, "messages": messages, "temperature": 0.4}
    response = requests.post(url, headers=headers, json=payload, timeout=90)
    response.raise_for_status()
    data = response.json()
    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return ProviderResult(text=text or json.dumps(data)[:4000], provider="openai-compatible", model=model, raw=data)


def call_ollama(config: dict[str, Any], model: str, messages: list[dict[str, str]]) -> ProviderResult:
    endpoint = config.get("ollama_endpoint") or "http://localhost:11434"
    selected_model = model or config.get("model") or ""
    available = list_ollama_models(endpoint)
    if available["ok"] and not available["models"]:
        raise ValueError("Ollama is running, but no local models are installed. Run `ollama pull llama3.1` or install a model from Ollama before selecting Ollama.")
    if not selected_model or selected_model == "openclaw-local":
        if available["models"]:
            selected_model = available["models"][0]["id"]
        else:
            selected_model = "llama3.1"
    payload = {"model": selected_model, "messages": messages, "stream": False}
    response = requests.post(endpoint.rstrip("/") + "/api/chat", json=payload, timeout=120)
    if response.status_code == 404:
        prompt = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)
        fallback = requests.post(
            endpoint.rstrip("/") + "/api/generate",
            json={"model": selected_model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        if fallback.status_code == 404:
            raise ValueError(f"Ollama model `{selected_model}` was not found or this Ollama server does not expose chat/generate for it. Install it with `ollama pull {selected_model}`.")
        fallback.raise_for_status()
        data = fallback.json()
        text = data.get("response", "")
        return ProviderResult(text=text or json.dumps(data)[:4000], provider="ollama", model=selected_model, raw=data)
    response.raise_for_status()
    data = response.json()
    text = data.get("message", {}).get("content", "")
    return ProviderResult(text=text or json.dumps(data)[:4000], provider="ollama", model=selected_model, raw=data)


def list_ollama_models(endpoint: str) -> dict[str, Any]:
    try:
        response = requests.get(endpoint.rstrip("/") + "/api/tags", timeout=8)
        response.raise_for_status()
        raw_models = response.json().get("models", [])
        models = []
        for item in raw_models:
            name = item.get("name") or item.get("model") or ""
            if name:
                models.append({
                    "id": name,
                    "name": name,
                    "provider": "ollama",
                    "size": item.get("size"),
                    "modified_at": item.get("modified_at"),
                })
        return {"ok": True, "models": models}
    except Exception as exc:
        return {"ok": False, "models": [], "error": str(exc)}


def is_public_free_model(model: dict[str, Any]) -> bool:
    if model.get("private") or model.get("gated"):
        return False
    tags = set(str(tag).lower() for tag in model.get("tags", []))
    if not tags:
        return True
    license_tags = {tag for tag in tags if tag.startswith("license:")}
    return not license_tags or bool(license_tags & OPEN_LICENSE_TAGS)


def public_model_card(model: dict[str, Any], source: str = "huggingface") -> dict[str, Any]:
    tags = [str(tag) for tag in model.get("tags", [])]
    license_tag = next((tag for tag in tags if tag.lower().startswith("license:")), "")
    model_id = model.get("id") or model.get("modelId") or ""
    return {
        "id": model_id,
        "name": model_id,
        "source": source,
        "provider": "huggingface",
        "pipeline_tag": model.get("pipeline_tag", ""),
        "downloads": model.get("downloads", 0),
        "likes": model.get("likes", 0),
        "license": license_tag.replace("license:", ""),
        "tags": tags,
        "gated": bool(model.get("gated")),
        "private": bool(model.get("private")),
        "free_note": "Public non-gated model. License/cost can still vary by inference provider.",
    }


def call_huggingface_text(config: dict[str, Any], model: str, prompt: str) -> ProviderResult:
    token = config.get("huggingface_api_key", "")
    if not token:
        raise ValueError("Hugging Face API key is not configured.")
    selected_model = model or "deepseek-ai/DeepSeek-V4-Pro"
    policy = config.get("huggingface_provider_policy", "fastest")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base_model = selected_model.split(":", 1)[0]
    candidates: list[str] = []
    if ":" in selected_model:
        candidates.append(selected_model)
    elif policy in {"fastest", "cheapest", "preferred"}:
        candidates.append(f"{selected_model}:{policy}")
    candidates.extend([base_model, f"{base_model}:cheapest", "deepseek-ai/DeepSeek-V4-Pro:cheapest"])

    last_error = ""
    for model_id in dict.fromkeys(candidates):
        response = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers=headers,
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "stream": False,
            },
            timeout=120,
        )
        if response.ok:
            data = response.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not text:
                text = json.dumps(data)[:4000]
            if model_id != candidates[0]:
                text = f"{text}\n\nNote: the selected Hugging Face model `{selected_model}` was not accepted by the chat router, so OpenClaw used `{model_id}` for this reply."
            return ProviderResult(text=text, provider="huggingface", model=model_id, raw=data)
        try:
            detail = response.json()
        except Exception:
            detail = response.text[:700]
        last_error = f"{response.status_code} {response.reason}: {detail}"
        if response.status_code in {401, 402, 403}:
            state = "quota" if response.status_code == 402 else "rejected"
            message = (
                "Hugging Face accepted the token but inference credits or provider access are not available."
                if response.status_code == 402
                else "Hugging Face rejected the configured token for this provider request."
            )
            mark_huggingface_token_inactive(token, state, message)
            raise HuggingFaceCredentialError(f"{message} Last router error: {last_error}")

    raise ValueError(
        "Hugging Face chat router rejected the selected model. "
        "Use Live chat models for chat, or use Free/open models for browsing public models that may need a different runtime. "
        f"Last router error: {last_error}"
    )


def run_agent(config: dict[str, Any], prompt: str, messages: list[dict[str, str]]) -> ProviderResult:
    incoming = request.json or {}
    runtime = resolve_provider_state(
        config,
        provider=str(incoming.get("provider") or config.get("provider", "local")),
        model=str(incoming.get("model") or config.get("model", "openclaw-local")),
    )
    provider = runtime.get("provider", "local")
    model = runtime.get("model", "openclaw-local")
    system = {
        "role": "system",
        "content": (
            "You are OpenClaw, a truthful, careful, multimodal coding and problem-solving agent. "
            "Reason step by step internally, give concise useful answers, use tools when needed, "
            "and clearly state when an external API key or runtime is required."
        ),
    }
    clean_messages = [system] + [{"role": m.get("role", "user"), "content": str(m.get("content", ""))} for m in messages]
    if not clean_messages or clean_messages[-1]["content"] != prompt:
        clean_messages.append({"role": "user", "content": prompt})
    if provider == "openai":
        return call_openai_compatible("https://api.openai.com/v1", config.get("openai_api_key", ""), model, clean_messages)
    if provider == "custom":
        endpoint = config.get("custom_endpoint", "")
        if not endpoint:
            raise ValueError("Custom endpoint is not configured.")
        return call_openai_compatible(endpoint, config.get("custom_api_key", ""), model, clean_messages)
    if provider == "ollama":
        return call_ollama(config, model, clean_messages)
    if provider == "huggingface":
        return call_huggingface_text(config, model, prompt)
    return local_reasoning_reply(prompt, messages)


def workspace_path(name: str) -> Path:
    base = Path(load_config().get("workspace") or WORKSPACE).resolve()
    base.mkdir(parents=True, exist_ok=True)
    target = (base / name).resolve()
    if base not in target.parents and target != base:
        raise ValueError("Path escapes the configured workspace.")
    return target


def search_duckduckgo(query: str, limit: int = 8) -> list[dict[str, str]]:
    response = requests.get(
        "https://duckduckgo.com/html/",
        params={"q": query},
        headers={"User-Agent": "OpenClaw/1.0"},
        timeout=25,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for item in soup.select(".result")[:limit]:
        link = item.select_one(".result__a")
        snippet = item.select_one(".result__snippet")
        if link:
            results.append({
                "title": link.get_text(" ", strip=True),
                "url": link.get("href", ""),
                "snippet": snippet.get_text(" ", strip=True) if snippet else "",
            })
    return results


def openvsx_search(query: str, size: int = 20) -> dict[str, Any]:
    response = requests.get(
        "https://open-vsx.org/api/-/search",
        params={"query": query, "size": size},
        headers={"User-Agent": "OpenClaw/1.0"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def openvsx_extension(namespace: str, extension: str) -> dict[str, Any]:
    response = requests.get(
        f"https://open-vsx.org/api/{namespace}/{extension}",
        headers={"User-Agent": "OpenClaw/1.0"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def validated_openvsx_download_url(download_url: str) -> str:
    """Accept only OpenVSX-owned HTTPS artifact URLs.

    The catalog button submits a URL back to the local service. Treat it as
    untrusted input so a malicious page cannot turn the desktop app into an
    SSRF client or make it install an arbitrary archive.
    """
    parsed = urlsplit(download_url)
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if (
        parsed.scheme.lower() != "https"
        or hostname not in OPENVSX_ALLOWED_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
        or not parsed.path.startswith("/")
    ):
        raise ValueError("VSIX downloads must use an approved OpenVSX HTTPS URL.")
    return download_url


def validated_plugin_component(value: str, label: str) -> str:
    normalized = (value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", normalized):
        raise ValueError(f"{label} contains unsupported characters.")
    return normalized


def remove_tree_force(path: Path) -> None:
    if not path.exists():
        return
    def onexc(function, target, excinfo):
        try:
            os.chmod(target, 0o700)
            function(target)
        except Exception:
            raise excinfo
    shutil.rmtree(path, onexc=onexc)


def find_vscode_cli() -> str | None:
    candidates = [
        shutil.which("code"),
        shutil.which("code.cmd"),
        shutil.which("code-insiders"),
        shutil.which("code-insiders.cmd"),
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code" / "bin" / "code.cmd"),
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code Insiders" / "bin" / "code-insiders.cmd"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def vscode_host_status() -> dict[str, Any]:
    cli = find_vscode_cli()
    if not cli:
        return {"available": False, "cli": None, "version": None}
    try:
        proc = subprocess.run(["cmd", "/c", cli, "--version"], capture_output=True, text=True, timeout=30)
        version = (proc.stdout or proc.stderr).strip().splitlines()
    except Exception as exc:
        version = [f"Version check failed: {exc}"]
    return {"available": True, "cli": cli, "version": version}


def install_vsix_into_vscode(vsix_path: Path) -> dict[str, Any]:
    cli = find_vscode_cli()
    if not cli:
        return {"attempted": False, "installed": False, "reason": "VS Code CLI was not found."}
    proc = subprocess.run(
        [cli, "--install-extension", str(vsix_path), "--force"],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    return {
        "attempted": True,
        "installed": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
        "cli": cli,
    }


def install_vscode_extension(
    namespace: str,
    extension: str,
    version: str | None = None,
    download_url: str | None = None,
    display_name: str | None = None,
) -> dict[str, Any]:
    namespace = validated_plugin_component(namespace, "Extension namespace")
    extension = validated_plugin_component(extension, "Extension name")
    meta: dict[str, Any] = {}
    if not download_url:
        meta = openvsx_extension(namespace, extension)
        version = version or meta.get("version") or meta.get("latestVersion") or "unknown"
        files = meta.get("files") or {}
        download_url = files.get("download") or files.get("downloadUrl") or meta.get("downloadUrl")
    version = validated_plugin_component(version or "unknown", "Extension version")
    if not download_url:
        raise ValueError("No downloadable VSIX URL was found for this extension.")
    download_url = validated_openvsx_download_url(download_url)
    install_dir = VSCODE_PLUGIN_ROOT / f"{namespace}.{extension}@{version}"
    staging_dir = VSCODE_PLUGIN_ROOT / f".{namespace}.{extension}@{version}.{uuid.uuid4().hex}.staging"
    staging_dir.mkdir(parents=True)
    filename = f"{namespace}.{extension}-{version}.vsix"
    staging_vsix = staging_dir / filename
    try:
        downloaded_bytes = 0
        with requests.get(download_url, stream=True, timeout=120) as response:
            response.raise_for_status()
            content_length = int(response.headers.get("content-length") or 0)
            if content_length > MAX_VSIX_DOWNLOAD_BYTES:
                raise ValueError("VSIX download exceeds the allowed size.")
            with staging_vsix.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    downloaded_bytes += len(chunk)
                    if downloaded_bytes > MAX_VSIX_DOWNLOAD_BYTES:
                        raise ValueError("VSIX download exceeds the allowed size.")
                    handle.write(chunk)
        package = extract_package_json(staging_vsix, staging_dir / "extracted")
        manifest = {
            "namespace": namespace,
            "extension": extension,
            "display_name": display_name or package.get("displayName") or f"{namespace}.{extension}",
            "version": version,
            "download_url": download_url,
            "vsix": str(install_dir / filename),
            "installed_at": time.time(),
            "package": package,
            "runtime_note": "Installed into OpenClaw plugin store. VS Code API execution requires a compatible adapter or VS Code host.",
        }
        if load_config().get("vscode_host_enabled", True):
            manifest["vscode_host"] = install_vsix_into_vscode(staging_vsix)
            if manifest["vscode_host"].get("installed"):
                manifest["runtime_note"] = "Installed into OpenClaw plugin store and installed into the local VS Code extension host."
        (staging_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        if install_dir.exists():
            remove_tree_force(install_dir)
        staging_dir.replace(install_dir)
        return manifest
    except Exception:
        remove_tree_force(staging_dir)
        raise


def extract_package_json(vsix_path: Path, destination: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    with zipfile.ZipFile(vsix_path, "r") as archive:
        members = archive.infolist()
        if len(members) > MAX_VSIX_FILES:
            raise ValueError("VSIX contains too many files.")
        if sum(member.file_size for member in members) > MAX_VSIX_UNCOMPRESSED_BYTES:
            raise ValueError("VSIX expands beyond the allowed size.")

        validated: list[tuple[zipfile.ZipInfo, Path]] = []
        destination_root = destination.resolve()
        for member in members:
            archive_name = member.filename.replace("\\", "/")
            parts = [part for part in archive_name.split("/") if part not in {"", "."}]
            unix_mode = member.external_attr >> 16
            if (
                not parts
                or archive_name.startswith("/")
                or any(part == ".." for part in parts)
                or ":" in parts[0]
                or stat.S_ISLNK(unix_mode)
            ):
                raise ValueError(f"VSIX contains an unsafe archive path: {member.filename}")
            target = destination_root.joinpath(*parts)
            if destination_root not in target.parents and target != destination_root:
                raise ValueError(f"VSIX path escapes the installation directory: {member.filename}")
            validated.append((member, target))

        destination_root.mkdir(parents=True, exist_ok=True)
        for member, target in validated:
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member, "r") as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)

        for member, target in validated:
            if member.filename.replace("\\", "/").endswith("extension/package.json"):
                metadata = json.loads(target.read_text(encoding="utf-8"))
                break
    return metadata


app = Flask(
    __name__,
    template_folder=str(ASSET_ROOT / "templates"),
    static_folder=str(ASSET_ROOT / "static"),
)


@app.before_request
def enforce_same_origin_mutations():
    """Reject browser cross-site writes while preserving local CLI clients."""
    if request.method not in MUTATING_METHODS:
        return None
    fetch_site = (request.headers.get("Sec-Fetch-Site") or "").strip().lower()
    if fetch_site == "cross-site":
        return safe_json_error("Cross-site mutations are not allowed.", 403)
    origin = (request.headers.get("Origin") or "").strip()
    if not origin:
        return None
    parsed_origin = urlsplit(origin)
    expected = urlsplit(request.host_url)
    if (
        parsed_origin.scheme.lower() != expected.scheme.lower()
        or parsed_origin.netloc.lower() != expected.netloc.lower()
        or parsed_origin.path not in {"", "/"}
        or parsed_origin.query
        or parsed_origin.fragment
    ):
        return safe_json_error("Mutation origin does not match this OpenClaw instance.", 403)
    return None


@app.after_request
def add_browser_security_headers(response):
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/")
def home():
    return render_template("index.html", version=VERSION, build_label=BUILD_LABEL)


@app.get("/generated/<path:filename>")
def generated_file(filename: str):
    return send_from_directory(GENERATED, filename)


@app.get("/api/health")
def health():
    config = load_config()
    return jsonify({
        "ok": True,
        "app": APP_NAME,
        "version": VERSION,
        "build": BUILD_LABEL,
        "workspace": config.get("workspace"),
        "plugin_count": len(list(VSCODE_PLUGIN_ROOT.glob("*/manifest.json"))),
    })


@app.get("/api/settings")
def get_settings():
    return jsonify({"ok": True, "settings": public_config(load_config())})


@app.post("/api/settings")
def update_settings():
    incoming = request.get_json(force=True, silent=True) or {}
    config = load_config()
    for key, value in incoming.items():
        if key in DEFAULT_CONFIG and value != "set":
            config[key] = value
    save_config(config)
    return jsonify({"ok": True, "settings": public_config(config)})


@app.get("/api/models")
def provider_models():
    config = load_config()
    provider = str(request.args.get("provider") or config.get("provider") or "local").strip().lower()
    try:
        if provider == "ollama":
            endpoint = str(request.args.get("endpoint") or config.get("ollama_endpoint") or "http://localhost:11434")
            result = list_ollama_models(endpoint)
            message = result.get("error") if not result.get("ok") else ""
            if result.get("ok") and not result.get("models"):
                message = "Ollama is reachable, but no models are installed. Run `ollama pull llama3.1`, then reload models."
            return jsonify({"ok": True, "provider": "ollama", "models": result.get("models", []), "message": message})
        if provider == "huggingface":
            headers = {"User-Agent": "OpenClaw/1.0"}
            token = config.get("huggingface_api_key", "")
            if token:
                headers["Authorization"] = f"Bearer {token}"
            response = requests.get("https://router.huggingface.co/v1/models", headers=headers, timeout=45)
            response.raise_for_status()
            models = []
            for item in response.json().get("data", []):
                model_id = item.get("id") or item.get("model") or ""
                if model_id:
                    models.append({
                        "id": model_id,
                        "name": model_id,
                        "provider": "huggingface",
                        "modalities": item.get("architecture", {}).get("input_modalities", []),
                    })
            return jsonify({"ok": True, "provider": "huggingface", "models": models[:200], "message": ""})
        if provider == "openai":
            return jsonify({"ok": True, "provider": "openai", "models": [
                {"id": "gpt-4.1", "name": "gpt-4.1", "provider": "openai"},
                {"id": "gpt-4.1-mini", "name": "gpt-4.1-mini", "provider": "openai"},
                {"id": "gpt-4o", "name": "gpt-4o", "provider": "openai"},
                {"id": "gpt-4o-mini", "name": "gpt-4o-mini", "provider": "openai"},
            ], "message": "OpenAI model list is the built-in quick list. You can still type any compatible model id."})
        if provider == "custom":
            return jsonify({"ok": True, "provider": "custom", "models": [], "message": "Custom OpenAI-compatible endpoints vary. Type the model id supplied by that endpoint."})
        return jsonify({"ok": True, "provider": "local", "models": [{"id": "openclaw-local", "name": "openclaw-local", "provider": "local"}], "message": "Local reasoning mode is selected."})
    except Exception as exc:
        return safe_json_error(f"Model loading failed for {provider}: {exc}", 502)


@app.post("/api/models/select")
def select_provider_model():
    data = request.get_json(force=True, silent=True) or {}
    provider = str(data.get("provider") or "").strip()
    model = str(data.get("model") or "").strip()
    if not provider:
        return safe_json_error("Provider is required.")
    if not model:
        return safe_json_error("Model id is required.")
    config = load_config()
    config["provider"] = provider
    config["model"] = model
    save_config(config)
    return jsonify({"ok": True, "settings": public_config(config)})


@app.post("/api/chat")
def chat():
    data = request.get_json(force=True, silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()
    messages = data.get("messages") or []
    if not prompt:
        return safe_json_error("Prompt is required.")
    try:
        result = run_agent(load_config(), prompt, messages)
        return jsonify({"ok": True, "reply": result.text, "provider": result.provider, "model": result.model})
    except HuggingFaceCredentialError as exc:
        fallback = local_reasoning_reply(prompt, messages)
        return jsonify({
            "ok": True,
            "reply": fallback.text + f"\n\nHugging Face is dormant: {exc}",
            "provider": fallback.provider,
            "model": fallback.model,
            "warning": str(exc),
        })
    except Exception as exc:
        fallback = local_reasoning_reply(prompt, messages)
        return jsonify({
            "ok": True,
            "reply": fallback.text + f"\n\nProvider call failed truthfully: {exc}",
            "provider": fallback.provider,
            "model": fallback.model,
            "warning": str(exc),
        })


@app.post("/api/search")
def web_search():
    data = request.get_json(force=True, silent=True) or {}
    query = str(data.get("query", "")).strip()
    if not query:
        return safe_json_error("Search query is required.")
    try:
        return jsonify({"ok": True, "results": search_duckduckgo(query, int(data.get("limit", 8)))})
    except Exception as exc:
        return safe_json_error(f"Search failed: {exc}", 502)


@app.post("/api/code/run")
def run_code():
    data = request.get_json(force=True, silent=True) or {}
    language = str(data.get("language", "python")).lower()
    code = str(data.get("code", ""))
    timeout = min(int(data.get("timeout", 20)), 60)
    if not code.strip():
        return safe_json_error("Code is required.")
    run_id = uuid.uuid4().hex[:10]
    commands = {
        "python": ("python", f"openclaw_{run_id}.py"),
        "javascript": ("node", f"openclaw_{run_id}.js"),
        "powershell": ("powershell", f"openclaw_{run_id}.ps1"),
    }
    if language not in commands:
        return safe_json_error("Language must be python, javascript, or powershell.")
    executable, filename = commands[language]
    script_path = workspace_path(filename)
    script_path.write_text(code, encoding="utf-8")
    try:
        proc = subprocess.run(
            [executable, str(script_path)],
            cwd=str(script_path.parent),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return jsonify({
            "ok": True,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-12000:],
            "file": str(script_path),
        })
    except subprocess.TimeoutExpired as exc:
        return jsonify({"ok": False, "error": "Execution timed out.", "stdout": exc.stdout, "stderr": exc.stderr}), 408
    except FileNotFoundError:
        return safe_json_error(f"{executable} is not installed or not on PATH.", 500)


@app.get("/api/files")
def list_files():
    base = Path(load_config().get("workspace") or WORKSPACE).resolve()
    base.mkdir(parents=True, exist_ok=True)
    files = []
    for path in base.rglob("*"):
        if path.is_file():
            files.append({"path": str(path.relative_to(base)), "size": path.stat().st_size, "modified": path.stat().st_mtime})
    return jsonify({"ok": True, "workspace": str(base), "files": sorted(files, key=lambda x: x["path"])})


@app.post("/api/files/write")
def write_file():
    data = request.get_json(force=True, silent=True) or {}
    name = str(data.get("path", "")).strip()
    content = str(data.get("content", ""))
    if not name:
        return safe_json_error("Path is required.")
    try:
        path = workspace_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return jsonify({"ok": True, "path": str(path), "size": path.stat().st_size})
    except Exception as exc:
        return safe_json_error(str(exc), 400)


@app.post("/api/image")
def image_generate():
    data = request.get_json(force=True, silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()
    provider = str(data.get("provider", "huggingface"))
    if not prompt:
        return safe_json_error("Image prompt is required.")
    config = load_config()
    try:
        if provider == "huggingface":
            token = config.get("huggingface_api_key", "")
            if not token:
                return safe_json_error("Hugging Face API key is required for image generation.", 400)
            model = data.get("model") or "stabilityai/stable-diffusion-xl-base-1.0"
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{model}",
                headers={"Authorization": f"Bearer {token}"},
                json={"inputs": prompt},
                timeout=180,
            )
            response.raise_for_status()
            filename = f"image_{int(time.time())}.png"
            (GENERATED / filename).write_bytes(response.content)
            return jsonify({"ok": True, "url": f"/generated/{filename}", "file": str(GENERATED / filename)})
        return safe_json_error("Configured provider is not implemented for direct image generation in this build.", 400)
    except Exception as exc:
        return safe_json_error(f"Image generation failed: {exc}", 502)


@app.post("/api/video")
def video_generate():
    data = request.get_json(force=True, silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()
    endpoint = str(data.get("endpoint") or load_config().get("custom_endpoint") or "")
    if not prompt:
        return safe_json_error("Video prompt is required.")
    if not endpoint:
        return safe_json_error("Video generation needs a configured provider endpoint. This build exposes the workflow and saves returned media.", 400)
    try:
        response = requests.post(endpoint, json={"prompt": prompt}, timeout=300)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return jsonify({"ok": True, "result": response.json()})
        filename = f"video_{int(time.time())}.mp4"
        (GENERATED / filename).write_bytes(response.content)
        return jsonify({"ok": True, "url": f"/generated/{filename}", "file": str(GENERATED / filename)})
    except Exception as exc:
        return safe_json_error(f"Video generation failed: {exc}", 502)


@app.post("/api/huggingface/search")
def huggingface_search():
    data = request.get_json(force=True, silent=True) or {}
    query = str(data.get("query", "")).strip()
    pipeline = str(data.get("pipeline", "")).strip()
    provider = str(data.get("inference_provider", data.get("provider", ""))).strip()
    sort = str(data.get("sort", "downloads")).strip()
    params = {"search": query, "limit": int(data.get("limit", 30)), "full": "true", "sort": sort}
    if pipeline:
        params["pipeline_tag"] = pipeline
    if provider:
        params["inference_provider"] = provider
    response = requests.get("https://huggingface.co/api/models", params=params, timeout=30)
    response.raise_for_status()
    return jsonify({"ok": True, "models": response.json()})


@app.post("/api/huggingface/free-models")
def huggingface_free_models():
    data = request.get_json(force=True, silent=True) or {}
    query = str(data.get("query", "")).strip()
    pipeline = str(data.get("pipeline", "")).strip()
    sort = str(data.get("sort", "downloads")).strip()
    limit = max(1, min(int(data.get("limit", 50)), 100))
    params = {"search": query, "limit": limit, "full": "true", "sort": sort}
    if pipeline:
        params["pipeline_tag"] = pipeline
    try:
        response = requests.get("https://huggingface.co/api/models", params=params, timeout=30)
        response.raise_for_status()
        public_models = [public_model_card(model) for model in response.json() if is_public_free_model(model)]
        return jsonify({
            "ok": True,
            "models": public_models,
            "message": "Showing public, non-gated Hugging Face models with open or unspecified license tags. Inference provider billing and gated access can still vary by model/provider.",
        })
    except Exception as exc:
        return safe_json_error(f"Free/open model catalog failed: {exc}", 502)


@app.get("/api/huggingface/router-models")
def huggingface_router_models():
    headers = {"User-Agent": "OpenClaw/1.0"}
    token = load_config().get("huggingface_api_key", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get("https://router.huggingface.co/v1/models", headers=headers, timeout=45)
    response.raise_for_status()
    return jsonify({"ok": True, "models": response.json().get("data", [])})


@app.get("/api/huggingface/model/<path:model_id>")
def huggingface_model(model_id: str):
    try:
        encoded = quote(model_id, safe="/")
        response = requests.get(
            f"https://huggingface.co/api/models/{encoded}",
            params={"expand": "inference,inferenceProviderMapping"},
            timeout=30,
        )
        if response.status_code >= 400:
            response = requests.get(f"https://huggingface.co/api/models/{encoded}", timeout=30)
        response.raise_for_status()
        return jsonify({"ok": True, "model": response.json()})
    except Exception as exc:
        return safe_json_error(f"Hugging Face model detail lookup failed: {exc}", 502)


@app.post("/api/huggingface/select")
def huggingface_select():
    data = request.get_json(force=True, silent=True) or {}
    model_id = str(data.get("model", "")).strip()
    provider_policy = str(data.get("provider_policy", data.get("policy", "fastest"))).strip()
    if not model_id:
        return safe_json_error("Hugging Face model id is required.")
    config = load_config()
    config["provider"] = "huggingface"
    config["model"] = model_id
    if provider_policy:
        config["huggingface_provider_policy"] = provider_policy
    save_config(config)
    return jsonify({"ok": True, "settings": public_config(config)})


@app.post("/api/huggingface/test")
def huggingface_test():
    data = request.get_json(force=True, silent=True) or {}
    prompt = str(data.get("prompt", "Say hello from the selected Hugging Face model in one sentence.")).strip()
    model = str(data.get("model") or load_config().get("model") or "openai/gpt-oss-120b").strip()
    try:
        result = call_huggingface_text(load_config(), model, prompt)
        return jsonify({"ok": True, "reply": result.text, "model": result.model})
    except Exception as exc:
        return safe_json_error(f"Hugging Face test failed: {exc}", 502)


@app.post("/api/plugins/vscode/search")
def vscode_search():
    data = request.get_json(force=True, silent=True) or {}
    query = str(data.get("query", "")).strip()
    if not query:
        return safe_json_error("Plugin search query is required.")
    try:
        return jsonify({"ok": True, "catalog": openvsx_search(query, int(data.get("size", 20)))})
    except Exception as exc:
        return safe_json_error(f"OpenVSX search failed: {exc}", 502)


@app.get("/api/plugins/vscode/host/status")
def vscode_host_status_route():
    return jsonify({"ok": True, "host": vscode_host_status()})


@app.post("/api/plugins/vscode/install")
def vscode_install():
    data = request.get_json(force=True, silent=True) or {}
    namespace = str(data.get("namespace", "")).strip()
    extension = str(data.get("extension", "")).strip()
    version = str(data.get("version", "")).strip() or None
    download_url = str(data.get("download_url", "")).strip() or None
    display_name = str(data.get("display_name", "")).strip() or None
    if not namespace or not extension:
        return safe_json_error("Namespace and extension are required.")
    try:
        manifest = install_vscode_extension(namespace, extension, version, download_url, display_name)
        return jsonify({"ok": True, "installed": manifest})
    except Exception as exc:
        return safe_json_error(f"Install failed: {exc}", 502)


@app.get("/api/plugins/vscode/installed")
def vscode_installed():
    installed = []
    for manifest in VSCODE_PLUGIN_ROOT.glob("*/manifest.json"):
        try:
            installed.append(json.loads(manifest.read_text(encoding="utf-8")))
        except Exception:
            pass
    return jsonify({"ok": True, "installed": installed})


if __name__ == "__main__":
    port = int(os.environ.get("OPENCLAW_PORT", "7865"))
    if getattr(sys, "frozen", False) and os.environ.get("OPENCLAW_NO_BROWSER") != "1":
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host="127.0.0.1", port=port, debug=False)
