#!/usr/bin/env python3
"""Game-independent FP runtime regression/cross-build checks.

python3 port/tests/fpmode_test.py [--zig /path/to/zig] [--require-arm-run]
Build artifacts and synthetic harness fixtures live only in a temporary directory.
ARM runtime tests run automatically when qemu-aarch64 is on PATH.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def run(args):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=ROOT, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zig", default=os.environ.get("ZIG", "/tmp/zig-x86_64-linux-0.14.1/zig"))
    ap.add_argument("--require-arm-run", action="store_true")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="fpmode-") as tmp:
        t = Path(tmp)
        # Entirely invented register state, never a game oracle or translated function.
        st = {k: ["00000000"] * 16 for k in ("r", "fr", "xf")}
        st.update({k: "00000000" for k in ("pr", "mach", "macl", "gbr", "fpul", "fpscr", "timer")})
        st.update({k: 0 for k in ("t", "s", "q", "m")})
        st["mem"] = []
        oracle = t / "synthetic.jsonl"
        oracle.write_text(json.dumps({"fn": "00000000", "in": st, "out": st}) + "\n")
        harness = t / "harness.c"
        run([sys.executable, "-I", "port/m0/gen_harness_fpu.py", oracle, harness, "00000000"])
        common = ["-O2", "-frounding-math", "-fno-fast-math", "-Iport/sh4c"]
        sources = [Path("port/tests/fpmode.c"), harness, Path("port/m0/replay.c")]
        for name, cc in [("x86", ["gcc"]), ("arm64", [a.zig, "cc", "-target", "aarch64-linux-musl"])]:
            for i, src in enumerate(sources):
                run(cc + common + ["-c", src, "-o", t / f"{name}-{i}.o"])
            exe = t / f"fpmode-{name}"
            run(cc + common + [sources[0], "-static", "-lm", "-o", exe])
            if name == "x86":
                run([exe])
            elif shutil.which("qemu-aarch64"):
                run(["qemu-aarch64", exe])
            elif a.require_arm_run:
                raise SystemExit("FAIL: qemu-aarch64 required but unavailable")
            else:
                print("SKIP ARM runtime: qemu-aarch64 unavailable; cross-compile is NOT semantic validation")
    print("PASS: native runtime and native/AArch64 runtime+replay+generated-harness builds")


if __name__ == "__main__":
    main()
