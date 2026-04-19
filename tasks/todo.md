# todo

## 本轮目标：MinerU 模型下载链路

- [x] 在 `installer.py` 中新增统一的 MinerU 模型下载函数
- [x] 让 `run_install(..., preload_models=True)` 真正触发 `mineru-models-download`
- [x] 为 `cli.py install` 增加 `--preload-models` / `--model-source` / `--model-type`
- [x] 让 `scripts/download_models.py` 复用统一实现
- [x] 为 installer / CLI 增加回归测试
- [x] 更新 `README.md` 与回顾

## 本轮目标：测试与稳固

- [x] 收紧 `src/pandoc_to_markdown/doctor.py` 的健康判断
- [x] 为 `routing.py` 建立 `unittest` 回归覆盖
- [x] 为 `doctor.py` 建立 `unittest` 回归覆盖
- [x] 为 `cli.py` 建立 `unittest` 回归覆盖
- [x] 跑通 `python3 -m unittest discover -s tests -v`
- [x] 跑通 `cli.py doctor --json`
- [x] 跑通 HTML → Markdown smoke test
- [x] 跑通 skill wrapper smoke test
- [x] 如有必要同步更新 `README.md`

## 本轮目标：PDF 首次模型下载提示

- [x] 为 Marker / MinerU PDF 转换增加统一进度事件
- [x] 让 `routing.py` 在 payload 中汇总模型下载 notices
- [x] 让 `cli.py convert` 在首次模型下载时输出用户可见提示
- [x] 为 routing / CLI 增加回归测试
- [x] 同步更新 skill 文档
- [x] 跑一次真实 PDF smoke test（MinerU 成功，Marker 运行期仍有加速器错误）

## 本轮目标：下载中断后的继续提示

- [x] 为 `cli.py` 增加“下载中断后如何继续”的恢复提示
- [x] 为 `cli.py` 增加相关回归测试
- [x] 同步更新 skill 文档

## 本轮目标：Marker 崩溃排查与 CPU 回退

- [x] 为 `marker_backend.py` 增加可控命令/环境装配
- [x] 为 Marker 增加 MPS 崩溃后的自动 CPU 重试
- [x] 为 CLI 增加“正在切到 CPU 重试”的用户提示
- [x] 为 Marker retry 增加回归测试
- [x] 跑通 `python3 -m unittest discover -s tests -v`
- [x] 用真实 PDF 做一次 Marker smoke test

## 回顾

- `doctor` 现在要求托管环境存在且各环境关键 CLI 可用，避免只看目录存在导致误报健康。
- 新增 `unittest` 基线，覆盖 `routing.py`、`doctor.py`、`cli.py` 的关键行为与失败分支。
- 已把 MinerU 模型下载接入统一安装链路：`install --preload-models` 会调用托管环境内的 `mineru-models-download`，独立脚本也复用同一实现。
- `pandoc_to_markdown` 的默认输出现在统一落到项目目录下的 `outputs/`，并在 skill 的“默认输出”选项里明确标注。
- 验证通过：标准库单测、CLI doctor、CLI HTML 转换、skill wrapper doctor、skill wrapper HTML 转换。
- PDF 首次模型下载现在会在运行时发出统一事件；CLI 文本模式会先告诉用户“正在下载模型，完成后继续转换”，并把关键下载进度实时打印出来。
- `routing` payload 新增 `notices`，便于 `--json` 调用方判断本次转换是否经历了模型下载。
- 实测：同一份 PDF 用 `MinerU` 已成功输出到 `outputs/`；`Marker` 已越过安装/下载阶段，但仍可能在 MPS/torch 布局识别阶段失败。
- `Marker` 现在会在命中典型 MPS / torch / surya 崩溃时自动切到 CPU 重试，并向 CLI 文本模式发出明确提示；这份 `Economic-Index_v4_2026.01.14_g.pdf` 已由 CPU 回退成功产出到 `outputs/Economic-Index_v4_2026.01.14_g/Economic-Index_v4_2026.01.14_g.md`。
