# Luffy cursors

One Piece cursor theme for Linux (XCursor) and Windows (`.cur` / `.ani`), generated from one script.

![preview](src/preview.png)

| Cursor | Look |
| --- | --- |
| Normal | Mihawk's Yoru, a shine runs down the blade |
| Working | Yoru coated in Haki |
| Busy | Gear 5 Luffy orbiting in a Haki ring |
| Link | Chibi Luffy pointing |
| Text | Meat on the bone |
| Grab / grabbing | Gear 3 giant hand |
| Not allowed | Jolly Roger shaking "no" |
| Move | Compass |
| Precision | Sogeking's scope |

## Linux

```sh
ln -s "$PWD/Luffy" ~/.icons/Luffy
```

Then set the theme to `Luffy`, e.g. `XCURSOR_THEME=Luffy` / `hyprctl setcursor Luffy 24`.
On Linux the pointer, text and grab cursors are drawn 1.5x and the link cursor 2x the nominal size.

## Windows

Copy `Luffy-Windows` to the PC, right-click `install.inf` → **Install**, then pick the **Luffy** scheme in
Mouse settings → Pointers. Untested on Windows so far.

## Build

Needs `xcursorgen`, `rsvg-convert` (librsvg) and Python with Pillow. With Nix:

```sh
nix shell --impure --expr 'with builtins.getFlake "nixpkgs"; with legacyPackages.${builtins.currentSystem}; [ xcursorgen librsvg (python3.withPackages (p: [ p.pillow ])) ]' -c python3 src/build.py
```

This rewrites `Luffy/`, `Luffy-Windows/` and `src/preview.png`.
