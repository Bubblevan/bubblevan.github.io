# 160. 相交链表

其实就是两条：
- A + C
- B + C

叠在一起就可以原地访问了：
- A + C + B + C
- B + C + A + C


```python
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, x):
#         self.val = x
#         self.next = None

class Solution:
    def getIntersectionNode(self, headA: ListNode, headB: ListNode) -> Optional[ListNode]:
        pA, pB = headA, headB

        while pA != pB:
            if pA is None:
                pA = headB
            else:
                pA = pA.next
            
            if pB is None:
                pB = headA
            else:
                pB = pB.next

        return pA
```