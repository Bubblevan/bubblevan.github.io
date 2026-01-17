# Python Day4 Collections库

## 前言：为什么Python需要Collections模块？

在我刚开始学习Python时，经常会陷入这样的思考："列表、字典、元组、集合已经很强大了，为什么还需要额外的数据结构？" 直到我遇到了一个实际项目——需要统计一篇文章中每个单词出现的频率，然后按频率排序。用纯字典实现时，代码变得异常复杂：

```python
# 用普通字典统计词频并排序
word_count = {}
for word in text.split():
    if word not in word_count:
        word_count[word] = 0
    word_count[word] += 1

# 按值排序：需要转换为列表，排序，再转换回去
sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
result = dict(sorted_words[:10])  # 只取前10个
```

这段代码不仅冗长，而且效率也不高。这时，`collections.Counter` 横空出世：

```python
from collections import Counter
word_count = Counter(text.split())
result = word_count.most_common(10)
```

两行代码，清晰、高效、易读。这就是Collections模块的魅力所在。

Collections模块是Python标准库的一部分，它提供了**专门化的容器数据类型**，是对内置容器（列表、字典、元组、集合）的有力补充。掌握这些数据结构，能让你写出更简洁、更高效、更易读的Python代码。

## 第一章：Counter——统计之王的诞生

### 1.1 Counter基础：不仅仅是计数器

`Counter`是Python中最实用的数据结构之一，专门用于**可哈希对象的计数**。它的底层实现是一个字典，但提供了更丰富的计数功能。

```python
from collections import Counter

# 创建Counter的几种方式
# 1. 从可迭代对象创建
words = ['apple', 'banana', 'apple', 'orange', 'banana', 'apple']
word_counter = Counter(words)
print("单词统计:", word_counter)
# 输出: Counter({'apple': 3, 'banana': 2, 'orange': 1})

# 2. 从字典创建
letter_counter = Counter({'a': 4, 'b': 2, 'c': 1})
print("字母统计:", letter_counter)

# 3. 从关键字参数创建
color_counter = Counter(red=5, blue=3, green=2)
print("颜色统计:", color_counter)

# 4. 空Counter，然后更新
empty_counter = Counter()
empty_counter.update(['a', 'b', 'a', 'c', 'b', 'a'])
print("更新后的Counter:", empty_counter)
```

### 1.2 Counter的魔法方法：超越普通字典

```python
# 创建示例Counter
c = Counter(['a', 'b', 'c', 'a', 'b', 'a'])
print("原始Counter:", c)

# 1. most_common(): 获取最常见的元素
print("最常见的2个元素:", c.most_common(2))  # [('a', 3), ('b', 2)]

# 2. elements(): 返回一个迭代器，每个元素重复其计数次数
print("所有元素（展开）:", list(c.elements()))  
# 输出: ['a', 'a', 'a', 'b', 'b', 'c']

# 3. subtract(): 减去另一个Counter或可迭代对象
c.subtract(['a', 'b'])
print("减去后的Counter:", c)  # Counter({'a': 2, 'b': 1, 'c': 1})

# 4. 算术运算：支持 +, -, &, |
c1 = Counter(a=3, b=1)
c2 = Counter(a=1, b=2)
print("\n加法:", c1 + c2)   # Counter({'a': 4, 'b': 3})
print("减法:", c1 - c2)     # Counter({'a': 2}) - 注意：只保留正计数
print("交集(&):", c1 & c2)  # Counter({'a': 1, 'b': 1}) - 最小计数
print("并集(|):", c1 | c2)  # Counter({'a': 3, 'b': 2}) - 最大计数
```

### 1.3 实战应用：文本分析与数据清洗

```python
import re
from collections import Counter

def analyze_text(text):
    """分析文本的词频和字符频率"""
    # 清洗文本：转为小写，移除标点
    cleaned_text = re.sub(r'[^\w\s]', '', text.lower())
    
    # 词频统计
    words = cleaned_text.split()
    word_counter = Counter(words)
    
    # 字符频率统计
    char_counter = Counter(text)
    
    # 获取前5个最常见单词和前10个最常见字符
    top_words = word_counter.most_common(5)
    top_chars = char_counter.most_common(10)
    
    return {
        'total_words': len(words),
        'unique_words': len(word_counter),
        'top_words': top_words,
        'total_chars': len(text),
        'unique_chars': len(char_counter),
        'top_chars': top_chars
    }

# 示例文本
sample_text = """
Python is an interpreted, high-level, general-purpose programming language. 
Created by Guido van Rossum and first released in 1991, Python's design 
philosophy emphasizes code readability with its notable use of significant 
whitespace.
"""

results = analyze_text(sample_text)
print(f"总单词数: {results['total_words']}")
print(f"唯一单词数: {results['unique_words']}")
print(f"最常见的5个单词: {results['top_words']}")
print(f"\n总字符数: {results['total_chars']}")
print(f"唯一字符数: {results['unique_chars']}")
print(f"最常见的10个字符: {results['top_chars']}")
```

### 1.4 高级技巧：Counter的巧妙应用

```python
# 应用1：找出列表中出现次数最多的元素
numbers = [1, 2, 3, 4, 2, 3, 2, 1, 2, 3, 2, 1, 2]
most_common_num = Counter(numbers).most_common(1)[0][0]
print(f"出现最多的数字: {most_common_num}")

# 应用2：验证两个字符串是否为字母异位词（字符相同但顺序不同）
def is_anagram(str1, str2):
    return Counter(str1) == Counter(str2)

print(f"'listen'和'silent'是字母异位词: {is_anagram('listen', 'silent')}")
print(f"'hello'和'world'是字母异位词: {is_anagram('hello', 'world')}")

# 应用3：统计文件扩展名
files = ['document.pdf', 'image.jpg', 'data.csv', 'photo.jpg', 'report.pdf']
ext_counter = Counter(file.split('.')[-1] for file in files)
print(f"文件扩展名统计: {ext_counter}")

# 应用4：找出两个列表的共同元素（考虑重复）
list1 = [1, 2, 2, 3, 4, 5]
list2 = [2, 2, 3, 3, 4, 6]
common = Counter(list1) & Counter(list2)
print(f"共同元素（考虑重复）: {dict(common)}")
```

## 第二章：defaultdict——告别KeyError的烦恼

### 2.1 defaultdict的核心思想：预设默认值

在普通字典中，访问不存在的键会引发`KeyError`。虽然可以用`get()`方法避免，但在某些场景下代码会变得冗长。`defaultdict`通过在创建时指定默认工厂函数，优雅地解决了这个问题。

```python
from collections import defaultdict

# 普通字典的问题
normal_dict = {}
# normal_dict['key'] += 1  # KeyError: 'key'

# 解决方法1：使用get方法
if 'key' in normal_dict:
    normal_dict['key'] += 1
else:
    normal_dict['key'] = 1

# 解决方法2：使用setdefault
normal_dict.setdefault('another_key', 0)
normal_dict['another_key'] += 1

# defaultdict的优雅解决方案
from collections import defaultdict

# 创建defaultdict，指定默认工厂函数
dd = defaultdict(int)  # 默认值为int()，即0
dd['key'] += 1  # 自动创建key并设置为0，然后+1
print(f"defaultdict结果: {dd}")  # defaultdict(<class 'int'>, {'key': 1})
```

### 2.2 常用工厂函数示例

```python
# 1. int作为工厂函数：默认值为0
int_dict = defaultdict(int)
int_dict['count'] += 5
print(f"int defaultdict: {int_dict}")

# 2. list作为工厂函数：默认值为空列表[]
list_dict = defaultdict(list)
list_dict['fruits'].append('apple')
list_dict['fruits'].append('banana')
print(f"list defaultdict: {list_dict}")

# 3. dict作为工厂函数：默认值为空字典{}
dict_dict = defaultdict(dict)
dict_dict['people']['Alice'] = 25
dict_dict['people']['Bob'] = 30
print(f"dict defaultdict: {dict_dict}")

# 4. set作为工厂函数：默认值为空集合set()
set_dict = defaultdict(set)
set_dict['tags'].add('python')
set_dict['tags'].add('programming')
set_dict['tags'].add('python')  # 重复添加会被忽略
print(f"set defaultdict: {set_dict}")

# 5. 自定义函数作为工厂函数
def default_value():
    return "Unknown"

custom_dict = defaultdict(default_value)
print(f"自定义默认值: {custom_dict['name']}")  # 输出: Unknown

# 6. lambda表达式作为工厂函数
lambda_dict = defaultdict(lambda: [])
lambda_dict['items'].append('item1')
print(f"lambda defaultdict: {lambda_dict}")
```

### 2.3 实战应用：数据分组与索引

```python
# 应用1：按类别分组数据
students = [
    {'name': 'Alice', 'grade': 'A', 'score': 95},
    {'name': 'Bob', 'grade': 'B', 'score': 82},
    {'name': 'Charlie', 'grade': 'A', 'score': 90},
    {'name': 'David', 'grade': 'C', 'score': 78},
    {'name': 'Eve', 'grade': 'B', 'score': 85}
]

# 按成绩等级分组
grade_groups = defaultdict(list)
for student in students:
    grade_groups[student['grade']].append(student['name'])

print("按成绩等级分组:")
for grade, names in grade_groups.items():
    print(f"  {grade}: {names}")

# 应用2：构建反向索引
documents = {
    1: "python is a programming language",
    2: "python is used for web development",
    3: "java is another programming language",
    4: "web development uses python and javascript"
}

# 构建词到文档ID的反向索引
inverted_index = defaultdict(set)
for doc_id, content in documents.items():
    words = content.lower().split()
    for word in words:
        inverted_index[word].add(doc_id)

print("\n反向索引:")
for word, doc_ids in sorted(inverted_index.items()):
    print(f"  {word}: {sorted(doc_ids)}")

# 查询示例
search_word = "python"
print(f"\n搜索'{search_word}': 出现在文档 {sorted(inverted_index[search_word])}")
```

### 2.4 高级模式：嵌套defaultdict

```python
# 创建二维defaultdict：默认值是defaultdict(int)
nested_dict = defaultdict(lambda: defaultdict(int))

# 填充数据：统计每个城市每个产品的销量
sales_data = [
    ('NYC', 'Laptop', 10),
    ('NYC', 'Phone', 15),
    ('LA', 'Laptop', 8),
    ('LA', 'Phone', 12),
    ('NYC', 'Laptop', 5),
    ('LA', 'Tablet', 7)
]

for city, product, quantity in sales_data:
    nested_dict[city][product] += quantity

print("嵌套defaultdict结构:")
for city, products in nested_dict.items():
    print(f"  {city}:")
    for product, total in products.items():
        print(f"    {product}: {total}")

# 转换为普通字典便于查看
import json
print(f"\nJSON格式:\n{json.dumps(nested_dict, indent=2)}")
```

## 第三章：OrderedDict——记得你的顺序

### 3.1 为什么需要有序字典？

在Python 3.7之前，普通字典（dict）是不保证插入顺序的。虽然Python 3.7+中字典已经保持插入顺序，但`OrderedDict`仍然有它的独特价值：

1. **显式表明顺序很重要**：代码可读性更好
2. **额外的顺序相关方法**：如`move_to_end()`、`popitem(last=True/False)`
3. **相等性比较考虑顺序**：两个`OrderedDict`顺序不同则不相等

```python
from collections import OrderedDict

# 创建OrderedDict
od = OrderedDict()
od['first'] = 1
od['second'] = 2
od['third'] = 3
od['fourth'] = 4

print("OrderedDict内容:")
for key, value in od.items():
    print(f"  {key}: {value}")

# 与普通字典的对比（Python 3.7+两者都保持顺序）
normal_dict = dict()
normal_dict['first'] = 1
normal_dict['second'] = 2
normal_dict['third'] = 3
normal_dict['fourth'] = 4

print("\n普通字典内容:")
for key, value in normal_dict.items():
    print(f"  {key}: {value}")
```

### 3.2 OrderedDict的独特方法

```python
# 重新创建OrderedDict
od = OrderedDict([('a', 1), ('b', 2), ('c', 3), ('d', 4)])
print(f"原始OrderedDict: {list(od.items())}")

# 1. move_to_end(): 将元素移动到末尾或开头
od.move_to_end('a')  # 默认移动到末尾
print(f"移动'a'到末尾: {list(od.items())}")  # [('b', 2), ('c', 3), ('d', 4), ('a', 1)]

od.move_to_end('c', last=False)  # 移动到开头
print(f"移动'c'到开头: {list(od.items())}")  # [('c', 3), ('b', 2), ('d', 4), ('a', 1)]

# 2. popitem(): 弹出最后一个或第一个元素
last_item = od.popitem()  # 默认弹出最后一个
print(f"弹出最后一个: {last_item}, 剩余: {list(od.items())}")

first_item = od.popitem(last=False)  # 弹出第一个
print(f"弹出第一个: {first_item}, 剩余: {list(od.items())}")

# 3. 相等性比较：OrderedDict考虑顺序
od1 = OrderedDict([('a', 1), ('b', 2)])
od2 = OrderedDict([('b', 2), ('a', 1)])
print(f"\nod1 == od2 (顺序不同): {od1 == od2}")  # False

# 普通字典不考虑顺序（Python 3.7+实际上考虑，但这是实现细节）
d1 = {'a': 1, 'b': 2}
d2 = {'b': 2, 'a': 1}
print(f"d1 == d2: {d1 == d2}")  # True
```

### 3.3 实战应用：LRU缓存实现

LRU（Least Recently Used，最近最少使用）缓存是一种常见的缓存淘汰策略。`OrderedDict`是实现LRU缓存的绝佳工具。

```python
from collections import OrderedDict

class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, capacity: int):
        self.cache = OrderedDict()
        self.capacity = capacity
    
    def get(self, key):
        """获取缓存值，如果存在则将其标记为最近使用"""
        if key not in self.cache:
            return -1
        
        # 将键移动到末尾（标记为最近使用）
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key, value):
        """添加或更新缓存值"""
        if key in self.cache:
            # 更新现有键的值并移动到末尾
            self.cache.move_to_end(key)
        
        self.cache[key] = value
        
        # 如果超过容量，移除最久未使用的（第一个）
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
    
    def __repr__(self):
        return f"LRUCache({list(self.cache.items())})"

# 使用示例
cache = LRUCache(3)

# 添加元素
cache.put('a', 1)
cache.put('b', 2)
cache.put('c', 3)
print(f"添加3个元素后: {cache}")

# 访问'a'，使其成为最近使用的
cache.get('a')
print(f"访问'a'后: {cache}")

# 添加新元素，应该淘汰最久未使用的'b'
cache.put('d', 4)
print(f"添加'd'后（淘汰'b'）: {cache}")
```

### 3.4 更多应用场景

```python
# 应用1：保持配置项的顺序
config = OrderedDict([
    ('database_host', 'localhost'),
    ('database_port', 5432),
    ('database_name', 'mydb'),
    ('database_user', 'admin'),
    ('database_password', 'secret')
])

print("配置项（按顺序）:")
for key, value in config.items():
    print(f"  {key}: {value}")

# 应用2：处理带顺序的CSV数据
import csv

def read_ordered_csv(filename):
    """读取CSV文件并保持列顺序"""
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        # 使用OrderedDict保持列顺序
        rows = [OrderedDict(row) for row in reader]
    return rows

# 假设有一个sample.csv文件，内容为：
# name,age,city
# Alice,30,NYC
# Bob,25,LA

# rows = read_ordered_csv('sample.csv')
# for row in rows:
#     print(dict(row))  # 保持name, age, city的顺序

# 应用3：实现FIFO（先进先出）队列
class FIFO:
    """使用OrderedDict实现FIFO缓存"""
    
    def __init__(self, capacity):
        self.cache = OrderedDict()
        self.capacity = capacity
    
    def add(self, key, value):
        if key in self.cache:
            # 如果已存在，先删除再重新添加（到末尾）
            del self.cache[key]
        
        self.cache[key] = value
        
        # 如果超过容量，移除最先添加的（第一个）
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
    
    def get(self, key):
        return self.cache.get(key, None)
    
    def __repr__(self):
        return f"FIFO({list(self.cache.items())})"

fifo = FIFO(3)
fifo.add('a', 1)
fifo.add('b', 2)
fifo.add('c', 3)
print(f"\nFIFO添加3个元素: {fifo}")
fifo.add('d', 4)  # 应该淘汰最先添加的'a'
print(f"添加'd'后: {fifo}")
```

## 第四章：deque——双端队列的艺术

### 4.1 deque vs list：为什么需要双端队列？

Python的列表（list）在末尾添加/删除元素是高效的（O(1)），但在开头添加/删除元素是低效的（O(n)），因为需要移动所有元素。`deque`（双端队列）在两端都能以O(1)时间复杂度进行添加和删除操作。

```python
from collections import deque
import time

# 性能对比：在开头插入元素
def test_performance():
    """对比list和deque在开头插入的性能"""
    n = 10000
    
    # 测试list
    start = time.time()
    lst = []
    for i in range(n):
        lst.insert(0, i)  # 在开头插入
    list_time = time.time() - start
    
    # 测试deque
    start = time.time()
    dq = deque()
    for i in range(n):
        dq.appendleft(i)  # 在开头插入
    deque_time = time.time() - start
    
    return list_time, deque_time

list_time, deque_time = test_performance()
print(f"在开头插入10000个元素:")
print(f"  list耗时: {list_time:.4f}秒")
print(f"  deque耗时: {deque_time:.4f}秒")
print(f"  deque比list快 {list_time/deque_time:.1f}倍")
```

### 4.2 deque的基本操作

```python
# 创建deque
dq = deque([1, 2, 3, 4])
print(f"原始deque: {dq}")

# 1. 两端操作
dq.append(5)           # 在右侧（末尾）添加
print(f"右侧添加5: {dq}")

dq.appendleft(0)       # 在左侧（开头）添加
print(f"左侧添加0: {dq}")

right_item = dq.pop()  # 从右侧（末尾）移除
print(f"右侧移除: {right_item}, 剩余: {dq}")

left_item = dq.popleft()  # 从左侧（开头）移除
print(f"左侧移除: {left_item}, 剩余: {dq}")

# 2. 扩展操作
dq.extend([5, 6, 7])       # 在右侧扩展
print(f"右侧扩展[5,6,7]: {dq}")

dq.extendleft([-1, -2])    # 在左侧扩展（注意顺序！）
print(f"左侧扩展[-1,-2]: {dq}")  # 注意：extendleft会反转顺序

# 3. 旋转操作
dq.rotate(1)  # 向右旋转1位（正数向右）
print(f"向右旋转1位: {dq}")

dq.rotate(-2)  # 向左旋转2位（负数向左）
print(f"向左旋转2位: {dq}")

# 4. 限制最大长度
limited_dq = deque(maxlen=3)
for i in range(5):
    limited_dq.append(i)
    print(f"添加{i}: {list(limited_dq)}")  # 当超过最大长度时，会自动从另一端移除
```

### 4.3 实战应用：滑动窗口算法

滑动窗口是算法中常见的技术，`deque`是实现滑动窗口的理想数据结构。

```python
from collections import deque

def sliding_window_maximum(nums, k):
    """
    返回每个滑动窗口的最大值
    
    参数:
    nums -- 整数数组
    k -- 窗口大小
    
    返回:
    每个滑动窗口最大值的列表
    """
    if not nums:
        return []
    
    result = []
    dq = deque()  # 存储索引，不是值
    
    for i in range(len(nums)):
        # 移除超出窗口范围的元素索引
        if dq and dq[0] < i - k + 1:
            dq.popleft()
        
        # 移除所有小于当前元素的元素索引
        # 因为如果当前元素更大，那么前面的小元素就不可能是窗口最大值了
        while dq and nums[dq[-1]] < nums[i]:
            dq.pop()
        
        # 添加当前元素索引
        dq.append(i)
        
        # 当窗口形成时，添加结果
        if i >= k - 1:
            result.append(nums[dq[0]])
    
    return result

# 示例
nums = [1, 3, -1, -3, 5, 3, 6, 7]
k = 3
result = sliding_window_maximum(nums, k)
print(f"数组: {nums}")
print(f"窗口大小: {k}")
print(f"滑动窗口最大值: {result}")
# 解释：
# 窗口位置              最大值
# [1  3  -1] -3  5  3  6  7       3
#  1 [3  -1  -3] 5  3  6  7       3
#  1  3 [-1  -3  5] 3  6  7       5
#  1  3  -1 [-3  5  3] 6  7       5
#  1  3  -1  -3 [5  3  6] 7       6
#  1  3  -1  -3  5 [3  6  7]      7
```

### 4.4 更多deque应用

```python
# 应用1：实现队列（FIFO）
queue = deque()

# 入队
queue.append('task1')
queue.append('task2')
queue.append('task3')
print(f"队列: {list(queue)}")

# 出队
while queue:
    task = queue.popleft()
    print(f"处理任务: {task}")

# 应用2：实现栈（LIFO）
stack = deque()

# 入栈
stack.append('item1')
stack.append('item2')
stack.append('item3')
print(f"\n栈: {list(stack)}")

# 出栈
while stack:
    item = stack.pop()
    print(f"弹出: {item}")

# 应用3：回文检查
def is_palindrome(text):
    """检查字符串是否为回文"""
    # 预处理：移除非字母数字字符，转为小写
    cleaned = ''.join(ch.lower() for ch in text if ch.isalnum())
    
    # 使用deque检查
    dq = deque(cleaned)
    
    while len(dq) > 1:
        if dq.popleft() != dq.pop():
            return False
    
    return True

test_cases = ["racecar", "A man, a plan, a canal: Panama", "hello"]
for test in test_cases:
    print(f"'{test}' 是回文: {is_palindrome(test)}")

# 应用4：任务调度器（轮询调度）
def round_robin_scheduler(tasks, time_quantum):
    """轮询调度算法"""
    queue = deque(tasks)
    result = []
    time = 0
    
    while queue:
        task = queue.popleft()
        
        # 模拟任务执行
        execution_time = min(time_quantum, task['burst_time'])
        task['burst_time'] -= execution_time
        time += execution_time
        
        print(f"时间 {time-execution_time}-{time}: 执行任务 {task['name']}")
        
        # 如果任务还没完成，重新加入队列
        if task['burst_time'] > 0:
            queue.append(task)
        else:
            result.append(task['name'])
    
    return result

tasks = [
    {'name': 'A', 'burst_time': 10},
    {'name': 'B', 'burst_time': 5},
    {'name': 'C', 'burst_time': 8}
]

print("\n轮询调度:")
completed = round_robin_scheduler(tasks, time_quantum=3)
print(f"完成顺序: {completed}")
```

## 第五章：ChainMap——字典的链式视图

### 5.1 ChainMap的概念：多层配置的解决方案

`ChainMap`将多个字典链接在一起，形成一个单一的视图。当查找一个键时，它会按顺序在链中的字典里搜索，直到找到为止。这对于处理多层配置（默认配置+用户配置+环境配置）特别有用。

```python
from collections import ChainMap

# 创建ChainMap
defaults = {'color': 'red', 'size': 'medium', 'theme': 'light'}
user_prefs = {'color': 'blue', 'language': 'en'}
environment = {'debug': True, 'theme': 'dark'}

# 创建配置链：优先使用环境变量，然后用户配置，最后默认值
config = ChainMap(environment, user_prefs, defaults)

print("配置链:")
print(f"  color: {config['color']}")      # 来自user_prefs: 'blue'
print(f"  size: {config['size']}")        # 来自defaults: 'medium'
print(f"  theme: {config['theme']}")      # 来自environment: 'dark'（最高优先级）
print(f"  language: {config['language']}") # 来自user_prefs: 'en'
print(f"  debug: {config['debug']}")       # 来自environment: True

# 注意：ChainMap是视图，修改会影响原始字典
config['color'] = 'green'
print(f"\n修改后user_prefs的color: {user_prefs['color']}")  # 变为'green'
```

### 5.2 ChainMap的方法与操作

```python
# 创建ChainMap
d1 = {'a': 1, 'b': 2}
d2 = {'b': 3, 'c': 4}
d3 = {'c': 5, 'd': 6}

chain = ChainMap(d1, d2, d3)
print(f"原始ChainMap: {dict(chain)}")

# 1. maps属性：访问底层字典列表
print(f"maps属性: {chain.maps}")

# 2. new_child()：添加新的字典到链的开头（最高优先级）
child_chain = chain.new_child({'e': 7, 'a': 8})
print(f"\nnew_child后: {dict(child_chain)}")
print(f"a的值: {child_chain['a']}")  # 8（来自新字典）

# 3. parents属性：获取除第一个字典外的所有字典
print(f"parents: {dict(child_chain.parents)}")  # 相当于原来的chain

# 4. 更新操作（只影响第一个字典）
chain['b'] = 100
print(f"\n修改chain['b']后:")
print(f"  chain['b']: {chain['b']}")  # 100
print(f"  d1['b']: {d1['b']}")       # 100（被修改）
print(f"  d2['b']: {d2['b']}")       # 3（不变）

# 5. 遍历：键的重复问题
print(f"\n所有键: {list(chain.keys())}")  # 注意：重复键只出现一次（第一次出现的）
print(f"所有值: {list(chain.values())}")
print(f"所有项: {list(chain.items())}")
```

### 5.3 实战应用：配置管理系统

```python
from collections import ChainMap
import os

class ConfigManager:
    """配置管理器：支持多层配置"""
    
    def __init__(self):
        # 配置层次：命令行参数 > 环境变量 > 用户配置 > 默认配置
        self.default_config = {
            'host': 'localhost',
            'port': 8080,
            'debug': False,
            'log_level': 'INFO',
            'max_connections': 100
        }
        
        self.user_config = {}
        self.env_config = {}
        self.cmdline_config = {}
        
        # 创建配置链
        self.config = ChainMap(
            self.cmdline_config,
            self.env_config,
            self.user_config,
            self.default_config
        )
    
    def load_from_env(self):
        """从环境变量加载配置"""
        # 环境变量通常有特定前缀，如APP_
        env_mapping = {
            'APP_HOST': 'host',
            'APP_PORT': 'port',
            'APP_DEBUG': 'debug',
            'APP_LOG_LEVEL': 'log_level',
            'APP_MAX_CONNECTIONS': 'max_connections'
        }
        
        for env_var, config_key in env_mapping.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                # 类型转换
                if config_key == 'port' or config_key == 'max_connections':
                    self.env_config[config_key] = int(value)
                elif config_key == 'debug':
                    self.env_config[config_key] = value.lower() == 'true'
                else:
                    self.env_config[config_key] = value
    
    def load_from_dict(self, config_dict):
        """从字典加载用户配置"""
        self.user_config.update(config_dict)
    
    def set_cmdline_arg(self, key, value):
        """设置命令行参数（最高优先级）"""
        self.cmdline_config[key] = value
    
    def get(self, key, default=None):
        """获取配置值"""
        return self.config.get(key, default)
    
    def __getitem__(self, key):
        return self.config[key]
    
    def __repr__(self):
        return f"ConfigManager({dict(self.config)})"

# 使用示例
config_manager = ConfigManager()

# 加载环境变量（假设设置了APP_HOST=192.168.1.100, APP_DEBUG=true）
# config_manager.load_from_env()

# 加载用户配置
config_manager.load_from_dict({
    'port': 9000,
    'log_level': 'DEBUG'
})

# 设置命令行参数（模拟）
config_manager.set_cmdline_arg('port', 9999)
config_manager.set_cmdline_arg('timeout', 30)

print("最终配置:")
for key in ['host', 'port', 'debug', 'log_level', 'max_connections', 'timeout']:
    value = config_manager.get(key, 'NOT SET')
    print(f"  {key}: {value} (来源: {config_manager.config.maps[0].get(key, '默认')})")
```

### 5.4 更多ChainMap应用

```python
# 应用1：变量作用域模拟
def simulate_scope():
    """模拟编程语言中的作用域链"""
    # 全局作用域
    global_scope = {'x': 1, 'y': 2}
    
    # 函数作用域
    function_scope = {'x': 10, 'z': 3}
    
    # 块作用域（如if、for内部）
    block_scope = {'x': 100, 'w': 4}
    
    # 作用域链：内层作用域优先
    scope_chain = ChainMap(block_scope, function_scope, global_scope)
    
    print("作用域链查找:")
    for var in ['x', 'y', 'z', 'w']:
        try:
            value = scope_chain[var]
            print(f"  {var} = {value}")
        except KeyError:
            print(f"  {var}: 未定义")

simulate_scope()

# 应用2：模板变量解析
def render_template(template, context, global_context=None):
    """渲染模板，支持局部和全局上下文"""
    if global_context is None:
        global_context = {}
    
    # 创建上下文链：局部上下文优先于全局上下文
    context_chain = ChainMap(context, global_context)
    
    # 简单模板渲染：替换{{变量名}}
    result = template
    for key, value in context_chain.items():
        placeholder = f"{{{{{key}}}}}"
        result = result.replace(placeholder, str(value))
    
    return result

# 使用示例
global_vars = {'company': 'TechCorp', 'year': 2024}
local_vars = {'username': 'Alice', 'role': 'Developer'}

template = """
Welcome to {{company}}, {{username}}!
Your role: {{role}}
Copyright {{year}}
"""

rendered = render_template(template, local_vars, global_vars)
print(f"\n模板渲染结果:\n{rendered}")

# 应用3：命令行参数优先级处理
def parse_arguments(defaults, config_file_args, env_args, cmdline_args):
    """解析参数，优先级：命令行 > 环境变量 > 配置文件 > 默认值"""
    chain = ChainMap(cmdline_args, env_args, config_file_args, defaults)
    
    # 转换为普通字典（可选）
    return dict(chain.items())

# 示例参数
defaults = {'verbose': False, 'output': 'stdout', 'timeout': 30}
config_args = {'verbose': True, 'input': 'data.txt'}
env_args = {'timeout': 60, 'output': 'file.txt'}
cmd_args = {'input': 'input.csv', 'mode': 'fast'}

final_args = parse_arguments(defaults, config_args, env_args, cmd_args)
print(f"\n最终参数: {final_args}")
```

## 第六章：namedtuple——给元组起名字

### 6.1 namedtuple的意义：自文档化的元组

普通元组使用数字索引访问元素，代码可读性差：

```python
# 使用普通元组表示点
point = (2, 3)
print(f"x坐标: {point[0]}, y坐标: {point[1]}")  # 不直观
```

`namedtuple`让元组变得自文档化：

```python
from collections import namedtuple

# 定义namedtuple类型
Point = namedtuple('Point', ['x', 'y'])

# 创建实例
p = Point(2, 3)
print(f"x坐标: {p.x}, y坐标: {p.y}")  # 直观！
```

### 6.2 namedtuple的创建与使用

```python
from collections import namedtuple

# 创建namedtuple类型
# 方式1：使用字段名列表
Person = namedtuple('Person', ['name', 'age', 'job'])

# 方式2：使用空格分隔的字段名字符串
Car = namedtuple('Car', 'make model year color')

# 方式3：使用逗号分隔的字段名字符串
Coordinate = namedtuple('Coordinate', 'x, y, z')

# 创建实例
person = Person('Alice', 30, 'Engineer')
car = Car('Toyota', 'Camry', 2020, 'blue')
coord = Coordinate(10, 20, 30)

print(f"Person: {person}")
print(f"Car: {car}")
print(f"Coordinate: {coord}")

# 访问字段
print(f"\n访问字段:")
print(f"  person.name: {person.name}")
print(f"  car.year: {car.year}")
print(f"  coord.x: {coord.x}")

# 索引访问仍然可用（向后兼容）
print(f"  person[0]: {person[0]}")

# 转换为字典
print(f"\n转换为字典: {person._asdict()}")

# 替换字段值（创建新实例）
new_person = person._replace(age=31)
print(f"修改年龄后: {new_person}")

# 获取字段名
print(f"字段名: {person._fields}")

# 从可迭代对象创建
data = ['Bob', 25, 'Designer']
person2 = Person._make(data)
print(f"从列表创建: {person2}")
```

### 6.3 高级特性与参数

```python
from collections import namedtuple

# 1. 默认值参数（Python 3.7+）
# 注意：有默认值的字段必须放在没有默认值的字段后面
Person = namedtuple('Person', ['name', 'age', 'job'], defaults=['Unknown', 'Unemployed'])

p1 = Person('Alice')  # age和job使用默认值
p2 = Person('Bob', 25)  # job使用默认值
p3 = Person('Charlie', 30, 'Engineer')  # 提供所有值

print(f"带默认值的Person:")
print(f"  p1: {p1}")
print(f"  p2: {p2}")
print(f"  p3: {p3}")

# 2. 字段重命名（当字段名是Python关键字或重复时）
# 如果字段名无效，rename=True会自动重命名
try:
    # 这会导致错误，因为'class'是关键字
    # Student = namedtuple('Student', ['name', 'class', 'grade'])
    pass
except ValueError as e:
    print(f"\n错误: {e}")

# 使用rename=True自动重命名无效字段
Student = namedtuple('Student', ['name', 'class', 'grade'], rename=True)
s = Student('Alice', 'Math', 'A')
print(f"自动重命名的字段名: {s._fields}")  # ('name', '_1', 'grade')

# 3. 类型注解支持（Python 3.6+）
from typing import NamedTuple

class Employee(NamedTuple):
    """使用typing.NamedTuple，支持类型注解"""
    name: str
    age: int
    department: str = 'Unknown'  # 默认值

e = Employee('David', 28, 'IT')
print(f"\n带类型注解的NamedTuple: {e}")
print(f"类型: {type(e)}")
```

### 6.4 实战应用：数据处理与记录

```python
from collections import namedtuple
import csv

# 应用1：处理CSV数据
def read_csv_as_namedtuples(filename, typename='Record'):
    """将CSV文件读取为namedtuple列表"""
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)  # 第一行是标题
        
        # 动态创建namedtuple类型
        Record = namedtuple(typename, headers)
        
        # 创建记录列表
        records = [Record(*row) for row in reader]
    
    return records

# 假设有一个employees.csv文件：
# name,age,department,salary
# Alice,30,Engineering,80000
# Bob,25,Marketing,60000
# Charlie,35,Sales,70000

# records = read_csv_as_namedtuples('employees.csv', 'Employee')
# for record in records:
#     print(f"{record.name}: {record.department}, ${record.salary}")

# 应用2：表示几何图形
Shape = namedtuple('Shape', 'shape_type points color')

Point = namedtuple('Point', 'x y')
Rectangle = namedtuple('Rectangle', 'x y width height')
Circle = namedtuple('Circle', 'x y radius')

# 创建图形
shapes = [
    Shape('rectangle', Rectangle(0, 0, 100, 50), 'blue'),
    Shape('circle', Circle(50, 50, 25), 'red'),
    Shape('polygon', [Point(0, 0), Point(10, 0), Point(5, 10)], 'green')
]

def calculate_area(shape):
    """计算图形面积"""
    if shape.shape_type == 'rectangle':
        rect = shape.points
        return rect.width * rect.height
    elif shape.shape_type == 'circle':
        circle = shape.points
        import math
        return math.pi * circle.radius ** 2
    elif shape.shape_type == 'polygon':
        # 简化：假设是三角形
        points = shape.points
        if len(points) == 3:
            # 使用海伦公式
            a = distance(points[0], points[1])
            b = distance(points[1], points[2])
            c = distance(points[2], points[0])
            s = (a + b + c) / 2
            return (s * (s - a) * (s - b) * (s - c)) ** 0.5
    return 0

def distance(p1, p2):
    """计算两点距离"""
    return ((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2) ** 0.5

print("\n图形面积计算:")
for shape in shapes:
    area = calculate_area(shape)
    print(f"  {shape.shape_type} ({shape.color}): {area:.2f}")

# 应用3：表示数据库记录
User = namedtuple('User', 'id username email created_at is_active')

# 模拟从数据库获取的数据
users_data = [
    (1, 'alice', 'alice@example.com', '2023-01-01', True),
    (2, 'bob', 'bob@example.com', '2023-02-01', True),
    (3, 'charlie', 'charlie@example.com', '2022-12-01', False)
]

users = [User(*data) for data in users_data]

print("\n活跃用户:")
active_users = [user for user in users if user.is_active]
for user in active_users:
    print(f"  {user.username} ({user.email})")

# 应用4：配置项管理
ConfigItem = namedtuple('ConfigItem', 'key value type description')

config_items = [
    ConfigItem('server.host', 'localhost', str, '服务器主机名'),
    ConfigItem('server.port', 8080, int, '服务器端口'),
    ConfigItem('debug.enabled', False, bool, '是否启用调试模式'),
    ConfigItem('database.url', 'sqlite:///app.db', str, '数据库连接URL')
]

print("\n配置项:")
for item in config_items:
    print(f"  {item.key}: {item.value} ({item.type.__name__}) - {item.description}")
```

## 第七章：其他Collections类型与总结

### 7.1 UserDict、UserList、UserString

这三个类用于创建自定义的字典、列表和字符串类。它们的主要用途是作为基类，让你可以继承并添加自定义行为，同时保持与内置类型相同的接口。

```python
from collections import UserDict, UserList, UserString

# 1. UserDict：创建自定义字典
class CaseInsensitiveDict(UserDict):
    """不区分大小写的字典"""
    
    def __setitem__(self, key, value):
        # 存储时统一转换为小写
        super().__setitem__(key.lower(), value)
    
    def __getitem__(self, key):
        # 获取时也转换为小写
        return super().__getitem__(key.lower())
    
    def __contains__(self, key):
        return super().__contains__(key.lower())

cid = CaseInsensitiveDict()
cid['Name'] = 'Alice'
print(f"cid['name']: {cid['name']}")  # Alice
print(f"cid['NAME']: {cid['NAME']}")  # Alice
print(f"'NaMe' in cid: {'NaMe' in cid}")  # True

# 2. UserList：创建自定义列表
class SortedList(UserList):
    """自动排序的列表"""
    
    def __init__(self, initlist=None):
        super().__init__(initlist)
        self.sort()
    
    def append(self, item):
        super().append(item)
        self.sort()
    
    def extend(self, other):
        super().extend(other)
        self.sort()

sorted_list = SortedList([3, 1, 4, 2])
print(f"\n排序列表: {sorted_list}")
sorted_list.append(0)
print(f"添加0后: {sorted_list}")

# 3. UserString：创建自定义字符串
class ReversibleString(UserString):
    """可反转的字符串"""
    
    def reverse(self):
        return self.data[::-1]

rs = ReversibleString("Hello, World!")
print(f"\n原始字符串: {rs}")
print(f"反转后: {rs.reverse()}")
```

### 7.2 总结与选择指南

经过对Collections模块的全面探索，我们来总结一下各个数据结构的适用场景：

| 数据结构 | 主要特点 | 典型应用场景 |
|---------|---------|------------|
| **Counter** | 计数、统计、频率分析 | 词频统计、数据分析、投票统计 |
| **defaultdict** | 自动处理缺失键 | 分组、索引构建、树状结构 |
| **OrderedDict** | 保持插入顺序，顺序相关操作 | LRU缓存、配置管理、有序映射 |
| **deque** | 双端高效操作，线程安全 | 队列、栈、滑动窗口、回文检查 |
| **ChainMap** | 多层字典链式查找 | 配置管理、作用域模拟、模板渲染 |
| **namedtuple** | 自文档化元组，轻量级对象 | 数据记录、小型类替代、CSV处理 |

### 7.3 性能考虑与最佳实践

```python
from collections import defaultdict, deque, Counter
import timeit

# 性能对比测试
def test_performance():
    """测试不同数据结构的性能"""
    
    # 测试1：defaultdict vs dict.get
    setup1 = """
from collections import defaultdict
data = [str(i) for i in range(10000)]
"""
    
    stmt1_dict = """
d = {}
for item in data:
    if item in d:
        d[item] += 1
    else:
        d[item] = 1
"""
    
    stmt1_defaultdict = """
dd = defaultdict(int)
for item in data:
    dd[item] += 1
"""
    
    time_dict = timeit.timeit(stmt1_dict, setup1, number=100)
    time_defaultdict = timeit.timeit(stmt1_defaultdict, setup1, number=100)
    
    print(f"计数性能:")
    print(f"  普通字典: {time_dict:.4f}秒")
    print(f"  defaultdict: {time_defaultdict:.4f}秒")
    print(f"  性能提升: {time_dict/time_defaultdict:.2f}倍")
    
    # 测试2：deque vs list（队列操作）
    setup2 = """
from collections import deque
n = 1000
"""
    
    stmt2_list = """
queue = []
for i in range(n):
    queue.append(i)
for i in range(n):
    queue.pop(0)
"""
    
    stmt2_deque = """
queue = deque()
for i in range(n):
    queue.append(i)
for i in range(n):
    queue.popleft()
"""
    
    time_list = timeit.timeit(stmt2_list, setup2, number=100)
    time_deque = timeit.timeit(stmt2_deque, setup2, number=100)
    
    print(f"\n队列操作性能:")
    print(f"  列表: {time_list:.4f}秒")
    print(f"  deque: {time_deque:.4f}秒")
    print(f"  性能提升: {time_list/time_deque:.2f}倍")

test_performance()
```

### 7.4 综合实战：简单的数据分析管道

```python
from collections import Counter, defaultdict, namedtuple
import csv
from datetime import datetime

# 定义数据结构
SaleRecord = namedtuple('SaleRecord', ['date', 'product', 'category', 'amount', 'region'])

class SalesAnalyzer:
    """销售数据分析器"""
    
    def __init__(self, filename):
        self.records = self._load_records(filename)
    
    def _load_records(self, filename):
        """加载销售记录"""
        records = []
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 解析日期
                date = datetime.strptime(row['date'], '%Y-%m-%d')
                
                record = SaleRecord(
                    date=date,
                    product=row['product'],
                    category=row['category'],
                    amount=float(row['amount']),
                    region=row['region']
                )
                records.append(record)
        return records
    
    def total_sales(self):
        """总销售额"""
        return sum(record.amount for record in self.records)
    
    def sales_by_category(self):
        """按类别统计销售额"""
        category_sales = defaultdict(float)
        for record in self.records:
            category_sales[record.category] += record.amount
        return dict(category_sales)
    
    def top_products(self, n=5):
        """最畅销的产品"""
        product_counter = Counter(record.product for record in self.records)
        return product_counter.most_common(n)
    
    def monthly_sales(self):
        """月度销售额"""
        monthly = defaultdict(float)
        for record in self.records:
            # 使用年月作为键
            key = record.date.strftime('%Y-%m')
            monthly[key] += record.amount
        return dict(monthly)
    
    def regional_performance(self):
        """地区表现分析"""
        regional_stats = defaultdict(lambda: {'count': 0, 'total': 0.0})
        for record in self.records:
            stats = regional_stats[record.region]
            stats['count'] += 1
            stats['total'] += record.amount
        
        # 计算平均
        result = {}
        for region, stats in regional_stats.items():
            result[region] = {
                'total_sales': stats['total'],
                'transaction_count': stats['count'],
                'average_sale': stats['total'] / stats['count']
            }
        return result

# 使用示例（假设有sales_data.csv文件）
# analyzer = SalesAnalyzer('sales_data.csv')
# print(f"总销售额: ${analyzer.total_sales():.2f}")
# print(f"按类别销售: {analyzer.sales_by_category()}")
# print(f"最畅销产品: {analyzer.top_products()}")
# print(f"月度销售趋势: {analyzer.monthly_sales()}")
# print(f"地区表现: {analyzer.regional_performance()}")
```

## 结语：掌握Collections，提升Python编程水平

Collections模块是Python标准库中的一颗明珠，它提供的数据结构虽然不是日常编程中的"必需品"，但却是提升代码质量、提高开发效率的"利器"。

**学习建议**：
1. **从实际问题出发**：不要为了用而用，当遇到普通数据结构难以优雅解决的问题时，再考虑Collections
2. **理解内部原理**：了解每个数据结构的时间复杂度，知道为什么在某些场景下它们更高效
3. **结合类型注解**：Python 3.6+支持类型注解，结合使用能让代码更清晰
4. **不要过度设计**：对于简单需求，普通列表和字典可能更合适

记住，好的程序员不是知道所有工具的人，而是**知道在什么场景选择什么工具**的人。Collections模块为你提供了更多选择，让你在面对复杂问题时能有更优雅的解决方案。

祝你在Python编程之路上越走越远！