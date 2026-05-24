from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "OpenClaw Agent"
BUILD_LABEL = "Build 1.0.5"


def asset_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def create_shortcut(target: Path, shortcut: Path) -> None:
    try:
        import win32com.client  # type: ignore

        shell = win32com.client.Dispatch("WScript.Shell")
        link = shell.CreateShortcut(str(shortcut))
        link.TargetPath = str(target)
        link.WorkingDirectory = str(target.parent)
        link.IconLocation = str(target)
        link.Save()
    except Exception:
        ps = (
            "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($args[0]);"
            "$s.TargetPath=$args[1];"
            "$s.WorkingDirectory=$args[2];"
            "$s.IconLocation=$args[1];"
            "$s.Save()"
        )
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps,
                str(shortcut),
                str(target),
                str(target.parent),
            ],
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

    for name in ("OpenClaw.exe", "BUILD_NOTES_openclaw_build105.md", "README.md"):
        shutil.copy2(src / name, install_dir / name)

    for desktop in desktop_locations():
        launcher = desktop / "START OpenClaw Build 1.0.5.bat"
        launcher.write_text(
            '@echo off\nstart "" "%LOCALAPPDATA%\\Programs\\OpenClaw Agent\\OpenClaw.exe"\n',
            encoding="utf-8",
        )
        create_shortcut(install_dir / "OpenClaw.exe", desktop / "OpenClaw Build 1.0.5.lnk")

    if "--no-launch" not in sys.argv:
        subprocess.Popen([str(install_dir / "OpenClaw.exe")], cwd=str(install_dir))

    print(f"{APP_NAME} {BUILD_LABEL} installed to {install_dir}")


if __name__ == "__main__":
    main()
