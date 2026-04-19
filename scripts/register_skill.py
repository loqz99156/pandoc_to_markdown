#!/usr/bin/env python3
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    skill_dir = project_root / ".claude" / "skills" / "pandoc_to_markdown"
    destination_dir = Path.home() / ".claude" / "skills" / "pandoc_to_markdown"

    destination_dir.mkdir(parents=True, exist_ok=True)

    for file_name in ["SKILL.md", "README.md", "pandoc_to_markdown_skill.py"]:
        source = skill_dir / file_name
        target = destination_dir / file_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    (destination_dir / ".project-root").write_text(str(project_root), encoding="utf-8")
    print(destination_dir)


if __name__ == "__main__":
    main()
