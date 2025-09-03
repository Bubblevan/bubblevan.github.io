```markdown
# 排序算法

import DocumentMetadata from '@site/src/components/DocumentMetadata';

<DocumentMetadata />

## 排序算法分类

### 比较排序 vs 非比较排序
- **比较排序**：通过比较元素大小进行排序（最坏时间复杂度 O(nlogn)）
- **非比较排序**：不通过比较元素大小（计数排序、基数排序等）

### 稳定排序 vs 不稳定排序
- **稳定排序**：相等元素的相对位置保持不变
- **不稳定排序**：相等元素的相对位置可能改变

## 常见排序算法

### 1. 快速排序 (Quick Sort)
```js
function quickSort(arr, left = 0, right = arr.length - 1) {
    if (left < right) {
        const pivotIndex = partition(arr, left, right);
        quickSort(arr, left, pivotIndex - 1);
        quickSort(arr, pivotIndex + 1, right);
    }
    return arr;
}

function partition(arr, left, right) {
    const pivot = arr[right];
    let i = left - 1;

    for (let j = left; j < right; j++) {
        if (arr[j] <= pivot) {
            i++;
            [arr[i], arr[j]] = [arr[j], arr[i]];
        }
    }

    [arr[i + 1], arr[right]] = [arr[right], arr[i + 1]];
    return i + 1;
}
```

**时间复杂度**：平均 O(nlogn)，最坏 O(n²)
**空间复杂度**：O(logn)
**稳定性**：不稳定

### 2. 归并排序 (Merge Sort)
```js
function mergeSort(arr) {
    if (arr.length <= 1) return arr;

    const mid = Math.floor(arr.length / 2);
    const left = mergeSort(arr.slice(0, mid));
    const right = mergeSort(arr.slice(mid));

    return merge(left, right);
}

function merge(left, right) {
    const result = [];
    let i = 0, j = 0;

    while (i < left.length && j < right.length) {
        if (left[i] <= right[j]) {
            result.push(left[i++]);
        } else {
            result.push(right[j++]);
        }
    }

    return result.concat(left.slice(i)).concat(right.slice(j));
}
```

**时间复杂度**：O(nlogn)
**空间复杂度**：O(n)
**稳定性**：稳定

### 3. 堆排序 (Heap Sort)
```js
function heapSort(arr) {
    const n = arr.length;

    // 建堆
    for (let i = Math.floor(n / 2) - 1; i >= 0; i--) {
        heapify(arr, n, i);
    }

    // 排序
    for (let i = n - 1; i > 0; i--) {
        [arr[0], arr[i]] = [arr[i], arr[0]];
        heapify(arr, i, 0);
    }

    return arr;
}

function heapify(arr, n, i) {
    let largest = i;
    const left = 2 * i + 1;
    const right = 2 * i + 2;

    if (left < n && arr[left] > arr[largest]) {
        largest = left;
    }

    if (right < n && arr[right] > arr[largest]) {
        largest = right;
    }

    if (largest !== i) {
        [arr[i], arr[largest]] = [arr[largest], arr[i]];
        heapify(arr, n, largest);
    }
}
```

**时间复杂度**：O(nlogn)
**空间复杂度**：O(1)
**稳定性**：不稳定

### 4. 冒泡排序 (Bubble Sort)
```js
function bubbleSort(arr) {
    const n = arr.length;

    for (let i = 0; i < n - 1; i++) {
        let swapped = false;

        for (let j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                [arr[j], arr[j + 1]] = [arr[j + 1], arr[j]];
                swapped = true;
            }
        }

        if (!swapped) break;
    }

    return arr;
}
```

**时间复杂度**：O(n²)
**空间复杂度**：O(1)
**稳定性**：稳定

### 5. 插入排序 (Insertion Sort)
```js
function insertionSort(arr) {
    const n = arr.length;

    for (let i = 1; i < n; i++) {
        const key = arr[i];
        let j = i - 1;

        while (j >= 0 && arr[j] > key) {
            arr[j + 1] = arr[j];
            j--;
        }

        arr[j + 1] = key;
    }

    return arr;
}
```

**时间复杂度**：O(n²)
**空间复杂度**：O(1)
**稳定性**：稳定

## 排序算法比较

| 算法       | 时间复杂度 | 空间复杂度 | 稳定性 | 适用场景                     |
|------------|------------|------------|--------|------------------------------|
| 快速排序   | O(nlogn)   | O(logn)    | 不稳定 | 大数据量，平均性能好         |
| 归并排序   | O(nlogn)   | O(n)       | 稳定   | 稳定排序，外排序             |
| 堆排序     | O(nlogn)   | O(1)       | 不稳定 | 大数据量，空间受限           |
| 冒泡排序   | O(n²)      | O(1)       | 稳定   | 小数据量，教学演示           |
| 插入排序   | O(n²)      | O(1)       | 稳定   | 基本有序的小数组             |

## 面试重点

### 1. 快速排序的优化
- 三数取中选择枢轴
- 小数组使用插入排序
- 尾递归优化

### 2. 外部排序
- 多路归并排序
- 败者树优化

### 3. 稳定性重要性
- 按多个关键字排序时
- 对象排序保持原有顺序

### 4. 实际应用场景
- 数据库索引
- 文件排序
- 算法竞赛

## LeetCode相关题目

- [排序数组](https://leetcode-cn.com/problems/sort-an-array/)
- [数组中的第K个最大元素](https://leetcode-cn.com/problems/kth-largest-element-in-an-array/)
- [合并区间](https://leetcode-cn.com/problems/merge-intervals/)
- [颜色分类](https://leetcode-cn.com/problems/sort-colors/)

## 总结

- **掌握核心算法**：快速排序、归并排序、堆排序
- **理解复杂度**：时间空间复杂度分析
- **优化技巧**：根据数据特点选择合适算法
- **稳定性考虑**：业务场景对排序稳定性的要求
```