# organize desktop

## Build a local macOS installer

Prerequisites: Node.js/npm, Rust, Xcode command-line tools, and Python 3.9 or
newer.

```bash
cd apps/desktop
npm ci
npm run bundle:macos
```

The build creates an architecture-specific application and DMG under:

```text
src-tauri/target/release/bundle/macos/organize.app
src-tauri/target/release/bundle/dmg/
```

The build script creates an isolated Python environment under the repository's
ignored `build/` directory, freezes the engine with PyInstaller, and bundles it
as a Tauri sidecar. The resulting application does not require Python to be
installed on the destination machine.

Local builds use an ad-hoc macOS signature. A Developer ID certificate and
Apple notarization are still required before distributing the DMG to other
users.

## Application icon

The approved O-and-folder master artwork is `app-icon.png`. Generate the
platform icon sizes with `npm run tauri -- icon app-icon.png`. The sidebar and
About page use `src/assets/app-icon.png`, copied from the generated
`src-tauri/icons/128x128@2x.png`. The older SVG concepts are retained as design
history and are not used by the installer.
