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
- Desktop launchers verified: `START OpenClaw Build 1.0.5.bat` and `OpenClaw Build 1.0.5.lnk`.

## Remaining Release Checks

- GitHub repository upload and release asset verification.

## Artifacts

- Windows setup EXE: `OpenClaw-Build-1.0.5-Windows-Setup.exe`
  - SHA256: `9FD59F6D1007D3057DE96CF897751E8873CC48976DEE8D3867969B2A5F76633F`
- Portable Windows ZIP: `OpenClaw-Build-1.0.5-Portable-Windows.zip`
  - SHA256: `C5030E2858B221855ED34777A01666A27A3C402A81C07C13706F729662556993`
- Frozen executable: `OpenClaw.exe`
  - SHA256: `A1CCAF086D2868E055304720495CB867C462A6F25EDF2C40BCD29DD9772E81A6`

## Known Truthful Limits

- Hugging Face model execution requires a valid Hugging Face token with Inference Providers permission.
- Some models are gated, not live, not routed, or require provider billing.
- Video generation is exposed as a provider-endpoint adapter because Hugging Face/provider video tasks vary by provider and response format.
- VS Code extensions are downloaded and stored, but executing their VS Code APIs requires an extension host adapter.
