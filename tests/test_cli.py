from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from isaac_online_modded import cli


def executable_bytes(include_experimental_lua_api: bool = False) -> bytes:
    patches = cli.selected_binary_patches(include_experimental_lua_api)
    return b"prefix" + b"middle".join(patch.pattern for patch in patches) + b"suffix"


def make_game_tree(root: Path, include_experimental_lua_api: bool = False) -> Path:
    game_dir = root / "The Binding of Isaac Rebirth"
    eid_dir = game_dir / "mods" / "External Item Descriptions"
    (eid_dir / "features").mkdir(parents=True)

    exe = game_dir / cli.GAME_EXE_NAME
    exe.write_bytes(executable_bytes(include_experimental_lua_api))

    (eid_dir / "main.lua").write_text(
        "EID = {}\n"
        "EID.isMultiplayer = false -- Used to color P1's highlight/outline indicators (single player just uses white)\n"
        "EID.isMultiplayer = false\n",
        encoding="utf-8",
    )
    (eid_dir / "features" / "eid_api.lua").write_text(
        "local function demo()\n"
        "  return listUpdatedForPlayers -- dont evaluate when bad data is present\n"
        "  player:HasCollectible(1)\n"
        "end\n",
        encoding="utf-8",
    )

    return game_dir


def make_game_without_eid(root: Path, include_experimental_lua_api: bool = False) -> Path:
    game_dir = root / "The Binding of Isaac Rebirth"
    game_dir.mkdir(parents=True)

    exe = game_dir / cli.GAME_EXE_NAME
    exe.write_bytes(executable_bytes(include_experimental_lua_api))

    return game_dir


class CLITest(unittest.TestCase):
    def test_default_patches_game_and_eid_when_installed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = make_game_tree(Path(tmp))
            exe = game_dir / cli.GAME_EXE_NAME
            original = exe.read_bytes()

            self.assertEqual(cli.main(["--game-exe", str(exe)]), 0)
            first_patch = exe.read_bytes()
            self.assertNotEqual(first_patch, original)
            for patch in cli.BINARY_PATCHES:
                self.assertIn(patch.already_patched_pattern, first_patch)
            self.assertEqual((game_dir / f"{cli.GAME_EXE_NAME}.bak").read_bytes(), original)

            main_lua = game_dir / "mods" / "External Item Descriptions" / "main.lua"
            eid_api = game_dir / "mods" / "External Item Descriptions" / "features" / "eid_api.lua"
            main_text = main_lua.read_text(encoding="utf-8")
            self.assertIn(
                "EID.isMultiplayer = true -- Used to color P1's highlight/outline indicators",
                main_text,
            )
            self.assertIn("\nEID.isMultiplayer = false\n", main_text)
            self.assertIn("if (stage >= 13 or stage < 1) then", eid_api.read_text(encoding="utf-8"))

            self.assertEqual(cli.main(["--game-exe", str(exe)]), 0)
            self.assertEqual(exe.read_bytes(), first_patch)

            self.assertEqual(cli.main(["--game-exe", str(exe), "--restore"]), 0)
            self.assertEqual(exe.read_bytes(), original)

    def test_default_skips_eid_when_not_installed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = make_game_without_eid(Path(tmp))
            exe = game_dir / cli.GAME_EXE_NAME

            self.assertEqual(cli.main(["--game-exe", str(exe)]), 0)
            for patch in cli.BINARY_PATCHES:
                self.assertIn(patch.already_patched_pattern, exe.read_bytes())

    def test_experimental_lua_api_patch_is_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = make_game_without_eid(Path(tmp), include_experimental_lua_api=True)
            exe = game_dir / cli.GAME_EXE_NAME

            self.assertEqual(cli.main(["--game-exe", str(exe), "--no-eid"]), 0)
            data = exe.read_bytes()
            self.assertIn(cli.EXPERIMENTAL_LUA_API_PATCH.pattern, data)
            self.assertNotIn(cli.EXPERIMENTAL_LUA_API_PATCH.already_patched_pattern, data)

            self.assertEqual(cli.main(["--game-exe", str(exe), "--no-eid", "--experimental-lua-api"]), 0)
            data = exe.read_bytes()
            self.assertNotIn(cli.EXPERIMENTAL_LUA_API_PATCH.pattern, data)
            self.assertIn(cli.EXPERIMENTAL_LUA_API_PATCH.already_patched_pattern, data)

    def test_revert_experimental_lua_api_patch_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = make_game_without_eid(Path(tmp), include_experimental_lua_api=True)
            exe = game_dir / cli.GAME_EXE_NAME

            self.assertEqual(cli.main(["--game-exe", str(exe), "--no-eid", "--experimental-lua-api"]), 0)
            patched = exe.read_bytes()
            self.assertIn(cli.EXPERIMENTAL_LUA_API_PATCH.already_patched_pattern, patched)

            self.assertEqual(cli.main(["--game-exe", str(exe), "--revert-experimental-lua-api"]), 0)
            repaired = exe.read_bytes()
            self.assertIn(cli.EXPERIMENTAL_LUA_API_PATCH.pattern, repaired)
            self.assertNotIn(cli.EXPERIMENTAL_LUA_API_PATCH.already_patched_pattern, repaired)
            for patch in cli.BINARY_PATCHES:
                self.assertIn(patch.already_patched_pattern, repaired)

    def test_no_eid_patches_game_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = make_game_tree(Path(tmp))
            exe = game_dir / cli.GAME_EXE_NAME

            self.assertEqual(cli.main(["--game-exe", str(exe), "--no-eid"]), 0)
            for patch in cli.BINARY_PATCHES:
                self.assertIn(patch.already_patched_pattern, exe.read_bytes())

            main_lua = game_dir / "mods" / "External Item Descriptions" / "main.lua"
            self.assertIn(
                "EID.isMultiplayer = false -- Used to color P1's highlight/outline indicators",
                main_lua.read_text(encoding="utf-8"),
            )

    def test_explicit_all_requires_eid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = make_game_without_eid(Path(tmp))
            exe = game_dir / cli.GAME_EXE_NAME

            with self.assertRaises(cli.EIDNotFoundError):
                cli.main(["--game-exe", str(exe), "--all"])

    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = make_game_tree(Path(tmp))
            exe = game_dir / cli.GAME_EXE_NAME
            original = exe.read_bytes()

            self.assertEqual(cli.main(["--game-exe", str(exe), "--all", "--dry-run"]), 0)
            self.assertEqual(exe.read_bytes(), original)
            self.assertFalse((game_dir / f"{cli.GAME_EXE_NAME}.bak").exists())

    def test_game_dir_argument_resolves_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = make_game_tree(Path(tmp))
            args = cli.parse_args(["--game-dir", str(game_dir), "--print-path"])
            self.assertEqual(cli.detect_game_exe(args), game_dir / cli.GAME_EXE_NAME)


if __name__ == "__main__":
    unittest.main()
