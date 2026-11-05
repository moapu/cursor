"""Shared cursor catalog and Linux/Windows theme packaging (standard library only)."""

from dataclasses import dataclass

# Control Panel scheme order, including the optional Windows 10+ roles.
ROLES = (
    "Arrow", "Help", "AppStarting", "Wait", "Crosshair", "IBeam", "NWPen", "No",
    "SizeNS", "SizeWE", "SizeNWSE", "SizeNESW", "SizeAll", "UpArrow", "Hand", "Pin", "Person",
)


@dataclass(frozen=True)
class Cursor:
    name: str
    aliases: tuple[str, ...] = ()
    role: str | None = None
    file: str | None = None
    linux: bool = True


@dataclass(frozen=True)
class Theme:
    folder: str
    title: str
    cursors: tuple[Cursor, ...]
    comment: str
    linux_name: str | None = None
    activate: bool = False

    def __post_init__(self):
        names, roles, files = set(), set(), set()
        for cursor in self.cursors:
            if cursor.linux:
                for name in (cursor.name, *cursor.aliases):
                    if name in names:
                        raise ValueError(f"Duplicate Linux cursor name: {name}")
                    names.add(name)
            if cursor.role is None and cursor.file is None:
                continue
            if cursor.role not in ROLES or not cursor.file:
                raise ValueError(f"Invalid Windows role/file: {cursor.name}")
            if cursor.role in roles or cursor.file in files:
                raise ValueError(f"Duplicate Windows role/file: {cursor.name}")
            roles.add(cursor.role)
            files.add(cursor.file)

    @property
    def windows(self):
        cursors = {cursor.role: cursor for cursor in self.cursors if cursor.role}
        return tuple(cursors[role] for role in ROLES if role in cursors)


def installer(theme):
    """Register a scheme; activation is explicit because existing themes differ."""
    cursors = theme.windows
    paths = [rf"%10%\%CUR_DIR%\{cursor.file}" for cursor in cursors]
    lines = [
        "[Version]", 'signature="$CHICAGO$"', "",
        "[DefaultInstall]", "CopyFiles = Scheme.Cur",
        "AddReg = Scheme.Reg" + (", Wreg" if theme.activate else ""), "",
        "[DestinationDirs]", 'Scheme.Cur = 10,"%CUR_DIR%"', "",
        "[Scheme.Reg]",
        rf'HKCU,"Control Panel\Cursors\Schemes","%SCHEME_NAME%",0x00020000,"{",".join(paths)}"', "",
    ]
    if theme.activate:
        lines += [
            "[Wreg]", r'HKCU,"Control Panel\Cursors",,0x00020000,"%SCHEME_NAME%"',
            *(rf'HKCU,"Control Panel\Cursors",{cursor.role},0x00020000,"{path}"'
              for cursor, path in zip(cursors, paths)), "",
        ]
    lines += [
        "[Scheme.Cur]", *(f'"{cursor.file}"' for cursor in cursors), "",
        "[Strings]", rf'CUR_DIR = "Cursors\{theme.folder}"', f'SCHEME_NAME = "{theme.title}"', "",
    ]
    return "\r\n".join(lines).encode("ascii")


def windows(theme, cursors, output):
    """Write encoded Windows files and their installer from the same catalog."""
    missing = {cursor.file for cursor in theme.windows} - cursors.keys()
    if missing:
        raise ValueError(f"Missing Windows cursors: {', '.join(sorted(missing))}")
    output.mkdir(parents=True, exist_ok=True)
    for cursor in theme.windows:
        (output / cursor.file).write_bytes(cursors[cursor.file])
    (output / "install.inf").write_bytes(installer(theme))


def linux(theme, output):
    """Package already-encoded XCursor files; never replace an alias's regular file."""
    directory = output / "cursors"
    for cursor in theme.cursors:
        if not cursor.linux:
            continue
        if not (directory / cursor.name).is_file():
            raise FileNotFoundError(directory / cursor.name)
        for alias in cursor.aliases:
            path = directory / alias
            if path.is_symlink():
                path.unlink()
            elif path.exists():
                raise FileExistsError(f"Refusing to overwrite existing cursor alias: {path}")
            path.symlink_to(cursor.name)
    metadata = f"[Icon Theme]\nName={theme.linux_name or theme.title}\nComment={theme.comment}\n"
    for name in ("index.theme", "cursor.theme"):
        (output / name).write_text(metadata)
