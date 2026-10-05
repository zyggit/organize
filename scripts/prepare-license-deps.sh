#!/usr/bin/env bash
# Populate the locked host graph before the deliberately offline license audit.
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
target_triple="$(rustc --print host-tuple)"

for manifest in "$repo_root/apps/desktop/src-tauri/Cargo.toml" "$repo_root/sidecars/similar-photos/Cargo.toml"; do
  cargo fetch --locked --target "$target_triple" --manifest-path "$manifest"
done
