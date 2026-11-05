# Kinetik JARVIS

Unofficial cyan / graphite / gold recolor of Kinetik Aqua for **Linux, NixOS and Windows**. Includes 15 animations / 203 source frames; Linux-only roles reuse the original art through aliases.

Windows preserves 64×64 shapes, transparency, hotspots and timing; only visible colors and incorrect RIFF lengths change. Linux exports 24, 32, 48, 64 and 96 px XCursor files with scaled hotspots and millisecond-rounded delays. Native 64 px pixels match after alpha premultiplication.

![Dark and light previews, enlarged 2×](preview.png)

Preview rows: Normal / Help / Working / Busy / Precision; Text / Handwriting / Unavailable / Vertical / Horizontal; Diagonal 1 / Diagonal 2 / Move / Alternate / Link.

## Windows

1. Right-click `install.inf` → **Install** (Windows 11: **Show more options** first); approve the prompt.
2. **Mouse Properties → Pointers → Kinetik JARVIS → Apply**.

Installs to `%WINDIR%\Cursors\Kinetik-JARVIS` without activating or overwriting another scheme. Select your previous scheme to switch back.

## Linux

From the cursor repository:

```sh
mkdir -p ~/.local/share/icons
cp -a Kinetik-JARVIS ~/.local/share/icons/
```

Select **Kinetik JARVIS** in desktop cursor settings, or set these before starting your session:

```sh
export XCURSOR_THEME=Kinetik-JARVIS
export XCURSOR_SIZE=32
```

Preserve alias symlinks when copying. Desktop settings may override variables; restart apps or log out/in. WSL installation affects Linux apps, not the Windows pointer.

## NixOS

Copy this folder beside your NixOS configuration and add:

```nix
imports = [ ./Kinetik-JARVIS/nixos.nix ];
```

Rebuild and log out/in. The module installs the Linux theme and selects it at 32 px, including the fallback theme. Choose it in desktop settings if they override session variables. Git-backed flakes must track the copied files.

Package-only configuration (the package also works with Home Manager):

```nix
environment.systemPackages = [ (pkgs.callPackage ./Kinetik-JARVIS/default.nix { }) ];
```

Build from the cursor repository:

```sh
nix build --impure --expr 'let pkgs = import <nixpkgs> {}; in pkgs.callPackage ./Kinetik-JARVIS/default.nix {}'
```

Installation needs no Python or conversion tools.

## Rebuild / test

Requires Python 3.10+ (standard library only); rebuilding also requires the original Aqua files:

```sh
python3 src/build_kinetik_jarvis.py --source /path/to/kinetik-aqua-x
KINETIK_SOURCE=/path/to/kinetik-aqua-x python3 -m unittest discover -s src -p 'test_kinetik_jarvis.py' -v
```

One build exports both platforms; `--output <directory>` changes the destination. Unit tests are self-contained. Without `KINETIK_SOURCE`, integration tests use the sibling Aqua directory or skip if absent; an explicit source must contain all 15 animations.

`src/kinetik_jarvis/` separates ANI parsing/recoloring, XCursor encoding and previews. Both themes share the cursor catalog and Linux/Windows packaging in `src/theme.py`; command-line builders stay thin. Tests cover pixels, geometry, transparency, hotspots, timing, aliases, palette and installer references. See the repository [source layout and full test command](../README.md#source-layout--tests).

Format verified with libXcursor 1.2.3; NixOS options checked against nixpkgs `1d060086d60cb76a40cf37109f979d88a5bd6396`.
