# 21. 合并两个有序链表

“双指针逐一比较”**完全正确**，这是这道题的标准解法。

但是，你贴出来的这份代码**存在严重的逻辑 Bug**，如果直接运行会报错或者死循环。主要有三个致命问题：

1. **没有处理空链表**：如果 `list1` 或 `list2` 是 `None`，代码第一行 `if head1.val` 就会直接报错（`AttributeError`）。
2. **指针覆盖导致节点丢失**：你在循环里直接修改了 `head1.next = head2`，这会**断掉** `head1` 原本后面的节点。比如 `list1 = [1,2,4]`，你让 `1` 指向了 `list2` 的头部，那 `list1` 原来的 `2` 和 `4` 就被丢弃了，再也找不回来了。
3. **缺少拼接剩余链表**：循环结束后，肯定有一个链表还有剩余节点，你直接返回 `first` 没有把剩下的接上去。

---

## 正确的“双指针”标准写法（迭代 + 虚拟头节点）

面试和工程中最推荐的写法是**创建一个虚拟头节点（Dummy Node）**，它像一根“针”，把两个链表的节点按顺序串起来。这样逻辑最清晰，且不用处理头节点的特判。

```python
class Solution:
    def mergeTwoLists(self, list1: Optional[ListNode], list2: Optional[ListNode]) -> Optional[ListNode]:
        # 虚拟头结点，这里返回原地操作不能新建，所以返回什么很关键
        # 哦错了我又搞混List和Array了，这里就是链表的创建操作，反而不能破坏原俩升序链表
        dummy = ListNode()
        tail = dummy

        # 2. 双指针逐一比较
        while list1 and list2:
            if list1.val <= list2.val:
                tail.next = list1   # 把 list1 当前节点接到新链表后面
                # list1.next = list2        # 见上不能破坏
                list1 = list1.next  # list1 指针后移
            else:
                tail.next = list2
                list2 = list2.next
            tail = tail.next        # 新链表末尾指针后移

        # 3. 循环结束后，哪个链表还有剩余，直接全部接上（因为本身就是有序的）
        if list1:
            tail.next = list1
        else:
            tail.next = list2

        # 4. 返回虚拟头节点的下一个节点（真正的头节点）
        return dummy.next
```

## 你的代码要怎么改才能运行？
如果你想保留你原来的风格（不创建虚拟头节点），那就需要**先特判空链表，再确定 `first` 头部**，并且保证移动过程中**绝对不覆盖 `head.next`**（你之前错在覆盖了）。修正版如下：

```python
class Solution:
    def mergeTwoLists(self, list1: Optional[ListNode], list2: Optional[ListNode]) -> Optional[ListNode]:
        # 特判空链表
        if not list1: return list2
        if not list2: return list1

        # 确定新链表的头节点
        if list1.val <= list2.val:
            head = list1
            list1 = list1.next
        else:
            head = list2
            list2 = list2.next
        
        # cur 用来遍历合并后的链表
        cur = head
        
        while list1 and list2:
            if list1.val <= list2.val:
                cur.next = list1
                list1 = list1.next
            else:
                cur.next = list2
                list2 = list2.next
            cur = cur.next
        
        # 拼接剩余
        cur.next = list1 if list1 else list2
        
        return head
```

---

## 补充一点（面试加分项）
这道题也可以用**递归**写，极其简洁，但递归有栈溢出风险（链表太长会报错）：

```python
class Solution:
    def mergeTwoLists(self, list1, list2):
        if not list1: return list2
        if not list2: return list1
        if list1.val <= list2.val:
            list1.next = self.mergeTwoLists(list1.next, list2)
            return list1
        else:
            list2.next = self.mergeTwoLists(list1, list2.next)
            return list2
```

**面试建议**：优先写**虚拟头节点迭代法**，因为它的空间复杂度是 O(1)（递归是 O(n)），且不会爆栈，是这道题的最优解。你只要把虚拟头节点（`dummy`）这个套路记住，以后凡是合并链表、删除节点需要“串”链表的题，都能用它解决。
