#!/usr/bin/env python3
"""Make disc.gdi plus relative trackNN.bin symlinks; never copy or read BIN data.

Only the three-file Redump layout is supported: single-density MODE1/2352,
AUDIO with INDEX 00 at zero and INDEX 01 at 00:02:00, then high-density
MODE1/2352 at LBA 45000. Other layouts are deliberately rejected rather than
being guessed. Run in a trusted local directory, not one concurrently edited
by another process. Existing different output files are never overwritten.
"""
import argparse
import os
from pathlib import Path
import re
import stat

SECTOR_BYTES = 2352
AUDIO_PREGAP = 150
HD_LBA = 45000


def parse_sources(cue):
    """Validate the complete supported CUE grammar and stat (not read) each BIN."""
    tokens = []
    names = []
    for raw in cue.read_text(encoding='utf-8-sig').splitlines():
        line = ' '.join(raw.strip().split())
        if not line:
            continue
        if line.startswith('REM ') and line not in (
                'REM SINGLE-DENSITY AREA', 'REM HIGH-DENSITY AREA'):
            continue
        # Preserve filename whitespace; normalize only command whitespace.
        match = re.fullmatch(r'\s*FILE\s+"([^"\r\n]+)"\s+BINARY\s*', raw)
        if match:
            names.append(match.group(1))
            tokens.append('FILE')
        else:
            tokens.append(line)
    expected = [
        'REM SINGLE-DENSITY AREA', 'FILE', 'TRACK 01 MODE1/2352',
        'INDEX 01 00:00:00', 'FILE', 'TRACK 02 AUDIO',
        'INDEX 00 00:00:00', 'INDEX 01 00:02:00',
        'REM HIGH-DENSITY AREA', 'FILE', 'TRACK 03 MODE1/2352',
        'INDEX 01 00:00:00',
    ]
    if tokens != expected:
        raise ValueError('unsupported CUE layout: expected three separate Redump BIN tracks')
    sources = []
    sectors = []
    for name in names:
        relative = Path(name)
        if (relative.is_absolute() or '..' in relative.parts or
                '\\' in name or ':' in name or any(ord(c) < 32 for c in name)):
            raise ValueError(f'unsafe BIN path: {name!r}')
        source = (cue.parent / relative).resolve(strict=True)
        if not source.is_relative_to(cue.parent):
            raise ValueError(f'BIN path escapes CUE directory: {name!r}')
        info = source.stat()
        if not stat.S_ISREG(info.st_mode) or not info.st_size or info.st_size % SECTOR_BYTES:
            raise ValueError(f'BIN must be a nonempty regular file of whole 2352-byte sectors: {name!r}')
        sources.append(source)
        sectors.append(info.st_size // SECTOR_BYTES)
    if len({(p.stat().st_dev, p.stat().st_ino) for p in sources}) != 3:
        raise ValueError('each track must have a distinct BIN file')
    if sectors[1] <= AUDIO_PREGAP or sum(sectors[:2]) > HD_LBA:
        raise ValueError('invalid single-density sizes or missing audio INDEX 01 data')
    return sources, sectors


def convert(cue, output_dir):
    """Validate all inputs and output collisions before creating any links."""
    cue = Path(cue).resolve(strict=True)
    sources, sectors = parse_sources(cue)
    descriptor = (f'3\n1 0 4 2352 track01.bin 0\n'
                  f'2 {sectors[0] + AUDIO_PREGAP} 0 2352 track02.bin '
                  f'{AUDIO_PREGAP * SECTOR_BYTES}\n'
                  f'3 {HD_LBA} 4 2352 track03.bin 0\n')
    output_dir = Path(output_dir).absolute()
    if output_dir.is_symlink():
        raise ValueError('output directory must not be a symlink')
    output_dir = output_dir.resolve()
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError('output path is not a directory')
    links = [(output_dir / f'track{i:02}.bin', source)
             for i, source in enumerate(sources, 1)]
    for link, source in links:
        if os.path.lexists(link):
            if (not link.is_symlink() or os.path.isabs(os.readlink(link)) or
                    link.resolve(strict=True) != source):
                raise ValueError(f'refusing existing different output: {link}')
    path = output_dir / 'disc.gdi'
    if os.path.lexists(path):
        # Never follow a descriptor symlink or read unbounded arbitrary files.
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'refusing existing nonregular descriptor: {path}')
        identity = path.stat()
        if any((identity.st_dev, identity.st_ino) ==
               (source.stat().st_dev, source.stat().st_ino)
               for source in [cue, *sources]):
            raise ValueError(f'descriptor aliases an input file: {path}')
        with path.open('rb') as stream:
            existing = stream.read(len(descriptor.encode('ascii')) + 1)
        if existing != descriptor.encode('ascii'):
            raise ValueError(f'refusing existing different descriptor: {path}')
    output_dir.mkdir(parents=True, exist_ok=True)
    for link, source in links:
        if not os.path.lexists(link):
            link.symlink_to(os.path.relpath(source, output_dir))
    if not os.path.lexists(path):
        # Exclusive creation also refuses files/symlinks appearing after preflight.
        with path.open('x', encoding='ascii', newline='\n') as stream:
            stream.write(descriptor)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cue', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        path = convert(args.cue, args.output_dir)
    except (OSError, ValueError, UnicodeError, RuntimeError) as exc:
        parser.exit(1, f'cue_to_gdi: {exc}\n')
    print(path)


if __name__ == '__main__':
    main()
