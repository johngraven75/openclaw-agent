# OpenClaw Build 1.0.4 Notes

Date: 2026-05-24

## Build Summary

Build 1.0.4 rebuilds OpenClaw as a complete local Flask application with a Copilot 365-inspired forward-facing UI, first-class Hugging Face model browsing and selection, and an OpenVSX-backed VS Code add-on catalog.

## Carried Forward

- Conversational agent UI.
- Local reasoning fallback.
- Provider configuration.
- Web search.
- Code execution tools.
- Image generation adapter.
- Workspace file management.
- VS Code/OpenVSX add-on catalog and installation store.
- Build notes and numbered packaging requirement.

## New In This Build

- Copilot 365 color scheme and responsive application shell.
- Hugging Face tab for model search, provider filtering, task filtering, and one-click model selection.
- Hugging Face router model listing via `https://router.huggingface.co/v1/models`.
- Hugging Face chat through the current OpenAI-compatible Inference Providers endpoint.
- Hugging Face provider policy selection: fastest, cheapest, preferred.
- Selected-model test panel.
- Improved settings flow for Hugging Face tokens and provider/model persistence.
- OpenVSX add-on install stores VSIX package, extracted package metadata, and manifest.

## Verification Completed

- Python syntax check passed with `python -m py_compile app.py`.
- Dependency install passed with `python -m pip install -r requirements.txt`.
- Health endpoint returned Build 1.0.4, version 1.0.4, and plugin count.
- Settings endpoint returned provider/model/workspace configuration.
- Local chat endpoint returned a reasoning-mode response.
- Python code runner executed a script and returned `runner ok`.
- Hugging Face Hub search returned selectable text-generation models.
- Hugging Face router model listing returned live provider-backed chat models.
- Hugging Face model detail lookup returned metadata for `openai/gpt-oss-120b`.
- Hugging Face selection endpoint persisted provider `huggingface` and model `openai/gpt-oss-120b`.
- File listing endpoint returned workspace contents.
- OpenVSX search returned VS Code-compatible add-on catalog results.
- Browser smoke test rendered the desktop UI with no console errors.
- Mobile browser smoke test rendered the Hugging Face model browser with no console errors, 128 router model cards, and 20 add-on results.
- Desktop install completed to `C:\Users\johng\Desktop\OpenClaw-Agent`.
- Desktop launcher created at `C:\Users\johng\Desktop\START OpenClaw Build 1.0.4.bat`.
- Installed app health endpoint returned Build 1.0.4 from the Desktop install.
- Launcher hardened to reuse existing dependency installs and open the running app instead of colliding with an active server.

## Remaining Release Checks

- GitHub repository upload and release asset verification.

## Known Truthful Limits

- Hugging Face model execution requires a valid Hugging Face token with Inference Providers permission.
- Some models are gated, not live, not routed, or require provider billing.
- Video generation is exposed as a provider-endpoint adapter because Hugging Face/provider video tasks vary by provider and response format.
- VS Code extensions are downloaded and stored, but executing their VS Code APIs requires an extension host adapter.
