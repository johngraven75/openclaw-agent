from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import time
import uuid
import zipfile
from urllib.parse import quote
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS


APP_NAME = "OpenClaw"
VERSION = "1.0.4"
BUILD_LABEL = "Build 1.0.4"
ROOT = Path(__file__).resolve().parent
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
    "stability_api_key": "",
    "custom_endpoint": "",
    "custom_api_key": "",
    "ollama_endpoint": "http://localhost:11434",
    "reasoning_style": "plan-act-check",
    "workspace": str(WORKSPACE),
}


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return {**DEFAULT_CONFIG, **data}
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any]) -> None:
    clean = {**DEFAULT_CONFIG, **config}
    CONFIG_PATH.write_text(json.dumps(clean, indent=2), encoding="utf-8")


def public_config(config: dict[str, Any]) -> dict[str, Any]:
    masked = dict(config)
    for key in list(masked):
        if key.endswith("_api_key") and masked[key]:
            masked[key] = "set"
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
    response = requests.post(
        endpoint.rstrip("/") + "/api/chat",
        json={"model": model or "llama3.1", "messages": messages, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    text = data.get("message", {}).get("content", "")
    return ProviderResult(text=text or json.dumps(data)[:4000], provider="ollama", model=model, raw=data)


def call_huggingface_text(config: dict[str, Any], model: str, prompt: str) -> ProviderResult:
    token = config.get("huggingface_api_key", "")
    if not token:
        raise ValueError("Hugging Face API key is not configured.")
    model_id = model or "openai/gpt-oss-120b"
    policy = config.get("huggingface_provider_policy", "fastest")
    if ":" not in model_id and policy in {"fastest", "cheapest", "preferred"}:
        model_id = f"{model_id}:{policy}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
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
    response.raise_for_status()
    data = response.json()
    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not text:
        text = json.dumps(data)[:4000]
    return ProviderResult(text=text, provider="huggingface", model=model_id, raw=data)


def run_agent(config: dict[str, Any], prompt: str, messages: list[dict[str, str]]) -> ProviderResult:
    provider = (request.json or {}).get("provider") or config.get("provider", "local")
    model = (request.json or {}).get("model") or config.get("model", "openclaw-local")
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


def extract_package_json(vsix_path: Path, destination: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    with zipfile.ZipFile(vsix_path, "r") as archive:
        archive.extractall(destination)
        for name in archive.namelist():
            if name.endswith("extension/package.json"):
                metadata = json.loads((destination / name).read_text(encoding="utf-8"))
                break
    return metadata


app = Flask(__name__)
CORS(app)


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


@app.post("/api/plugins/vscode/install")
def vscode_install():
    data = request.get_json(force=True, silent=True) or {}
    namespace = str(data.get("namespace", "")).strip()
    extension = str(data.get("extension", "")).strip()
    if not namespace or not extension:
        return safe_json_error("Namespace and extension are required.")
    try:
        meta = openvsx_extension(namespace, extension)
        version = meta.get("version") or meta.get("latestVersion") or "unknown"
        files = meta.get("files") or {}
        download_url = files.get("download") or files.get("downloadUrl") or meta.get("downloadUrl")
        if not download_url:
            return safe_json_error("No downloadable VSIX URL was found for this extension.", 404, metadata=meta)
        install_dir = VSCODE_PLUGIN_ROOT / f"{namespace}.{extension}@{version}"
        if install_dir.exists():
            shutil.rmtree(install_dir)
        install_dir.mkdir(parents=True)
        vsix_path = install_dir / f"{namespace}.{extension}-{version}.vsix"
        with requests.get(download_url, stream=True, timeout=120) as response:
            response.raise_for_status()
            with vsix_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        handle.write(chunk)
        package = extract_package_json(vsix_path, install_dir / "extracted")
        manifest = {
            "namespace": namespace,
            "extension": extension,
            "version": version,
            "download_url": download_url,
            "vsix": str(vsix_path),
            "installed_at": time.time(),
            "package": package,
            "runtime_note": "Installed into OpenClaw plugin store. VS Code API execution requires a compatible adapter or VS Code host.",
        }
        (install_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
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
    app.run(host="127.0.0.1", port=int(os.environ.get("OPENCLAW_PORT", "7865")), debug=False)
