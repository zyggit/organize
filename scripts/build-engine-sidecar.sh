#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
venv_dir="$repo_root/build/desktop-python"
pyinstaller_dist="$repo_root/build/desktop-sidecar/dist"
pyinstaller_work="$repo_root/build/desktop-sidecar/work"
pyinstaller_spec="$repo_root/build/desktop-sidecar/spec"
pyinstaller_cache="$repo_root/build/desktop-sidecar/cache"
tauri_binaries="$repo_root/apps/desktop/src-tauri/binaries"

export PYINSTALLER_CONFIG_DIR="$pyinstaller_cache"

if [[ ! -x "$venv_dir/bin/python" ]]; then
  python3 -m venv "$venv_dir"
fi

if ! "$venv_dir/bin/python" -c 'import PyInstaller' >/dev/null 2>&1; then
  "$venv_dir/bin/python" -m pip install 'pyinstaller>=6,<7'
fi

if ! "$venv_dir/bin/python" -c 'import organize, send2trash' >/dev/null 2>&1; then
  "$venv_dir/bin/python" -m pip install --upgrade pip
  "$venv_dir/bin/python" -m pip install -e "$repo_root"
else
  "$venv_dir/bin/python" -m pip install --no-deps -e "$repo_root"
fi

rm -rf "$pyinstaller_dist" "$pyinstaller_work" "$pyinstaller_spec" "$pyinstaller_cache"
mkdir -p \
  "$pyinstaller_dist" \
  "$pyinstaller_work" \
  "$pyinstaller_spec" \
  "$pyinstaller_cache" \
  "$tauri_binaries"

"$venv_dir/bin/python" -m PyInstaller \
  --clean \
  --noconfirm \
  --onefile \
  --name organize-engine \
  --paths "$repo_root" \
  --paths "$repo_root/engine/src" \
  --distpath "$pyinstaller_dist" \
  --workpath "$pyinstaller_work" \
  --specpath "$pyinstaller_spec" \
  "$repo_root/engine/sidecar.py"

target_triple="$(rustc --print host-tuple)"
extension=""
if [[ "$target_triple" == *-windows-* ]]; then
  extension=".exe"
fi

source_binary="$pyinstaller_dist/organize-engine$extension"
target_binary="$tauri_binaries/organize-engine-$target_triple$extension"
cp "$source_binary" "$target_binary"
chmod +x "$target_binary"

echo "Engine sidecar: $target_binary"
