from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from isaac_online_modded import cli


def make_game_tree(root: Path) -> Path:
    game_dir = root / "The Binding of Isaac Rebirth"
    eid_dir = game_dir / "mods" / "External Item Descriptions"
    (eid_dir / "features").mkdir(parents=True)

    patch1 = cli.BINARY_PATCHES[0].pattern
    patch2 = cli.BINARY_PATCHES[1].pattern
    exe = game_dir / cli.GAME_EXE_NAME
    exe.write_bytes(b"prefix" + patch1 + b"middle" + patch2 + b"suffix")

    (eid_dir / "main.lua").write_text(
        "EID = {}\n"
        "EID.isMultiplayer = false -- Used to color P1's highlight/outline indicators (single player just uses white)\n",
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


class CLITest(unittest.TestCase):
    def test_patch_game_eid_idempotent_and_restore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = make_game_tree(Path(tmp))
            exe = game_dir / cli.GAME_EXE_NAME
            original = exe.read_bytes()

            self.assertEqual(cli.main(["--game-exe", str(exe), "--all"]), 0)
            first_patch = exe.read_bytes()
            self.assertNotEqual(first_patch, original)
            self.assertIn(cli.BINARY_PATCHES[0].already_patched_pattern, first_patch)
            self.assertIn(cli.BINARY_PATCHES[1].already_patched_pattern, first_patch)
            self.assertEqual((game_dir / f"{cli.GAME_EXE_NAME}.bak").read_bytes(), original)

            main_lua = game_dir / "mods" / "External Item Descriptions" / "main.lua"
            eid_api = game_dir / "mods" / "External Item Descriptions" / "features" / "eid_api.lua"
            self.assertIn("EID.isMultiplayer = true", main_lua.read_text(encoding="utf-8"))
            self.assertIn("if (stage >= 13 or stage < 1) then", eid_api.read_text(encoding="utf-8"))

            self.assertEqual(cli.main(["--game-exe", str(exe), "--all"]), 0)
            self.assertEqual(exe.read_bytes(), first_patch)

            self.assertEqual(cli.main(["--game-exe", str(exe), "--restore"]), 0)
            self.assertEqual(exe.read_bytes(), original)

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
