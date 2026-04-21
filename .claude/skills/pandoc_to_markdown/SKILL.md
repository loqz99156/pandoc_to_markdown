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

1. 如果用户还没有明确说明模式、输出方式或转换后端，第一个 `AskUserQuestion` 直接同时确认这三项：
   - 模式：`single` / `batch`
   - 输出方式：
     - 无历史时：`默认输出（项目目录下的 outputs/）` / `自定义输出目录`
     - 有历史时：`默认输出（项目目录下的 outputs/）` / `上次使用目录（显示上次成功的自定义输出路径）` / `自定义输出目录`
   - 转换后端：
     - `pandoc`：适合本来就有可复制文本和清晰样式的文档，比如 DOCX、EPUB、HTML、Markdown、普通导出的 ODT/RTF；如果你主要关心标题、段落、列表、链接这些现成结构，通常最稳
     - `Marker`：适合数字版 PDF、论文、报告、合同、带表格/公式/表单的文档；如果你希望尽量保住原文档结构，并且后面可能还想做表单抽取、结构化提取或细调转换参数，优先选它
     - `MinerU`：适合中文 PDF、扫描件、截图型文档、手写内容、双栏/多栏排版、宣传册/资料册这类复杂版面；如果你最在意 OCR 能力、阅读顺序恢复和复杂页面理解，优先选它
2. 第一轮选择确认后，用普通文本逐个询问真实路径：
   - 总是先问输入路径
   - 如果用户选了 `自定义输出目录`，在确认输入路径后再问输出目录
   - 如果用户选了 `上次使用目录`，不要再追问输出目录，直接复用上次成功的自定义输出路径
3. 后端选择后的校验规则：
   - 如果用户选了 `pandoc`，但输入里包含 PDF，再额外追问一次，让用户改选 `Marker` 或 `MinerU`
   - 如果用户选了 `Marker` 或 `MinerU`，但输入全是非 PDF，不报错；明确说明 PDF 后端不会生效，本次会按实际输入回到 pandoc 路由
4. 如果首次运行触发模型下载，先明确告诉用户：正在下载模型，下载完成后会继续转换，不是卡住；并显示该引擎对应模型的固定下载链接和大小。
5. 如果下载中断，告诉用户：先重跑同一条转换命令即可继续。只有反复卡在同一个 `.incomplete` 文件时，才建议删除那个 `.incomplete` 文件后重试，不要清空整个缓存。
6. 信息齐全后，调用项目内置 skill 入口：
   - `python3 .claude/skills/pandoc_to_markdown/pandoc_to_markdown_skill.py convert --mode single --paths <paths...>`
   - `python3 .claude/skills/pandoc_to_markdown/pandoc_to_markdown_skill.py convert --mode batch --paths <dirs...>`
7. 只在需要时附加参数：
   - `--exts epub,docx,html,...`
   - `--recursive`
   - `--out-dir <dir>`
   - `--overwrite`
   - `--pdf-engine marker|mineru`
   - `--marker-mode auto|cpu`
   - `--to commonmark_x`
   - `--json`
8. 转换成功后默认继续自动做一轮 Markdown 轻量后处理，不再额外询问用户；最终仍只输出 `.md` 文件。
9. 向用户汇报生成的 Markdown 文件，或者报告转换失败原因。

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
- 如果之前有一次成功的自定义输出目录，后续运行 skill 时会把它作为“上次使用目录”选项展示出来
- 默认转换成功后会自动继续做一轮 Markdown 轻量后处理
- 默认行为：不覆盖已有文件，除非传入 `--overwrite`
- 默认批量遍历：非递归，除非传入 `--recursive`

## 注意事项

- skill 入口本身不再实现转换逻辑，只负责把参数转发给项目 CLI。
- 安装、自检、依赖隔离、后端路由都以 `src/pandoc_to_markdown/` 为准。
- 进入这个 skill 后，如果当前步骤是用 `AskUserQuestion` 收集模式、输出方式或转换后端，直接发起 `AskUserQuestion`，不要先输出解释性的过渡文字。
- 如果第一个用于确认模式、输出方式或转换后端的 `AskUserQuestion` 被中断、拒绝或未完成，重新调用这个 skill 时必须从第 1 步重新开始，不要沿用上一轮未完成交互的隐含状态。
- 路径提问保持简短，先问输入路径，再在需要时问输出目录。
