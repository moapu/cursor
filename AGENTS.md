# Cursor themes

## Want

- Static, low-maintenance themes: nothing runs in the background, no helper apps (the Windows directional-resize helper stays gone), no build tools to install.
- Every theme ships Linux/NixOS and Windows; READMEs document both installs.
- One folder per theme holding all platforms and the preview; generated files committed.
- Linux cursors drawn bigger than nominal via `ZOOM`; change cursor size here, not in `~/nix-configs`.
- Refactors keep generated files byte-identical.

## Don't

- Add dependencies (Kinetik stays standard-library only).
- Overwrite real files with aliases, or other Windows schemes with an installer.
