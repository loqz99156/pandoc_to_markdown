# pandoc-to-markdown

一个把本地文档统一转换成 Markdown 的工具集，封装了 `pandoc`、`Marker` 和 `MinerU`，同时提供 CLI 和 Claude Code skill。

## 功能

- 一个 CLI 入口，统一处理安装、自检和转换
- 非 PDF 文档走 `pandoc`
- PDF 文档可选 `Marker` 或 `MinerU`
- 使用项目内 `.venvs/` 隔离不同后端依赖
- PDF 模型统一放在项目内 `.models/`：Marker 使用 `.models/marker/`，MinerU 使用 `.models/mineru/`
- 转换完成后默认做一轮 Markdown 轻量后处理
- 自带 Claude Code skill，可在 Claude 中直接调用

## 快速安装

如果你在 Claude Code 里，可以直接用自然语言让 AI 帮你安装。

例如：

- `帮我安装这个项目`
- `帮我把 pandoc-to-markdown 安装好，然后做一遍 doctor 检查`
- `用 python3.12 安装这个项目`

AI 会按项目内安装流程准备 `.venvs/core`、`.venvs/marker`、`.venvs/mineru`，并在需要时继续做自检。

## 快速使用

如果你在 Claude Code 里，最简单的方式是直接用自然语言描述你的目标。

例如：

- `把 /Users/me/Desktop/book.docx 转成 Markdown`
- `把 /Users/me/Desktop/report.pdf 转成 Markdown，输出到 /Users/me/Desktop/md-out`
- `批量转换 /Users/me/Desktop/inbox 里的 PDF 和 DOCX`
- `用 Marker 转这个 PDF`
- `用 MinerU 转这个扫描版 PDF`

也可以直接调用内置 skill：

```text
/pandoc_to_markdown
```

skill 会继续询问模式、输出方式、转换后端和路径，然后自动执行转换。

## Claude Code skill

项目内置了 `pandoc_to_markdown` skill。

注册：

```bash
python3 scripts/register_skill.py
```

注册后，Claude Code 可以直接调用：

```text
/pandoc_to_markdown
```

skill 会按交互流程让你选择模式、输出方式和转换后端，再继续收集路径并执行转换。

## 项目结构

```text
pandoc-to-markdown/
├── .claude/skills/pandoc_to_markdown/
│   ├── SKILL.md
│   └── pandoc_to_markdown_skill.py
├── install.sh
├── install.ps1
├── scripts/
│   ├── register_skill.py
│   └── setup_env.py
└── src/pandoc_to_markdown/
    ├── cli.py
    ├── bootstrap.py
    ├── config.py
    ├── doctor.py
    ├── installer.py
    ├── markdown_postprocess.py
    ├── model_metadata.py
    ├── routing.py
    └── converters/
```

## 路由方式

- 非 PDF：`pandoc`
- PDF：`Marker` 或 `MinerU`
