import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import importlib.util


MODULE_PATH = Path(__file__).resolve().parents[1] / '.claude' / 'skills' / 'pandoc_to_markdown' / 'pandoc_to_markdown_skill.py'
SPEC = importlib.util.spec_from_file_location('pandoc_to_markdown_skill', MODULE_PATH)
pandoc_to_markdown_skill = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(pandoc_to_markdown_skill)


class PandocToMarkdownSkillHistoryTests(unittest.TestCase):
    def test_read_last_custom_out_dir_returns_none_when_history_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            self.assertIsNone(pandoc_to_markdown_skill.read_last_custom_out_dir(project_root))

    def test_read_last_custom_out_dir_returns_none_for_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            history_path = pandoc_to_markdown_skill.get_history_path(project_root)
            history_path.parent.mkdir(parents=True, exist_ok=True)
            history_path.write_text('{broken', encoding='utf-8')

            self.assertIsNone(pandoc_to_markdown_skill.read_last_custom_out_dir(project_root))

    def test_write_last_custom_out_dir_persists_resolved_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            out_dir = project_root / 'nested' / '..' / 'custom-out'

            pandoc_to_markdown_skill.write_last_custom_out_dir(project_root, out_dir)

            history_path = pandoc_to_markdown_skill.get_history_path(project_root)
            payload = json.loads(history_path.read_text(encoding='utf-8'))
            self.assertEqual(payload['last_custom_out_dir'], str((project_root / 'custom-out').resolve()))

    def test_get_effective_out_dir_defaults_to_project_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            self.assertEqual(
                pandoc_to_markdown_skill.get_effective_out_dir(['convert', '--mode', 'single'], project_root),
                (project_root / 'outputs').resolve(),
            )

    def test_main_persists_history_after_successful_custom_output_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            cli_path = project_root / 'src' / 'pandoc_to_markdown' / 'cli.py'
            cli_path.parent.mkdir(parents=True, exist_ok=True)
            cli_path.write_text('', encoding='utf-8')
            custom_out = project_root / 'my-output'

            with patch.object(pandoc_to_markdown_skill, 'resolve_project_root', return_value=project_root), \
                patch.object(pandoc_to_markdown_skill, 'resolve_runner_python', return_value=Path('/usr/bin/python3')), \
                patch.object(pandoc_to_markdown_skill, 'subprocess') as subprocess_mock, \
                patch('sys.argv', ['skill', 'convert', '--mode', 'single', '--paths', '/tmp/book.pdf', '--out-dir', str(custom_out)]):
                subprocess_mock.run.return_value.returncode = 0
                with self.assertRaises(SystemExit) as ctx:
                    pandoc_to_markdown_skill.main()

            self.assertEqual(ctx.exception.code, 0)
            history_path = pandoc_to_markdown_skill.get_history_path(project_root)
            payload = json.loads(history_path.read_text(encoding='utf-8'))
            self.assertEqual(payload['last_custom_out_dir'], str(custom_out.resolve()))

    def test_main_does_not_persist_history_for_default_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            cli_path = project_root / 'src' / 'pandoc_to_markdown' / 'cli.py'
            cli_path.parent.mkdir(parents=True, exist_ok=True)
            cli_path.write_text('', encoding='utf-8')

            with patch.object(pandoc_to_markdown_skill, 'resolve_project_root', return_value=project_root), \
                patch.object(pandoc_to_markdown_skill, 'resolve_runner_python', return_value=Path('/usr/bin/python3')), \
                patch.object(pandoc_to_markdown_skill, 'subprocess') as subprocess_mock, \
                patch('sys.argv', ['skill', 'convert', '--mode', 'single', '--paths', '/tmp/book.pdf']):
                subprocess_mock.run.return_value.returncode = 0
                with self.assertRaises(SystemExit):
                    pandoc_to_markdown_skill.main()

            self.assertFalse(pandoc_to_markdown_skill.get_history_path(project_root).exists())

    def test_main_does_not_persist_history_when_run_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            cli_path = project_root / 'src' / 'pandoc_to_markdown' / 'cli.py'
            cli_path.parent.mkdir(parents=True, exist_ok=True)
            cli_path.write_text('', encoding='utf-8')
            custom_out = project_root / 'my-output'

            with patch.object(pandoc_to_markdown_skill, 'resolve_project_root', return_value=project_root), \
                patch.object(pandoc_to_markdown_skill, 'resolve_runner_python', return_value=Path('/usr/bin/python3')), \
                patch.object(pandoc_to_markdown_skill, 'subprocess') as subprocess_mock, \
                patch('sys.argv', ['skill', 'convert', '--mode', 'single', '--paths', '/tmp/book.pdf', '--out-dir', str(custom_out)]):
                subprocess_mock.run.return_value.returncode = 1
                with self.assertRaises(SystemExit):
                    pandoc_to_markdown_skill.main()

            self.assertFalse(pandoc_to_markdown_skill.get_history_path(project_root).exists())


if __name__ == '__main__':
    unittest.main()
