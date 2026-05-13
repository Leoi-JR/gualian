# RuleKit v2.0

一个专业的关键词规则验证、模式转换和智能匹配工具集，支持多进程加速计算，适用于大规模文本数据的规则驱动批量分类标注。

> **数据说明**：项目中的示例数据均为虚构生成的虚拟数据，不涉及真实企业信息或个人数据。

## 🖥️ 可视化介绍

打开 [项目介绍页面](https://leoi-jr.github.io/rulekit/) 即可在浏览器中查看项目的交互式介绍页面，快速了解功能特性、处理流程和性能优势。

## 🚀 功能特色

### 核心功能
- **关键词规则验证器**：支持10种关键词组合规则模式，自动验证Excel文件中的关键词格式
- **关键词模式转换器**：将关键词规则转换为正则表达式匹配格式，支持有序匹配和无序匹配
- **智能关键词匹配器**：基于转换后的关键词规则，对文本数据进行智能匹配和批量标记
- **匹配结果高亮导出**：将匹配结果导出为高亮标记的Excel文件，便于人工审查

### 性能特性
- **多进程并行处理**：支持ProcessPoolExecutor多进程批量处理大量Parquet文件，自动根据CPU核心数分配工作进程
- **多级批处理策略**：根据数据量智能选择traditional（<5000操作）、vectorized（<50000操作）、chunked（>=50000操作）三种匹配策略
- **线程级并行编译**：使用ThreadPoolExecutor并行编译关键词正则表达式
- **向量化匹配**：使用pandas的向量化字符串操作进行批量正则匹配，大数据量下性能大幅提升
- **三阶段短路求值**：Like→Must→Unlike三步匹配流程，Like阶段失败即跳过后续阶段，显著减少不必要的正则操作

## 📁 项目结构

```
v2.0/
├── cli/                          # CLI工具模块
│   ├── __init__.py
│   ├── keyword_rules_validator_cli.py    # 关键词规则验证CLI
│   ├── keyword_converter_cli.py          # 关键词转换CLI
│   ├── keyword_matcher_cli.py            # 智能关键词匹配CLI
│   └── highlight_results_cli.py          # 匹配结果高亮导出CLI
├── core/                         # 核心业务逻辑
│   ├── __init__.py
│   ├── pattern_transformer.py           # 模式转换器
│   ├── keyword_compiler.py             # 关键词编译器
│   ├── filter_logic.py                 # 筛选逻辑模块
│   ├── matching_engine.py              # 匹配引擎模块
│   ├── result_processor.py             # 结果处理模块
│   ├── keyword_matcher.py              # 主控制模块
│   ├── text_preprocessor.py            # 文本预处理工具
│   ├── batch_matcher.py                # 批处理匹配器
│   └── parquet_manager.py              # Parquet文件管理器
├── tests/                        # 单元测试（88个测试用例）
│   ├── __init__.py
│   ├── test_keyword_matching.py
│   ├── test_text_preprocessor.py
│   ├── test_batch_matcher.py
│   ├── test_parquet_manager.py
│   └── test_runner.py
├── scripts/                      # 辅助脚本
│   └── generate_sample_data.py   # 生成虚构示例数据
├── config/                       # 配置管理
│   ├── __init__.py
│   ├── config.example.json       # 配置示例文件
│   └── manager.py                # 配置管理器
├── utils/                        # 工具模块
│   └── progress_bar.py           # 进度条工具
├── main.py                       # 主程序入口
├── requirements.txt              # 项目依赖
└── README.md                     # 项目说明
```

## 🛠️ 安装使用

### 环境要求
- Python 3.8+
- pandas >= 1.3.0
- openpyxl >= 3.0.0
- tqdm >= 4.60.0
- loguru >= 0.6.0

### 安装依赖
```bash
pip install -r requirements.txt
```

### 快速开始
```bash
# 生成示例数据（首次使用）
python scripts/generate_sample_data.py

# 启动主菜单
python main.py

# 运行所有单元测试
python tests/test_runner.py

# 详细模式运行单元测试
python tests/test_runner.py --verbose
```

## 📋 功能详解

### 1. 关键词规则验证器

验证Excel文件中的关键词是否符合预定义的规则模式：

#### 支持的规则模式
1. **规则1**: `A&B` - 两个关键词用&连接
2. **规则2**: `A&&B` - 两个关键词用&&连接
3. **规则3**: `A&(B,C,D)` - 单个关键词与括号内多个关键词组合
4. **规则4**: `(B,C,D)&A` - 括号内多个关键词与单个关键词组合
5. **规则5**: `A&&(B,C,D)` - 使用&&的单个与组合
6. **规则6**: `(B,C,D)&&A` - 使用&&的组合与单个
7. **规则7**: `(A,B)&(C,D)` - 两组括号关键词的&组合
8. **规则8**: `(A,B)&&(C,D)` - 两组括号关键词的&&组合
9. **规则9**: `A.{0,X}B` - 正则表达式距离限制模式
10. **规则10**: `A` - 单个关键词

### 2. 关键词模式转换器

将关键词规则转换为结构化的匹配格式：

#### 转换格式说明
- **格式0**: `[0, "关键词"]` - 单个关键词直接匹配
- **格式1**: `[1, ["左关键词"], ["右关键词"], 最小间隔, 最大间隔]` - 有序匹配
- **格式2**: `[2, ["关键词组1"], ["关键词组2"], 最小间隔, 最大间隔]` - 无序匹配

#### 支持的输入模式
- `汽车&保险` → `[1, ["汽车"], ["保险"], 0, 200]`
- `汽车&&保险` → `[2, ["汽车"], ["保险"], 0, 200]`
- `车载.{0,5}充电机` → `[1, ["车载"], ["充电机"], 0, 5]`

### 3. 智能关键词匹配器

基于转换后的关键词规则表，对文本数据进行智能匹配和批量标记：

#### 匹配逻辑
1. **类型筛选**：基于 type_filter 和 category_code 进行前置过滤
2. **字段范围筛选**：基于 field_scope 控制参与匹配的文本列
3. **Like关键词匹配**：检查是否存在，记录匹配信息
4. **Must关键词匹配**：检查是否存在，记录匹配信息
5. **Unlike关键词匹配**：检查是否存在，如存在则匹配失败

#### 多进程批处理
当启用性能优化时（`enable_performance_optimization: true`），系统会根据CPU核心数自动分配工作进程：
- `max_workers: -1` 表示使用CPU核心数-1个进程
- 每个工作进程独立处理一个Parquet文件，互不干扰
- 支持跳过已处理文件（`enable_skip_processed: true`）
- 提供实时进度条显示多进程处理状态

#### 输出
- **匹配结果文件**：CSV/Excel格式，包含所有匹配成功的记录
- **摘要报告文件**：JSON格式，提供详细的匹配统计信息

### 4. 匹配结果高亮导出

将匹配结果导出为高亮标记的Excel文件，便于人工审查：

- 成功匹配的记录用绿色高亮标记
- 失败匹配的记录用红色高亮标记
- 支持批量处理，可配置每批处理数量

## 🧪 测试框架

### 单元测试
项目包含88个单元测试用例，覆盖所有核心功能模块：

```bash
# 运行所有测试
python tests/test_runner.py

# 运行特定测试模块
python -m pytest tests/test_keyword_matching.py -v

# 生成覆盖率报告
python tests/test_runner.py --coverage
```

### 测试覆盖范围
- 关键词编译器测试（KeywordCompiler）
- 筛选逻辑测试（FilterLogic）
- 匹配引擎测试（MatchingEngine）
- 结果处理器测试（ResultProcessor）
- 关键词匹配器测试（KeywordMatcher）
- **核心链路集成测试**（TestCoreMatchingPipeline）：type_filter 筛选、field_scope 列排除、unlike 拦截、多规则匹配等端到端场景
- 文本预处理器测试（TextPreprocessor）
- 批处理匹配器测试（BatchMatcher）
- Parquet管理器测试（ParquetManager）

## ⚙️ 核心配置

主要配置项在 `config.example.json` 中定义。复制为 `config.json` 后按需修改：

| 配置项 | 说明 |
|--------|------|
| `keyword_matching.enable_performance_optimization` | 是否启用性能优化（多进程等） |
| `keyword_matching.max_workers` | 最大工作进程数（-1=CPU-1） |
| `keyword_matching.parquet_data_source` | Parquet数据源文件夹配置 |
| `keyword_matching.input_table_columns` | 输入数据表的列定义 |
| `keyword_matching.matching_rules` | 匹配规则配置 |

## 🔮 未来规划

- [ ] Web界面支持
- [ ] 更多文件格式支持
- [ ] API服务模式

---

**RuleKit** - 让关键词规则处理更简单、更可靠！
