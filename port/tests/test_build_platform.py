"""Build-platform contract: no compiler or installed SDL needed."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location('voldorium_build', Path(__file__).resolve().parents[2] / 'tools/build.py')
assert SPEC is not None and SPEC.loader is not None
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


class BuildPlatformTests(unittest.TestCase):
    def test_native_target_aliases_and_unsupported_host(self):
        for machine, target in [('x86_64', 'x86_64'), ('AMD64', 'x86_64'), ('aarch64', 'aarch64'), ('arm64', 'aarch64')]:
            with mock.patch.object(build.platform, 'machine', return_value=machine):
                self.assertEqual(build.native_target(), target + '-linux-gnu.2.28')
        with mock.patch.object(build.platform, 'machine', return_value='riscv64'):
            with self.assertRaises(ValueError):
                build.native_target()

    def test_cli_target_sysroot_jobs(self):
        args = build.argument_parser().parse_args(['--target', 'aarch64-linux-gnu.2.28', '--sysroot', '/sdk', '--jobs', '2'])
        self.assertEqual((args.target, args.sysroot, args.jobs), ('aarch64-linux-gnu.2.28', '/sdk', 2))
        for argv in (['--target', 'arm-linux-gnu'], ['--jobs', '0'], ['--jobs', '-1']):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                build.argument_parser().parse_args(argv)

    def test_zig_archive_tracks_host_not_target(self):
        with mock.patch.object(build, 'ZIG_TARGET', 'aarch64-linux-gnu.2.28'):
            self.assertIn('zig-x86_64-linux-0.14.1', build.zig_archive('x86_64')[0])
            archive = build.zig_archive('aarch64')
            self.assertIn('zig-aarch64-linux-0.14.1', archive[0])
            self.assertEqual(archive[1], 'f7a654acc967864f7a050ddacfaa778c7504a0eca8d2b678839c21eea47c992b')

    def test_compiler_command_uses_selected_target(self):
        with mock.patch.object(build, 'ZIG_TARGET', 'aarch64-linux-gnu.2.28'):
            self.assertEqual(build.zig_cc('/zig'), ['/zig/zig', 'cc', '-target', 'aarch64-linux-gnu.2.28'])
            self.assertEqual(build.zig_cc('/zig', True)[1], 'c++')

    def test_output_marker_rejects_other_target_and_unmarked_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            build.prepare_output(tmp, 'aarch64-linux-gnu.2.28')
            build.prepare_output(tmp, 'aarch64-linux-gnu.2.28')
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                build.prepare_output(tmp, 'x86_64-linux-gnu.2.28')
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'obj').mkdir()
            (Path(tmp) / 'obj' / 'stale.o').write_bytes(b'old')
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                build.prepare_output(tmp, 'aarch64-linux-gnu.2.28')

    def test_sysroot_dependency_flags_never_query_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'sdk'
            out = Path(tmp) / 'out'
            for directory in ('usr/include/SDL2', 'usr/include/GL', 'usr/include/aarch64-linux-gnu/SDL2', 'usr/lib/aarch64-linux-gnu', 'lib/aarch64-linux-gnu'):
                (root / directory).mkdir(parents=True, exist_ok=True)
            (root / 'usr/include/SDL2/SDL.h').write_text('/* SDL */')
            (root / 'usr/include/aarch64-linux-gnu/SDL2/SDL_config.h').write_text('/* ARM */')
            with mock.patch.object(build, 'run', side_effect=AssertionError('host command forbidden')):
                cf, ld = build.linux_dependency_flags(str(root), 'aarch64-linux-gnu.2.28', str(out))
            self.assertIn('-D_REENTRANT', cf)
            self.assertIn('-L' + str(root / 'usr/lib/aarch64-linux-gnu'), ld)
            self.assertIn('-L' + str(root / 'lib/aarch64-linux-gnu'), ld)
            self.assertNotIn('-L/usr/lib/x86_64-linux-gnu', ld)
            inc = Path(cf[cf.index('-I') + 1])
            self.assertEqual((inc / 'SDL2/SDL_config.h').read_text(), '/* ARM */')
            for header in inc.rglob('*'):
                if header.is_symlink():
                    self.assertTrue(header.resolve().is_relative_to(root))

    def test_native_dependency_fallback_uses_target_multiarch(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(build, 'run', return_value='-lSDL2'):
            _, ld = build.linux_dependency_flags(None, 'aarch64-linux-gnu.2.28', tmp)
            self.assertIn('-L/usr/lib/aarch64-linux-gnu', ld)

    def test_cross_host_requires_sysroot_before_tool_lookup(self):
        with mock.patch.object(build.platform, 'machine', return_value='x86_64'), mock.patch.object(build, 'tool_dirs', side_effect=AssertionError('tools reached too soon')):
            with mock.patch.object(build.sys, 'argv', ['build.py', '--only', 'host', '--target', 'aarch64-linux-gnu.2.28']), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                build.main()

    def test_host_build_generates_cross_compile_and_link_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'sdk'
            (root / 'usr/include/SDL2').mkdir(parents=True)
            (root / 'usr/lib/aarch64-linux-gnu').mkdir(parents=True)
            gg = Path(tmp) / 'repo/third_party/ggpo/src'
            for sub in ('lib/ggpo', 'lib/ggpo/backends', 'lib/ggpo/network'):
                (gg / sub).mkdir(parents=True)
            (gg / 'lib/ggpo/client.cpp').write_text('// test')
            commands = []
            def record(command, cwd=build.PORT):
                commands.append(command)
                if '-o' in command:
                    Path(command[command.index('-o') + 1]).touch()
                return ''
            with mock.patch.multiple(build, OUT=str(Path(tmp) / 'out'), SC=str(Path(tmp) / 'repo'), PORT=tmp,
                                     ZIG_TARGET='aarch64-linux-gnu.2.28', SYSROOT=str(root)), \
                 mock.patch.object(build, 'build_id', return_value='test'), \
                 mock.patch.object(build, 'translator_id', return_value='test'), \
                 mock.patch.object(build, 'run', side_effect=record), contextlib.redirect_stdout(io.StringIO()):
                build.step_host_linux('/zig')
            self.assertGreater(len(commands), len(build.GAME_SOURCES))
            for command in commands:
                self.assertEqual(command[:4], ['/zig/zig', 'c++' if command[1] == 'c++' else 'cc', '-target', 'aarch64-linux-gnu.2.28'])
            link = commands[-1]
            self.assertIn('-L' + str(root / 'usr/lib/aarch64-linux-gnu'), link)
            self.assertIn('-lSDL2', link)
            self.assertIn('-lGL', link)
            self.assertNotIn('sdl2-config', ' '.join(' '.join(c) for c in commands))

    def test_output_marker_includes_sysroot_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            build.prepare_output(tmp, 'aarch64-linux-gnu.2.28', '/sdk-one')
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                build.prepare_output(tmp, 'aarch64-linux-gnu.2.28', '/sdk-two')

    def test_parallel_obeys_job_limit(self):
        with mock.patch.object(build, 'JOBS', 2), mock.patch.object(build.concurrent.futures, 'ThreadPoolExecutor', wraps=build.concurrent.futures.ThreadPoolExecutor) as executor, mock.patch.object(build, 'run', return_value=''):
            build.parallel([(['compiler'],)] * 5)
            self.assertEqual(executor.call_args.kwargs['max_workers'], 2)


if __name__ == '__main__':
    unittest.main()
