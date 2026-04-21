import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pandoc_to_markdown.converters import marker_backend


class MarkerBackendHelpersTests(unittest.TestCase):
    def test_build_marker_env_sets_project_local_model_cache_dir(self) -> None:
        env = marker_backend.build_marker_env(Path('/tmp/project'))

        self.assertEqual(env['MODEL_CACHE_DIR'], '/tmp/project/.models/marker')
        self.assertNotIn('TORCH_DEVICE', env)

    def test_build_marker_env_preserves_torch_device(self) -> None:
        env = marker_backend.build_marker_env(Path('/tmp/project'), 'cpu')

        self.assertEqual(env['MODEL_CACHE_DIR'], '/tmp/project/.models/marker')
        self.assertEqual(env['TORCH_DEVICE'], 'cpu')

    def test_build_marker_command_includes_requested_flags(self) -> None:
        command = marker_backend.build_marker_command(
            Path('/tmp/in.pdf'),
            Path('/tmp/out'),
            '/bin/marker_single',
            debug=True,
            force_ocr=True,
            disable_multiprocessing=True,
            disable_image_extraction=True,
        )

        self.assertEqual(
            command,
            [
                '/bin/marker_single',
                '/tmp/in.pdf',
                '--output_dir',
                '/tmp/out',
                '--output_format',
                'markdown',
                '--debug',
                '--force_ocr',
                '--disable_multiprocessing',
                '--disable_image_extraction',
            ],
        )

    def test_get_marker_output_path_returns_nested_markdown_path(self) -> None:
        self.assertEqual(
            marker_backend.get_marker_output_path(Path('/tmp/book.pdf'), Path('/tmp/out')),
            Path('/tmp/out/book/book.md'),
        )

    def test_looks_like_marker_device_crash_detects_known_signatures(self) -> None:
        self.assertTrue(marker_backend.looks_like_marker_device_crash('torch.AcceleratorError: boom'))
        self.assertTrue(marker_backend.looks_like_marker_device_crash('RuntimeError: Invalid buffer size: 10 GiB'))
        self.assertTrue(marker_backend.looks_like_marker_device_crash('surya failed on mps backend with Traceback'))
        self.assertFalse(marker_backend.looks_like_marker_device_crash('ordinary marker failure'))


class MarkerDownloadEventTests(unittest.TestCase):
    def test_run_marker_command_emits_download_metadata_on_first_download_line(self) -> None:
        events = []

        class FakeProc:
            def __init__(self):
                self.stdout = iter(["Downloading manifest.json\n"])

            def wait(self):
                return 0

        with patch("pandoc_to_markdown.converters.marker_backend.subprocess.Popen", return_value=FakeProc()):
            returncode, detail, download_started = marker_backend.run_marker_command(
                Path("/tmp/in.pdf"),
                Path("/tmp/out"),
                "/bin/marker_single",
                progress_callback=events.append,
            )

        self.assertEqual(returncode, 0)
        self.assertTrue(download_started)
        self.assertEqual(events[0]["type"], "MODEL_DOWNLOAD_STARTED")
        self.assertIn("models", events[0])
        self.assertTrue(events[0]["models"])
        self.assertIn("download_url", events[0]["models"][0])
        self.assertIn("model_size", events[0]["models"][0])


class ConvertPdfWithMarkerTests(unittest.TestCase):
    def test_convert_pdf_with_marker_retries_on_cpu_after_device_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            src = Path(tmp_dir) / 'book.pdf'
            src.write_text('pdf', encoding='utf-8')
            out_dir = Path(tmp_dir) / 'out'
            out_dir.mkdir()
            dst = out_dir / 'book' / 'book.md'
            dst.parent.mkdir()
            events = []
            calls = []

            def fake_run_marker_command(src_arg, target_dir_arg, marker_bin_arg, **kwargs):
                calls.append(kwargs.get('torch_device'))
                if kwargs.get('torch_device') == 'cpu':
                    dst.write_text('# ok', encoding='utf-8')
                    return 0, '', False
                return 1, 'torch.AcceleratorError: boom', False

            with patch('pandoc_to_markdown.converters.marker_backend.run_marker_command', side_effect=fake_run_marker_command):
                result = marker_backend.convert_pdf_with_marker(
                    src,
                    out_dir,
                    overwrite=True,
                    marker_bin='/bin/marker_single',
                    progress_callback=events.append,
                    marker_mode='auto',
                )

        self.assertEqual(calls, [None, 'cpu'])
        self.assertTrue(result['ok'])
        self.assertEqual(result['output'], str(dst))
        self.assertEqual(events, [{'type': 'MARKER_RETRY_CPU', 'engine': 'marker', 'message': marker_backend.MARKER_CPU_RETRY_NOTICE}])

    def test_convert_pdf_with_marker_does_not_retry_on_regular_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            src = Path(tmp_dir) / 'book.pdf'
            src.write_text('pdf', encoding='utf-8')
            out_dir = Path(tmp_dir) / 'out'
            out_dir.mkdir()
            calls = []

            def fake_run_marker_command(src_arg, target_dir_arg, marker_bin_arg, **kwargs):
                calls.append(kwargs.get('torch_device'))
                return 1, 'ordinary marker failure', False

            with patch('pandoc_to_markdown.converters.marker_backend.run_marker_command', side_effect=fake_run_marker_command):
                result = marker_backend.convert_pdf_with_marker(
                    src,
                    out_dir,
                    overwrite=True,
                    marker_bin='/bin/marker_single',
                )

        self.assertEqual(calls, [None])
        self.assertFalse(result['ok'])
        self.assertEqual(result['error'], 'MARKER_FAILED')
        self.assertEqual(result['detail'], 'ordinary marker failure')

    def test_convert_pdf_with_marker_cpu_mode_starts_on_cpu_without_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            src = Path(tmp_dir) / 'book.pdf'
            src.write_text('pdf', encoding='utf-8')
            out_dir = Path(tmp_dir) / 'out'
            out_dir.mkdir()
            calls = []

            def fake_run_marker_command(src_arg, target_dir_arg, marker_bin_arg, **kwargs):
                calls.append(kwargs.get('torch_device'))
                return 1, 'torch.AcceleratorError: boom', False

            with patch('pandoc_to_markdown.converters.marker_backend.run_marker_command', side_effect=fake_run_marker_command):
                result = marker_backend.convert_pdf_with_marker(
                    src,
                    out_dir,
                    overwrite=True,
                    marker_bin='/bin/marker_single',
                    marker_mode='cpu',
                )

        self.assertEqual(calls, ['cpu'])
        self.assertFalse(result['ok'])
        self.assertEqual(result['error'], 'MARKER_FAILED')
        self.assertEqual(result['detail'], 'torch.AcceleratorError: boom')

    def test_convert_pdf_with_marker_returns_combined_detail_when_cpu_retry_also_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            src = Path(tmp_dir) / 'book.pdf'
            src.write_text('pdf', encoding='utf-8')
            out_dir = Path(tmp_dir) / 'out'
            out_dir.mkdir()

            def fake_run_marker_command(src_arg, target_dir_arg, marker_bin_arg, **kwargs):
                if kwargs.get('torch_device') == 'cpu':
                    return 1, 'cpu still failed', False
                return 1, 'RuntimeError: Invalid buffer size: 10 GiB', False

            with patch('pandoc_to_markdown.converters.marker_backend.run_marker_command', side_effect=fake_run_marker_command):
                result = marker_backend.convert_pdf_with_marker(
                    src,
                    out_dir,
                    overwrite=True,
                    marker_bin='/bin/marker_single',
                )

        self.assertFalse(result['ok'])
        self.assertIn('default-device failure', result['detail'])
        self.assertIn('cpu retry failure', result['detail'])
        self.assertIn('cpu still failed', result['detail'])



class MarkerAssetsPathTests(unittest.TestCase):
    def test_project_root_points_to_repo_root(self) -> None:
        self.assertEqual(marker_backend._project_root(), Path(__file__).resolve().parents[1])


if __name__ == '__main__':
    unittest.main()
