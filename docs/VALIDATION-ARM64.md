# ARM64 validation record

This is an offline development/test-ready port, **not a real-device acceptance report**.

## Source and compiler

- Upstream baseline: `f02cfc9e448757670695f011362b3ed2c3d8b191` (same as upstream HEAD at audit).
- Development branch: `port/linux-arm64`; the exact published source commit is recorded in each release archive’s `BUILD-RECEIPT.json`.
- Zig 0.14.1 host archive SHA-256: `24aeeec8af16c381934a6cd7d95c807a8cb2cf7df9fa40d359aa884195c4716c`.
- Target: `aarch64-linux-gnu.2.28`; runtime build key `9f59df4b7a6a`.
- SDL2 target headers/libs: Ubuntu 24.04 ARM64 `2.30.0+dfsg-1ubuntu3.1`.
- Exported-sysroot and clean public-base Docker host builds produced the same executable SHA-256: `ec4006a9a79cc41c4eabc95185c49f3f4bac23ec0ecf00239d33b4da49280a41`.

## Verified offline

1. User disc extraction matched both upstream supported SHA-1 values.
2. Generated 3,632 SH-4 entry points (3,251 original plus 381 supplemental entries).
3. Runtime and private module are AArch64 ELF; module exports `sc_game_attach`.
4. Runtime imports glibc symbols through `GLIBC_2.27`; the selected compiler target is glibc 2.28. System SDL/Mesa dependency requirements remain separate.
5. 23 Python unit tests passed for build platform/sysroot/cache handling, safe CUE descriptor generation and the documented external-disc Docker mount paths. A real Docker namespace test confirmed that a relative link to a sibling external disc directory resolves correctly with same-absolute-path mounts.
6. Real x86 and QEMU AArch64 synthetic FP tests passed: float/double rounding modes, FTZ, signed underflow, NaN payload, control/status reset and bank swap. Native and ARM64 builds of the replay and synthetic harness passed. The FP arithmetic/control executable also passed on x86 and QEMU AArch64 with the production Zig flags (`-O1 -ffp-contract=off -fno-strict-aliasing -DSH4_TAG_WRITES`) and glibc 2.28 targets, without adding `-frounding-math`.
7. Corrected-script QEMU AArch64 regression (240 seconds): reached fight mode 1 at virtual frame 1845, **329/329 fight SyncTest re-runs identical**, 35,408 thread switches, 8 threads started, 11 contexts. Battle HUD called 18 times. Stopped normally at the watchdog time limit, not an unimplemented instruction or freeze.
8. QEMU + Xvfb + AArch64 Mesa llvmpipe created an OpenGL 4.5 Core context (game requests 3.3) and saved six actual game readbacks at 320×240. `shot_50.png` shows the SoulCalibur opening sword/logo. This is software rendering, not device-GPU evidence.
9. Same-source x86 baseline reached fight mode 1 and passed 360/360 SyncTest re-runs using the previous slower script. Menu dwell alone was not an ARM64-specific hang.
10. AICA generated real nonzero stereo PCM. A bounded sample scan found 2,586,344 nonzero samples in 4,000,000 analyzed signed 16-bit values, range -32,060..30,525. This proves PCM generation, not audible device output.

## Test-script correction

The original shared script sent A at main-menu mode 11, where Start is required; both architectures waited through the longer automatic flow. `port/tests/common.sh` now sends Start at controller poll 900 and A at poll 1200, entering the battle flow sooner. The full corrected sequence is retained in that file. The new script was actually exercised before replacement.

## Important limitations

- The translator reports four original functions with unimplemented reachable instructions (2 `stc.l ctl`, 1 `ldc.l ctl`, 1 undefined opcode); the report is not globally clean. Tested paths did not trigger them; untested modes remain unproven.
- AArch64 FZ flushes input and output denormals, while the existing SSE implementation uses FTZ with DAZ clear. This is explicit in source/tests; it is not full SH-4 exception/NaN emulation and does not certify x86/ARM online lockstep.
- The first Xvfb wrapper did not launch QEMU due to its readiness signal wait. Direct X11-socket readiness allowed the game to run. Softpipe was too slow for bounded screenshot collection; llvmpipe produced real frames.
- QEMU/software-renderer timing is not representative of handheld performance. No 60 FPS claim is made.

## Outstanding real-device gates

- Native OpenGL 3.3/Core context and correct sustained menu/battle rendering on the target GPU.
- SDL audio device output and audible correctness.
- Physical controller mapping, press-to-picture response and actual game speed.
- VMU save/reload and cold restart on target paths, fullscreen/gamescope launch.
- Stable battle frame times/thermals and longer mode/rollback regressions.
- Copying, installing, launching and input/sampling require an explicit handoff; no device has been accessed by this task.

Private full logs, screenshots, derived module and receipts remain under ignored `.arm64/`. Public archives exclude all game-derived data.

## Independent review follow-up

The reviewer found one actionable documentation error: remapping the repository alone to `/src` changes relative-link destinations for discs stored outside it. The build instructions now preserve canonical host paths for both bind mounts. A new regression first failed on the old invocation and passed after the correction, including a real container path-resolution check. This was a documentation/test change only; runtime and private module binaries remain unchanged. No security concerns were reported.

## Armada user report

The user reports that the game runs on their Armada handheld. This is user-reported native runtime confirmation, not an independently measured audio/controller/performance/thermal acceptance. No new device access or input was performed for publication.
