# OpenClaw Build 1.0.7 Notes

Date: 2026-05-26

## Build Summary

Build 1.0.7 updates OpenClaw branding to use the supplied OpenClaw Founders Edition logo for the splash screen, sidebar brand mark, Windows executable icon, and installer icon. It also improves Hugging Face chat routing so a selected public/free Hub model that is not accepted by the Hugging Face chat router retries through safer chat-router candidates instead of dropping straight into vague local fallback mode.

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
- Hugging Face model browsing, router-backed model list, in-app model selection, selected-model testing, and free/open public model catalog.
- Windows user `HF_TOKEN` loading and local installed-app Hugging Face config support.

## New In This Build

- Version bumped to Build 1.0.7.
- Added `static/img/openclaw-founders-logo.png` from `C:\Users\johng\OneDrive\Documents\Desktop\Copilot_20260526_083415.png`.
- Rebuilt `static/img/openclaw.ico` from the supplied OpenClaw logo for the Windows executable and installer.
- Replaced the first splash screen image with the supplied OpenClaw Founders Edition logo.
- Replaced the sidebar `OC` text mark with the supplied OpenClaw logo.
- Adjusted splash sizing and styling for the wide logo artwork.
- Improved Hugging Face chat error recovery when a selected model is not accepted by the router.
- Hugging Face chat now retries the selected model with policy, base model, cheapest policy, and a known routed fallback before surfacing an error.
- Provider errors now include more actionable Hugging Face router context.

## Verification Completed

- Python syntax check passed with `python -m py_compile app.py`.
- Source app returned Build 1.0.7 from `/api/health`.
- Source app served `/static/img/openclaw-founders-logo.png` with HTTP 200.
- Source Hugging Face chat recovered from a public non-router model and returned a real Hugging Face response through `deepseek-ai/DeepSeek-V4-Pro:cheapest` with no local fallback warning.
- Rebuilt frozen `OpenClaw.exe` with the new icon and splash asset.
- Rebuilt Windows setup EXE and portable ZIP as Build 1.0.7.
- Installed setup EXE returned exit code 0.
- Installed app returned Build 1.0.7 from `/api/health`.
- Installed app served the new OpenClaw Founders Edition logo with HTTP 200.
- Installed free/open Hugging Face model catalog returned public model results.
- Installed Hugging Face chat recovered from a non-router public model and returned a routed Hugging Face response with no local fallback warning.
- Rebuilt setup creates `START OpenClaw Build 1.0.7.bat` and `OpenClaw Build 1.0.7.lnk` in both detected Desktop locations: `C:\Users\johng\Desktop` and `C:\Users\johng\OneDrive\Documents\Desktop`.
- In-app browser verification loaded `http://127.0.0.1:7865/?build=107`, confirmed page title `OpenClaw 1.0.7`, confirmed the new splash logo, confirmed the new sidebar brand logo, and confirmed the old CinaVault splash logo is no longer present in the visible UI.

## Known Truthful Limits

- Public/free Hugging Face Hub models are not all chat-router models.
- Some public/free models require a different runtime, provider, or local download path even when they are visible in the catalog.
- Build 1.0.7 improves recovery and messaging, but it cannot make every public model available through a chat-completions API.
