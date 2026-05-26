# OpenClaw Agent

OpenClaw is a local desktop-friendly multimodal agent workspace with a Flask backend and responsive Copilot 365-inspired web UI.

## Build

Current version: **Build 1.0.8**

## Features

- Conversational agent shell with local reasoning fallback.
- Hugging Face model browser, router model list, model selection, provider policy selection, and in-app model testing.
- Provider model loader in the chat header for Hugging Face, Ollama, OpenAI quick models, local mode, and custom endpoints.
- Hugging Face LLM chat through the current OpenAI-compatible Inference Providers router.
- Hugging Face image generation adapter for text-to-image models when a token is configured.
- Provider settings for Hugging Face, OpenAI, Ollama, and OpenAI-compatible custom endpoints.
- Web search via DuckDuckGo HTML search.
- Code runner for Python, JavaScript, and PowerShell inside the configured workspace.
- VS Code-compatible add-on catalog using OpenVSX search and VSIX download into an OpenClaw plugin store.
- OpenClaw Founders Edition logo splash screen and Windows program icon.
- Workspace file browser and generated media browser.
- Browser voice input where the browser supports SpeechRecognition.

## Run

Double-click `START_OPENCLAW.bat`, or run:

```powershell
cd openclaw-agent
.\START_OPENCLAW.bat
```

Then open:

```text
http://127.0.0.1:7865
```

## Hugging Face Setup

1. Create a Hugging Face token with permission to call Inference Providers.
2. Open Settings.
3. Paste the token into `Hugging Face token`.
4. Open the Hugging Face tab.
5. Click `Live chat models` or search by task.
6. Press `Use` on a model.
7. Test it in the selected model panel or use Chat.

OpenClaw reports provider errors truthfully. Some Hugging Face models are gated, unavailable for serverless inference, or require billing/provider access. A token can be saved in Settings or installed as the Windows user environment variable `HF_TOKEN`.

## Add-on Store

OpenClaw downloads VS Code-compatible extensions from OpenVSX into `plugins/vscode` and installs them into the local VS Code extension host when the VS Code CLI is available.
