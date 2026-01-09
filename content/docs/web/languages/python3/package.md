# Python Day3 包与模块

## Preface

1. 本章主题：模块与包。
2. 学习目标：理解“模块是什么、怎么导入、主模块判断、包的组织方式、模块级作用域约定”。

## 1. Python 模块简介

### 1.1 模块解决什么问题

1. 代码增长后，单文件会越来越长、难维护。
2. 函数用于封装一段功能，类用于封装属性与方法；模块用于把“变量、函数、类”等组织在一个文件里，便于复用与维护。

### 1.2 模块的定义

1. 在 Python 中，一个 `.py` 文件就是一个模块（Module）。
2. 模块中可以直接定义变量、函数和类，不需要额外语句来“声明模块”。

### 1.3 使用模块的价值

1. 提升可维护性：将功能拆分到不同文件，减少耦合。
2. 提高复用性：模块写好后可被多处引用，包括标准库与第三方库。
3. 降低命名冲突概率：不同模块可以拥有同名函数/变量，通过模块名区分；但仍应避免与内置函数重名。

### 1.4 标准库模块与自定义模块

1. 标准库模块：Python 安装目录的 `Lib` 下大量 `.py` 文件。
2. 自定义模块：自己编写的 `.py` 文件，通过导入使用。

## 2. 模块的使用

### 2.1 `import` 导入模块

1. 基本语法：`import module1[, module2, ...]`。
2. 导入后使用模块成员：`module.name`（例如 `math.pi`）。
3. 模块只会被导入一次：重复 `import` 不会重复执行模块代码。

示例：导入 `math` 并使用常量
```python
import math

print(math.pi)
```

示例：一次导入多个模块
```python
import math, sys

print(math.e)
print(len(sys.path))
```

示例：使用 `as` 起别名（避免名字过长）
```python
import math as m

print(m.sqrt(16))
```

### 2.2 模块搜索路径 `sys.path`

1. 解释器执行 `import` 时，会按搜索路径列表依次查找目标模块。
2. 搜索路径存储在 `sys.path` 中，可打印查看。

示例：查看模块搜索路径
```python
import sys

print(sys.path)
```

### 2.3 `from ... import ...` 导入成员

1. `import mod` 导入的是模块对象；要访问成员需要写 `mod.xxx`。
2. `from mod import name` 直接把模块中的某个成员导入当前命名空间，可以直接写 `name`。

语法：
```python
from modname import name1[, name2, ...]
```

示例：对比 `import sys` 与 `from sys import version`
```python
import sys
print(sys.version)
```

```python
from sys import version
print(version)
```

### 2.4 `from ... import *` 导入全部成员（谨慎）

1. `from mod import *` 会把模块中的“所有方法属性”导入当前命名空间，书写更省事。
2. 文档提示：不应过多使用这种方式，原因是命名空间污染与可读性下降，且更容易引入名称冲突。

示例：`from sys import *`
```python
from sys import *

print(version)
print(executable)
```

## 3. 主模块和非主模块

### 3.1 主模块与非主模块

1. 主模块：模块被直接运行（直接使用），而不是被其他模块导入。
2. 非主模块：模块被其他模块导入并使用。

### 3.2 `__name__` 属性与 `__main__`

1. 每个模块都有系统提供的 `__name__` 变量。
2. 当模块作为“主模块”运行时，`__name__ == '__main__'`。
3. `__name__` 只是用于判断当前运行方式；主模块与否的根本条件是“是否被直接运行/是否被导入调用”。

典型写法（主入口保护）：
```python
def main():
    pass

if __name__ == '__main__':
    main()
```

示例：区分“直接运行”和“被导入”（两个文件）

文件 `lname.py`
```python
print(__name__)

if __name__ == '__main__':
    print('main')
else:
    print('not main')
```

文件 `use_lname.py`
```python
import lname
```

## 4. 包（Package）

### 4.1 为什么需要包

1. 模块能减少命名冲突，但不同人仍可能写出同名模块文件。
2. 包通过目录层级组织模块，借助路径（包名）来进一步避免冲突。

### 4.2 包的识别：`__init__.py`

1. 每个包目录下通常包含 `__init__.py`，否则该目录会被当作普通目录而不是包。
2. `__init__.py` 可以为空文件，也可以包含 Python 代码。
3. `__init__.py` 本身也是一个模块，对应的模块名就是包名。

示例：包结构示意
```text
project/
  main.py
  pkg/
    __init__.py
    util.py
```

示例：导入包内模块
```python
import pkg.util
```

### 4.3 模块全名（模块路径）

1. 通过包名 + 模块名形成更长的“模块全名”，例如 `com.Learn.module.nameattributes.lname`。
2. 模块全名本质上对应目录路径层级，用于唯一定位模块。

## 5. 作用域

### 5.1 模块级“公开/非公开”约定

1. 模块中的函数与变量默认是公开的（public），可被外部直接引用，例如 `abc`、`PI`。
2. 形如 `__xxx__` 的名称为特殊变量/特殊方法名（例如 `__name__`、`__author__`），可直接引用但通常有约定用途；一般不建议自定义时随意使用这类命名。
3. 以单下划线开头的 `_xxx`、双下划线开头的 `__xxx` 通常约定为非公开（private），不应该被外部直接引用。

示例：模块内定义特殊变量与非公开函数（单文件示意）
```python
__author__ = 'twowater'

PI = 3.1415926

def _internal_calc(x):
    return x * 2

def public_calc(x):
    return _internal_calc(x) + 1
```

### 5.2 “不应该”而非“不能”

1. Python 没有强制机制完全禁止外部访问模块内的 private 名称。
2. 这里的 private 更接近“编程习惯与约定”，用于表达“这是内部实现细节，外部不必依赖”。

### 5.3 用 private 封装内部实现的例子

1. 对外只暴露统一入口函数 `vip_lv_name`。
2. 内部把不同分支逻辑封装到 `_gold_vip`、`_diamond_vip` 中，调用方无需关心细节。

```python
def _diamond_vip(lv):
    vip_name = 'DiamondVIP' + str(lv)
    return vip_name


def _gold_vip(lv):
    vip_name = 'GoldVIP' + str(lv)
    return vip_name


def vip_lv_name(lv):
    if lv == 1:
        print(_gold_vip(lv))
    elif lv == 2:
        print(_diamond_vip(lv))
```

### 5.4 经验规则

1. 外部不需要引用的函数尽量定义为 private（`_xxx` 或 `__xxx`）。
2. 外部需要引用的函数才定义为 public（无下划线前缀）。

## 6. 闭包：用需求理解 `global`、`nonlocal` 与 `__closure__`

### 6.1 需求引入：累计学习时间

1. 目标：每次传入本次学习分钟数，返回累计分钟数。
2. 直觉写法：使用全局变量 `time`，在函数内累加并返回。

### 6.2 为什么会报 `UnboundLocalError`

1. 在函数内部对某个名字赋值时，Python 会把它判定为局部变量。
2. 当函数体内既读取 `time` 又对 `time` 赋值时，`time` 会被当成局部变量，但在赋值前已读取，因此触发 `UnboundLocalError: local variable 'time' referenced before assignment`。

### 6.3 使用 `global` 修改全局变量（能用但不推荐）

1. `global time` 表示在函数内对 `time` 的读写指向模块级全局变量。
2. 缺点：全局变量可被多个模块/函数随意修改，容易产生不可预知性，降低可读性与可复用性。

示例：`global` 方式
```python
time = 0

def insert_time(minutes):
    global time
    time = time + minutes
    return time
```

### 6.4 使用闭包替代全局变量：`nonlocal` 绑定外层局部变量

1. 做法：外层函数 `study_time(time)` 创建并返回内层函数 `insert_time(minutes)`。
2. 关键：在内层函数中用 `nonlocal time` 表示 `time` 来自外层函数的局部作用域（非全局），允许修改该变量。
3. 结果：累加状态保存在闭包环境中，全局变量 `time` 不会被修改。

示例：闭包方式
```python
def study_time(time):
    def insert_time(minutes):
        nonlocal time
        time = time + minutes
        return time
    return insert_time

f = study_time(0)
print(f(2))
print(f(10))
```

### 6.5 闭包的定义与特征

1. 内部函数可以访问外部函数局部变量，并把该内部函数返回给外部使用，这种“函数 + 环境变量绑定”称为闭包。
2. 即使生成闭包的外层函数已经执行结束，其局部环境释放，闭包仍能保持对这些变量的引用与状态。

### 6.6 如何验证函数是闭包：`__closure__` 与 `cell_contents`

1. 函数对象有 `__closure__` 属性。
2. 若为闭包，`__closure__` 通常是由 `cell` 组成的元组，每个 `cell` 的 `cell_contents` 保存被捕获的外层变量值。

示例：查看闭包捕获的值
```python
f = study_time(0)
print(f.__closure__)
print(f.__closure__[0].cell_contents)
```

### 6.7 与“类”思路的类比

1. 可以把外层函数类比为“创建器”，闭包类比为“带状态的可调用对象”。
2. 对一些需要保存少量状态、但又不值得定义为类的场景，闭包往往更轻巧、占用资源更少。
