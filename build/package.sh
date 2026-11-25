#!/usr/bin/env bash
set -euo pipefail

# Simple packaging helper for Linux using PyInstaller (if installed)
pyinstaller --onefile -n acteo src/acteo/main.py || echo "Install pyinstaller to build a binary"
