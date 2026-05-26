# OpenClaw Build 1.0.6 Notes

Date: 2026-05-26

## Build Summary

Build 1.0.6 fixes provider model loading and selection, improves Ollama diagnostics, permanently supports Windows user `HF_TOKEN` loading, and adds a live free/open Hugging Face model catalog. It carries forward the Build 1.0.5 Windows installer line, CinaVault Build 129 splash logo, Copilot-style UI skin, VS Code/OpenVSX add-ons, and VS Code extension host adapter.

## Carried Forward

- Conversational agent UI.
- Local reasoning fallback.
- Provider configuration.
- Web search.
- Code execution tools.
- Image generation adapter.
- Workspace file management.
- VS Code/OpenVSX add-on catalog and installation store.
- VS Code extension host adapter.
- CinaVault Build 129 logo splash screen.
- Hugging Face model browsing, router-backed model list, in-app model selection, and selected-model testing.

## New In This Build

- Version bumped to Build 1.0.6.
- Added `/api/models` provider model discovery for local, Hugging Face, OpenAI quick models, Ollama, and custom endpoints.
- Added `/api/models/select` so model selection persists to the same provider/model fields used by Chat.
- Added a top-bar model selector with a reload button and clear model-loading status.
- Added `/api/huggingface/free-models` for live public non-gated Hugging Face model discovery.
- Added the `Free/open models` button to the Hugging Face browser.
- Free/open model catalog filters out private and gated models and prefers recognized open license tags when license tags are present.
- Ollama now checks `/api/tags` before chat, reports when Ollama is running with no installed models, and falls back from `/api/chat` to `/api/generate` when needed.
- Installed the user's valid Hugging Face token locally in the Windows user environment as `HF_TOKEN` and in the installed app config. The token is not stored in Git, build notes, installer source, or release notes.

## Verification Completed

- Python syntax check passed with `python -m py_compile app.py`.
- Source app on port 7866 returned Build 1.0.6.
- Source `/api/models?provider=local` returned the local reasoning model.
- Source `/api/models?provider=ollama` returned the truthful empty-model diagnostic: Ollama is reachable, but no models are installed.
- Source `/api/huggingface/free-models` returned public non-gated text-generation model results.
- Source `/api/models/select` persisted Hugging Face provider/model selection.
- PyInstaller rebuilt frozen `OpenClaw.exe`.
- Windows setup EXE and portable ZIP were rebuilt as Build 1.0.6.
- Installed setup EXE returned exit code 0.
- Installed app returned Build 1.0.6 from `/api/health`.
- Installed `/api/models?provider=huggingface` returned 54 router models using the installed Hugging Face token.
- Installed `/api/huggingface/free-models` returned public free/open model results.
- Installed `/api/models/select` persisted the selected Hugging Face model.
- Installed `/api/chat` successfully called a Hugging Face router model and returned `OpenClaw HF ready` with no warning.
- Installed `/api/models?provider=ollama` returned the clear no-installed-models message instead of exposing a raw provider 404.
- Rebuilt setup creates `START OpenClaw Build 1.0.6.bat` and `OpenClaw Build 1.0.6.lnk` in both detected Desktop locations: `C:\Users\johng\Desktop` and `C:\Users\johng\OneDrive\Documents\Desktop`.
- In-app browser verification loaded `http://127.0.0.1:7865/`, confirmed page title `OpenClaw 1.0.6`, confirmed the splash logo, confirmed the top-bar model selector, and confirmed the `Free/open models` control.

## Release Checks

- Build artifacts were copied to `C:\Users\johng\OneDrive\Documents\Desktop\John\openclaw builds\build-106`.
- Release artifacts were staged under `releases/build-106`.
- GitHub repository upload and release asset verification are required for tag `v1.0.6`.

## Known Truthful Limits

- "All known free models" cannot be a permanent static list because model availability, licenses, provider support, and pricing change continuously.
- Build 1.0.6 implements live public/free/open model discovery instead of hardcoding a stale list.
- Public Hugging Face model access does not guarantee free hosted inference for every model or provider.
- Some public models are too large for local execution unless downloaded into a suitable runtime such as Ollama, llama.cpp, Transformers, or a provider endpoint.
