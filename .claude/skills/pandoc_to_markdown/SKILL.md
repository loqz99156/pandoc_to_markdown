---
name: pandoc_to_markdown
description: |
  当用户想把一个或多个本地文档转换成 Markdown 时使用这个 skill。它会通过项目内置的薄入口脚本转发到统一 CLI，再由 CLI 按输入类型路由到 pandoc、Marker 或 MinerU。
---

# pandoc_to_markdown

这是 `pandoc-to-markdown` 开源项目内置的 Claude Code skill。

## 何时使用

当用户有以下需求时，使用这个 skill：
- 转换单个本地文档为 Markdown
- 转换多个明确指定的文件为 Markdown
- 批量转换一个或多个目录中的文档
- 指定输出目录
- 选择是否覆盖已有 `.md`
- 在 PDF 输入时，在 Marker 和 MinerU 之间选择更合适的引擎

## 交互顺序

1. 如果用户还没有明确说明模式，先确认：
   - `single`：一个或多个明确文件路径
   - `batch`：一个或多个目录路径
2. 模式确认后，再确认输出方式：
   - `默认输出（项目目录下的 outputs/）`
   - `自定义输出目录`
3. 两个选择确认后，用普通文本逐个询问真实路径：
   - 总是先问输入路径
   - 如果用户选了 `自定义输出目录`，在确认输入路径后再问输出目录
4. 如果确认后的输入里包含 PDF，再额外确认 PDF 引擎：
   - `Marker`：结构较简单、数字文本为主
   - `MinerU`：中文、扫描件、复杂版面、OCR 需求更强
5. 如果首次运行触发模型下载，先明确告诉用户：正在下载模型，下载完成后会继续转换，不是卡住。
6. 如果下载中断，告诉用户：先重跑同一条转换或模型下载命令即可继续；只有反复卡在同一个 `.incomplete` 文件时，才建议删除那个 `.incomplete` 文件后重试，不要清空整个缓存。
7. 信息齐全后，调用项目内置 skill 入口：
   - `python3 .claude/skills/pandoc_to_markdown/pandoc_to_markdown_skill.py --mode single --paths <paths...>`
   - `python3 .claude/skills/pandoc_to_markdown/pandoc_to_markdown_skill.py --mode batch --paths <dirs...>`
8. 只在需要时附加参数：
   - `--exts epub,docx,html,...`
   - `--recursive`
   - `--out-dir <dir>`
   - `--overwrite`
   - `--pdf-engine marker|mineru`
   - `--to commonmark_x`
   - `--json`
7. 向用户汇报生成的 Markdown 文件，或者报告转换失败原因。

## 执行链路

```text
Claude skill
→ .claude/skills/pandoc_to_markdown/pandoc_to_markdown_skill.py
→ src/pandoc_to_markdown/cli.py
→ routing / converters / installer / doctor
```

## 默认值

- 默认目标格式：`commonmark_x`
- 默认批量扩展名：`epub,docx,pdf,html,htm,txt,md,markdown,odt,rtf`
- 默认输出目录：不传 `--out-dir` 时输出到项目目录下的 `outputs/`
- 默认行为：不覆盖已有文件，除非传入 `--overwrite`
- 默认批量遍历：非递归，除非传入 `--recursive`

## 注意事项

- skill 入口本身不再实现转换逻辑，只负责把参数转发给项目 CLI。
- 安装、自检、依赖隔离、后端路由都以 `src/pandoc_to_markdown/` 为准。
- 路径提问保持简短，先问输入路径，再在需要时问输出目录。
