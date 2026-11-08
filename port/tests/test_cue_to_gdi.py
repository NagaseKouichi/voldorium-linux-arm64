"""Black-box tests; sparse temporary BINs are never read by the converter."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "cue_to_gdi.py"
CUE = '''REM SINGLE-DENSITY AREA
FILE "Soulcalibur (USA) (Track 1).bin" BINARY
  TRACK 01 MODE1/2352
    INDEX 01 00:00:00
FILE "Soulcalibur (USA) (Track 2).bin" BINARY
  TRACK 02 AUDIO
    INDEX 00 00:00:00
    INDEX 01 00:02:00
REM HIGH-DENSITY AREA
FILE "Soulcalibur (USA) (Track 3).bin" BINARY
  TRACK 03 MODE1/2352
    INDEX 01 00:00:00
'''
EXPECTED = '3\n1 0 4 2352 track01.bin 0\n2 450 0 2352 track02.bin 352800\n3 45000 4 2352 track03.bin 0\n'


class CueToGdiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'original disc'
        self.source.mkdir()
        self.cue = self.source / 'Soulcalibur (USA).cue'
        self.cue.write_text(CUE)
        self.bins = []
        for number, size in enumerate((705600, 1589952, 1185760800), 1):
            path = self.source / f'Soulcalibur (USA) (Track {number}).bin'
            with path.open('wb') as stream:
                stream.truncate(size)
            self.bins.append(path)
        self.out = self.root / 'safe output'

    def run_cli(self):
        return subprocess.run([sys.executable, str(SCRIPT), '--cue', str(self.cue),
                               '--output-dir', str(self.out)], capture_output=True, text=True)

    def test_redump_offsets_safe_names_and_original_preservation(self):
        before = [(p.stat().st_ino, p.stat().st_size, p.stat().st_mtime_ns)
                  for p in [self.cue, *self.bins]]
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.out / 'disc.gdi').read_text(), EXPECTED)
        for number, original in enumerate(self.bins, 1):
            link = self.out / f'track{number:02}.bin'
            self.assertTrue(link.is_symlink())
            self.assertFalse(os.path.isabs(os.readlink(link)))
            self.assertEqual(link.resolve(), original.resolve())
        self.assertEqual(before, [(p.stat().st_ino, p.stat().st_size, p.stat().st_mtime_ns)
                                  for p in [self.cue, *self.bins]])


    def test_idempotent_preserves_links_and_descriptor(self):
        self.assertEqual(self.run_cli().returncode, 0)
        paths = list(self.out.iterdir())
        before = [(p.lstat().st_ino, p.lstat().st_mtime_ns) for p in paths]
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, [(p.lstat().st_ino, p.lstat().st_mtime_ns) for p in paths])

    def test_unsupported_layouts_rejected_before_output(self):
        replacements = [
            ('REM SINGLE-DENSITY AREA', ''),
            ('REM HIGH-DENSITY AREA', ''),
            ('TRACK 03 MODE1/2352', 'TRACK 03 MODE2/2352'),
            ('TRACK 02 AUDIO', 'TRACK 02 MODE1/2352'),
            ('TRACK 03', 'TRACK 04'),
            ('INDEX 01 00:02:00', 'INDEX 01 00:01:00'),
            ('INDEX 00 00:00:00', ''),
            ('INDEX 01 00:00:00', 'INDEX 01 00:00:01'),
            (' BINARY', ' WAVE'),
            ('  TRACK 01', '  PREGAP 00:02:00\n  TRACK 01'),
            ('INDEX 01 00:02:00', 'INDEX 01 00:02:00\n    INDEX 02 00:03:00'),
            ('REM HIGH-DENSITY AREA', 'REM HIGH-DENSITY AREA\nREM SINGLE-DENSITY AREA'),
        ]
        for old, new in replacements:
            with self.subTest(replacement=(old, new)):
                self.cue.write_text(CUE.replace(old, new))
                self.assertNotEqual(self.run_cli().returncode, 0)
                self.assertFalse(self.out.exists())
        self.cue.write_text(CUE + CUE)
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertFalse(self.out.exists())

    def test_escaping_paths_rejected(self):
        for name in ('../escape.bin', '/tmp/escape.bin', 'C:/escape.bin', r'..\escape.bin'):
            with self.subTest(name=name):
                self.cue.write_text(CUE.replace(self.bins[0].name, name))
                self.assertNotEqual(self.run_cli().returncode, 0)
                self.assertFalse(self.out.exists())

    def test_input_symlink_escape_rejected(self):
        external = self.root / 'outside.bin'
        self.bins[0].rename(external)
        self.bins[0].symlink_to(external)
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertFalse(self.out.exists())

    def test_invalid_sizes_rejected(self):
        for size in (0, 705601, 45000 * 2352):
            with self.subTest(size=size):
                with self.bins[0].open('r+b') as stream:
                    stream.truncate(size)
                self.assertNotEqual(self.run_cli().returncode, 0)
                self.assertFalse(self.out.exists())
        with self.bins[0].open('r+b') as stream:
            stream.truncate(705600)
        with self.bins[1].open('r+b') as stream:
            stream.truncate(150 * 2352)
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertFalse(self.out.exists())

    def test_missing_input_rejected(self):
        self.bins[2].unlink()
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertFalse(self.out.exists())

    def test_file_collisions_preflight_without_partial_links(self):
        self.out.mkdir()
        for name in ('track01.bin', 'track03.bin', 'disc.gdi'):
            with self.subTest(name=name):
                blocker = self.out / name
                blocker.write_text('keep me')
                before = blocker.stat().st_ino
                self.assertNotEqual(self.run_cli().returncode, 0)
                self.assertEqual(blocker.read_text(), 'keep me')
                self.assertEqual(blocker.stat().st_ino, before)
                self.assertEqual(list(self.out.iterdir()), [blocker])
                blocker.unlink()

    def test_wrong_and_dangling_symlinks_preserved(self):
        self.out.mkdir()
        target = self.root / 'unrelated.bin'
        target.write_text('unrelated')
        for name in ('track01.bin', 'disc.gdi'):
            for destination in (target, self.root / 'missing.bin'):
                with self.subTest(name=name, destination=destination):
                    link = self.out / name
                    link.symlink_to(destination)
                    before = (link.lstat().st_ino, os.readlink(link))
                    self.assertNotEqual(self.run_cli().returncode, 0)
                    self.assertEqual(before, (link.lstat().st_ino, os.readlink(link)))
                    self.assertEqual(target.read_text(), 'unrelated')
                    self.assertEqual(list(self.out.iterdir()), [link])
                    link.unlink()

    def test_existing_equivalent_relative_link_reused(self):
        self.out.mkdir()
        link = self.out / 'track01.bin'
        link.symlink_to(os.path.relpath(self.bins[0], self.out))
        before = (link.lstat().st_ino, os.readlink(link))
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, (link.lstat().st_ino, os.readlink(link)))


    def test_input_descriptor_collision_rejected_without_opening_bin(self):
        original = self.bins[2]
        renamed = self.source / 'disc.gdi'
        original.rename(renamed)
        self.cue.write_text(CUE.replace(original.name, renamed.name))
        # Real interpreter audit events verify absence of BIN opens, even on
        # noatime filesystems. The converter still runs against real files.
        wrapper = (
            "import sys, runpy\n"
            "from pathlib import Path\n"
            "target = Path(sys.argv[1]).resolve()\n"
            "def audit(event, args):\n"
            "    if event == 'open' and isinstance(args[0], str) and Path(args[0]).resolve() == target:\n"
            "        raise AssertionError('BIN DATA OPENED')\n"
            "sys.addaudithook(audit)\n"
            "sys.argv = sys.argv[2:]\n"
            "runpy.run_path(sys.argv[0], run_name='__main__')\n"
        )
        result = subprocess.run([sys.executable, '-c', wrapper, str(renamed),
                                 str(SCRIPT), '--cue', str(self.cue),
                                 '--output-dir', str(self.source)],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('BIN DATA OPENED', result.stderr)
        self.assertFalse((self.source / 'track01.bin').exists())


if __name__ == '__main__':
    unittest.main()
