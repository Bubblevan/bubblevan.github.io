# 141. 环形链表

## 哈希法

直到现在我确实还是觉得“哈希”听起来很高大上，以为必须是那种带 `{key: value}` 的字典（HashMap）或者要自己写哈希函数才算。

其实在算法领域，**“哈希法”指的就是利用哈希表（Hash Table）进行 O(1) 的快速查找和去重**。

### 1. 为什么 Python 的 `set` 算“哈希”？
Python 的 `set` 底层**就是由哈希表（Hash Table）实现的**。当你把链表节点 `head` 放入 `set` 时，Python 会调用节点对象的 `__hash__()` 方法（默认基于内存地址）计算出哈希值，然后存入哈希桶中。
当你写 `if node in visited:` 时，底层执行的就是**哈希查找**，平均时间复杂度是 O(1)。所以，维护一个 `set` 就是在维护一个哈希表，这当然叫哈希解法。

### 2. 哈希法（Set） vs 双指针（快慢指针）的区别
这两种方法都是经典解法，它们的区别在于**空间换时间**：

| 解法 | 数据结构 | 时间复杂度 | 空间复杂度 | 本质 |
| :--- | :--- | :--- | :--- | :--- |
| **哈希法（Set）** | 哈希表 | O(n) | **O(n)** | 记录“我来过这里”，查重 |
| **双指针（快慢）** | 两个指针 | O(n) | **O(1)** | 追及问题，省内存 |

如果面试官问“能否优化空间”，那就得用双指针；如果问“能否想到最直观的做法”，那哈希 `set` 就是标准答案。

### 3. 解法

```python
def hasCycle(head):
    visited = set()  # 这行代码就是在初始化一个哈希表
    while head:
        if head in visited:  # 这行代码就是在做哈希查找（O(1)）
            return True
        visited.add(head)    # 这行代码就是在做哈希插入（O(1)）
        head = head.next
    return False
```

> 在 Python 中，如果自定义的类没有重写 `__hash__`，默认用 `id()`（内存地址）作为哈希值。链表节点对象的内存地址是唯一的，所以哪怕两个节点值一样，只要地址不同，`set` 也能准确区分，绝不会误判。这正是哈希表在此场景下的完美应用。

所以放心，以后刷题时说到“哈希解法”，用 `set` 就是标准答案！

> 是觉得它太简单了，不像 C++/Java 里那样需要显式声明 `HashMap` 才产生了误解吧？

## 双指针法

```python
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, x):
#         self.val = x
#         self.next = None

class Solution:
    def hasCycle(self, head: Optional[ListNode]) -> bool:
        slow = head
        fast = head
        # while fast is not None:   # 如果 fast.next 是 None，这里会报 AttributeError
        while fast is not None and fast.next is not None:
            slow = slow.next
            fast = fast.next.next
            if slow == fast:
                return True
        return False
```