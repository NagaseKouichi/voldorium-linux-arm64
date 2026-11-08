"""Regression for external-disc links in the documented Docker invocation."""
import os
from pathlib import Path
import posixpath
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DockerPathTests(unittest.TestCase):
    def test_documented_mounts_preserve_external_disc_links(self):
        doc = (ROOT / 'docs/BUILD-ARM64.md').read_text()
        # The invocation itself must preserve both host locations, not relocate to /src.
        self.assertIn('-v "$REPO:$REPO"', doc)
        self.assertIn('-v "$DISC_DIR:$DISC_DIR:ro"', doc)
        self.assertIn('-w "$REPO"', doc)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / 'home/user/workspace'
            repo = base / 'repository'
            disc = base / 'external disc'
            output = repo / '.arm64/disc'
            disc.mkdir(parents=True)
            cue = disc / 'game.cue'
            cue.write_text('REM SINGLE-DENSITY AREA\nFILE "one.bin" BINARY\n'
                           ' TRACK 01 MODE1/2352\n INDEX 01 00:00:00\n'
                           'FILE "two.bin" BINARY\n TRACK 02 AUDIO\n'
                           ' INDEX 00 00:00:00\n INDEX 01 00:02:00\n'
                           'REM HIGH-DENSITY AREA\nFILE "three.bin" BINARY\n'
                           ' TRACK 03 MODE1/2352\n INDEX 01 00:00:00\n')
            for name, sectors in [('one.bin', 300), ('two.bin', 676), ('three.bin', 1)]:
                with (disc / name).open('wb') as f:
                    f.truncate(sectors * 2352)
            result = subprocess.run([sys.executable, str(ROOT / 'tools/cue_to_gdi.py'),
                                     '--cue', str(cue), '--output-dir', str(output)],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            link = output / 'track03.bin'
            relative = os.readlink(link)
            self.assertFalse(os.path.isabs(relative))
            # Same absolute host/container mounts preserve the external destination.
            target = posixpath.normpath(posixpath.join(str(link.parent), relative))
            self.assertEqual(target, str(disc / 'three.bin'))
            # The former relocation does NOT preserve that destination.
            relocated = posixpath.normpath(posixpath.join('/src/.arm64/disc', relative))
            self.assertNotEqual(relocated, target)


if __name__ == '__main__':
    unittest.main()
