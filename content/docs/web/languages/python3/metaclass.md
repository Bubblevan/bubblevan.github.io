# Python Day3 元类

为了避免昏头转向，我们先来回忆一下类与对象的定义：

在 Python 中，**对象**是内存中具备 “**身份、类型、值**” 三大核心特征的实体，是 “**数据（属性）+ 行为（方法）**” 的封装体。

*   **身份（Identity）**：对象的唯一标识，对应内存地址，可通过 `id()` 函数获取；
*   **类型（Type）**：决定对象能执行的操作、可存储的数据形态，可通过 `type()` 函数获取；
*   **值（Value）**：对象存储的具体数据（如整数 10 的值是 10，列表 `[1,2]` 的值是有序的两个整数）。

Python 的核心哲学是 “**一切皆对象**”—— 数字、字符串、列表、函数、甚至 `None`，本质都是对象；类的实例（比如 `Person` 类创建的 小明）是 “**实例对象**”，类本身也是对象（“**类对象**”）。

**类**是创建实例对象的 “**模板 / 蓝图（Blueprint）**”，是对一类具有相同属性（数据）和方法（行为）的对象的抽象描述。
*   类定义了**类属性**（该类所有实例共享的数据，如 “人类” 的 “物种 = 智人”）；
*   类定义了**方法**（该类所有实例共有的行为，如 “人类” 的 “说话”“走路”）；
*   类的核心行为是 “**实例化**”：通过类创建具体的实例对象，每个实例会继承类的属性和方法，且拥有独立内存存储自身的 “**实例属性**”（如 “小明” 的 “年龄 = 20”）。

## 一、颠覆认知的起点：类本身也是对象

在大多数编程语言中，我们习惯了“类是模具，对象是成品”的思维模式。类用来描述对象长什么样，然后我们用这个模具去批量生产对象。但在 Python 里，这个“模具”本身也是一个“成品”。

当你写下一个 `class` 关键字定义一个类时，Python 解释器在运行到这段代码的那一瞬间，实际上是在内存里创建了一个对象。

来看一个简单的例子：

```python
class ObjectCreator(object):
    pass

mObject = ObjectCreator()
print(mObject)
```

输出结果：
```
<__main__.ObjectCreator object at 0x00000000023EE048>
```

这看起来很平常。但是，Python 中的类有一点跟大多数的编程语言不同，**类本身也是一种对象**。只要使用关键字 `class` ，Python 解释器在执行的时候就会创建一个对象。

既然它是一个对象，这就意味着它拥有对象的一切特权：

1.  可以把它打印出来看看
2.  可以把它作为参数传递给函数
3.  可以把它赋值给一个变量

让我们通过代码来验证这一点：

```python
class ObjectCreator(object):
    pass

def echo(ob):
    print(ob)

mObject = ObjectCreator()
print(mObject)

# 1. 可以直接打印一个类，因为它其实也是一个对象
print(ObjectCreator)

# 2. 可以直接把一个类作为参数传给函数（注意这里是类，是没有实例化的）
echo(ObjectCreator)

# 3. 也可以直接把类赋值给一个变量
objectCreator = ObjectCreator
print(objectCreator)
```

输出结果：
```
<__main__.ObjectCreator object at 0x000000000240E358>
<class '__main__.ObjectCreator'>
<class '__main__.ObjectCreator'>
<class '__main__.ObjectCreator'>
```

## 二、`type` 的双重身份与动态创建类

因为类也是对象，所以我们可以在程序运行的时候动态创建类。这是动态语言（如 Python）和静态语言最大的不同：**函数和类的定义，不是编译时定义的，而是运行时动态创建的。**

我们平时常用的 `type()` 函数，其实有两个作用：
1.  查看一个对象的类型。
2.  **创建出新的类型（类）**。

> 赞美所有类的缔造者！

```python
class Hello(object):
    def hello(self, name='Py'):
        print('Hello,', name)

h = Hello()
print(type(Hello))
print(type(h))
```

输出：
```
<class 'type'>
<class '__main__.Hello'>
```

注意到了吗？`Hello` 类的类型是 `type`。这暗示了 `type` 其实是所有类的创造者。

事实上，我们可以直接用 `type()` 函数来“捏造”一个类出来，完全不需要 `class` 关键字。

`type` 创建类的语法如下：
```python
type(类名, 父类的元组, 包含属性的字典)
```

比如，我们可以把上面的 `Hello` 类用 `type` 重新写一遍：

```python
def printHello(self, name='Py'):
    # 定义一个打印 Hello 的函数
    print('Hello,', name)

# 创建一个 Hello 类
# 1. 类名为 'Hello'
# 2. 继承自基类 (object,)
# 3. 将 printHello 函数绑定给 'hello' 属性
Hello = type('Hello', (object,), dict(hello=printHello))

# 实例化 Hello 类
h = Hello()
# 调用 Hello 类的方法
h.hello()

# 查看类型
print(type(Hello))
print(type(h))
```

输出结果和使用 `class` 关键字定义是一模一样的：
```
Hello, Py
<class 'type'>
<class '__main__.Hello'>
```

这揭示了 Python 的本质：**Python 解释器遇到 `class` 定义时，仅仅是扫描一下语法，然后调用 `type()` 函数创建出这个类对象。**

## 三、到底什么是元类？

把前面的概念串起来，我们就能触及元类的定义了。

*   对象是由类实例化出来的。
*   类本身也是对象。
*   **那么，类是由谁实例化出来的？**

答案是：**元类 (Metaclass)**。

元类就是用来创建类的“东西”。你也可以理解为，**元类就是类的类**。

我们通过 `__class__` 属性可以一路追溯上去：

```python
age = 23
print(age.__class__)
# 输出: <class 'int'>

name = 'Bubblevan'
print(name.__class__)
# 输出: <class 'str'>

def fu(): pass
print(fu.__class__)
# 输出: <class 'function'>

class eat(object): pass
mEat = eat()
print(mEat.__class__)
# 输出: <class '__main__.eat'>
```

所有这些东西（int, str, function, class）本质上都是对象。那么创造它们的类（即 `__class__` 的 `__class__`）是什么呢？

```python
print(age.__class__.__class__)
print(name.__class__.__class__)
print(fu.__class__.__class__)
print(mEat.__class__.__class__)
```

输出结果惊人的一致：
```
<class 'type'>
<class 'type'>
<class 'type'>
<class 'type'>
```

是的，**`type` 就是 Python 内建的元类**，它是所有类的源头。

## 四、自定义元类

既然 `type` 能创建类，那我们能不能自定义一个元类，来干预类的创建过程呢？

答案是可以的。元类的主要目的就是**为了当创建类时能够自动地改变类**。

### 1. `__metaclass__` 属性

在 Python 中（特别是在旧版本或兼容写法中），我们可以给类添加一个 `__metaclass__` 属性。

```python
class MyObject(object):
    __metaclass__ = something…
```

当你写下这段代码时，Python 就会用 `something` 来创建 `MyObject` 这个类，而不是用默认的 `type`。

Python 寻找元类的顺序是：
1.  类中是否有 `__metaclass__`？
2.  父类中是否有 `__metaclass__`？
3.  模块层次中是否有 `__metaclass__`？
4.  如果都找不到，使用内置的 `type`。

### 2. 实战：把所有属性变成大写

假设我们要创建一个“变态”的模块，里面所有类的属性都必须是大写的。我们可以写一个元类来实现这个需求。

**方法一：使用函数作为元类**

`__metaclass__` 不需要非得是一个类，它可以是任何可调用的东西（比如函数）。

```python
# 元类会自动将你通常传给‘type’的参数作为自己的参数传入
def upper_attr(future_class_name, future_class_parents, future_class_attr):
    '''返回一个类对象，将属性都转为大写形式'''
    
    #  选择所有不以'__'开头的属性
    attrs = ((name, value) for name, value in future_class_attr.items() if not name.startswith('__'))
    
    # 将它们转为大写形式
    uppercase_attr = dict((name.upper(), value) for name, value in attrs)
    
    # 通过'type'来做类对象的创建
    return type(future_class_name, future_class_parents, uppercase_attr)
 
__metaclass__ = upper_attr  
#  这会作用到这个模块中的所有类
 
class Foo(object):
    # 我们也可以只在这里定义__metaclass__，这样就只会作用于这个类中
    bar = 'bip'

print(hasattr(Foo, 'bar'))
# 输出: False
print(hasattr(Foo, 'BAR'))
# 输出: True
 
f = Foo()
print(f.BAR)
# 输出: 'bip'
```

**方法二：使用类作为元类（推荐）**

更正规的做法是继承 `type` 来编写元类。这里我们需要重写 `__new__` 方法，因为 `__new__` 才是真正创建对象（这里指类对象）的地方。

```python
class UpperAttrMetaclass(type):
    def __new__(cls, name, bases, dct):
        # 过滤并转换属性名为大写
        attrs = ((name, value) for name, value in dct.items() if not name.startswith('__'))
        uppercase_attr = dict((name.upper(), value) for name, value in attrs)
        
        # 复用 type.__new__ 方法
        # 这是标准的 OOP 写法
        return super(UpperAttrMetaclass, cls).__new__(cls, name, bases, uppercase_attr)
```

元类本身其实很简单：
1.  **拦截**类的创建
2.  **修改**类
3.  **返回**修改之后的类

## 五、什么时候使用元类？

虽然元类很强大，但正如 Python 界的领袖 Tim Peters 所说：

> “元类就是深度的魔法，99% 的用户应该根本不必为此操心。如果你想搞清楚究竟是否需要用到元类，那么你就不需要它。那些实际用到元类的人都非常清楚地知道他们需要做什么，而且根本不需要解释为什么要用元类。”

元类最典型的应用场景是 **API 的设计** 和 **框架开发**。

最著名的例子就是 Django 的 ORM。它允许你这样定义数据模型：

```python
class Person(models.Model):
    name = models.CharField(max_length=30)
    age = models.IntegerField()
```

如果你实例化它：
```python
guy = Person(name='bob', age='35')
print(guy.age)
```

这里 `guy.age` 返回的不是一个 `IntegerField` 对象，而是一个直接的 `int`。这是因为 `models.Model` 使用了元类，将你定义的简单类转换成了复杂的数据库钩子。框架在背后默默完成了所有脏活累活，留给使用者一个干净简单的 API。

总结来说，Python 中一切皆对象，类也不例外。元类就是创造类的类，理解它有助于深入掌握 Python 的运行机制，但在日常业务开发中，我们应保持敬畏，尽量少用“黑魔法”。
