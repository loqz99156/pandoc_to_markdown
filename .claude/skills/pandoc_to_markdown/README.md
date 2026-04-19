# pandoc_to_markdown

`pandoc_to_markdown` 是 `pandoc-to-markdown` 项目内置的 Claude Code skill。

这个目录现在只保留 **薄入口层**：
- `pandoc_to_markdown_skill.py` 负责转发参数
- 真正的安装、自检、格式路由、转换执行都在 `src/pandoc_to_markdown/` 里

## 当前执行链路

```text
Claude skill
→ .claude/skills/pandoc_to_markdown/pandoc_to_markdown_skill.py
→ src/pandoc_to_markdown/cli.py
→ routing / converters / installer / doctor
```

## 直接运行

```bash
python3 .claude/skills/pandoc_to_markdown/pandoc_to_markdown_skill.py --help
```

单文件示例：

```bash
python3 .claude/skills/pandoc_to_markdown/pandoc_to_markdown_skill.py \
  convert \
  --mode single \
  --paths "/path/to/book.epub" \
  --overwrite \
  --json
```

安装环境：

```bash
python3 .claude/skills/pandoc_to_markdown/pandoc_to_markdown_skill.py \
  install \
  --python /opt/homebrew/bin/python3.12 \
  --json
```

自检环境：

```bash
python3 .claude/skills/pandoc_to_markdown/pandoc_to_markdown_skill.py doctor --json
```

## 说明

- 优先使用项目自己的 `.venvs/core` 运行统一 CLI。
- 如果 `.venvs/core` 还没准备好，会退回当前 `python3` 执行入口。
- PDF 转换仍然由统一 CLI 分流到 Marker 或 MinerU，对应可执行文件来自项目托管环境。
