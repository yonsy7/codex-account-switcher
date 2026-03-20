"""
py2app build script.

Usage:
    python setup.py py2app

This creates a standalone macOS .app bundle in the dist/ folder.
The .app is fully standalone — no Python install needed on the target machine.
"""

from setuptools import setup

# py2app conflicts with pyproject.toml's install_requires,
# so we keep this file minimal and self-contained.
APP = ["src/codex_switcher/app.py"]

OPTIONS = {
    "argv_emulation": False,
    # LSUIElement=True = menu bar app only (no Dock icon, no Cmd+Tab entry)
    "plist": {
        "CFBundleName": "Codex Switcher",
        "CFBundleDisplayName": "Codex Switcher",
        "CFBundleIdentifier": "com.yonsy7.codex-switcher",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "LSUIElement": True,
        "LSMinimumSystemVersion": "12.0",
    },
    # Include our package + rumps and its dependencies
    "packages": ["codex_switcher", "rumps"],
    "includes": ["objc", "Foundation", "AppKit"],
    "resources": ["src/codex_switcher/resources"],
}

setup(
    app=APP,
    name="Codex Switcher",
    options={"py2app": OPTIONS},
    install_requires=[],
    setup_requires=["py2app"],
)
