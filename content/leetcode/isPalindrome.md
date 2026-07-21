# 234. 回文链表

经典的快慢链表。所谓快慢链表就是如何得到回文的一半？这可是链表不是数组！
答案就是一个fast走两步，一个slow走一步，fast==None时slow就到中间了。

```python
fast = head
slow = head

while fast is not None and fast.next is not None:
    slow = slow.next
    fast = fast.next.next
```

现在slow指向第二个链表的头节点。思路很简单，链表只能从头到尾，那我们从尾到头的方法就是 **反转链表**！
好在就是一天里刷的Leetcode Easy，默写一下：
```python
def reverseList(head: ListNode) -> ListNode:    # 不要加self
    cur = head
    prev = None     # 新增的初始化

    while cur is not None:          # 不能是cur.next，你看我return都是prev，就怕null.next
        nxt = cur.next
        cur.next = prev
        prev = cur
        cur = nxt
    return prev
```

最后比较second和first是否有不一致的值就行了，以短的second为主。

```python
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def isPalindrome(self, head: Optional[ListNode]) -> bool:
        def reverseList(head: ListNode) -> ListNode:
            cur = head
            prev = None

            while cur is not None:
                nxt = cur.next
                cur.next = prev
                prev = cur
                cur = nxt
            return prev

        fast = head
        slow = head

        while fast is not None and fast.next is not None:
            slow = slow.next
            fast = fast.next.next
        
        second = reverseList(slow)
        first = head

        while second is not None:
            if second.val != first.val:
                return False
            second = second.next
            first = first.next

        return True
```