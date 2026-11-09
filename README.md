# Trace Lens · 迹线透镜

![Trace Lens logo](assets/logo.svg)

面向研究 CSV 的离线数值检查工具。把一组时间序列整理为可追溯的统计、独立 SVG 图，以及无需服务器、网络、JavaScript 或第三方库即可打开的 HTML 报告。

## 快速开始

需要 **Python 3.10+**。在本仓库根目录直接运行，无需 pip 安装：

```sh
python -m trace_lens --help
python -m trace_lens sample examples/my-sample.csv
python -m trace_lens report examples/my-sample.csv --x time_s --out output
```

在浏览器中打开 `output/report.html`。同目录还有 `stats.json`、`trace-001.svg`、`trace-002.svg`。HTML 已内嵌全部图，不依赖 SVG 文件位置。

仓库提供固定样例 `examples/signals.csv` 和完整报告 `examples/demo-report/report.html`，可直接查看。输出目录必须不存在；样例命令也只创建新文件，避免覆盖研究结果。重复运行时更换 `--out` 或样例路径。

## 常见用法

选择特定测量列，并减去时间区间内的均值：

```sh
python -m trace_lens report examples/signals.csv --x time_s --columns sensor_a sensor_b --baseline 0 1 --out corrected
python -m trace_lens report examples/signals.csv --x time_s --columns sensor_a --out sensor-a-report
python -m unittest discover -s tests -v
```

`--baseline START END` 使用闭区间 [START, END]；每个信号分别计算有效样本的均值，随后从该列所有有效值中减去该均值。区间没有有效样本、非有限区间或相减溢出会报错，不会静默生成错误结果。JSON 保存基线区间和各列减去的值。原文件不改动。

## CSV 与统计约定

- UTF-8（可有 BOM）、逗号分隔、标准 CSV 引号，第一行是唯一且非空的列名。
- `--x` 是数值时间/横坐标。日期字符串须先转换为秒等数值；不猜测日期、单位或时区。
- 不指定 `--columns` 时，除 x 外所有列均作为数值信号；文本列会产生 invalid 诊断。
- 空白单元格为 missing，非数值为 invalid，NaN/Inf/溢出数字为 nonfinite。stderr 和 JSON 同时记录行号、列名、原因，不记录单元格原文。
- x 无效时整行排除统计与绘图；单个信号无效时仅排除该信号。图线在无效样本处断开，不插值。
- 行号为 CSV 记录结束的物理行号，带多行引号字段时可能跨行。
- 提供 count、excluded、min、max、mean、std、rms；std 是总体标准差（ddof=0），RMS 是相对于零的均方根。基线启用后统计使用校正后的值。
- 没有可用点的列输出 count=0、数值统计为 JSON null；不输出 NaN。
- 重复列名、不齐整的行、空文件、未知列名会报错。空行也是不齐整的行。
- x 的原始顺序保留。递减时给出 unsorted_x 警告；不会擅自排序。相同 x 允许存在。

## 结构

```text
trace_lens/core.py       CSV 校验、诊断、稳定缩放统计、基线校正
trace_lens/report.py     转义、安全文件名、独立 SVG 和 HTML/JSON 输出
trace_lens/__main__.py   argparse 命令行与退出码
assets/logo.svg         原创透镜/波形品牌图形
examples/               固定样例及可直接打开的报告
 tests/test_trace_lens.py  标准库 unittest 与子进程 CLI 测试
```

每个 SVG 使用序号命名，列名不会作为路径。所有插入 HTML/SVG 的标签与文件名都经过 HTML 转义。报告仅作本地文件输出，不上传数据。退出码 0 表示成功，2 表示参数、输入或输出失败；有效数据存在时，missing 等诊断为警告，不改变退出码。

## 限制与边界

这是轻量原型，不替代专业信号处理平台。仅支持 CSV；没有 FFT、滤波、重采样、交互缩放、数据编辑或统计推断。使用二进制双精度浮点；统计通过缩放降低中间值溢出风险，但不提供任意精度保证。每个点均绘制、全部数据和诊断保存在内存，建议用于小到中型文件（数万行以内），不是流式大数据工具。不同量纲分图展示，轴仅标示范围而不是完整刻度。

创建输出目录后若磁盘写入失败，可能留下部分文件；错误会返回 2，请检查并删除不完整目录后重试。报告会显示输入路径及列名，如需分享请检查是否包含私人信息。绘图生成结构经过自动测试；未声称做过跨浏览器视觉验收。

## 来源与独立实现

Trace Lens 围绕通用 CSV/时间序列分析需求独立编写。没有复制其他项目的实现、界面、资源或文档。品牌、布局、示例数据、代码和说明均为本项目新建；不存在运行时外部资源。

## 开发验证

```sh
python -m unittest discover -s tests -v
python -m compileall -q trace_lens tests
```

测试覆盖数值统计、空/常量/极端数据、缺失/非法/非有限值、横坐标排除、基线边界与溢出、CSV 结构、选择校验、无序横坐标、转义、断线与单点图、JSON、禁止覆盖以及命令行端到端。Python 代码仅使用标准库。
