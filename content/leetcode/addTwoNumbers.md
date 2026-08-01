# 2. 两数之和

用一个 `while` 循环把**“两个链表没走完”**和**“还有进位”**这两种情况一起处理。

不需要像 21 题那样分前后两段，只需要在一个循环里，当 `l1` 为空时取 `0`，`l2` 为空时取 `0`，直到**两个链表都为空且进位为 0** 才停止。

```python
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def addTwoNumbers(self, l1: Optional[ListNode], l2: Optional[ListNode]) -> Optional[ListNode]:
        dummy = ListNode()
        cur = dummy
        carry= 0    # 进位

        while l1 or l2 or carry:
            # BYD 空链表逼我加if
            val1 = l1.val if l1 else 0
            val2 = l2.val if l2 else 0
            total = val1 + val2 + carry

            carry = total // 10
            total = total % 10

            cur.next = ListNode(total)
            cur = cur.next

            # 各自步进
            if l1 is not None:
                l1 = l1.next
            if l2 is not None:
                l2 = l2.next
        
        return dummy.next
```

**“两根链表一根短，进位还没还给完；宁可补零接着算，不可拼接留后患。”** 