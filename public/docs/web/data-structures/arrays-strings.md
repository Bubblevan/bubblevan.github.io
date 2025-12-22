```markdown
# 数组与字符串

import DocumentMetadata from '@site/src/components/DocumentMetadata';

<DocumentMetadata />

## 数组基础

### 时间复杂度
- 访问：O(1)
- 插入/删除：O(n)（非末尾）
- 搜索：O(n)

### 常用操作

```js
// JavaScript数组操作
const arr = [1, 2, 3, 4, 5];

// 访问元素
console.log(arr[0]); // 1

// 添加元素
arr.push(6); // [1, 2, 3, 4, 5, 6]

// 删除元素
arr.pop(); // [1, 2, 3, 4, 5]
arr.shift(); // [2, 3, 4, 5]
```

## 字符串基础

### 不可变性
字符串在大多数语言中是不可变的，每次修改都会创建新字符串。

```python
# Python字符串操作
s = "hello"
s[0] = "H"  # 错误！字符串不可变

# 正确方式
s = "H" + s[1:]  # "Hello"
```

## 高频面试题

### 1. 两数之和
```js
function twoSum(nums, target) {
    const map = new Map();

    for (let i = 0; i < nums.length; i++) {
        const complement = target - nums[i];
        if (map.has(complement)) {
            return [map.get(complement), i];
        }
        map.set(nums[i], i);
    }

    return [];
}
```

### 2. 移动零
```js
function moveZeroes(nums) {
    let left = 0;

    for (let right = 0; right < nums.length; right++) {
        if (nums[right] !== 0) {
            [nums[left], nums[right]] = [nums[right], nums[left]];
            left++;
        }
    }
}
```

### 3. 最长公共前缀
```js
function longestCommonPrefix(strs) {
    if (strs.length === 0) return "";

    let prefix = strs[0];

    for (let i = 1; i < strs.length; i++) {
        while (strs[i].indexOf(prefix) !== 0) {
            prefix = prefix.substring(0, prefix.length - 1);
            if (prefix === "") return "";
        }
    }

    return prefix;
}
```

## 字符串匹配算法

### KMP算法
```js
function buildKMPTable(pattern) {
    const table = new Array(pattern.length).fill(0);
    let i = 1, j = 0;

    while (i < pattern.length) {
        if (pattern[i] === pattern[j]) {
            j++;
            table[i] = j;
            i++;
        } else {
            if (j !== 0) {
                j = table[j - 1];
            } else {
                table[i] = 0;
                i++;
            }
        }
    }

    return table;
}
```

## 总结

- **数组**：连续内存，随机访问快
- **字符串**：通常不可变，操作时注意性能
- **重点掌握**：双指针、滑动窗口、哈希表等技巧
- **时间空间**：多考虑边界情况和复杂度
```