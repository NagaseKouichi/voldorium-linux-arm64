# Voldorium — Linux ARM64

[中文说明](README-CN.md) · [Build instructions](docs/BUILD-ARM64.md) · [Original upstream README](docs/README.upstream.md)

Native Linux AArch64 port of [enrique363/voldorium](https://github.com/enrique363/voldorium), the static-recompilation port of Dreamcast **SoulCalibur USA, T-1401N, V1.000**. SH-4 code is translated to C and compiled as an AArch64 game module; the game is not run through an x86 translation layer.

## Status

- ARM64 executable and privately generated `sc_game.so` built using pinned Zig 0.14.1.
- x86 SSE floating-point control retained; AArch64 FPCR/FPSR support and game-independent runtime tests added.
- Host/target architecture separated; cross SDL/OpenGL sysroot, bounded jobs and incompatible object-cache rejection implemented.
- Verified AArch64 game startup, coroutine switching and actual OpenGL readbacks under QEMU with Mesa llvmpipe. This is **not real-device performance, GPU, audio or physical-controller acceptance**.
- OpenGL **3.3 Core** is required. This is not an OpenGL ES/Android build.
- The user reports that the game runs on an Armada handheld. Audio, physical-controller behavior, frame times and thermals have not been independently accepted.
- See [validation evidence and remaining gates](docs/VALIDATION-ARM64.md). Cross-architecture online determinism is not certified.

## Own disc required

No disc images, extracted boot files, generated translation units, game-derived modules, BIOS font or personal saves are distributed. Build `sc_game.so` from your legally owned supported disc. Keep the module and runtime from compatible sources together.

For Redump CUE+BIN dumps, `tools/cue_to_gdi.py` creates a GDI descriptor and relative symlinks without altering or copying BIN files. Only the explicitly validated three-track layout is accepted. Copying a descriptor alone does not transfer the disc; keep its relative symlinks and source files valid.

## Quick build

See [BUILD-ARM64.md](docs/BUILD-ARM64.md) for the complete tested x86-host Docker cross-build and native ARM64 module setup commands. Native ARM64 builds select the ARM64 Zig download; x86-host cross-builds select x86 Zig and target AArch64.

Runtime dependencies are the target system's `libSDL2-2.0.so.0`, `libGL.so.1`, glibc and graphics/audio drivers. Compiler target baseline is glibc 2.28; downstream SDL/Mesa packages may require newer glibc. No x86 fallback libraries, bundled libc or fixed CPU affinity are used. The operating system selects CPUs on heterogeneous ARM systems.

## Packages

- **build/setup ZIP:** ARM64 runtime plus first-run module builder and corresponding source.
- **runtime ZIP:** ARM64 runtime only; requires a compatible module you built privately.

Both exclude all game-derived data. If your extractor drops executable permissions, run `chmod +x voldorium builder/first_run.sh` (omit the builder path for runtime-only packages).

## Credits and licensing

Original project: enrique363; original translator/runtime work and co-author credits are preserved in [the upstream README](docs/README.upstream.md). Upstream first-party code is offered for **personal, non-commercial use with a legally owned game**; this fork does not relicense it. GGPO retains its MIT license. SDL, Zig and Flycast components retain their respective upstream terms. Review the upstream licensing section before redistribution.
