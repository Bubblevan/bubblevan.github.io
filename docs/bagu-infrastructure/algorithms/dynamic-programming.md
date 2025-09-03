```markdown
# 动态规划

## 动态规划基础

### 核心思想
将复杂问题分解为子问题，通过存储子问题的解来避免重复计算。

### 适用条件
1. **最优子结构**：原问题的最优解包含子问题的最优解
2. **无后效性**：子问题的解不影响其他子问题
3. **重叠子问题**：子问题会被重复计算

### 解题步骤
1. 定义状态（DP数组的含义）
2. 找出状态转移方程
3. 确定初始条件
4. 考虑边界情况

## 经典问题

### 1. 斐波那契数列
```js
// 递归（效率低）
function fib(n) {
    if (n <= 1) return n;
    return fib(n - 1) + fib(n - 2);
}

// 动态规划（高效）
function fib(n) {
    if (n <= 1) return n;

    const dp = new Array(n + 1);
    dp[0] = 0;
    dp[1] = 1;

    for (let i = 2; i <= n; i++) {
        dp[i] = dp[i - 1] + dp[i - 2];
    }

    return dp[n];
}

// 空间优化
function fib(n) {
    if (n <= 1) return n;

    let prev2 = 0, prev1 = 1;
    for (let i = 2; i <= n; i++) {
        const current = prev1 + prev2;
        prev2 = prev1;
        prev1 = current;
    }

    return prev1;
}
```

### 2. 0-1背包问题
```js
function knapsack(weights, values, capacity) {
    const n = weights.length;
    const dp = Array(n + 1).fill().map(() => Array(capacity + 1).fill(0));

    for (let i = 1; i <= n; i++) {
        for (let w = 1; w <= capacity; w++) {
            if (weights[i - 1] <= w) {
                dp[i][w] = Math.max(
                    dp[i - 1][w],                                    // 不选第i个物品
                    dp[i - 1][w - weights[i - 1]] + values[i - 1]    // 选第i个物品
                );
            } else {
                dp[i][w] = dp[i - 1][w];
            }
        }
    }

    return dp[n][capacity];
}

// 空间优化
function knapsack(weights, values, capacity) {
    const n = weights.length;
    const dp = new Array(capacity + 1).fill(0);

    for (let i = 0; i < n; i++) {
        for (let w = capacity; w >= weights[i]; w--) {
            dp[w] = Math.max(dp[w], dp[w - weights[i]] + values[i]);
        }
    }

    return dp[capacity];
}
```

### 3. 最长递增子序列 (LIS)
```js
function lengthOfLIS(nums) {
    if (nums.length === 0) return 0;

    const dp = new Array(nums.length).fill(1);

    for (let i = 1; i < nums.length; i++) {
        for (let j = 0; j < i; j++) {
            if (nums[i] > nums[j]) {
                dp[i] = Math.max(dp[i], dp[j] + 1);
            }
        }
    }

    return Math.max(...dp);
}

// 贪心 + 二分查找优化
function lengthOfLIS(nums) {
    const tails = [];

    for (const num of nums) {
        let left = 0, right = tails.length;

        while (left < right) {
            const mid = Math.floor((left + right) / 2);
            if (tails[mid] < num) {
                left = mid + 1;
            } else {
                right = mid;
            }
        }

        if (left === tails.length) {
            tails.push(num);
        } else {
            tails[left] = num;
        }
    }

    return tails.length;
}
```

### 4. 编辑距离
```js
function minDistance(word1, word2) {
    const m = word1.length;
    const n = word2.length;

    const dp = Array(m + 1).fill().map(() => Array(n + 1).fill(0));

    // 初始化
    for (let i = 0; i <= m; i++) {
        dp[i][0] = i;
    }
    for (let j = 0; j <= n; j++) {
        dp[0][j] = j;
    }

    // 填充DP表
    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (word1[i - 1] === word2[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1];
            } else {
                dp[i][j] = Math.min(
                    dp[i - 1][j - 1] + 1,  // 替换
                    dp[i - 1][j] + 1,      // 删除
                    dp[i][j - 1] + 1       // 插入
                );
            }
        }
    }

    return dp[m][n];
}
```

## 不同类型的问题

### 1. 线性DP
- 斐波那契数列
- 爬楼梯
- 打家劫舍

### 2. 区间DP
- 矩阵链乘法
- 石子合并
- 回文子串

### 3. 树形DP
- 二叉树最大路径和
- 树的最大独立集

### 4. 状态压缩DP
- TSP问题
- 集合划分

## 常见技巧

### 1. 滚动数组
空间优化：只保留前几行的结果

### 2. 状态压缩
用二进制位表示状态，适用于集合相关问题

### 3. 记忆化搜索
自顶向下：递归 + 缓存

### 4. 数字DP
处理数字范围内的DP问题

## LeetCode相关题目

### 简单
- [爬楼梯](https://leetcode-cn.com/problems/climbing-stairs/)
- [打家劫舍](https://leetcode-cn.com/problems/house-robber/)

### 中等
- [最长递增子序列](https://leetcode-cn.com/problems/longest-increasing-subsequence/)
- [编辑距离](https://leetcode-cn.com/problems/edit-distance/)
- [0-1背包](https://leetcode-cn.com/problems/partition-equal-subset-sum/)

### 困难
- [正则表达式匹配](https://leetcode-cn.com/problems/regular-expression-matching/)
- [戳气球](https://leetcode-cn.com/problems/burst-balloons/)
- [俄罗斯套娃信封问题](https://leetcode-cn.com/problems/russian-doll-envelopes/)

## 调试技巧

### 1. 打印DP表
观察状态转移过程

### 2. 检查边界
特殊情况：空数组、单元素等

### 3. 验证状态定义
确保DP数组含义清晰

### 4. 时间空间优化
根据具体问题优化复杂度

## 总结

- **核心思路**：分解问题，存储子解，避免重复计算
- **关键步骤**：状态定义、转移方程、初始条件
- **常见类型**：线性DP、区间DP、树形DP、状态压缩DP
- **优化技巧**：滚动数组、记忆化搜索、贪心优化
- **实践重点**：多做题，理解状态转移的本质
```