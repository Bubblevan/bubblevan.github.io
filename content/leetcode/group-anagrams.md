# 49. 字母异位词分组

---

## 第一部分：题目信息

### 题目描述

给你一个字符串数组，请你将**字母异位词**组合在一起。可以按任意顺序返回结果列表。

**字母异位词**：由重新排列源单词的字母得到的一个新单词，所有源单词中的字母通常恰好只用一次。

### 示例

#### 示例 1

**输入：**
```python
strs = ["eat", "tea", "tan", "ate", "nat", "bat"]
```

**输出：**
```python
[["bat"],["nat","tan"],["ate","eat","tea"]]
```

**解释：**
- 在 `strs` 中没有字符串可以通过重新排列来形成 "bat"
- 字符串 "nat" 和 "tan" 是字母异位词，因为它们可以重新排列以形成彼此
- 字符串 "ate"、"eat" 和 "tea" 是字母异位词，因为它们可以重新排列以形成彼此

#### 示例 2

**输入：**
```python
strs = [""]
```

**输出：**
```python
[[""]]
```

#### 示例 3

**输入：**
```python
strs = ["a"]
```

**输出：**
```python
[["a"]]
```

### 提示

- `1 <= strs.length <= 10^4`
- `0 <= strs[i].length <= 100`
- `strs[i]` 仅包含小写字母

### 代码模板
```python
class Solution:
    def groupAnagrams(self, strs: List[str]) -> List[List[str]]:
        
```


---

## 方法一：排序法

### 核心思路

#### 为什么排序后的字符串相同？

**字母异位词的定义**：由重新排列源单词的字母得到的新单词，所有源单词中的字母通常恰好只用一次。

**关键洞察**：如果两个字符串是字母异位词，那么它们包含的字母种类和数量完全相同，只是顺序不同。

**排序的作用**：将字符串按字母顺序排序后，所有字母异位词都会变成相同的字符串。

**示例：**
- "eat" 排序后是 "aet"（按字母顺序：a, e, t）
- "tea" 排序后是 "aet"（按字母顺序：a, e, t）
- "ate" 排序后是 "aet"（按字母顺序：a, e, t）

这三个不同的字符串排序后都变成了 "aet"，所以它们是字母异位词。

#### 算法步骤

1. **创建字典**：使用 `defaultdict(list)` 创建一个字典，value 默认是空列表
2. **遍历字符串**：对每个字符串，将其排序并拼接成字符串作为 key
3. **分组存储**：将原始字符串添加到对应的列表中
4. **返回结果**：返回字典中所有的 value

### 关键知识点

#### 1. sorted() 和 "".join() 的使用

**sorted() 函数：**

`sorted()` 是 Python 的内置函数（不是方法），用于对可迭代对象进行排序。

```python
sorted("eat")  # 返回列表：['a', 'e', 't']
```

**执行过程：**
1. `sorted("eat")` 将字符串 "eat" 的每个字符排序，返回列表 `['a', 'e', 't']`
2. `"".join(['a', 'e', 't'])` 用空字符串 `""` 将列表中的元素连接，得到字符串 `"aet"`

**完整示例：**
```python
s = "eat"
sorted_result = sorted(s)        # ['a', 'e', 't']（列表）
key = "".join(sorted_result)     # "aet"（字符串）
print(key)  # 输出：aet
```

**为什么需要 join？**

- Python 字典的 Key 必须是**不可变对象**（immutable）
- 列表是可变的（mutable），**不能作为字典的 key**
- 所以我们要用 `"".join()` 把列表拼回字符串

#### 2. 字典的 value 可以是列表

**重要概念**：字典的 value 可以是任何类型，包括列表。

```python
# 初始状态
hashmap["aet"] = ["eat"]  # hashmap["aet"] 的值是一个列表：["eat"]

# 现在 hashmap["aet"] 指向这个列表
# 我们可以对这个列表进行操作
hashmap["aet"].append("tea")  # 在列表末尾添加 "tea"

# 现在 hashmap["aet"] 的值变成了：["eat", "tea"]
```

**关键点：**
- `hashmap["aet"]` 返回的是列表对象本身，不是列表的副本
- 所以可以直接对这个列表调用 `append()` 方法
- 列表是**可变对象（mutable）**，可以修改

**可视化：**
```
执行前：
hashmap = {
    "aet": ["eat"]  ← 这是一个列表，包含一个元素
}

执行 hashmap["aet"].append("tea") 后：
hashmap = {
    "aet": ["eat", "tea"]  ← 同一个列表，现在包含两个元素
}
```

#### 3. collections.defaultdict(list)

**普通 dict 的问题：**

```python
# 普通 dict：如果你访问一个不存在的 key，会报错
hashmap = {}
hashmap["key"].append("value")  # ❌ KeyError: 'key'
```

**defaultdict 的解决方案：**

```python
from collections import defaultdict

# defaultdict(list) 就像一个"慷慨的房东"
# 如果你找的房间不存在，他会立刻给你建一个空的列表房间
hashmap = defaultdict(list)
hashmap["key"].append("value")  # ✅ 自动创建空列表，不会报错
```

**`list` 参数的含义：**

`list` 参数告诉 `defaultdict`：**当遇到不存在的 key 时，自动创建一个空列表 `[]` 作为默认值**。

**执行过程：**
```python
hashmap = defaultdict(list)

# 第一次访问 "aet"（key 不存在）
hashmap["aet"].append("eat")

# defaultdict 内部发生了什么？
# 1. 检查 "aet" 是否存在 → 不存在
# 2. 调用 list() 创建空列表 → []
# 3. 将 hashmap["aet"] = []
# 4. 然后执行 .append("eat")
# 5. 结果：hashmap["aet"] = ["eat"]
```

**其他类型的 defaultdict：**

`defaultdict` 可以接受任何**可调用对象**作为参数：

```python
from collections import defaultdict

# 默认值是空列表
hashmap1 = defaultdict(list)        # 访问不存在的 key → 自动创建 []
hashmap1["key"].append("value")     # ✅ 可以

# 默认值是 0（整数）
hashmap2 = defaultdict(int)         # 访问不存在的 key → 自动创建 0
hashmap2["count"] += 1              # ✅ 可以，hashmap2["count"] = 1

# 默认值是空集合
hashmap3 = defaultdict(set)         # 访问不存在的 key → 自动创建 set()
hashmap3["key"].add("value")        # ✅ 可以

# 默认值是空字符串
hashmap4 = defaultdict(str)         # 访问不存在的 key → 自动创建 ""
hashmap4["key"] += "hello"          # ✅ 可以，hashmap4["key"] = "hello"
```

**对比：**

```python
# 使用普通 dict（需要判断 key 是否存在）
hashmap = {}
if key not in hashmap:
    hashmap[key] = []
hashmap[key].append(value)

# 使用 defaultdict（自动处理）
hashmap = defaultdict(list)
hashmap[key].append(value)  # 更简洁！
```

**普通 dict 的问题：**
```python
# 普通 dict：如果你访问一个不存在的 key，会报错
hashmap = {}
hashmap["key"].append("value")  # ❌ KeyError: 'key'
```

**defaultdict 的解决方案：**

```python
from collections import defaultdict

# defaultdict(list) 就像一个"慷慨的房东"
# 如果你找的房间不存在，他会立刻给你建一个空的列表房间
hashmap = defaultdict(list)
hashmap["key"].append("value")  # ✅ 自动创建空列表，不会报错
```
> defaultdict 可以接受任何可调用对象作为参数:
```
from collections import defaultdict

# 默认值是空列表
hashmap1 = defaultdict(list)        # 访问不存在的 key → 自动创建 []
hashmap1["key"].append("value")     # ✅ 可以

# 默认值是 0（整数）
hashmap2 = defaultdict(int)         # 访问不存在的 key → 自动创建 0
hashmap2["count"] += 1              # ✅ 可以，hashmap2["count"] = 1

# 默认值是空集合
hashmap3 = defaultdict(set)         # 访问不存在的 key → 自动创建 set()
hashmap3["key"].add("value")        # ✅ 可以

# 默认值是空字符串
hashmap4 = defaultdict(str)         # 访问不存在的 key → 自动创建 ""
hashmap4["key"] += "hello"          # ✅ 可以，hashmap4["key"] = "hello"
```
**对比：**

```python
# 使用普通 dict（需要判断 key 是否存在）
hashmap = {}
if key not in hashmap:
    hashmap[key] = []
hashmap[key].append(value)

# 使用 defaultdict（自动处理）
hashmap = defaultdict(list)
hashmap[key].append(value)  # 更简洁！
```


### 完整代码

```python
from collections import defaultdict

class Solution:
    def groupAnagrams(self, strs: List[str]) -> List[List[str]]:
        # 使用 defaultdict 可以避免判断 key 是否存在的繁琐步骤
        # 如果 key 不存在，它会自动创建一个空列表 []
        hashmap = defaultdict(list)
        
        for s in strs:
            # 1. 将字符串排序。例如 "eat" -> ['a', 'e', 't']
            # 2. join 回字符串 -> "aet" (作为 Key)
            key = "".join(sorted(s))
            
            # 3. 将原字符串放入对应的分组中
            hashmap[key].append(s)
            
        # 返回字典中所有的 value 即可
        return list(hashmap.values())
```

### 算法复杂度

- **时间复杂度**：O(n × k log k)，其中 n 是字符串数组的长度，k 是字符串的平均长度
  - 遍历所有字符串：O(n)
  - 对每个字符串排序：O(k log k)
- **空间复杂度**：O(n × k)，用于存储结果

---

## 方法二：计数法

### 核心思路

**计数法的思想**：统计每个字母出现的次数，用字母频率作为 key。

**为什么可行？**

字母异位词的特点是：**每个字母出现的次数相同**。

例如：
- "eat" 的特征：a:1, e:1, t:1，其他字母全是 0
- "tea" 的特征：a:1, e:1, t:1，其他字母全是 0
- "ate" 的特征：a:1, e:1, t:1，其他字母全是 0

这三个字符串的字母频率完全相同，所以它们是字母异位词。

### 关键知识点

#### 1. 计数数组

**Python 中没有传统意义上的"数组"，只有列表（list）**

在 Python 中，我们使用**列表（list）**来实现类似数组的功能。

**创建长度为 26 的列表的几种方式：**

**方式一：使用 `*` 运算符（最常用）**
```python
count = [0] * 26  # 创建一个包含 26 个 0 的列表
```

**执行过程：**
- `[0]` 是一个包含一个元素 0 的列表
- `* 26` 表示将这个列表重复 26 次
- 结果：`[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]`

**方式二：使用列表推导式**
```python
count = [0 for _ in range(26)]  # 创建一个包含 26 个 0 的列表
```

**`_` 是什么？**

在 Python 中，`_` 是一个**约定俗成的占位符**，表示"这个变量我不需要用到，只是占个位置"。

**列表推导式的语法：**
```python
[表达式 for 变量 in 可迭代对象]
```

**在这个例子中：**
- `0` 是表达式（我们要创建的值）
- `_` 是变量（但我们不需要用到它）
- `range(26)` 是可迭代对象（生成 0 到 25 的数字）

**执行过程：**
```python
# range(26) 生成：0, 1, 2, 3, ..., 25
# 对于每个数字（虽然我们不用它），都创建一个 0
# 结果：[0, 0, 0, 0, ..., 0]（26 个 0）
```

**为什么用 `_` 而不是 `i`？**

```python
# 方式 A：用 _（推荐，表示不需要这个变量）
count = [0 for _ in range(26)]

# 方式 B：用 i（也可以，但表示你可能会用到这个变量）
count = [0 for i in range(26)]  # i 的值是 0, 1, 2, ..., 25，但我们没用它
```

**如果我们需要用到索引值，就用 `i`：**
```python
# 创建 [0, 1, 2, 3, ..., 25]
count = [i for i in range(26)]  # 这里需要用到 i 的值

# 创建 [0, 2, 4, 6, ..., 50]（偶数）
count = [i * 2 for i in range(26)]  # 这里需要用到 i 的值
```

**与 C 语言的对比：**

**C 语言：**
```c
int count[26];  // 声明数组
int i;          // 必须在外定义循环变量
for (i = 0; i < 26; i++) {
    count[i] = 0;  // 必须使用 i 来访问数组
}
```

**Python：**
```python
# 方式一：不需要定义变量（推荐）
count = [0] * 26

# 方式二：列表推导式，_ 是占位符，不需要在外面定义
count = [0 for _ in range(26)]

# 方式三：传统循环，i 在 for 循环中自动定义（不需要在外面定义）
count = []
for i in range(26):  # i 在这里自动定义，作用域只在循环内
    count.append(0)
```

**关键区别：**

| 语言 | 循环变量定义 | 作用域 |
|------|------------|--------|
| **C 语言** | 必须在循环外定义 | 循环外也能访问 |
| **Python** | 在 `for` 语句中自动定义 | 只在循环内有效（Python 3） |

**方式三：使用循环**
```python
count = []
for i in range(26):  # i 在这里自动定义，不需要在外面定义
    count.append(0)
```

**注意：** 在 Python 3 中，`for` 循环中的变量（如 `i`）只在循环内有效，循环结束后就不可访问了（与 C 语言不同）。

**方式四：使用 `list()` 和 `range()`**
```python
count = list(range(26))  # 创建 [0, 1, 2, 3, ..., 25]，但我们需要全 0
# 所以这种方式不适合，除非后续全部重置为 0
```

**在这个问题中，我们使用方式一：**
```python
count = [0] * 26  # 创建一个包含 26 个 0 的列表
```

**这个列表的每个位置对应一个字母：**
- `count[0]` 对应字母 'a'
- `count[1]` 对应字母 'b'
- `count[2]` 对应字母 'c'
- ...
- `count[25]` 对应字母 'z'

**验证：**
```python
count = [0] * 26
print(len(count))  # 输出：26
print(count)       # 输出：[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

**注意：浅拷贝问题（在这个场景下不是问题）**

`[0] * 26` 对于**不可变对象**（如整数 0）是安全的，因为每个位置都是独立的。

```python
# ✅ 对于整数（不可变对象），这是安全的
count = [0] * 26
count[0] = 1  # 只修改 count[0]，不影响其他位置
print(count)  # [1, 0, 0, 0, ..., 0]
```

但如果列表包含**可变对象**（如列表），需要注意浅拷贝问题：

```python
# ⚠️ 对于列表（可变对象），会有问题
matrix = [[]] * 3  # 创建 3 个空列表
matrix[0].append(1)  # 修改第一个列表
print(matrix)  # [[1], [1], [1]]  # 所有列表都被修改了！

# ✅ 正确的方式
matrix = [[] for _ in range(3)]  # 创建 3 个独立的空列表
matrix[0].append(1)  # 只修改第一个列表
print(matrix)  # [[1], [], []]  # 只有第一个列表被修改
```

**在我们的问题中，因为都是整数（不可变对象），所以 `[0] * 26` 是完全安全的。**

#### 2. ord() 函数

**ord() 函数**：返回字符的 ASCII 码值。

```python
ord('a')  # 97
ord('b')  # 98
ord('z')  # 122
```

**如何将字母映射到 0-25？**

```python
ord('a') - ord('a')  # 0
ord('b') - ord('a')  # 1
ord('c') - ord('a')  # 2
ord('z') - ord('a')  # 25
```

**示例：**
```python
char = 'e'
index = ord(char) - ord('a')  # ord('e') - ord('a') = 101 - 97 = 4
count[index] += 1  # count[4] += 1，表示字母 'e' 出现了一次
```

#### 3. 为什么用 tuple 而不是 list？

**关键点**：Python 字典的 key 必须是**不可变对象**（immutable）。

- **列表（list）**：可变对象，**不能作为字典的 key**
- **元组（tuple）**：不可变对象，**可以作为字典的 key**

```python
# ❌ 错误：列表不能作为 key
count = [1, 0, 0, 0, 1, 0, ..., 1]
ans[count] = ["eat"]  # TypeError: unhashable type: 'list'

# ✅ 正确：元组可以作为 key
count = [1, 0, 0, 0, 1, 0, ..., 1]
ans[tuple(count)] = ["eat"]  # 正确！
```

**tuple() 函数**：将列表转换为元组。

```python
count = [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
key = tuple(count)  # (1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0)
```

### 完整代码

```python
from collections import defaultdict

class Solution:
    def groupAnagrams(self, strs: List[str]) -> List[List[str]]:
        ans = defaultdict(list)
        
        for s in strs:
            # 创建一个长度为 26 的计数器
            # 每个位置对应一个字母：count[0]='a', count[1]='b', ..., count[25]='z'
            count = [0] * 26
            
            # 统计每个字母出现的次数
            for char in s:
                # ord(char) 获取字符的 ASCII 码
                # 减去 ord('a') 得到 0-25 的索引（'a'->0, 'b'->1, ..., 'z'->25）
                count[ord(char) - ord('a')] += 1
            
            # 将列表转为元组，作为字典的 Key
            # 元组是不可变的，可以作为字典的 key
            ans[tuple(count)].append(s)
        
        return list(ans.values())
```

### 执行过程示例

**输入：** `strs = ["eat", "tea", "ate"]`

**执行过程：**

```python
# 处理 "eat"
count = [0] * 26
# 遍历 "eat" 的每个字符
count[ord('e') - ord('a')] += 1  # count[4] = 1
count[ord('a') - ord('a')] += 1  # count[0] = 1
count[ord('t') - ord('a')] += 1  # count[19] = 1
# count = [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
ans[tuple(count)] = ["eat"]

# 处理 "tea"
count = [0] * 26
count[ord('t') - ord('a')] += 1  # count[19] = 1
count[ord('e') - ord('a')] += 1  # count[4] = 1
count[ord('a') - ord('a')] += 1  # count[0] = 1
# count = [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
# tuple(count) 和之前相同，所以添加到同一组
ans[tuple(count)].append("tea")  # ans[tuple(count)] = ["eat", "tea"]

# 处理 "ate"
count = [0] * 26
count[ord('a') - ord('a')] += 1  # count[0] = 1
count[ord('t') - ord('a')] += 1  # count[19] = 1
count[ord('e') - ord('a')] += 1  # count[4] = 1
# count = [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
# tuple(count) 和之前相同，所以添加到同一组
ans[tuple(count)].append("ate")  # ans[tuple(count)] = ["eat", "tea", "ate"]

# 返回结果
return [["eat", "tea", "ate"]]
```

**可视化说明：**

```
字符串 "eat" 的计数过程：
字符:  e    a    t
索引:  4    0    19
count: [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
       a   b   c   d   e   f   g   h   i   j   k   l   m   n   o   p   q   r   s   t   u   v   w   x   y   z
       0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16  17  18  19  20  21  22  23  24  25
```

### 算法复杂度

- **时间复杂度**：O(n × k)，其中 n 是字符串数组的长度，k 是字符串的平均长度
  - 遍历所有字符串：O(n)
  - 对每个字符串统计字母频率：O(k)
  - **比排序法更快**：不需要排序，只需要遍历一次字符串
- **空间复杂度**：O(n × k)，用于存储结果
  - 额外空间：O(26) = O(1) 用于计数数组（常数空间）

### 两种方法对比

| 方法 | 时间复杂度 | 空间复杂度 | 优点 | 缺点 |
|------|-----------|-----------|------|------|
| **排序法** | O(n × k log k) | O(n × k) | 思路直观，代码简单 | 需要排序，较慢 |
| **计数法** | O(n × k) | O(n × k) | 不需要排序，更快 | 代码稍复杂，需要理解 ord() 和 tuple() |

**选择建议：**
- 如果字符串长度 k 较小（k < 10），两种方法性能差异不大，可以选择排序法（更直观）
- 如果字符串长度 k 较大（k > 10），建议使用计数法（更快）