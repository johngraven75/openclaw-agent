from __future__ import annotations

import os
import shutil
import subprocess
import sys
import base64
from pathlib import Path


APP_NAME = "OpenClaw Agent"
BUILD_LABEL = "Build 1.0.8"


def asset_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def create_shortcut(target: Path, shortcut: Path) -> None:
    def ps_quote(value: Path) -> str:
        return str(value).replace("'", "''")

    ps = (
        "$ErrorActionPreference='Stop';"
        "$shell=New-Object -ComObject WScript.Shell;"
        f"$link=$shell.CreateShortcut('{ps_quote(shortcut)}');"
        f"$link.TargetPath='{ps_quote(target)}';"
        f"$link.WorkingDirectory='{ps_quote(target.parent)}';"
        f"$link.IconLocation='{ps_quote(target)}';"
        "$link.Save();"
    )
    encoded = base64.b64encode(ps.encode("utf-16le")).decode("ascii")
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def desktop_locations() -> list[Path]:
    candidates = [
        Path.home() / "Desktop",
        Path(os.environ.get("USERPROFILE", str(Path.home()))) / "OneDrive" / "Documents" / "Desktop",
        Path(os.path.expandvars(r"%USERPROFILE%\OneDrive\Desktop")),
        Path(os.environ.get("OneDrive", "")) / "Desktop",
        Path(os.environ.get("OneDrive", "")) / "Documents" / "Desktop",
    ]
    desktops: list[Path] = []
    for desktop in candidates:
        if not str(desktop) or str(desktop) == ".":
            continue
        try:
            desktop.mkdir(parents=True, exist_ok=True)
            resolved = desktop.resolve()
        except Exception:
            continue
        if resolved not in desktops:
            desktops.append(resolved)
    return desktops


def main() -> None:
    src = asset_root()
    install_dir = Path(os.environ["LOCALAPPDATA"]) / "Programs" / APP_NAME
    install_dir.mkdir(parents=True, exist_ok=True)

    for name in ("OpenClaw.exe", "BUILD_NOTES_openclaw_build108.md", "README.md"):
        shutil.copy2(src / name, install_dir / name)

    for desktop in desktop_locations():
        launcher = desktop / "START OpenClaw Build 1.0.8.bat"
        launcher.write_text(
            '@echo off\nstart "" "%LOCALAPPDATA%\\Programs\\OpenClaw Agent\\OpenClaw.exe"\n',
            encoding="utf-8",
        )
        create_shortcut(install_dir / "OpenClaw.exe", desktop / "OpenClaw Build 1.0.8.lnk")

    if "--no-launch" not in sys.argv:
        subprocess.Popen([str(install_dir / "OpenClaw.exe")], cwd=str(install_dir))

    print(f"{APP_NAME} {BUILD_LABEL} installed to {install_dir}")


if __name__ == "__main__":
    main()
