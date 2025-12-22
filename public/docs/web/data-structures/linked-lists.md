```markdown
# 链表

## 链表基础

### 链表类型

1. **单向链表**：每个节点只有一个指向下一个节点的指针
2. **双向链表**：每个节点有两个指针（前驱和后继）
3. **循环链表**：尾节点指向头节点

### 时间复杂度
- 访问：O(n)
- 插入/删除：O(1)（知道位置的情况下）
- 搜索：O(n)

## 链表节点定义

```js
// JavaScript链表节点
class ListNode {
    constructor(val = 0, next = null) {
        this.val = val;
        this.next = next;
    }
}

// Python链表节点
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
```

## 高频面试题

### 1. 反转链表
```js
function reverseList(head) {
    let prev = null;
    let curr = head;

    while (curr !== null) {
        const next = curr.next;
        curr.next = prev;
        prev = curr;
        curr = next;
    }

    return prev;
}
```

### 2. 检测环
```js
function hasCycle(head) {
    if (!head || !head.next) return false;

    let slow = head;
    let fast = head;

    while (fast && fast.next) {
        slow = slow.next;
        fast = fast.next.next;

        if (slow === fast) {
            return true;
        }
    }

    return false;
}
```

### 3. 环的入口
```js
function detectCycle(head) {
    if (!head || !head.next) return null;

    let slow = head;
    let fast = head;

    // 找到相遇点
    while (fast && fast.next) {
        slow = slow.next;
        fast = fast.next.next;

        if (slow === fast) {
            // 找到环的入口
            let ptr1 = head;
            let ptr2 = slow;

            while (ptr1 !== ptr2) {
                ptr1 = ptr1.next;
                ptr2 = ptr2.next;
            }

            return ptr1;
        }
    }

    return null;
}
```

### 4. 合并两个有序链表
```js
function mergeTwoLists(list1, list2) {
    const dummy = new ListNode();
    let current = dummy;

    while (list1 && list2) {
        if (list1.val <= list2.val) {
            current.next = list1;
            list1 = list1.next;
        } else {
            current.next = list2;
            list2 = list2.next;
        }
        current = current.next;
    }

    current.next = list1 || list2;

    return dummy.next;
}
```

### 5. 删除倒数第N个节点
```js
function removeNthFromEnd(head, n) {
    const dummy = new ListNode(0, head);
    let fast = dummy;
    let slow = dummy;

    // fast先走n+1步
    for (let i = 0; i <= n; i++) {
        fast = fast.next;
    }

    // 一起走直到fast为null
    while (fast !== null) {
        fast = fast.next;
        slow = slow.next;
    }

    // 删除slow.next
    slow.next = slow.next.next;

    return dummy.next;
}
```

## 双指针技巧

### 1. 快慢指针
- 检测环
- 寻找中点
- 删除倒数第N个节点

### 2. 双指针遍历
- 反转链表
- 合并有序链表
- 移除元素

## 常见坑点

1. **空指针检查**：操作前检查head是否为空
2. **边界情况**：只有一个节点、两个节点等
3. **环检测**：使用快慢指针，避免死循环
4. **内存管理**：注意垃圾回收，防止内存泄漏

## 链表 vs 数组

| 特性 | 数组 | 链表 |
|------|------|------|
| 访问 | O(1) | O(n) |
| 插入/删除 | O(n) | O(1) |
| 内存分配 | 连续 | 不连续 |
| 缓存友好 | 是 | 否 |

## 总结

- **链表操作**：多用递归和迭代两种方法
- **双指针技巧**：快慢指针、双指针遍历
- **边界处理**：空链表、单节点、环形链表
- **时间空间**：注意算法的时间复杂度优化
```