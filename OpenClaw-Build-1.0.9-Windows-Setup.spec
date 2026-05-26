# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['packaging\\windows\\openclaw_setup_installer.py'],
    pathex=[],
    binaries=[],
    datas=[('installer-build\\build-109\\src\\OpenClaw.exe', '.'), ('installer-build\\build-109\\src\\BUILD_NOTES_openclaw_build109.md', '.'), ('installer-build\\build-109\\src\\README.md', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='OpenClaw-Build-1.0.9-Windows-Setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['static\\img\\openclaw.ico'],
)
