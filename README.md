# Quantitative ETF Analyst（量化 ETF 分析师）

一套面向 **A 股 ETF 市场** 的量化交易规则分析与板块扫描工具集。它既能对量化交易规则文档（如算法说明书、策略说明书）进行结构化拆解并生成标准化 PDF 分析报告，又能基于实时市场数据对全市场 ETF 板块进行扫描、筛选与评分。

> 核心理念：**规则可解析、参数可量化、风险可识别、报告可交付。**

---

## ✨ 功能特性

- **七维规则分析框架**：从文件基本信息、策略概述、逻辑流程、关键参数、风险点、有效性评估、优化建议七个维度对量化规则文件进行结构化拆解。
- **实时市场数据获取**：基于 [akshare](https://akshare.akfamily.xyz/) 接入新浪财经 / 同花顺 / 东方财富等多源数据，含 ETF K 线、最新净值、财经新闻、份额规模等。
- **全市场板块扫描**：自动扫描全市场 1600+ 只 ETF，按 40 个板块分类，依据 V9.3 规则（F90 分类器 / F73 红线）筛选有交易机会的板块。
- **双模型评分体系**：
  - `V9.3-ST` 超短线量化交易模型（次日清仓）
  - `V9.3-LT` 中长期量化投资模型（3-12 个月持有）
- **标准化 PDF 报告**：金融级专业排版，含封面、流程图、参数表格、风险清单、KPI 卡片、评分进度条等可视化元素。
- **数据缓存机制**：1 小时 TTL 文件缓存，避免重复请求，提升响应速度。

---

## 📁 项目结构

```
.
├── Trading Rules/                         # 量化交易规则说明书
│   ├── V9.3-LT 中长期量化投资模型 完整算法说明书.md
│   └── V9.3-ST 超短线量化交易模型 完整算法逻辑说明书.md
│
├── quant-rule-analyzer/                   # 核心技能模块
│   ├── SKILL.md                           # 技能定义与七维分析框架
│   ├── analysis_schema.json               # 分析结果 JSON Schema
│   ├── data_fetcher.py                    # 市场数据获取模块
│   ├── sector_scanner.py                  # 板块全盘扫描模块
│   ├── generate_report.py                 # 规则分析 PDF 报告生成器
│   ├── generate_sector_report.py          # 板块分析 PDF 报告生成器
│   ├── generate_trend_report.py           # 走势分析 PDF 报告生成器
│   ├── report_styles.py                   # 共享样式模块（色彩/字体/组件）
│   └── reports/                           # 生成的报告输出目录
│       └── .cache/                        # 数据缓存（已 gitignore）
│
├── .gitignore
└── README.md
```

---

## 🔧 环境依赖

- **Python** ≥ 3.9
- 核心第三方库：

| 库 | 用途 |
|----|------|
| `akshare` | A 股 / ETF / 财经新闻数据获取 |
| `reportlab` | PDF 报告生成 |
| `matplotlib` | 图表与流程图绘制 |
| `pandas` / `numpy` | 数据处理与数值计算 |

安装依赖：

```bash
pip install akshare reportlab matplotlib pandas numpy
```

---

## 🚀 快速开始

### 1. 规则文件分析模式

分析 `Trading Rules/` 下的量化模型说明书，生成 PDF 分析报告：

```bash
# 步骤1：按七维框架提取信息，生成 analysis JSON
# 步骤2：根据 JSON 生成 PDF
python "quant-rule-analyzer/generate_report.py" \
    "quant-rule-analyzer/reports/V9.3-ST_analysis.json" \
    "quant-rule-analyzer/reports/V9.3-ST_分析报告.pdf"
```

### 2. 实时数据分析模式

获取单只 ETF 的实时行情与技术指标：

```bash
python "quant-rule-analyzer/data_fetcher.py" etf 159770
```

获取最新财经新闻：

```bash
python "quant-rule-analyzer/data_fetcher.py" news 50
```

### 3. 板块全盘扫描模式

扫描全市场 ETF，自动筛选有交易机会的板块并生成报告：

```bash
# 全盘扫描，自动筛选（默认排除追涨区）
python "quant-rule-analyzer/sector_scanner.py" scan --report

# 全盘扫描，显示所有板块
python "quant-rule-analyzer/sector_scanner.py" scan --all --report

# 限制最大板块数
python "quant-rule-analyzer/sector_scanner.py" scan --max 10 --report

# 列出所有可扫描板块
python "quant-rule-analyzer/sector_scanner.py" list
```

分析指定板块：

```bash
python "quant-rule-analyzer/sector_scanner.py" analyze 机器人 创新药 白酒 --report
```

---

## 📐 七维分析框架

| 维度 | 字段 | 说明 |
|------|------|------|
| 1 | `metadata` | 文件基本信息（模型名称、版本、类型、持有周期、目标收益等） |
| 2 | `strategy_overview` | 核心策略概述（定位、核心因子及权重、评分公式、决策阈值、纪律） |
| 3 | `logic_flow` | 规则逻辑流程图（按时间序列或逻辑链路提取的步骤数组） |
| 4 | `key_parameters` | 关键参数说明（仓位/风控/评分/时间/筛选五类参数） |
| 5 | `risk_analysis` | 潜在风险点分析（参数刚性、数据依赖、逻辑缺口、执行、集中度、黑天鹅、过拟合） |
| 6 | `effectiveness_evaluation` | 规则有效性评估（优势、不足、回测状态、适应性、完整性评分） |
| 7 | `optimization_suggestions` | 优化建议（参数优化、逻辑补强、风控增强、执行优化、可扩展性） |

分析结果 JSON 结构定义见 [analysis_schema.json](quant-rule-analyzer/analysis_schema.json)。

---

## 📊 数据源说明

| 数据源 | 接口 | 用途 | 稳定性 |
|--------|------|------|--------|
| 新浪财经 | `money.finance.sina.com.cn` | ETF 历史 K 线 | 高 |
| 同花顺 | `fund_etf_spot_ths` | ETF 最新净值 | 高 |
| 东方财富 | `stock_info_global_em` | 全球财经新闻 | 中 |
| 东方财富 | `fund_etf_hist_em` | ETF K 线（备用） | 中（有反爬） |
| 交易所 | `fund_etf_scale_sse/szse` | ETF 份额规模 | 高 |

---

## 📄 PDF 报告输出规范

生成的 PDF 报告包含以下固定章节顺序：

1. **封面页** — 报告标题、模型名称、分析日期、分析师（AI）
2. **文件基本信息** — 元数据表格
3. **核心交易策略概述** — 定位、因子体系、评分公式、决策阈值
4. **规则逻辑流程图** — 可视化流程图 + 步骤说明表
5. **关键参数说明** — 分类参数表格（仓位/风控/评分/时间/筛选）
6. **潜在风险点分析** — 风险清单表格，含等级标识
7. **规则有效性评估** — 优势/不足分栏 + 完整性评分
8. **优化建议** — 建议清单表格，含优先级
9. **免责声明** — 标准风险提示

---

## 🎨 报告样式系统

`report_styles.py` 提供现代化金融级报告样式，采用 **深海蓝 × 珊瑚金 × 青瓷色** 三色体系：

- 卡片式信息布局，层次分明
- 统一的色彩、字体层级、页眉页脚
- 内置 KPI 卡片、状态徽章、评分进度条、风险等级标识等可视化组件
- 三个报告生成器（规则 / 板块 / 走势）共享同一套样式，保证视觉一致性

---

## ⚠️ 免责声明

本项目仅用于 **量化策略研究与教育目的**，不构成任何投资建议。市场有风险，投资需谨慎。基于历史数据回测的策略在未来市场中可能失效，请使用者自行承担相关风险。

---

## 📜 License

本项目仅供学习与内部研究使用。
