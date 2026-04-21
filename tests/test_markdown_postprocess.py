import tempfile
import unittest
from pathlib import Path

from pandoc_to_markdown.markdown_postprocess import postprocess_markdown, postprocess_markdown_file


class PostprocessMarkdownTests(unittest.TestCase):
    def test_postprocess_normalizes_whitespace_headers_lists_and_fences(self) -> None:
        source = """# Title
Paragraph with trailing spaces.
### Section
- item one
Paragraph after list
```
code sample
"""

        expected = """# Title

Paragraph with trailing spaces.

### Section

- item one

Paragraph after list

```
code sample

```
"""

        self.assertEqual(postprocess_markdown(source), expected)

    def test_postprocess_removes_noise_lines_and_collapses_blank_runs(self) -> None:
        source = """Alpha

·



Beta
"""
        self.assertEqual(postprocess_markdown(source), "Alpha\n\nBeta\n")

    def test_postprocess_is_idempotent(self) -> None:
        source = """# Title
Paragraph

- item
"""
        once = postprocess_markdown(source)
        twice = postprocess_markdown(once)
        self.assertEqual(twice, once)

    def test_postprocess_file_rewrites_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.md"
            path.write_text("# Title\nText   \n", encoding="utf-8")
            postprocess_markdown_file(path)
            self.assertEqual(path.read_text(encoding="utf-8"), "# Title\n\nText\n")


if __name__ == "__main__":
    unittest.main()
