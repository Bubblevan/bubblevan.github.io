# 1. 两数之和

---

## 第一部分：题目信息

### 题目描述

给定一个整数数组 `nums` 和一个整数目标值 `target`，请你在该数组中找出**和为目标值 `target`** 的那**两个**整数，并返回它们的数组下标。

你可以假设每种输入只会对应一个答案，并且你不能使用两次相同的元素。

你可以按任意顺序返回答案。

### 示例

#### 示例 1

**输入：**
```python
nums = [2, 7, 11, 15]
target = 9
```

**输出：**
```python
[0, 1]
```

**解释：** 因为 `nums[0] + nums[1] == 9`，返回 `[0, 1]`。

#### 示例 2

**输入：**
```python
nums = [3, 2, 4]
target = 6
```

**输出：**
```python
[1, 2]
```

**解释：** 因为 `nums[1] + nums[2] == 6`，返回 `[1, 2]`。

#### 示例 3

**输入：**
```python
nums = [3, 3]
target = 6
```

**输出：**
```python
[0, 1]
```

**解释：** 因为 `nums[0] + nums[1] == 6`，返回 `[0, 1]`。

### 提示

- `2 <= nums.length <= 10^4`
- `-10^9 <= nums[i] <= 10^9`
- `-10^9 <= target <= 10^9`
- **只会存在一个有效答案**

### 进阶

你可以想出一个时间复杂度小于 **O(n²)** 的算法吗？

### 代码模板

```python
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        
```

---

## 第二部分：Python 基础

### 理解 Python 类和方法

#### C 思维 vs Python 思维

- **C 思维**：我有一个专门解题的"函数"。
- **Python 思维**：我雇佣了一个专门解题的"机器人"，这个机器人的型号叫 **Solution**（类），它有一个"技能"叫 **twoSum**（方法）。

所以这里的 **Class** 更类似于一个 C 语言中的函数：

```c
int twoSum(int* nums, int numsSize, int target, int* returnSize) {...}
```

**LeetCode** 平台会自动通过类似 `s = Solution(); s.twoSum(...)` 的方式来运行代码。

#### self 参数

在 **Python** 中，如果一个函数定义在类里面，它的第一个参数必须是 **self**。

**含义**：**self** 代表调用这个方法的对象实例，也就是 Solution 类的实例。

> **类比**：C++ 里面代表 **this** 指针，Java 中的 this 关键字

在调用这个函数时，你不需要传这个参数，**Python** 会自动帮你传进去。

**eg:**
```python
# 定义时
def twoSum(self, nums: List[int], target: int) -> List[int]:
    ...

# 调用时（LeetCode 自动执行）
s = Solution()
result = s.twoSum([2, 7, 11, 15], 9)  # 不需要传 self
```

#### 类型注解：`nums: List[int]` 与 `-> List[int]`

这是 **Python 3** 引入的"**类型暗示（Type Hints）**"。它并不会强制限制变量类型（**Python** 依然是动态语言），但它告诉读代码的人：这个参数预期是什么类型，返回的又是什么类型。

| Python | C 语言等价表达 | 含义 |
|--------|---------------|------|
| `nums: List[int]` | `int* nums`（或数组） | 传入的形参之一，`nums` 应该是一个由整数组成的列表 |
| `target: int` | `int target` | 传入的形参之二，`target` 是一个整数 |
| `->` |  | 返回类型注解，表示函数返回什么类型 |
| `-> List[int]` | `int* func_name(...)` | 这个函数最后要返回一个整数列表 |

### 动态语言 vs 静态语言

#### 什么是动态语言？

**动态语言（Dynamic Language）** 是指在**运行时**才确定变量类型的语言。与之相对的是**静态语言（Static Language）**，在**编译时**就必须确定所有变量的类型。

**对比示例：**

**静态语言（C/C++/Java）：**
```c
// C 语言：编译时必须声明类型
int num = 10;        // 必须声明 num 是 int 类型
char* str = "hello"; // 必须声明 str 是 char* 类型

// 如果类型不匹配，编译时就会报错
int num = "hello";   // ❌ 编译错误：不能将字符串赋给 int
```

**动态语言（Python）：**
```python
# Python：运行时才确定类型
num = 10        # 运行时才知道 num 是 int
str = "hello"   # 运行时才知道 str 是 str

# 类型可以随时改变
num = "hello"   # ✅ 完全合法：num 现在变成了字符串
```

#### Python 的方法对于输入和输出的数据类型没有规定吗？

**关键点**：**Python 的类型注解（Type Hints）只是"提示"和"文档"，不会在运行时强制检查类型**。

**示例对比：**

```python
def twoSum(self, nums: List[int], target: int) -> List[int]:
    return [0, 1]

# 即使传入错误的类型，Python 也不会报错！
result = twoSum(None, "hello", "world")  # ✅ 不会报错，但逻辑会出错
result = twoSum(None, [1, 2, 3], 5)      # ✅ 正常运行
```

**在静态语言（如 C++）中：**
```cpp
vector<int> twoSum(vector<int>& nums, int target) {
    return {0, 1};
}

// 如果类型不匹配，编译时就会报错
twoSum("hello", "world");  // ❌ 编译错误：类型不匹配
```

#### 类型注解的实际作用

虽然 **Python** 不会强制检查类型，但类型注解仍然很有用：

1. **IDE 智能提示**：编辑器可以根据类型注解提供代码补全和错误提示
2. **文档作用**：让代码更易读，明确函数期望的输入输出类型

**eg:**
```python
# 使用 mypy 进行类型检查（需要单独安装和运行）
# pip install mypy
# mypy your_code.py

def twoSum(self, nums: List[int], target: int) -> List[int]:
    return [0, 1]

# mypy 会检查出类型错误（但 Python 解释器不会）
result = twoSum(None, "hello", "world")  # mypy 会警告：类型不匹配
```

---

## 第三部分：解法与知识点

### 解法一：暴力枚举（二重循环）

**思路**：遍历所有可能的数对，检查它们的和是否等于 `target`。

```python
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        for i in range(len(nums)):
            for j in range(i+1, len(nums)):
                if nums[i] + nums[j] == target:
                    return [i, j]
        return []
```

**时间复杂度**：O(n²) - 需要嵌套循环遍历所有数对

**空间复杂度**：O(1) - 只使用了常数额外空间

### 解法二：哈希表（推荐）

**思路**：利用字典（dict）存储已访问的数字和其索引，每看到一个数字 `x`，就检查字典中是否存在 `target - x`。

```python
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        hashtable = {}
        for i, num in enumerate(nums):
            complement = target - num
            if complement in hashtable:
                return [hashtable[complement], i]
            hashtable[num] = i
        return []
```

**时间复杂度**：O(n) - 只需要遍历一次数组

**空间复杂度**：O(n) - 最坏情况下需要存储 n 个数字

### 哈希表解法详解

#### 核心思想

利用字典（dict）的 O(1) 查找特性，将"查找两个数的和"转化为"查找一个数是否存在于字典中"。

#### 字典的 key 和 value 设计

**关键点**：在这个字典中：
- **key（键）**：数组中的**值**（`num`）
- **value（值）**：该值对应的**索引**（`i`）

**为什么这样设计？**

我们需要快速查找："某个值是否出现过？如果出现过，它的索引是多少？"

- 如果用索引作为 key：`hashtable[0] = 2` → 只能知道"索引 0 的值是 2"，但无法快速查找"值 7 在哪个索引"
- 用值作为 key：`hashtable[2] = 0` → 可以直接查找"值 2 在索引 0"，这正是我们需要的！

**执行流程示例：**

```python
nums = [2, 7, 11, 15]
target = 9
hashtable = {}

# 第 1 次循环：i=0, num=2
complement = 9 - 2 = 7
# 检查：hashtable 中有 7 吗？没有（字典是空的）
hashtable[2] = 0  # 存储：值 2 → 索引 0
# hashtable = {2: 0}

# 第 2 次循环：i=1, num=7
complement = 9 - 7 = 2
# 检查：hashtable 中有 2 吗？有！hashtable[2] = 0
return [hashtable[2], 1]  # return [0, 1]
```

**详细执行流程表：**

| 循环次数 | i | num | complement | hashtable 状态 | 操作 |
|---------|---|-----|------------|---------------|------|
| **初始** | - | - | - | `{}` | 空字典 |
| **第 1 次** | 0 | 2 | 7 | `{}` | `7` 不在字典中，存储 `hashtable[2] = 0` |
| | | | | `{2: 0}` | |
| **第 2 次** | 1 | 7 | 2 | `{2: 0}` | `2` 在字典中！返回 `[hashtable[2], 1] = [0, 1]` |

#### 为什么 `hashtable[complement]` 能工作？

**关键理解**：
- `complement` 是一个**值**（例如 2 或 7）
- `hashtable[complement]` 表示：查找 key 为 `complement` 的条目
- 返回的是该 key 对应的 **value**，也就是**索引**

### 相关知识点

#### enumerate() 函数

`enumerate()` 是 Python 的内置函数，用于在遍历序列（如列表、元组、字符串）时，同时获取**索引**和**值**。

**基本用法：**

```python
fruits = ['apple', 'banana', 'orange']

for index, fruit in enumerate(fruits):
    print(f"索引 {index}: {fruit}")

# 输出：
# 索引 0: apple
# 索引 1: banana
# 索引 2: orange
```

**指定起始索引：**

```python
fruits = ['apple', 'banana', 'orange']

for index, fruit in enumerate(fruits, start=1):
    print(f"第 {index} 个: {fruit}")

# 输出：
# 第 1 个: apple
# 第 2 个: banana
# 第 3 个: orange
```

**转换为列表：**

```python
nums = [2, 7, 11, 15]
list(enumerate(nums))
# 输出: [(0, 2), (1, 7), (2, 11), (3, 15)]

list(enumerate(nums, start=1))
# 输出: [(1, 2), (2, 7), (3, 11), (4, 15)]
```

#### `if x in dict` 的查找机制

**关键点**：`if x in dict` 检查的是 `x` 是否是字典的 **key（键）**，而不是 **value（值）**。

**分析**：
- `hashtable[num] = i`：将**值**（`num`）作为 **key**，**索引**（`i`）作为 **value**
- `if complement in hashtable`：检查 `complement`（一个**值**）是否是字典的 **key**
- **所以 `x` 必须是值（数组中的数字），不能是索引**

**为什么这样设计？**

**问题**：我们需要快速查找"某个值是否出现过？"

**解决方案**：
- 用**值**作为 **key**，**索引**作为 **value**
- 这样 `if complement in hashtable` 就能快速检查"值 `complement` 是否出现过"

**如果反过来（用索引作为 key）**：
```python
# ❌ 错误的设计
hashtable = {0: 2, 1: 7}  # key: 索引, value: 值

# 无法快速查找"值 7 是否出现过"
# 只能遍历所有 value，时间复杂度 O(n)
```

**示例对比：**

```python
hashtable = {2: 0, 7: 1, 11: 2}  # key: 值, value: 索引

# ✅ 检查 key（可以）
2 in hashtable      # True（2 是 key）
7 in hashtable      # True（7 是 key）
5 in hashtable      # False（5 不是 key）

# ❌ 检查 value（不可以）
0 in hashtable      # False（0 是 value，不是 key）
1 in hashtable      # False（1 是 value，不是 key）
```

**时间复杂度**：O(1) - 字典的 key 查找是 O(1)

---

## 总结

| 解法 | 时间复杂度 | 空间复杂度 | 适用场景 |
|------|-----------|-----------|---------|
| **暴力枚举** | O(n²) | O(1) | 数据量小，简单直接 |
| **哈希表** | O(n) | O(n) | **推荐**，数据量大，需要高效查找 |

**核心技巧**：
- 利用字典的 O(1) 查找特性
- 用值作为 key，索引作为 value
- 一次遍历即可完成查找
