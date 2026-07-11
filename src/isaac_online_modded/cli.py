"""
Linux-native CLI for Isaac Online Modded.

This is the standalone Linux project: no WPF, no .csproj, no Windows publish
profiles.  It mirrors the original patching logic with only Python's standard
library so it can be packaged and run as a normal Linux/Nix command.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


GAME_DIR_NAME = "The Binding of Isaac Rebirth"
GAME_EXE_NAME = "isaac-ng.exe"
DEFAULT_BACKUP_SUFFIX = ".bak"


class PatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class BinaryPatch:
    name: str
    pattern: bytes
    already_patched_pattern: bytes
    replacements: tuple[tuple[int, int], ...]


BINARY_PATCHES = (
    BinaryPatch(
        name="online co-op mod gate",
        pattern=bytes(
            [
                0x83,
                0xE8,
                0x02,
                0x74,
                0x2A,
                0x83,
                0xE8,
                0x01,
                0x74,
                0x1E,
                0x83,
                0xE8,
                0x01,
                0x74,
                0x12,
                0x32,
                0xC0,
                0x8B,
                0x4D,
                0xF4,
                0x64,
                0x89,
                0x0D,
                0x00,
                0x00,
                0x00,
                0x00,
            ]
        ),
        already_patched_pattern=bytes(
            [
                0x83,
                0xE8,
                0x02,
                0x90,
                0x90,
                0x83,
                0xE8,
                0x01,
                0x90,
                0x90,
                0x83,
                0xE8,
                0x01,
                0x90,
                0x90,
                0x32,
                0xC0,
                0x8B,
                0x4D,
                0xF4,
                0x64,
                0x89,
                0x0D,
                0x00,
                0x00,
                0x00,
                0x00,
            ]
        ),
        replacements=((3, 0x90), (4, 0x90), (8, 0x90), (9, 0x90), (13, 0x90), (14, 0x90)),
    ),
    BinaryPatch(
        name="desync analytics sender",
        pattern=bytes([0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x10, 0x53, 0x56, 0x57, 0xFF, 0x15]),
        already_patched_pattern=bytes([0xC3, 0x8B, 0xEC, 0x83, 0xEC, 0x10, 0x53, 0x56, 0x57, 0xFF, 0x15]),
        replacements=((0, 0xC3),),
    ),
)


OLD_EID_PATCHES = (
    (
        "if EID.isOnlineMultiplayer and Game():GetLevel():GetStage() >= LevelStage.Home then",
        "return listUpdatedForPlayers -- Calling player:HasCollectible can cause a crash after beating The Beast in R+ Coop",
        "end",
        "",
    ),
    (
        "local stage = Game():GetLevel():GetStage()",
        "if stage == nil then",
        "return listUpdatedForPlayers",
        "end",
        "if EID.isOnlineMultiplayer and (stage >= 13 or stage < 1) then",
        "return listUpdatedForPlayers -- Calling player:HasCollectible can cause a crash after beating The Beast in R+ Coop",
        "end",
        "",
    ),
)

NEW_EID_BLOCK = (
    "\t\t",
    "\t\tlocal stage = Game():GetLevel():GetStage()",
    "\t\tif stage == nil then",
    "\t\t\treturn listUpdatedForPlayers",
    "\t\tend",
    "\t\tif (stage >= 13 or stage < 1) then",
    "\t\t\treturn listUpdatedForPlayers -- Calling player:HasCollectible can cause a crash after beating The Beast in R+ Coop",
    "\t\tend",
)


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value)))


def unique_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def steam_roots() -> list[Path]:
    home = Path.home()
    candidates = [
        os.environ.get("STEAM_ROOT"),
        os.environ.get("STEAM_DIR"),
        os.environ.get("STEAM_COMPAT_CLIENT_INSTALL_PATH"),
    ]
    paths = [expand_path(p) for p in candidates if p]
    paths.extend(
        [
            home / ".local/share/Steam",
            home / ".steam/steam",
            home / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
        ]
    )
    return unique_paths(paths)


def unescape_vdf_path(value: str) -> str:
    return value.replace("\\\\", "\\").replace('\\"', '"')


def steam_library_roots(steam_root: Path) -> list[Path]:
    paths = [steam_root]
    vdf_path = steam_root / "steamapps/libraryfolders.vdf"
    if not vdf_path.exists():
        return unique_paths(paths)

    text = vdf_path.read_text(encoding="utf-8", errors="replace")

    for raw in re.findall(r'"path"\s+"((?:\\.|[^"\\])*)"', text):
        paths.append(expand_path(unescape_vdf_path(raw)))

    # Old libraryfolders.vdf format used numeric keys directly as paths.
    for raw in re.findall(r'"\d+"\s+"((?:\\.|[^"\\])*)"', text):
        candidate = unescape_vdf_path(raw)
        if candidate.startswith(("/", "~", "$")):
            paths.append(expand_path(candidate))

    return unique_paths(paths)


def candidate_game_dirs() -> list[Path]:
    paths: list[Path] = []
    env_game_dir = os.environ.get("ISAAC_GAME_DIR")
    if env_game_dir:
        paths.append(expand_path(env_game_dir))

    for steam_root in steam_roots():
        for library_root in steam_library_roots(steam_root):
            paths.append(library_root / "steamapps/common" / GAME_DIR_NAME)

    return unique_paths(paths)


def detect_game_exe(args: argparse.Namespace) -> Path:
    if args.game_exe:
        return expand_path(args.game_exe)

    if args.game_dir:
        return expand_path(args.game_dir) / GAME_EXE_NAME

    if args.path:
        path = expand_path(args.path)
        if path.name.lower() == GAME_EXE_NAME or (path.exists() and path.is_file()):
            return path
        return path / GAME_EXE_NAME

    env_game_exe = os.environ.get("ISAAC_GAME_EXE")
    if env_game_exe:
        return expand_path(env_game_exe)

    for game_dir in candidate_game_dirs():
        exe = game_dir / GAME_EXE_NAME
        if exe.exists():
            return exe

    return Path.home() / ".local/share/Steam/steamapps/common" / GAME_DIR_NAME / GAME_EXE_NAME


def backup_once(path: Path, suffix: str, dry_run: bool) -> Path:
    if not suffix:
        raise PatchError("Backup suffix must not be empty")

    backup_path = path.with_name(path.name + suffix)
    if backup_path.exists():
        print(f"Using existing backup: {backup_path}")
        return backup_path

    if dry_run:
        print(f"Would create backup: {backup_path}")
    else:
        shutil.copy2(path, backup_path)
        print(f"Created backup: {backup_path}")

    return backup_path


def restore_backup(game_exe: Path, suffix: str, dry_run: bool) -> None:
    backup_path = game_exe.with_name(game_exe.name + suffix)
    if not backup_path.exists():
        raise PatchError(f"Backup not found: {backup_path}")

    if dry_run:
        print(f"Would restore {game_exe} from {backup_path}")
        return

    shutil.copy2(backup_path, game_exe)
    print(f"Restored: {game_exe}")


def patch_game_executable(game_exe: Path, suffix: str, dry_run: bool) -> bool:
    if not game_exe.exists():
        searched = "\n  ".join(str(p / GAME_EXE_NAME) for p in candidate_game_dirs())
        raise PatchError(
            f"Game executable not found: {game_exe}\n"
            f"Pass --game-exe/--game-dir, set ISAAC_GAME_EXE/ISAAC_GAME_DIR, or install Steam in the default path.\n"
            f"Searched candidates:\n  {searched}"
        )
    if not game_exe.is_file():
        raise PatchError(f"Game executable is not a file: {game_exe}")

    original = game_exe.read_bytes()
    patched = bytearray(original)
    changed = False

    for patch in BINARY_PATCHES:
        index = original.find(patch.pattern)
        if index != -1:
            changed = True
            for offset, value in patch.replacements:
                patched[index + offset] = value
            print(f"Will patch {patch.name} at offset 0x{index:x}")
            continue

        already_index = original.find(patch.already_patched_pattern)
        if already_index != -1:
            print(f"Already patched: {patch.name} at offset 0x{already_index:x}")
            continue

        raise PatchError(f"Pattern for {patch.name!r} not found. The game may have updated and this patcher may be outdated.")

    if not changed:
        print("Game executable already patched.")
        return False

    backup_once(game_exe, suffix, dry_run)
    if dry_run:
        print(f"Would write patched executable: {game_exe}")
    else:
        game_exe.write_bytes(patched)
        print(f"Patched executable: {game_exe}")
    return True


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def remove_old_eid_patches(lines: list[str]) -> tuple[list[str], bool]:
    changed = False
    result = list(lines)

    for old_patch in OLD_EID_PATCHES:
        for start in range(0, len(result)):
            if old_patch[0] not in result[start]:
                continue
            end = start + len(old_patch)
            if end > len(result):
                continue
            if all(old_patch[i] in result[start + i] for i in range(1, len(old_patch))):
                del result[start:end]
                changed = True
                break

    return result, changed


def has_new_eid_patch(lines: list[str]) -> bool:
    checks = (
        "if stage == nil then",
        "return listUpdatedForPlayers",
        "end",
        "if (stage >= 13 or stage < 1) then",
        "return listUpdatedForPlayers",
        "end",
    )
    for index, line in enumerate(lines):
        if "local stage = Game():GetLevel():GetStage()" not in line:
            continue
        if index + len(checks) >= len(lines):
            continue
        if all(check in lines[index + 1 + offset] for offset, check in enumerate(checks)):
            return True
    return False


def patch_eid_main_lua(main_lua: Path) -> tuple[list[str], bool]:
    lines = read_lines(main_lua)
    if any("EID.isMultiplayer = true" in line for line in lines):
        return lines, False

    marker = "EID.isMultiplayer = false -- Used to color P1's highlight/outline indicators (single player just uses white)"
    changed = False
    new_lines: list[str] = []
    for line in lines:
        if marker in line or "EID.isMultiplayer = false" in line:
            new_lines.append(line.replace("EID.isMultiplayer = false", "EID.isMultiplayer = true"))
            changed = True
        else:
            new_lines.append(line)

    if not changed:
        raise PatchError(f"Could not find EID.isMultiplayer setting in {main_lua}")

    return new_lines, True


def patch_eid_api_lua(eid_api: Path) -> tuple[list[str], bool]:
    original_lines = read_lines(eid_api)
    lines, removed_old_patch = remove_old_eid_patches(original_lines)

    if has_new_eid_patch(lines):
        return lines, removed_old_patch

    try:
        anchor = next(
            index
            for index, line in enumerate(lines)
            if "return listUpdatedForPlayers -- dont evaluate when bad data is present" in line
        )
    except StopIteration as exc:
        raise PatchError(f"Could not find EID patch anchor in {eid_api}") from exc

    insert_at = min(anchor + 2, len(lines))
    lines[insert_at:insert_at] = list(NEW_EID_BLOCK)
    return lines, True


def find_eid_dir(mods_dir: Path) -> Path:
    if not mods_dir.exists():
        raise PatchError(f"Mods directory not found: {mods_dir}")
    if not mods_dir.is_dir():
        raise PatchError(f"Mods path is not a directory: {mods_dir}")

    matches = [
        path
        for path in mods_dir.iterdir()
        if path.is_dir()
        and "external" in path.name.lower()
        and "item" in path.name.lower()
        and "descriptions" in path.name.lower()
    ]
    if not matches:
        raise PatchError(f"External Item Descriptions not found in: {mods_dir}")
    return sorted(matches)[0]


def patch_external_item_descriptions(game_exe: Path, mods_dir_arg: str | None, suffix: str, dry_run: bool) -> bool:
    mods_dir = expand_path(mods_dir_arg) if mods_dir_arg else game_exe.parent / "mods"
    eid_dir = find_eid_dir(mods_dir)
    print(f"Using EID mod directory: {eid_dir}")

    main_lua = eid_dir / "main.lua"
    eid_api = eid_dir / "features/eid_api.lua"
    for required in (main_lua, eid_api):
        if not required.exists():
            raise PatchError(f"Required EID file not found: {required}")

    changed_any = False

    new_main_lines, main_changed = patch_eid_main_lua(main_lua)
    if main_changed:
        changed_any = True
        backup_once(main_lua, suffix, dry_run)
        if dry_run:
            print(f"Would patch: {main_lua}")
        else:
            write_lines(main_lua, new_main_lines)
            print(f"Patched: {main_lua}")
    else:
        print(f"Already patched: {main_lua}")

    new_api_lines, api_changed = patch_eid_api_lua(eid_api)
    if api_changed:
        changed_any = True
        backup_once(eid_api, suffix, dry_run)
        if dry_run:
            print(f"Would patch: {eid_api}")
        else:
            write_lines(eid_api, new_api_lines)
            print(f"Patched: {eid_api}")
    else:
        print(f"Already patched: {eid_api}")

    if not changed_any:
        print("External Item Descriptions already patched.")
    return changed_any


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Patch The Binding of Isaac: Rebirth to allow mods in online co-op on Linux.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "path",
        nargs="?",
        help=f"Optional game executable or game directory. Directories are resolved to {GAME_EXE_NAME}.",
    )
    parser.add_argument("--game-exe", help=f"Path to {GAME_EXE_NAME}.")
    parser.add_argument("--game-dir", help=f"Path to '{GAME_DIR_NAME}'.")
    parser.add_argument("--mods-dir", help="Path to the Isaac mods directory for --patch-eid/--all.")
    parser.add_argument("--patch-game", action="store_true", help="Patch the game executable.")
    parser.add_argument("--patch-eid", action="store_true", help="Patch External Item Descriptions for co-op.")
    parser.add_argument("--all", action="store_true", help="Patch both the game executable and EID.")
    parser.add_argument("--restore", action="store_true", help="Restore the game executable from its backup and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without writing files.")
    parser.add_argument("--print-path", action="store_true", help="Print the detected game executable path and exit.")
    parser.add_argument("--backup-suffix", default=DEFAULT_BACKUP_SUFFIX, help="Suffix used for backup files.")
    args = parser.parse_args(argv)

    explicit_path_options = sum(bool(v) for v in (args.path, args.game_exe, args.game_dir))
    if explicit_path_options > 1:
        parser.error("Use only one of positional path, --game-exe, or --game-dir.")
    if args.restore and (args.patch_game or args.patch_eid or args.all):
        parser.error("--restore cannot be combined with patch actions.")

    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    game_exe = detect_game_exe(args)

    if args.print_path:
        print(game_exe)
        return 0

    if args.restore:
        restore_backup(game_exe, args.backup_suffix, args.dry_run)
        return 0

    patch_game = args.patch_game or args.all
    patch_eid = args.patch_eid or args.all
    if not patch_game and not patch_eid:
        patch_game = True

    if patch_game:
        patch_game_executable(game_exe, args.backup_suffix, args.dry_run)
    if patch_eid:
        patch_external_item_descriptions(game_exe, args.mods_dir, args.backup_suffix, args.dry_run)

    return 0


def main_entry() -> None:
    try:
        raise SystemExit(main(sys.argv[1:]))
    except PatchError as exc:
        eprint(f"error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main_entry()
