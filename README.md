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

### macOS / Linux

```bash
bash install.sh
```

### Windows

```powershell
./install.ps1
```

如果你想显式指定 Python：

```bash
PYTHONPATH="$PWD/src" python3 scripts/setup_env.py --python /path/to/python3.12
```

安装完成后，项目会准备这些环境：

- `.venvs/core`
- `.venvs/marker`
- `.venvs/mineru`

## 快速使用

### 1. 自检

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py doctor --json
```

### 2. 转换单个非 PDF 文件

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py \
  convert \
  --mode single \
  --paths "/path/to/book.html" \
  --overwrite \
  --json
```

### 3. 转换单个 PDF 文件

使用 Marker：

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py \
  convert \
  --mode single \
  --paths "/path/to/book.pdf" \
  --pdf-engine marker \
  --overwrite \
  --json
```

如果你希望 Marker 从一开始固定走 CPU：

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py \
  convert \
  --mode single \
  --paths "/path/to/book.pdf" \
  --pdf-engine marker \
  --marker-mode cpu \
  --overwrite \
  --json
```

使用 MinerU：

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py \
  convert \
  --mode single \
  --paths "/path/to/book.pdf" \
  --pdf-engine mineru \
  --overwrite \
  --json
```

### 4. 批量转换目录

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py \
  convert \
  --mode batch \
  --paths "/path/to/inbox" \
  --exts "epub,docx,html,pdf" \
  --recursive \
  --out-dir "/tmp/md-out" \
  --overwrite \
  --json
```

### 5. 默认行为

- 默认输出到项目目录下的 `outputs/`
- 默认目标格式是 `commonmark_x`
- 默认不覆盖已有文件，除非显式传 `--overwrite`
- 首次真正触发 PDF 转换时，相关模型会自动下载到项目内 `.models/`

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
