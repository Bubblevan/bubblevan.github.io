# Python Day2-3 面向对象

## 1. 面向对象的概念

### 1.1 编程思维：面向过程 vs 面向对象

1. 面向过程强调“解决问题的过程”，习惯先拆分步骤，再按步骤顺序执行。
2. 面向对象是一种抽象方法，强调用分类的眼光看世界，把问题拆成对象并让对象协作。
3. Python 是面向对象语言，解决实际问题时可以把事物分解成对象，再围绕对象的属性与方法组织程序。

### 1.2 两个基本概念：类与对象

1. 类（Class）是具有相同属性与方法的一组对象的抽象集合；对象是类的实例。
2. 对象（Object）是通过类定义出来的数据结构实例，可以理解为“类在运行时的一份具体拷贝/实体”。

### 1.3 面向对象三大特性

1. 继承：派生类继承基类的字段与方法，表达“是一个（is-a）”关系。
2. 多态：不同类型对象对同一操作表现不同的行为。
3. 封装：把数据与行为结合为整体，通过外部接口在特定访问权限下使用，隐藏实现细节以增强安全性与简化编程。

## 2. 类的定义与调用

### 2.1 类的理解方式

1. 可以把类直观理解为“变量（属性）和函数（方法）的集合”，把同一类事物的状态与行为打包到一起，便于复用与组织。

### 2.2 类的定义语法

```python
class ClassName():
    <statement-1>
    ...
    <statement-N>
```

1. 使用 `class` 关键字定义类，这一点类似于用 `def` 定义函数。
2. 类体中的变量称为类属性，类体中的函数称为类方法（在“直接通过类调用”的语境下）。

**示例（作业题1）：定义基础类**
```python
class Person(object):
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def greet(self):
        return f"Hello, {self.name}!"
```

### 2.3 直接通过类名调用属性与方法

1. 访问类属性：`ClassName.var`。
2. 调用类方法：`ClassName.func(...)`。

**示例（作业题2）：类属性与实例属性的区别**
```python
class Counter(object):
    total = 0  # 类属性

    def __init__(self):
        self.count = 0  # 实例属性

    def inc(self, n):
        self.count += n
        Counter.total += n  # 通过类名访问类属性
```

## 3. 类方法

### 3.1 `@classmethod` 的意义

1. `@classmethod` 用于声明“下面这个函数是类方法”。
2. 类方法与普通函数/实例方法的关键区别在于：它接收“类本身”作为第一个参数，因此可以在方法内部访问类属性。

### 3.2 `cls` 参数与类属性访问

1. 类方法第一个参数写作 `cls`（class 的缩写），表示当前类对象。
2. 类属性访问写作 `cls.变量名`。
3. 文档强调：`@classmethod` 与 `cls` 都不能省略，否则会导致调用失败或报错。

### 3.3 类方法传参

1. 类方法除了 `cls` 以外可以继续接收其他参数，传参方式与普通函数一致。

## 4. 修改与增加类属性

### 4.1 从类内部修改/新增类属性

1. 在类内部修改类属性，典型方式是定义类方法，然后在类方法里通过 `cls.xxx = ...` 修改/新增。
2. 这种修改作用于“类对象”，因此会影响通过类或实例读取该类属性的结果（未被实例同名属性遮蔽时）。

### 4.2 从类外部修改/新增类属性

1. 可以在类定义之外直接写 `ClassName.xxx = ...` 修改或新增类属性。
2. 这种方式同样是直接改动类对象本身的属性集合。

## 5. 类与对象

### 5.1 类与对象的关系

1. 类是对象的模板；对象是类的实例。
2. 从类变成对象的过程称为类的实例化。

### 5.2 类的实例化与调用方式的变化

1. 直接使用类：`ClassName.method()`，常配合 `@classmethod` 与 `cls`。
2. 实例化后使用：`obj = ClassName()`，再用 `obj.method()` 调用实例方法，方法内第一个参数通常写 `self`。

### 5.3 `self` 的含义与约定

1. `self` 不是关键字，而是实例方法里“默认放在首位的特殊参数”的约定写法。
2. 理论上可改名，但推荐遵循 `self` 约定以保持可读性与一致性。

### 5.4 一个类可实例化多个对象

1. 同一个类可以创建多个实例对象，每个实例都有独立的实例属性集合。

### 5.5 实例属性与类属性的关系

1. 当类属性改变时，实例对该属性的读取结果会随之变化（前提是该实例没有创建同名实例属性进行遮蔽）。
2. 当实例属性改变时，不会反向影响类属性，因为实例是独立个体。

### 5.6 实例方法与类方法的关系（方法替换/重写）

1. 当类的方法定义被替换（例如 `ClassA.fun = new_fun`）时，实例调用该方法会跟随变化。
2. 文档强调“替换方法是赋值，不是调用”，因此不能写括号。
3. 文档展示：不能直接对某个实例对象“重写实例方法”（会报错），能替换的是类上的方法定义。

## 6. 初始化函数（构造）与析构函数

### 6.1 初始化函数 `__init__`

1. 作用：创建实例时自动调用，用于初始化实例状态。
2. 规则：方法名固定为 `__init__`（两侧双下划线），第一个参数必须接收实例（通常命名 `self`）。
3. `__init__` 可以接收参数，用于初始化不同实例属性值。

### 6.2 析构函数 `__del__`

1. 作用：对象销毁时调用，可用于资源释放提示或清理。
2. 规则：方法名固定为 `__del__`，第一个参数通常命名 `self`。

**示例（作业题4）：初始化与析构**
```python
class Resource(object):
    def __init__(self):
        self.status = 'allocated'

    def __del__(self):
        print('释放资源')  # 对象被销毁时触发
```

### 6.3 Python 类定义的历史遗留：旧式类与新式类

1. Python 2 中存在旧式类与新式类（新式类显式继承 `object`）的差异。
2. Python 3 中不存在该问题：所有类都是新式类，输出表现一致。

## 7. 类的继承

### 7.1 继承语法

1. 单继承：`class Child(Base): ...`。
2. 多继承：`class Child(Base1, Base2, ...): ...`。
3. 多继承同名方法查找：文档给出的直观规则是从左到右搜索父类，先找到先使用。

**示例（作业题9）：多继承与方法解析顺序**
```python
class A(object):
    def ping(self): return 'A'

class B(object):
    def ping(self): return 'B'

class C(A, B):
    pass  # 继承顺序为 A, B

# C().ping() 返回 'A'，因为从左到右先找到 A 的 ping 方法
```

### 7.2 继承带来的能力

1. 子类会继承父类的属性与方法。
2. 子类可以覆盖父类的属性与方法（重写）。

**示例（作业题5）：继承与方法重写**
```python
class User(object):
    def __init__(self, name):
        self.name = name
        
    def welcome(self):
        print(f"Hello, 用户:{self.name}")

class UserVip(User):
    def welcome(self):
        return f"Hello, 尊敬的Vip用户：{self.name}"  # 重写父类方法
    ```

### 7.3 调用父类方法与 `super`

1. 子类可直接调用父类已有方法（继承得到）。
2. 子类重写构造函数时，常用 `super(Child, self).__init__(...)` 调父类构造函数，再补充子类新增字段。
3. 文档出现 `@property`：它可以把“方法”以“属性访问”的形式暴露出来（例如 `obj.get_age`），常用于封装读取逻辑与保持调用简洁。

**示例（作业题11）：@property 封装**
```python
class Inventory(object):
    @property
    def size(self):
        return len(self._bucket)  # 将方法作为属性调用：inv.size
```

### 7.4 子类类型判断

1. `isinstance(obj, Class)` 用于判断对象是否为某类或其子类的实例。
2. `isinstance` 同样可判断基本类型实例关系。

## 8. 类的多态

### 8.1 多态的直观理解

1. 多态是指对不同类型对象执行同一操作，会得到不同表现。
2. 文档用 `1 + 2` 与 `'a' + 'b'` 说明：同一个 `+` 运算符在不同类型上表现不同。

### 8.2 基于继承的多态

1. 父类定义一个方法接口（例如 `printUser`）。
2. 子类重写该方法实现不同逻辑（Vip 与 General 输出不同）。
3. 外部函数只依赖“接口”（例如只调用 `user.printUser()`），传入不同子类对象即可表现不同，这就是多态。
4. 文档强调：有继承才更容易形成这种多态结构。

**示例（作业题6）：基于继承的多态**
```python
def welcome_user(u):
    # u 可以是 UserVip 或 UserGeneral，调用的是各自重写后的 welcome
    return u.welcome()
```

## 9. 类的访问控制、专有方法与内省

### 9.1 访问控制在 Python 中的定位

1. Python 不提供强制意义上的私有属性机制，访问控制更多依赖命名约定与自觉遵守。

### 9.2 属性命名约定与实际效果

1. 单下划线 `_attr`：约定为“受保护/内部使用”，技术上仍可访问。
2. 双下划线 `__attr`：约定为“私有”，会触发名称改写（name mangling），并非真正不可访问。
3. 名称改写后的访问方式形如 `obj._ClassName__attr`，文档用该方式验证“双下划线不是严格私有”。

**示例（作业题7）：访问控制**
```python
class AccountUser(object):
    def __init__(self, name, age, account):
        self.name = name          # 公开
        self._age = age           # 受保护（约定）
        self.__account = account  # 私有（名称改写）
```

### 9.3 类专有方法（魔法方法）清单

| 方法 | 说明 |
| --- | --- |
| `__init__` | 构造函数，在生成对象时调用 |
| `__del__` | 析构函数，释放对象时使用 |
| `__repr__` | 打印、转换 |
| `__setitem__` | 按照索引赋值 |
| `__getitem__` | 按照索引获取值 |
| `__len__` | 获得长度 |
| `__cmp__` | 比较运算 |
| `__call__` | 函数调用 |
| `__add__` | 加运算 |
| `__sub__` | 减运算 |
| `__mul__` | 乘运算 |
| `__div__` | 除运算 |
| `__mod__` | 求余运算 |
| `__pow__` | 乘方 |

**示例：魔法方法应用**
```python
class Bucket(object):
    def __len__(self):
        return len(self._items)  # 支持 len(bucket)

    def __repr__(self):
        return f"Bucket(size={len(self._items)})"  # 支持 print(bucket)

class KVStore(object):
    def __setitem__(self, k, v):
        self._data[k] = v  # 支持 kv['a'] = 1

    def __getitem__(self, k):
        return self._data[k]  # 支持 kv['a']
```

详情可参考隔壁[Magic Method](./magic)
### 9.4 常用内省函数

1. `type(obj)`：获取对象类型。
2. `isinstance(obj, type)`：判断对象是否为指定类型实例。
3. `hasattr(obj, attr)`：判断对象是否具有指定属性/方法。
4. `getattr(obj, attr[, default])`：获取属性/方法的值，不存在时返回默认值或抛出 `AttributeError`。
5. `setattr(obj, attr, value)`：设置属性/方法值，等价于 `obj.attr = value`。
6. `dir(obj)`：列出对象的属性和方法名列表。

**示例（作业题8）：内省函数使用**
```python
x = Person2('D', 22)
setattr(x, 'country', 'CN')          # 动态添加属性
assert getattr(x, 'country') == 'CN' # 获取属性
assert hasattr(x, 'name')            # 检查属性
print(dir(x))                        # 列出所有属性方法
```

### 9.5 方法的访问控制

1. 方法本质上也是属性，因此命名约定与属性一致。
2. 示例命名：公开方法 `upgrade`，受保护方法 `_buy_equipment`，私有方法 `__pk`。


## 10. Enum：把“有限集合”变成类型

在实际写代码的时候，我们经常需要定义一些常量。比如一年有12个月，或者一周有7天。以前新手时期，我们可能习惯用大写变量名来表示，比如定义 JAN=1, FEB=2 这样：

```python
JAN = 1
FEB = 2
MAR = 3
...
NOV = 11
DEC = 12
```

虽然这种方式简单快捷，但也有明显的缺点：这些常量本质上还是普通的整数（int）或字符串，类型定义不够明确，而且它们仅仅是普通的变量，很容易在代码的其他地方被不小心修改，混在一起也不太好管理。

当一个变量只能取有限几种状态（方向、颜色、订单状态），把它写成 `Enum` 往往比写一堆字符串更安全：可读性更强，也更不容易写错。

### 什么是枚举类？

简单来说，枚举就是把一组相关的常量封装在一个类里面，给它们打上标签。在这个类里，每一个常量（成员）都是类里面唯一的实例。

这样做的好处显而易见：它不仅让代码更清晰（看到 `Month.Jan` 肯定比看到数字 `1` 更容易理解），而且更加安全。Enum 里的成员具有**单例（Singleton）**的特性，这意味着你不能在外部去实例化它（不能 `new` 一个枚举），也不能在定义好之后去修改它。它们就像是被“焊死”在模具里的标签，稳固且可靠，专门用来做标识。

```python
from enum import Enum

# 定义枚举类
class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

def set_color(c):
    if c == Color.RED:
        print("红色")

# 优势1：不可变（枚举成员不能被修改）
# Color.RED = 100  # 直接报错：AttributeError: cannot reassign members.

# 优势2：类型安全
set_color(Color.RED)  # 正确
# set_color(1)  # 函数里判断 c == Color.RED 会返回False，避免非法值
# 更严格的写法：用 Enum 的类型检查
def set_color_strict(c: Color):
    if not isinstance(c, Color):
        raise TypeError("必须传入Color枚举成员")
    print(c.name, c.value)

# 优势3：语义清晰（有名字和值）
print(Color.RED.name)  # 输出 "RED"，调试/日志更友好
print(Color.RED.value) # 输出 1

# 优势4：可遍历所有成员
for color in Color:
    print(color)  # 输出 Color.RED、Color.GREEN、Color.BLUE

# 优势5：支持身份比较（is）和值比较（==）
print(Color.RED is Color(1))  # True
print(Color.RED == 1)         # True（默认支持值比较）
```
除上面5个之外还有一些OOP的优势：
*   枚举是类，可继承、可加方法（比如给 Color 加 to_hex() 方法，返回颜色的十六进制值）；
*   支持唯一值（enum.Unique），避免枚举成员值重复；
*   支持自动赋值（enum.AutoEnum），不用手动写 1、2、3。

### 如何使用它？

我们可以利用 Python 内置的 `enum` 模块来使用它。

最直接的用法是像函数调用一样创建一个 Enum 对象，传入类名和一组成员名称。这时候，Python 会贴心地自动给这些成员分配值（通常是默认从 1 开始的整数）。通过这种方式，我们就能得到一个包含所有常量的枚举类型：

```python
from enum import Enum

Month = Enum('Month', ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'))

# 遍历枚举类型
for name, member in Month.__members__.items():
    print(name, '---------', member, '----------', member.value)

# 直接引用一个常量
print('\n', Month.Jan)
```

但在实际开发中，更常见也更推荐的做法是**自定义一个类去继承 Enum**。这样你就可以拥有更精细的控制权，比如给每个成员指定具体的值（可以是整数，也可以是字符串，甚至是其他对象）。

如果你担心自己手滑，给不同的成员定义了相同的值，Python 还提供了一个 **@unique** 装饰器。把它戴在你的自定义枚举类头上，一旦发现有重复的值，程序运行的时候就会立刻报错提醒你，非常有助于保持数据的纯洁性：

```python
from enum import Enum, unique

# @unique 装饰器可以帮助我们检查保证没有重复值
@unique
class Month(Enum):
    Jan = 'January'
    Feb = 'February'
    Mar = 'March'
    Apr = 'April'
    May = 'May'
    Jun = 'June'
    Jul = 'July'
    Aug = 'August'
    Sep = 'September '
    Oct = 'October'
    Nov = 'November'
    Dec = 'December'

if __name__ == '__main__':
    print(Month.Jan, '----------',
          Month.Jan.name, '----------', Month.Jan.value)
    for name, member in Month.__members__.items():
        print(name, '----------', member, '----------', member.value)
```

### 原理浅析：它为什么这么特别？

为什么我们可以通过 `__members__` 这样的属性去遍历枚举里的所有成员？或者为什么它能保持只读？

这其实涉及到了 Python 的[**元类（Metaclass）**](./metaclass)机制。Enum 类背后有一个叫 `EnumMeta` 的元类在“撑腰”。当我们去访问枚举成员列表时，实际上是这个元类在工作。它把 `__members__` 定义成了一个只读的映射视图（MappingProxyType）。你可以把它想象成一个上了锁的透明展示柜，我们既能方便地查看里面有哪些成员，又不用担心不小心伸手进去把它们给弄乱或改坏了。

### 关于比较：谁大谁小？

枚举成员之间怎么比较呢？

因为它们本质上是用来做“标识”的符号，所以它们天生支持**“相等性”比较**。也就是说，我们可以判断 `A == B` 或者 `A is B`，来看看它们是不是代表同一个常量：

```python
from enum import Enum

class User(Enum):
    Twowater = 98
    Liangdianshui = 30
    Tom = 12

Twowater = User.Twowater
Liangdianshui = User.Liangdianshui

print(Twowater == Liangdianshui, Twowater == User.Twowater)
print(Twowater is Liangdianshui, Twowater is User.Twowater)
```

但是，普通的枚举类是**不支持“大小”比较**的。你不能直接说“User.Tom > User.Jerry”，因为对于抽象的符号来说，这种比较逻辑上往往没有意义，Python 会直接抛出一个 TypeError 错误。

不过，凡事总有例外。如果你定义的枚举确实代表了某种顺序（比如等级、分数），你需要它们能像数字一样比较大小和排序，Python 提供了一个 **IntEnum** 类。如果你的枚举类继承自它，那么里面的成员就会被当成整数来看待，这时候既可以比较大小，也可以直接进行排序了：

```python
import enum

class User(enum.IntEnum):
    Twowater = 98
    Liangdianshui = 30
    Tom = 12

try:
    print('\n'.join(s.name for s in sorted(User)))
except TypeError as err:
    print(' Error : {}'.format(err))
```