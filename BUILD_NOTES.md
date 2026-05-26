# OpenClaw Build 1.0.8 Notes

Date: 2026-05-26

## Build Summary

Build 1.0.8 fixes all open GitHub Dependabot alerts reported for `requirements.txt` by upgrading vulnerable runtime dependencies and rebuilding the Windows packaged app with the patched libraries.

## Carried Forward

- OpenClaw Founders Edition splash screen, sidebar brand mark, Windows app icon, and installer icon.
- Hugging Face token support through local config and Windows user `HF_TOKEN`.
- Hugging Face router model list, free/open public model catalog, model selection, and chat-router recovery.
- Local reasoning fallback.
- Web search.
- Code execution tools.
- Image/video provider adapters.
- Workspace file management.
- VS Code/OpenVSX add-on catalog and VS Code extension host adapter.

## Security Fixes

- Upgraded `requests` from `2.32.3` to `2.34.2`.
- Upgraded `flask` from `3.0.3` to `3.1.3`.
- Upgraded `flask-cors` from `4.0.1` to `6.0.2`.
- Addresses the seven GitHub Dependabot alerts for `requests`, `flask`, and `flask-cors` in `requirements.txt`.

## Verification Completed

- Installed patched Python dependencies with `python -m pip install -r requirements.txt`.
- Python syntax check passed with `python -m py_compile app.py`.
- Source app returned Build 1.0.8 from `/api/health`.
- Source dependency-version check confirmed Flask 3.1.3, Flask-CORS 6.0.2, and Requests 2.34.2.
- Source app served the OpenClaw Founders Edition logo with HTTP 200.
- Source Hugging Face chat recovery returned a routed Hugging Face response with no local fallback warning.
- Rebuilt frozen `OpenClaw.exe` using patched dependencies.
- Rebuilt Windows setup EXE and portable ZIP as Build 1.0.8.
- Installed setup EXE returned exit code 0.
- Installed app returned Build 1.0.8 from `/api/health`.
- Installed app served the OpenClaw Founders Edition logo with HTTP 200.
- Installed Hugging Face chat recovery returned a routed Hugging Face response with no local fallback warning.
- Rebuilt setup creates `START OpenClaw Build 1.0.8.bat` and `OpenClaw Build 1.0.8.lnk` in both detected Desktop locations: `C:\Users\johng\Desktop` and `C:\Users\johng\OneDrive\Documents\Desktop`.
- Dependabot alert closure is verified after the GitHub push because alerts are evaluated from the default branch.
