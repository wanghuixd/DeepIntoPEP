# PEP 8：Python 代码风格指南（要点说明）

PEP 8 是 Python 社区最常用的**代码风格规范**（Code Style Guide），目标是让代码在团队内保持一致、可读、易维护。

## 1. 总体原则

- **可读性优先**：代码写给人读，其次才是给机器跑。
- **一致性优先**：在一个项目内保持统一风格，比追求“最完美规则”更重要。
- **遵循项目约定**：如果项目已有格式化/检查工具（例如 Black、Ruff），以项目配置为准。

## 2. 代码布局（Layout）

### 缩进与换行

- **缩进 4 个空格**，不要用 Tab（或确保编辑器将 Tab 转为空格）。
- 续行优先使用括号自然换行（implicit line continuation）：

```python
result = some_function(
    arg1,
    arg2,
    arg3,
)
```

### 行长度

- 传统建议 **每行不超过 79 字符**；注释/文档字符串不超过 72 字符。
- 现代项目常见做法：配合格式化工具放宽到 **88/99/100** 等（以项目配置为准）。

### 空行

- 顶层函数/类之间 **空两行**。
- 类中方法之间 **空一行**。

```python
class A:
    def m1(self):
        pass

    def m2(self):
        pass


def f():
    pass
```

### Imports（导入）

- 导入放在文件顶部。
- 分组并用空行分隔：**标准库** / **第三方库** / **本地应用**。
- 避免 `from x import *`。

```python
import os
from pathlib import Path

import requests

from myapp import settings
```

## 3. 命名规范（Naming Conventions）

- **模块/包**：`lowercase`，必要时用下划线 `lowercase_with_underscores`
- **类**：`CapWords`（驼峰式首字母大写），如 `HttpClient`
- **函数/变量**：`lowercase_with_underscores`，如 `parse_config`
- **常量**：`UPPERCASE_WITH_UNDERSCORES`，如 `MAX_RETRIES`
- **实例方法的第一个参数**：`self`；类方法：`cls`
- **非公开成员**：前缀 `_internal`（表示内部使用）

## 4. 空白字符（Whitespace）

- 逗号、冒号后面加一个空格；前面不加：

```python
items = [1, 2, 3]
mapping = {"a": 1, "b": 2}
```

- 运算符两侧一般加空格：

```python
x = a + b
y = (a + b) * (c - d)
```

- 关键字参数的 `=` 两侧不加空格：

```python
func(a=1, b=2)
```

## 5. 注释与文档字符串（Comments & Docstrings）

- 注释解释**为什么**而非重复代码**做了什么**。
- 文档字符串使用三引号 `"""`，为模块/类/函数提供简洁说明、参数与返回值含义。

```python
def add(x: int, y: int) -> int:
    """Return the sum of two integers."""
    return x + y
```

## 6. 编程实践建议（常见约定）

- 用 `is None` / `is not None` 判断 `None`。
- 不要和内置名冲突（例如 `list`, `dict`, `id`），必要时用后缀 `_`：

```python
id_ = "user-123"
```

- 异常捕获避免裸 `except:`，优先捕获具体异常；确需捕获所有异常用 `except Exception:`。

## 7. 与自动化工具的关系（推荐）

PEP 8 是“规范”，实践中通常交给工具自动落地：

- **格式化（formatter）**：Black（强制统一格式）
- **静态检查/风格检查**：Ruff（快速，覆盖大量规则）、Flake8（传统选择）
- **导入排序**：Ruff（内置）或 isort

如果你希望我在这个仓库里同时加上对应的配置（例如 `pyproject.toml`，启用 Ruff/Black 并给出默认规则），告诉我你希望的行宽（如 88/100）即可。

## 参考

- PEP 8 原文：`https://peps.python.org/pep-0008/`

