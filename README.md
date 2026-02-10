# DeepIntoPep

本项目旨在从 PEP（Python Enhancement Proposals）中汲取素材，进行归类、对比、拓展，以期帮助开发人员从底层构建起含技巧、领域等维度的知识体系。

## 📚 项目简介

PEP 是 Python 社区中用于提议和讨论新特性、设计决策和最佳实践的正式文档。本项目致力于：

- 📖 深入解析重要的 PEP 文档
- 🔍 分类整理不同领域的 PEP 内容
- 🚀 提供实用的代码示例和最佳实践
- 📝 构建系统化的 Python 知识体系

## 📂 项目结构

```
DeepIntoPep/
├── README.md              # 项目说明文档
├── LICENSE                # Apache 2.0 开源许可证
├── docs/                  # 文档目录
│   └── DeepIntoPep.pdf   # 生成的 PDF 文档
└── scripts/               # 工具脚本
    └── build_pdf.py      # Markdown 转 PDF 工具
```

## 🚀 快速开始

### 生成 PDF 文档

本项目提供了一个便捷的脚本，可以将 Markdown 文档转换为 PDF 格式：

```bash
# 使用默认配置（转换 README.md 和 LICENSE）
python scripts/build_pdf.py

# 指定输入文件
python scripts/build_pdf.py --input README.md --input other.md

# 自定义输出路径和标题
python scripts/build_pdf.py --output output/my.pdf --title "我的文档"
```

### 依赖安装

如果需要生成 PDF，请先安装依赖：

```bash
pip install reportlab
```

## 📖 内容目录

### PEP 8（Python 代码风格指南）简介

PEP 8 是 Python 官方推荐的代码风格规范，目标是让代码在团队协作中更**一致**、更**可读**、更**易维护**。它不改变语义，但能显著降低"看懂代码"的成本。

#### 核心原则

- **可读性优先**：优先写"容易被人读懂"的代码，而不是"看起来很聪明"的代码。
- **一致性优先**：同一项目内保持一致（哪怕与某条规则略有偏离），通常比"严格但混乱"更重要。

#### 常见规则速览

- **缩进**：使用 4 个空格；不要使用 Tab（或确保编辑器将 Tab 转为空格）。
- **行长度**：传统建议每行不超过 79 字符（注释/文档字符串常见上限 72）；现代工程中也常见 88/100 等团队约定。
- **空行**：顶层函数/类之间通常空两行；类内方法之间空一行。
- **导入**：
  - 标准库、第三方库、本地应用导入分组并用空行分隔；
  - 尽量在文件顶部导入；
  - 避免 `from x import *`。
- **命名**（常见约定）：
  - `snake_case`：函数、变量、模块；
  - `CapWords`（PascalCase）：类；
  - `UPPER_CASE`：常量；
  - 受保护成员以 `_leading_underscore` 标识。
- **空白符**：避免多余空格；运算符两侧通常留空格；括号内侧不留空格。
- **注释与文档**：注释说明"为什么这么做"；公共 API 建议写 docstring（可参考 PEP 257 的 docstring 约定）。

#### 落地建议（自动化优先）

风格规范最容易在"靠自觉"时失效，建议在项目里用工具自动化约束：

- **格式化**：`black`
- **静态检查/风格检查**：`ruff`（可替代/覆盖大量传统工具）
- **导入排序**：`isort`（或使用 `ruff` 的 import 规则）

> 若本仓库后续加入可执行代码与 CI，可在此基础上补充具体的配置文件与执行命令。

## 🤝 贡献指南

欢迎贡献内容！如果你想添加新的 PEP 解析或改进现有内容：

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/new-pep`)
3. 提交更改 (`git commit -m 'Add PEP XXX analysis'`)
4. 推送到分支 (`git push origin feature/new-pep`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 Apache License 2.0 开源许可证。详见 [LICENSE](LICENSE) 文件。

## 🔗 相关资源

- [Python PEP 官方索引](https://www.python.org/dev/peps/)
- [PEP 8 官方文档](https://www.python.org/dev/peps/pep-0008/)
- [Python 官方文档](https://docs.python.org/)

---

**持续更新中...** 更多 PEP 解析内容敬请期待！
