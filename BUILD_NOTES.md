# OpenClaw Build 1.0.10 Notes

Date: 2026-08-12

## Build Summary

Build 1.0.10 hardens OpenClaw's local browser and add-on boundaries while preserving the local-first provider behavior introduced in 1.0.9. Browser mutations are same-origin, OpenVSX downloads and archive extraction are validated before installation, interface icons are bundled locally, and transient pending UI no longer enters model history.

## Corrective Changes

- Rejects cross-site browser mutations while preserving direct local API clients.
- Accepts add-on downloads only from approved OpenVSX HTTPS URLs.
- Validates add-on identifiers and rejects ZIP traversal, absolute paths, symlinks, archive bombs, and oversized downloads.
- Stages add-on updates transactionally so a failed download or validation does not replace the working installation.
- Replaces the executable Lucide CDN dependency with a small bundled icon renderer and a restrictive Content Security Policy.
- Keeps the visible `Thinking...` placeholder transient and sends only real prior turns to the agent.
- Adds complete unittest discovery across Windows, Linux, and macOS CI runners.

## Carried Forward from 1.0.9

- Replaced the shipped Hugging Face default provider state with active `local` provider and `openclaw-local` model.
- Preserved the previous Hugging Face model as `dormant_huggingface_model` instead of deleting the user's selection.
- Added Hugging Face credential states: missing, invalid-format, verified, rejected, quota, and unverified.
- Chat resolves provider state before calling Hugging Face, so missing or invalid Hugging Face credentials never call the router.
- Hugging Face 401/402/403 router failures mark the token dormant for subsequent Settings and Chat state.
- Settings displays Hugging Face credential state, active/dormant status, and the dormant model.
- Chat now includes a task deck for common work without leaving the chat screen.
- Restyled the UI toward a quieter Codex-like workspace: dark rail, neutral surfaces, compact command deck, and local-first status language.

## Additional Carried Forward Capabilities

- OpenClaw Founders Edition splash screen, sidebar brand mark, Windows app icon, and installer icon.
- Hugging Face router model list, free/open public model catalog, model selection, and selected-model testing.
- Local reasoning fallback.
- Web search.
- Code execution tools.
- Image/video provider adapters.
- Workspace file management.
- VS Code/OpenVSX add-on catalog and VS Code extension host adapter.

## Verification Completed

- Provider-state and security boundary tests: 13 passed through unittest discovery.
- `python -m compileall -q app.py tests` passed.
- `node --check static/js/app.js` and `node --check static/js/icons.js` passed.
- Live OpenVSX API verification confirmed current artifact URLs use the approved `https://open-vsx.org` origin.
- Source app returned Build 1.0.9 from `/api/health`.
- Source `/api/settings` returned active local provider with preserved dormant Hugging Face model when Hugging Face was unavailable.
- Source `/api/chat` stayed local when Hugging Face was requested without a usable credential.
- Chrome headless desktop screenshot verified the Codex-like Chat screen, task deck, and credential state UI.
- Chrome/CDP mobile check confirmed no horizontal document overflow at the mobile breakpoint.

## Packaging and Rollback

- The Windows release workflow builds a frozen executable, per-user Inno Setup installer, portable ZIP, and SHA-256 manifest only after the full test suite passes.
- CI smoke-tests both the frozen executable and a silent installer installation before publication.
- Rollback is an uninstall followed by installing the previous GitHub release. User configuration remains outside the replacement transaction and is not deleted by uninstall.
- Post-release diagnosis uses `/api/health`, the workflow test evidence, and published SHA-256 hashes.
