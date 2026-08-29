# 142. 环形链表II

## 1. 哈希法（Set）的思路
不需要“维护一个数组”，只需要维护一个**计数器（pos）**即可。
因为链表不是数组，我们没法通过下标随机访问，但我们在**按顺序遍历**，所以每走一步，`pos` 就加 1。

- **逻辑**：遍历链表，用 `set` 记录走过的节点，用 `pos` 记录当前步数（从0开始）。
- **当** `head in visited` **时**，当前这个节点就是环的入口，**直接返回 `pos`**（这就是入口的索引位置）。
- **代码逻辑**：
```python
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, x):
#         self.val = x
#         self.next = None

class Solution:
    def detectCycle(self, head: Optional[ListNode]) -> Optional[ListNode]:
        visited = set()
        pos = 0
        while head:
            if head in visited:
                return head
            visited.add(head)
            head = head.next
            pos = pos + 1
        return None
```

## 2. 双指针（快慢指针）的思路
“两个指针第一次相遇的地方，fast再走一步就是pos”是**不对的**。

**正确的经典操作是（Floyd 判圈算法）**：
1. **第一阶段**：快指针 `fast` 走两步，慢指针 `slow` 走一步，直到它们在环中**第一次相遇**（记这个点为 Meeting Point）。
2. **第二阶段（关键）**：将**慢指针 `slow` 重新放回链表头节点 `head`**，快指针 `fast` 留在原地（相遇点）。然后，**两个指针都改为每次只走一步**。
3. 当它们**再次相遇**时，所在的节点 **才是环的入口节点（pos）**。

### 数学证明简析
设：
- **L**：头节点到环入口的距离（即我们要找的 pos）。
- **S**：环入口到第一次相遇点的距离。
- **R**：第一次相遇点绕回环入口的距离（即环的剩余部分）。
- 环的周长 = **S + R**。

**第一次相遇时**：
- `slow` 走了 `L + S` 步。
- `fast` 走了 `L + S + n*(S+R)` 步（n 为 fast 绕的圈数）。
- 因为 fast 速度是 slow 的 2 倍，所以：`2 * (L + S) = L + S + n*(S+R)`。
- 化简得：**L = (n-1)*(S+R) + R**。

![detect-cycle-double-pointer](/img/leetcode/detectCycle/detect-cycle-double-pointer.jpg)

**这个公式的含义极其重要**：
它告诉我们：**从头节点走到入口的距离（L），等于从第一次相遇点走到入口的距离（R）再加上（n-1）圈**。

所以，当你把 `slow` 扔回头节点，`fast` 留在相遇点，两者同速（每次1步）前进时：
- `slow` 从 head 走 L 步到达入口。
- `fast` 从相遇点走 L 步，根据公式 L = R + (n-1)圈，它正好也走到入口。
- **正因为它们再次相遇在入口，我们才能确定这个位置。**

如果你在第一次相遇后，让 `fast` 只“再走一步”，那它还在环内瞎转悠，绝对不在入口，所以那个操作是不成立的。

```python
class Solution:
    def detectCycle(self, head: Optional[ListNode]) -> Optional[ListNode]:
        slow = fast = head
        while fast and fast.next:
            slow = slow.next
            fast = fast.next.next
            if slow == fast:
                neo_slow = head
                while neo_slow != fast:
                    neo_slow = neo_slow.next
                    fast = fast.next
                return fast
        return None
```