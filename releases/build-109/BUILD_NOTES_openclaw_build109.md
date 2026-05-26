# OpenClaw Build 1.0.9 Notes

Date: 2026-05-26

## Build Summary

Build 1.0.9 makes OpenClaw local-first on fresh installs. A shipped or saved Hugging Face selection no longer becomes the active chat provider unless the Hugging Face credential can actually be used. The selected Hugging Face model is preserved as dormant state, Settings now shows the credential state clearly, and the Chat screen has a Codex-like task deck for web search, code execution, image generation, add-on lookup, workspace files, and credential access.

## Corrective Changes

- Replaced the shipped Hugging Face default provider state with active `local` provider and `openclaw-local` model.
- Preserved the previous Hugging Face model as `dormant_huggingface_model` instead of deleting the user's selection.
- Added Hugging Face credential states: missing, invalid-format, verified, rejected, quota, and unverified.
- Chat resolves provider state before calling Hugging Face, so missing or invalid Hugging Face credentials never call the router.
- Hugging Face 401/402/403 router failures mark the token dormant for subsequent Settings and Chat state.
- Settings displays Hugging Face credential state, active/dormant status, and the dormant model.
- Chat now includes a task deck for common work without leaving the chat screen.
- Restyled the UI toward a quieter Codex-like workspace: dark rail, neutral surfaces, compact command deck, and local-first status language.

## Carried Forward

- OpenClaw Founders Edition splash screen, sidebar brand mark, Windows app icon, and installer icon.
- Hugging Face router model list, free/open public model catalog, model selection, and selected-model testing.
- Local reasoning fallback.
- Web search.
- Code execution tools.
- Image/video provider adapters.
- Workspace file management.
- VS Code/OpenVSX add-on catalog and VS Code extension host adapter.

## Verification Completed

- Added provider-state unit tests for a shipped Hugging Face config with no token, dormant Hugging Face model selection, Chat fallback with no token, and Hugging Face quota failure.
- `python -m unittest tests.test_provider_state` passed.
- `python -m py_compile app.py` passed.
- Source app returned Build 1.0.9 from `/api/health`.
- Source `/api/settings` returned active local provider with preserved dormant Hugging Face model when Hugging Face was unavailable.
- Source `/api/chat` stayed local when Hugging Face was requested without a usable credential.
- Chrome headless desktop screenshot verified the Codex-like Chat screen, task deck, and credential state UI.
- Chrome/CDP mobile check confirmed no horizontal document overflow at the mobile breakpoint.

## Packaging Verification

- Rebuilt frozen `OpenClaw.exe` with PyInstaller 6.16.0.
- Rebuilt Windows setup EXE as `OpenClaw-Build-1.0.9-Windows-Setup.exe`.
- Created portable ZIP as `OpenClaw-Build-1.0.9-Portable-Windows.zip`.
- Copied setup EXE, portable ZIP, and build notes to `releases/build-109`.
- Copied setup EXE, portable ZIP, and build notes to `C:\Users\johng\OneDrive\Documents\Desktop\John\openclaw builds\build-109`.
- Installed setup EXE with `--no-launch`; installer exit code was 0.
- Installed app returned Build 1.0.9 from `/api/health`.
- Installed clean/fresh-state smoke with no config and empty HF token env returned provider `local`, model `openclaw-local`, Hugging Face state `missing`, and local Chat fallback with no provider-failed warning.
- Installed dormant-state smoke with saved Hugging Face provider/model and no token returned provider `local`, model `openclaw-local`, dormant Hugging Face model `hmellor/tiny-random-LlamaForCausalLM`, and Hugging Face state `missing`.
