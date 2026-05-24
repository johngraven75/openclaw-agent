# OpenClaw Build 1.0.5 Notes

Date: 2026-05-24

## Build Summary

Build 1.0.5 creates the Windows installer line for OpenClaw and carries forward the full Build 1.0.4 app surface. It adds the CinaVault Build 129 logo as the first-load splash screen, fixes the visible add-on installation flow, and packages a frozen `OpenClaw.exe` with Windows setup artifacts.

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
- Hugging Face model browsing, router-backed model list, in-app model selection, and selected-model testing.

## New In This Build

- Version bumped to Build 1.0.5.
- Added the CinaVault Build 129 logo mark as `/static/img/cinavault-build129-logo.png`.
- Added a first-load splash screen using the Build 129 logo.
- Fixed the add-on install button UX with visible Installing, Installed, Retry, and inline error states.
- Fixed add-on installation to use the exact OpenVSX catalog VSIX download URL when available.
- Added frozen-app asset handling for PyInstaller.
- Added automatic browser open when running the packaged Windows `OpenClaw.exe`.
- Built a Windows executable with PyInstaller.
- Added tracked Windows packaging scripts under `packaging/windows`.
- Added a local VS Code extension host adapter.
- Add-on installs now download the VSIX into OpenClaw and install it into the local VS Code host with `code --install-extension`.
- Added VS Code host status to the Add-ons panel.
- Added default Hugging Face token loading from local environment variables `HF_TOKEN` or `HUGGINGFACE_API_KEY`.
- Did not store the pasted `ghp_...` value as a Hugging Face token because it is a GitHub-style token and not a valid Hugging Face token format.

## Verification Completed

- Python syntax check passed with `python -m py_compile app.py`.
- Build 1.0.5 health endpoint returned version 1.0.5 on a source run.
- OpenVSX catalog install endpoint installed the Python extension using the searched catalog download URL.
- PyInstaller completed and produced `dist\OpenClaw.exe`.
- Frozen `OpenClaw.exe` health endpoint returned Build 1.0.5.
- Frozen `OpenClaw.exe` served the splash HTML with `/static/img/cinavault-build129-logo.png`.
- Frozen `OpenClaw.exe` served the Build 129 logo PNG with HTTP 200.
- Frozen `OpenClaw.exe` installed the Python OpenVSX extension through the updated add-on route.
- Source run detected VS Code host CLI at `C:\Users\johng\AppData\Local\Programs\Microsoft VS Code\bin\code.CMD`.
- Source run installed `ms-python.python-2026.4.0.vsix` into VS Code with return code 0.
- Final Windows setup EXE installed Build 1.0.5 to `%LOCALAPPDATA%\Programs\OpenClaw Agent`.
- Installed executable hash matched the freshly frozen `dist\OpenClaw.exe`.
- Installed app health endpoint returned Build 1.0.5 from `%LOCALAPPDATA%\Programs\OpenClaw Agent\workspace`.
- Installed app VS Code host endpoint detected VS Code 1.121.0.
- Installed app successfully installed `ms-python.python-2026.4.0.vsix` into VS Code with return code 0.
- Rebuilt setup creates `START OpenClaw Build 1.0.5.bat` and `OpenClaw Build 1.0.5.lnk` in both detected Desktop locations: `C:\Users\johng\Desktop` and `C:\Users\johng\OneDrive\Documents\Desktop`.
- Installed app after rebuilt setup returned Build 1.0.5 and detected VS Code host 1.121.0.
- In-app browser verification loaded `http://127.0.0.1:7865/`, confirmed page title `OpenClaw 1.0.5`, confirmed the splash logo element, and confirmed visible Hugging Face and VS Code host controls.
- Hugging Face model browsing was verified through the installed app POST route and returned live text-generation model results.

## Release Checks

- GitHub repository upload and release asset verification completed for tag `v1.0.5`.

## Artifacts

- Windows setup EXE: `OpenClaw-Build-1.0.5-Windows-Setup.exe`
  - SHA256: `3325E9B579EB03206DD994FE5315C7A5FCD5FA21D02511E7582B6A7662F38377`
- Portable Windows ZIP: `OpenClaw-Build-1.0.5-Portable-Windows.zip`
  - SHA256: `37F29EC83C5D9A96A889C83E4B7B227B6E260D23833B3CE24EA99A6C1A4C69B7`
- Frozen executable: `OpenClaw.exe`
  - SHA256: `A1CCAF086D2868E055304720495CB867C462A6F25EDF2C40BCD29DD9772E81A6`

## Known Truthful Limits

- Hugging Face model execution requires a valid Hugging Face token with Inference Providers permission.
- Some models are gated, not live, not routed, or require provider billing.
- Video generation is exposed as a provider-endpoint adapter because Hugging Face/provider video tasks vary by provider and response format.
- VS Code extensions are downloaded into OpenClaw's plugin store and installed into the local VS Code extension host when VS Code CLI is available.
