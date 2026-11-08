# Linux ARM64 build / Linux ARM64 构建

[English overview](../README.md) · [中文概览](../README-CN.md)

## Supported input

SoulCalibur USA T-1401N V1.000. Extraction verifies both hashes and rejects a different executable:

| File | SHA-1 |
|---|---|
| IP.BIN | `38b8ef1fc65f53ccf154038d16e26a99ecc65875` |
| 1ST_READ.BIN | `967ca1fe2e8c7df57a5de1e83d939bed483cc6c9` |

The input is a GDI with its tracks. For the supported three-file Redump CUE layout, run from the repository root (Python 3.9+ for this optional converter):

```sh
python3 tools/cue_to_gdi.py --cue '/path/to/Soulcalibur (USA).cue' --output-dir .arm64/disc
```

This creates `disc.gdi` and relative links to the original BINs. No conversion of sector data, game download, or BIN modification occurs. Existing conflicting paths are rejected. The source BIN files must remain accessible. This helper is intentionally not a universal CUE converter.

## x86 Linux → AArch64 cross build

Requirements on the build host: Docker, Python 3 and internet for initial tool/dependency downloads. Do not install packages on the handheld.

```sh
# All apt operations are inside the new container.
docker build -t voldorium-arm64-cross:portable -f tools/Dockerfile.arm64-cross tools

# If you have GDI already, use its absolute path instead of this converter's output.
python3 tools/cue_to_gdi.py --cue '/path/to/Soulcalibur (USA).cue' --output-dir .arm64/disc
mkdir -p .arm64/player

# Keep canonical absolute locations unchanged inside Docker.
REPO=$(pwd -P)
DISC_DIR=$(realpath '/path/to/disc-directory')
docker run --rm -v "$REPO:$REPO" -v "$DISC_DIR:$DISC_DIR:ro" -w "$REPO" \
  voldorium-arm64-cross:portable \
  python3 -I tools/build.py --download \
    --target aarch64-linux-gnu.2.28 --sysroot / --jobs 4 \
    --out "$REPO/.arm64/container-build" --player-dir "$REPO/.arm64/player" \
    --gdi "$REPO/.arm64/disc/disc.gdi"
```

**External disc paths:** set `DISC_DIR` to the actual parent directory containing the CUE/BIN files. Both repository and disc directory are mounted at their **canonical host absolute paths**, so the converter's relative symlinks resolve identically on the host and inside Docker. Do not remap only the repository to `/src`: sibling or ancestor-relative disc links would resolve to different locations even if the disc directory is mounted at its host path. A disc directory inside the repository can be mounted read-only at the same location too. If the repository path is itself reached via a symlink, use `pwd -P` as above. If you relocate either directory, rerun the converter into a fresh output directory rather than reusing old links.

The Docker recipe uses public Ubuntu 24.04, not any pre-existing local image. Apt packages are not snapshot-pinned; record their installed versions with `docker run --rm voldorium-arm64-cross:portable dpkg-query -W`. Zig 0.14.1 and Flycast auxiliary files are pinned by SHA-256 in `tools/build.py`. Output objects are architecture/sysroot marked; use a fresh `--out` when changing either. Keep `--jobs` modest on memory-limited hosts. Source paths may differ between host/container, so do not reuse one output directory with a differently spelled sysroot path.

`--only host` builds the runtime without any disc. `--only module --module-dir DIR` builds the private module only. `--only player` stages the private player folder. Use a separate output for x86 regression builds.

To use a host-side pinned Zig with an exported ARM64 sysroot:

```sh
ZIG=/path/to/zig-x86_64-linux-0.14.1 python3 -I tools/build.py \
  --target aarch64-linux-gnu.2.28 --sysroot /path/to/arm64-sysroot \
  --jobs 4 --out .arm64/host-build --player-dir .arm64/player \
  --gdi /absolute/path/disc.gdi
```

The target sysroot must include SDL2/GL/KHR headers and AArch64 SDL2/libGL link libraries. Host libc headers are not mixed into Zig's glibc-baseline headers.

## Native ARM64 module setup

A build/setup archive contains `builder/first_run.sh`. On an ARM64 Linux system with Python 3 and internet, the builder downloads **AArch64** Zig, translates your own disc and compiles a native module. The ordinary player UI can invoke it after choosing a GDI; from a terminal:

```sh
chmod +x voldorium builder/first_run.sh
sh builder/first_run.sh /absolute/path/disc.gdi "$PWD"
./voldorium --disc /absolute/path/disc.gdi
```

The module-only builder needs no SDL/OpenGL development packages. A full native source build does need native SDL/OpenGL development headers. On read-only distributions prefer cross-building on the workstation; do not alter `/usr/lib`, `/lib` or the OS image.

## Runtime-only handheld deployment

Use an AArch64 Linux desktop/gamescope environment with native SDL2 and desktop GL 3.3 Core. A pure GLES driver is insufficient. Stage the entire runtime directory and add your privately built `sc_game.so`, replacement font and disc tracks. Start `voldorium`, not a compiler. Set `[game] disc` in `voldorium.ini` to the device path or use `--disc`; changing only the APK/Android configuration is not applicable to this Linux port.

No CPU affinity is forced. For Armada Steam/game mode retain its launcher wrapper `/usr/libexec/armada/armada-game-launch %command%`. Installation/copying does not grant automatic device launch: coordinate before replacing a running game or using a shared device.

## Tests

```sh
python3 -m unittest discover -s port/tests -p 'test_*.py' -v
python3 port/tests/fpmode_test.py --zig /path/to/zig --require-arm-run
```

The latter needs native gcc and `qemu-aarch64` in PATH. It checks real x86 and AArch64 arithmetic/control behavior and cross-compiles the replay and generated synthetic harness. A skipped ARM execution is not a runtime pass. Game regression must additionally reach fight mode and report nonzero SyncTest samples; a menu-only run is not a pass.

## Distribution boundary

The private player includes game-derived code and is not a public release. Public packages must exclude `.arm64`, `Soulcalibur (USA)`, `extracted`, `port/build`, `sc_game.so`, `biosfont.bin`, VMUs, logs, translated C and toolchain caches. Package from an explicit source allowlist, retain credits/licenses, and include source matching the runtime build in build/setup archives.
