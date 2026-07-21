# 206. 反转链表

错误在于：
```python
while cur is not None:
    nxt = cur.next

    # 原来，cur.next == nxt, cur == cur
    cur.next = prev   # 1. 把当前节点指向前一个（这一步是对的）

    nxt.next = cur    # 2. ❌ 这一行是多余的，而且会破坏链表
    cur = cur.next    # 3. ❌ cur.next 已经被你改成 prev 了，cur 会走回头路
```
- 第 2 行 nxt.next = cur：
  - 反转链表时，我们只需要把当前节点的箭头调转方向。下一个节点 nxt 的箭头，应该留到下一次循环时，由它自己来调转。
  - 现在提前把 nxt 指向了 cur，不仅打乱了链表结构，还让后续步骤无法正确拿到原本的 nxt.next。
  - 更严重的是，当 cur 是最后一个节点时，nxt 是 None，执行 nxt.next = cur 会直接报错 AttributeError。

- 第 3 行 cur = cur.next：
  - 因为已经把 cur.next 改成了 prev，所以这一步会让 cur 跳到 prev（即往回走），而不是往前走。这会导致循环在原地打转或出错。

- prev 从未更新：
  - 在整个循环里，没有写 prev = cur，所以 prev 永远是 None。最后 return prev 永远返回 None。

```python
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def reverseList(self, head: Optional[ListNode]) -> Optional[ListNode]:
        prev = None
        cur = head

        while cur is not None:
            nxt = cur.next
            # 现在已经有的情况是prev->cur, cur->nxt
            # 对于第0个来说，prev==None, cur->nxt
            # 对于第n个来说，prev->cur, cur->None

            # 我们希望达成的反转效果是，cur->prev, nxt->cur
            cur.next = prev     # 先反转当前的节点
            prev = cur          # 更新prev前移
            cur = nxt           # cur++

        return prev
```