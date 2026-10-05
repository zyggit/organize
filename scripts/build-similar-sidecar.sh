#!/usr/bin/env bash
# Build the MIT similar-photos sidecar (czkawka_core only, no krokiet).
# Requires Rust 1.94.1 or newer because czkawka_core 12 uses edition 2024.
# The default build does not link libheif. On macOS, HEIC is decoded with /usr/bin/sips.

set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
manifest="$repo_root/sidecars/similar-photos/Cargo.toml"
tauri_binaries="$repo_root/apps/desktop/src-tauri/binaries"

rust_ok() {
  local version
  version="$(rustc --version | awk '{print $2}')"
  python3 - "$version" <<'PY'
import sys
parts = tuple(int(piece) for piece in sys.argv[1].split(".")[:3])
sys.exit(0 if parts >= (1, 94, 1) else 1)
PY
}

if ! rust_ok; then
  if command -v rustup >/dev/null 2>&1 && rustup run stable rustc --version >/dev/null 2>&1; then
    export RUSTUP_TOOLCHAIN=stable
  else
    echo "similar-photos needs Rust 1.94.1 or newer (czkawka_core 12)." >&2
    echo "Install it with: rustup toolchain install stable --profile minimal" >&2
    exit 1
  fi
  if ! rust_ok; then
    echo "The stable toolchain is still older than Rust 1.94.1." >&2
    exit 1
  fi
fi

mkdir -p "$tauri_binaries"
target_triple="$(rustc --print host-tuple)"
cargo fetch --locked --target "$target_triple" --manifest-path "$manifest"
cargo build --release --locked --manifest-path "$manifest"

python3 - "$repo_root" "$target_triple" <<'PY'
import json, re, subprocess, sys
from pathlib import Path

def copyleft_only(token):
    name = token.strip().upper()
    if name.startswith("LGPL"):
        return False
    return name.startswith(("GPL", "AGPL"))

def forbidden(name, license_name):
    if name == "krokiet":
        return True
    expression = license_name.replace("(", " ").replace(")", " ")
    for clause in re.split(r"\bAND\b", expression):
        options = [option for option in re.split(r"\bOR\b", clause) if option.strip()]
        if options and all(copyleft_only(option) for option in options):
            return True
    return False

root = Path(sys.argv[1]) / "sidecars" / "similar-photos"
raw = subprocess.check_output(
    ["cargo", "metadata", "--format-version", "1", "--locked", "--offline",
     "--filter-platform", sys.argv[2]],
    cwd=root, text=True,
)
metadata = json.loads(raw)
target_packages = {node["id"] for node in metadata["resolve"]["nodes"]}
packages = [package for package in metadata["packages"] if package["id"] in target_packages]
for package in packages:
    license_name = package.get("license") or ""
    if forbidden(package["name"], license_name):
        raise SystemExit(f"refusing GPL crate {package['name']} ({license_name})")
PY

extension=""
if [[ "$target_triple" == *-windows-* ]]; then
  extension=".exe"
fi
target_dir="$(cargo metadata --format-version 1 --locked --offline --manifest-path "$manifest" --no-deps | python3 -c 'import json,sys; print(json.load(sys.stdin)["target_directory"])')"
source_binary="$target_dir/release/similar-photos$extension"
target_binary="$tauri_binaries/similar-photos-$target_triple$extension"
cp "$source_binary" "$target_binary"
chmod +x "$target_binary"
echo "Similar-photos sidecar: $target_binary"
echo "HEIC: macOS uses /usr/bin/sips. This build does not link libheif."
