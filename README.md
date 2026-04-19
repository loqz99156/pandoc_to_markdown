# pandoc-to-markdown

一个面向本地文档转换的 Markdown 工具集，统一封装了 `pandoc`、`Marker` 和 `MinerU`，并提供可直接使用的 CLI、托管运行环境和 Claude Code skill。

## 核心能力

- 单一 CLI 入口，统一处理安装、自检和转换
- 非 PDF 输入走 `pandoc`
- PDF 输入按场景选择 `Marker` 或 `MinerU`
- 使用项目内 `.venvs/` 隔离不同后端依赖
- 自带 Claude Code skill 薄入口，便于在 Claude 中直接调用

## 快速开始

安装：

```bash
bash install.sh
```

自检：

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py doctor --json
```

单文件转换：

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py \
  convert \
  --mode single \
  --paths "/path/to/book.html" \
  --overwrite \
  --json
```

当前路由规则：
- 非 PDF：走 `pandoc`
- PDF：按用户选择走 `Marker` 或 `MinerU`

## 项目结构

```text
pandoc-to-markdown/
├── .claude/skills/pandoc_to_markdown/
│   ├── SKILL.md
│   ├── README.md
│   └── pandoc_to_markdown_skill.py
├── install.sh
├── install.ps1
├── pyproject.toml
├── scripts/
│   ├── download_models.py
│   ├── register_skill.py
│   └── setup_env.py
└── src/pandoc_to_markdown/
    ├── cli.py
    ├── bootstrap.py
    ├── config.py
    ├── doctor.py
    ├── installer.py
    ├── routing.py
    └── converters/
```

## 执行流程

```text
安装
→ 创建 .venvs/core、.venvs/marker、.venvs/mineru
→ doctor 检查环境
→ Claude skill / CLI 接收参数
→ routing 判断输入类型
→ pandoc / Marker / MinerU 执行转换
→ 输出 Markdown 或明确错误
```

这里的安装是**单次安装、内部隔离环境**：
- `core`：`pypandoc` 与 pandoc 发现/下载
- `marker`：`marker-pdf`
- `mineru`：`mineru[all]`

这样做是为了避免 `marker-pdf` 和 `mineru[all]` 在同一个 venv 里的依赖冲突。

## 安装

### macOS / Linux

```bash
bash install.sh
```

如果你要显式指定 Python：

```bash
PYTHONPATH="$PWD/src" python3 scripts/setup_env.py --python /path/to/python3.12
```

### Windows

```powershell
./install.ps1
```

## 自检

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py doctor --json
```

`doctor` 会检查：
- 托管环境目录 `.venvs/`
- `core` / `marker` / `mineru` 三个环境是否存在
- `pandoc` / `marker_single` / `mineru` / `mineru-models-download`
- MinerU 配置文件与模型来源
- 磁盘剩余空间

说明：
- 如果你是用系统 `python3` 启动 `doctor`，而这个 Python 恰好是 3.14，也不会直接判定项目坏掉。
- 只要 `.venvs/` 里的托管环境健康，`doctor` 仍会返回 `ok: true`，同时给出 warning。

## CLI 用法

先看帮助：

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py --help
```

### 安装入口

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py install --python /path/to/python3.12 --json
```

如需在安装完成后立即下载 MinerU 模型：

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py install \
  --python /path/to/python3.12 \
  --preload-models \
  --model-source huggingface \
  --model-type all \
  --json
```

### 自检入口

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py doctor --json
```

### 非 PDF 转换

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py \
  convert \
  --mode single \
  --paths "/path/to/book.html" \
  --overwrite \
  --json
```

### 批量转换

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

### PDF 转换

Marker：

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py \
  convert \
  --mode single \
  --paths "/path/to/simple.pdf" \
  --pdf-engine marker \
  --overwrite \
  --json
```

MinerU：

```bash
PYTHONPATH="$PWD/src" python3 src/pandoc_to_markdown/cli.py \
  convert \
  --mode single \
  --paths "/path/to/complex.pdf" \
  --pdf-engine mineru \
  --overwrite \
  --json
```

## Claude Code skill

项目内自带 skill 薄入口：

```text
.claude/skills/pandoc_to_markdown/
```

注册到 Claude Code：

```bash
python3 scripts/register_skill.py
```

注册后会写到：

```text
~/.claude/skills/pandoc_to_markdown/
```

直接执行 skill wrapper：

```bash
python3 ~/.claude/skills/pandoc_to_markdown/pandoc_to_markdown_skill.py --help
```

通过 skill wrapper 转换：

```bash
python3 ~/.claude/skills/pandoc_to_markdown/pandoc_to_markdown_skill.py \
  convert \
  --mode single \
  --paths "/path/to/book.html" \
  --overwrite \
  --json
```

## Markdown 输出默认值

- 目标格式：`commonmark_x`
- 标题风格：ATX（`#`）
- 换行策略：`wrap=none`
- 链接风格：`reference-links`
- 默认输出目录：项目目录下的 `outputs/`
- 默认不覆盖已有文件，除非显式传 `--overwrite`

## Python 与依赖说明

- MinerU 需要 Python `3.10-3.13`
- 安装器会优先寻找可用的 `python3.13` / `python3.12` / `python3.11` / `python3.10`
- 建议显式传入一个受支持版本的 Python，例如 `python3.12`

## 验证范围

当前仓库已覆盖：
- 安装入口与托管环境创建
- `doctor` 健康检查
- `python3 -m unittest discover -s tests -v`
- 通过 CLI 的 HTML → Markdown smoke test
- 通过注册后 skill wrapper 的 `doctor` 与 HTML → Markdown smoke test

另外，`doctor` 的健康定义现在是：
- `.venvs/` 与 `core` / `marker` / `mineru` 三个托管环境都存在
- `core` 环境能提供 `pandoc`
- `marker` 环境能提供 `marker_single`
- `mineru` 环境能提供 `mineru` 与 `mineru-models-download`
- 如果当前启动用的 Python 不在 MinerU 支持范围内，但托管环境完整，`doctor` 仍会返回 `ok: true`，并附带 warning

## 当前限制

- `install` 默认不会自动下载 MinerU 模型；只有显式传入 `--preload-models` 才会触发下载
- 也可以单独执行下载脚本：

```bash
PYTHONPATH="$PWD/src" python3 scripts/download_models.py --source huggingface --model-type all
```

- PDF 成功转换依赖本机是否已具备对应模型、配置与运行条件
- 如果当前机器尚未准备好模型，CLI 会返回真实错误信息，而不是假装转换成功
