# Python Day4 Numpy库

> **如果你在用Python做数据分析或机器学习，NumPy不是可选项，而是必选项**。

想象一下，你需要处理一个包含100万条记录的销售数据表，每条记录有50个字段。如果用Python原生的列表(list)来存储和计算，光是计算每列的平均值可能就要等上好几秒。而NumPy可以将这个时间缩短到**毫秒级别**，这种性能差距在真实项目中是决定性的。

NumPy (Numerical Python) 是Python科学计算生态系统的**基石**。Pandas、Scikit-learn、TensorFlow、PyTorch这些耳熟能详的库，底层都重度依赖NumPy。学好NumPy，就是为整个数据科学和机器学习之路打下最坚实的基础。

## 第一章：NumPy的"世界观"——一切都是数组

### 1.1 导入NumPy：约定俗成的仪式

```python
import numpy as np
```

这行简单的代码背后有一个Python社区约定俗成的传统：**总是将numpy导入为np**。这不仅是为了打字方便，更是为了代码的一致性和可读性。几乎所有NumPy教程、项目代码、开源库都使用这个别名，看到`np.`就知道在使用NumPy。

### 1.2 理解NumPy数组(ndarray)的本质

在NumPy的世界里，**一切数据都以多维数组(ndarray)的形式存在**。这与Python的列表(list)有本质区别：

- **列表**：可以存放不同类型的元素，灵活性高但效率低
- **NumPy数组**：**所有元素必须是同一种数据类型**，这使得它在内存中连续存储，计算效率极高

```python
# 创建你的第一个NumPy数组
a = np.array([[1, 2], [3, 4], [5, 6]])
print("数组内容:\n", a)
print("数组形状(shape):", a.shape)
print("数组维度(ndim):", a.ndim)
print("数组数据类型(dtype):", a.dtype)
```

输出结果：
```
数组内容:
 [[1 2]
 [3 4]
 [5 6]]
数组形状(shape): (3, 2)  # 3行2列
数组维度(ndim): 2        # 二维数组
数组数据类型(dtype): int64  # 64位整数
```

**关键理解**：`shape`属性可能是NumPy中最重要的概念之一。它描述了数组在每个维度上的大小。对于上面的数组`a`，形状`(3, 2)`意味着：
- 第一个维度（轴0）有3个元素（3行）
- 第二个维度（轴1）有2个元素（2列）

### 1.3 快速创建特殊数组的实用技巧

在实际项目中，我们经常需要快速创建特定形状和内容的数组：

```python
# 创建全零数组 - 常用于初始化
zeros_matrix = np.zeros((3, 4))  # 3行4列的全0数组
print("全零数组:\n", zeros_matrix)

# 创建全一数组 - 常用于创建掩码或基准值
ones_matrix = np.ones((2, 5))    # 2行5列的全1数组
print("\n全一数组:\n", ones_matrix)

# 创建单位矩阵 - 线性代数运算的基础
identity_matrix = np.eye(5)      # 5×5的单位矩阵
print("\n5×5单位矩阵:\n", identity_matrix)

# 创建未初始化的数组（内容随机，是内存中的残留值）
# 注意：这在某些需要极致性能的场景有用，但通常不推荐
empty_matrix = np.empty((2, 3))
print("\n未初始化数组（内容随机）:\n", empty_matrix)

# 创建等差序列数组
range_array = np.arange(0, 10, 2)  # 从0到10（不含），步长为2
print("\n等差序列:", range_array)

# 创建等间隔数组（更灵活）
linspace_array = np.linspace(0, 1, 5)  # 从0到1，均匀取5个点
print("\n等间隔数组:", linspace_array)  # [0., 0.25, 0.5, 0.75, 1.]
```

## 第二章：数组形状的"七十二变"

数据处理中，最常遇到的操作之一就是改变数组的形状。NumPy提供了极其灵活的形状操作工具。

### 2.1 基础形状变换：reshape与flatten

```python
# 创建基础数组
a = np.arange(8)  # 类似Python的range()，但返回的是数组：[0, 1, 2, 3, 4, 5, 6, 7]
print("原始数组:", a)
print("原始形状:", a.shape)  # (8,) - 一维数组

# 改变形状为4行2列
b = a.reshape((4, 2))
print("\nreshape((4, 2)):\n", b)
print("新形状:", b.shape)  # (4, 2)

# 展平为一维数组（两种方式）
c = b.flatten()  # 总是返回原数组的拷贝
d = b.ravel()    # 尽可能返回原数组的视图（不拷贝数据）
print("\nflatten()结果:", c)
print("ravel()结果:", d)
```

**重要区别**：
- `flatten()`：**总是返回拷贝**，修改返回的数组不会影响原始数组
- `ravel()`：**尽可能返回视图**（当可能时），修改可能影响原始数组

### 2.2 NumPy的"智能"维度：-1参数的妙用

NumPy有一个非常贴心的功能：在reshape时，可以用`-1`自动计算某一维度的大小。

```python
# 使用-1让NumPy自动计算
a = np.arange(12)

# 自动计算行数，保证是2列
b = a.reshape((-1, 2))  # NumPy会计算：总元素12 ÷ 2列 = 6行
print("reshape((-1, 2)):\n", b)
print("形状:", b.shape)  # (6, 2)

# 自动计算深度，保证是3行4列
c = a.reshape((3, 4, -1))  # 总元素12 ÷ (3×4) = 1
print("\nreshape((3, 4, -1))的形状:", c.shape)  # (3, 4, 1)

# 三维数组：2×2×2
d = a[:8].reshape((2, 2, -1))  # 只取前8个元素
print("\n三维数组形状:", d.shape)  # (2, 2, 2)
```

**实际应用场景**：当你从文件加载数据，知道总样本数和特征数，但不确定批量大小时，`-1`特别有用。

### 2.3 维度的增加与压缩：expand_dims和squeeze

```python
# 增加维度
a = np.arange(5)  # 形状: (5,)
print("原始数组:", a)
print("原始形状:", a.shape)

# 在第0轴增加维度（变成1×5）
b = np.expand_dims(a, 0)  # 等价于 a.reshape(1, -1)
print("\n在第0轴增加维度:")
print("数组:\n", b)
print("形状:", b.shape)  # (1, 5)

# 在第1轴增加维度（变成5×1）
c = np.expand_dims(a, 1)  # 等价于 a.reshape(-1, 1)
print("\n在第1轴增加维度:")
print("数组:\n", c)
print("形状:", c.shape)  # (5, 1)

# 压缩多余的维度（删除长度为1的维度）
d = np.array([[[1, 2, 3]]])  # 形状: (1, 1, 3)
print("\n压缩前形状:", d.shape)

e = np.squeeze(d)  # 删除所有长度为1的维度
print("压缩后形状:", e.shape)  # (3,)

# 选择性压缩
f = np.squeeze(d, axis=0)  # 只压缩第0轴
print("选择性压缩后形状:", f.shape)  # (1, 3)
```

**为什么这很重要**？在深度学习中，经常需要处理批量数据。单个样本可能形状是`(32, 32, 3)`，但一批样本需要是`(batch_size, 32, 32, 3)`。`expand_dims`和`squeeze`就是用来处理这种维度需求的。

## 第三章：数组的"拼图游戏"：连接与堆叠

### 3.1 基本连接：concatenate

```python
# 创建两个相同的数组
a = np.ones((4, 3))  # 4行3列的全1数组
b = np.ones((4, 3)) * 2  # 4行3列的全2数组

print("数组a:\n", a)
print("\n数组b:\n", b)

# 沿第0轴连接（垂直堆叠，增加行数）
c = np.concatenate([a, b], axis=0)
print("\n沿axis=0连接（垂直堆叠）:")
print("结果形状:", c.shape)  # (8, 3)
print("结果:\n", c)

# 沿第1轴连接（水平堆叠，增加列数）
d = np.concatenate([a, b], axis=1)
print("\n沿axis=1连接（水平堆叠）:")
print("结果形状:", d.shape)  # (4, 6)
print("结果:\n", d)
```

### 3.2 更便捷的堆叠方法

除了`concatenate`，NumPy还提供了更直观的堆叠函数：

```python
# vstack：垂直堆叠（沿axis=0）
v_result = np.vstack([a, b])  # 等价于 np.concatenate([a, b], axis=0)

# hstack：水平堆叠（沿axis=1）
h_result = np.hstack([a, b])  # 等价于 np.concatenate([a, b], axis=1)

# stack：沿新轴堆叠
s_result = np.stack([a, b], axis=0)  # 形状: (2, 4, 3)
print("stack结果形状:", s_result.shape)  # 创建了一个新的维度！
```

**关键区别**：
- `concatenate`、`vstack`、`hstack`：**不增加新维度**，只是扩展现有维度
- `stack`：**创建新维度**，把多个数组堆叠在新维度上

### 3.3 实际应用：构建神经网络批量数据

```python
# 模拟三个32×32的RGB图像（深度学习常见输入尺寸）
x1 = np.ones((32, 32, 3)) * 0.1  # 图像1
x2 = np.ones((32, 32, 3)) * 0.2  # 图像2
x3 = np.ones((32, 32, 3)) * 0.3  # 图像3

print("单个图像形状:", x1.shape)  # (32, 32, 3)

# 目标：构建一个批量，形状为(3, 32, 32, 3)
# 方法1：分步法（清晰易懂）
x_list = [x1, x2, x3]

# 为每个图像增加批次维度
x_expanded = [np.expand_dims(xx, 0) for xx in x_list]
print("增加批次维度后单个形状:", x_expanded[0].shape)  # (1, 32, 32, 3)

# 沿批次维度连接
x_batch = np.concatenate(x_expanded, axis=0)
print("\n批量数据形状:", x_batch.shape)  # (3, 32, 32, 3)

# 方法2：使用stack（更简洁）
x_batch_alt = np.stack([x1, x2, x3], axis=0)
print("stack方法批量形状:", x_batch_alt.shape)  # (3, 32, 32, 3)
```

## 第四章：NumPy的"超能力"：索引与切片

### 4.1 基础索引与切片

NumPy的索引语法与Python列表类似，但功能更强大：

```python
# 创建一个10×10的数组
a = np.zeros((10, 10))

# 基础切片
a[:3] = 1          # 前3行所有列赋值为1
print("前3行赋值为1:\n", a[:4, :])  # 查看前4行

a[:, :3] = 2       # 所有行的前3列赋值为2
print("\n所有行前3列赋值为2:\n", a[:4, :4])  # 查看左上角4×4区域

a[:3, :3] = 3      # 前3行、前3列的交叉区域赋值为3
print("\n前3行前3列交叉区域赋值为3:\n", a[:4, :4])
```

### 4.2 花式索引(Fancy Indexing)

```python
# 创建新数组
a = np.zeros((10, 10))

# 使用列表指定要访问的行和列
rows = [4, 6, 7, 2]  # 第4、6、7、2行
cols = [9, 3, 5, 1]  # 第9、3、5、1列

# 花式索引：同时指定行索引和列索引
a[rows, cols] = 4

print("花式索引结果（部分显示）:")
# 显示涉及的行
for i in range(10):
    if i in rows:
        print(f"第{i}行: {a[i, :]}")
```

### 4.3 布尔索引（过滤数据）

```python
# 创建随机数据
data = np.random.randn(10, 3)  # 10个样本，每个样本3个特征
print("原始数据:\n", data)

# 布尔索引：选择第一列大于0的所有行
positive_mask = data[:, 0] > 0
positive_samples = data[positive_mask]
print("\n第一列大于0的样本:\n", positive_samples)

# 多条件筛选
complex_mask = (data[:, 0] > 0) & (data[:, 1] < 0.5)  # 注意：必须用括号
filtered_data = data[complex_mask]
print("\n第一列>0且第二列<0.5的样本:\n", filtered_data)
```

## 第五章：数组的"变形金刚"：转置与轴交换

### 5.1 转置操作

```python
# 创建三维数组
a = np.arange(24).reshape(2, 3, 4)
print("原始数组形状:", a.shape)  # (2, 3, 4)
print("\n原始数组:\n", a)

# 基础转置：反转所有轴的顺序
a_T = a.T
print("\n基础转置后形状:", a_T.shape)  # (4, 3, 2)

# 指定轴交换顺序
# 原始轴顺序：(0, 1, 2) → 新顺序：(2, 1, 0)
a_transposed = np.transpose(a, (2, 1, 0))
print("\n指定轴交换(2,1,0)后形状:", a_transposed.shape)  # (4, 3, 2)
```

### 5.2 实际应用：图像通道处理

```python
# 模拟一张图像数据：高度×宽度×通道 (H×W×C)
image_hwc = np.random.rand(224, 224, 3)  # 224×224的RGB图像
print("H×W×C格式形状:", image_hwc.shape)

# 深度学习框架有时需要C×H×W格式
image_chw = np.transpose(image_hwc, (2, 0, 1))
print("转换为C×H×W格式形状:", image_chw.shape)  # (3, 224, 224)

# 转置是视图（不复制数据），修改会影响原始数组
image_chw[0, 0, 0] = 999
print("\n修改转置后数组，原始数组对应值:", image_hwc[0, 0, 0])  # 也会变成999
```

## 第六章：NumPy的"数学大脑"：线性代数运算

### 6.1 基本线性代数操作

```python
# 创建一个矩阵
c = np.array([[1, 2], [3, 4]])
print("原始矩阵:\n", c)

# 求逆矩阵（对于可逆矩阵）
try:
    inv_c = np.linalg.inv(c)
    print("\n逆矩阵:\n", inv_c)
except np.linalg.LinAlgError:
    print("矩阵不可逆")

# 伪逆矩阵（更稳定，即使矩阵不可逆或不是方阵也能计算）
pinv_c = np.linalg.pinv(c)
print("\n伪逆矩阵:\n", pinv_c)

# 验证：原矩阵 × 逆矩阵 ≈ 单位矩阵
identity_approx = c @ pinv_c
print("\n原矩阵 × 伪逆矩阵 ≈ 单位矩阵:\n", identity_approx)

# 矩阵范数（默认是Frobenius范数/二范数）
norm_c = np.linalg.norm(c)
print(f"\n矩阵范数: {norm_c:.4f}")
```

### 6.2 理解axis参数：NumPy的灵魂所在

**axis参数是NumPy中最重要也是最容易混淆的概念之一**。理解axis，就理解了NumPy的一半。

```python
c = np.array([[1, 2], 
              [3, 4]])
print("矩阵c:\n", c)

# 不指定axis：对所有元素求和
total_sum = np.sum(c)
print(f"\n所有元素求和: {total_sum}")  # 1+2+3+4 = 10

# axis=0：沿着行的方向（垂直方向）压缩，对每列进行操作
sum_axis0 = np.sum(c, axis=0)
print(f"沿axis=0求和（对每列求和）: {sum_axis0}")  # [1+3, 2+4] = [4, 6]

# axis=1：沿着列的方向（水平方向）压缩，对每行进行操作
sum_axis1 = np.sum(c, axis=1)
print(f"沿axis=1求和（对每行求和）: {sum_axis1}")  # [1+2, 3+4] = [3, 7]

# 直观记忆法：
# axis=0 → 沿着行的方向 → 行被压缩消失 → 对列操作
# axis=1 → 沿着列的方向 → 列被压缩消失 → 对行操作

# 三维数组示例
d = np.arange(24).reshape(2, 3, 4)
print(f"\n三维数组形状: {d.shape}")  # (2, 3, 4)

# axis=0：压缩第0维
print(f"沿axis=0求和的形状: {np.sum(d, axis=0).shape}")  # (3, 4)

# axis=1：压缩第1维  
print(f"沿axis=1求和的形状: {np.sum(d, axis=1).shape}")  # (2, 4)

# axis=2：压缩第2维
print(f"沿axis=2求和的形状: {np.sum(d, axis=2).shape}")  # (2, 3)

# 多个axis同时操作
print(f"沿axis=(0,1)求和的形状: {np.sum(d, axis=(0, 1)).shape}")  # (4,)
```

## 第七章：NumPy的"效率魔法"：向量化运算

### 7.1 点积与矩阵乘法

```python
# 向量点积
c = np.array([1, 2])
d = np.array([3, 4])

dot_product = np.dot(c, d)
print(f"向量点积: {dot_product}")  # 1*3 + 2*4 = 11

# 矩阵乘法
a = np.ones((4, 3))  # 4×3矩阵
b = np.ones((3, 2))  # 3×2矩阵

# 三种等价的矩阵乘法写法
result1 = a @ b           # Python 3.5+ 推荐写法
result2 = np.dot(a, b)    # 传统写法
result3 = a.dot(b)        # 面向对象写法

print(f"\n矩阵乘法结果形状: {result1.shape}")  # (4, 2)

# 验证结果相同
print("结果是否相同:", np.allclose(result1, result2) and np.allclose(result2, result3))
```

### 7.2 广播机制：NumPy最强大的特性之一

广播(Broadcasting)允许NumPy在算术运算中处理不同形状的数组。

```python
# 示例1：矩阵 + 向量
c = np.ones((4, 2))  # 4×2矩阵
print("矩阵c:\n", c)

d = np.array([1, 2, 3, 4]).reshape(4, 1)  # 4×1列向量
print("\n列向量d:\n", d)

# 广播：将d复制扩展为4×2矩阵，然后与c相加
result = c + d
print("\n矩阵 + 列向量（广播）:\n", result)

# 示例2：更复杂的广播
batch = np.ones((3, 32))  # 3个样本，每个样本32个特征
weight = np.ones((32, 10))  # 权重矩阵
bias = np.ones((1, 10))  # 偏置向量

# 神经网络前向传播（利用广播）
output = batch @ weight + bias
print(f"\n批量运算结果形状: {output.shape}")  # (3, 10)

# 广播规则解析：
# 1. 从最右边维度开始对齐
# 2. 维度大小为1或缺失的维度可以扩展
# 3. 其他维度大小必须相等
```

### 7.3 NumPy vs 纯Python：性能大比拼

```python
import time

# 创建两个100×100的矩阵
a = np.ones((100, 100))
b = np.ones((100, 100))

# 纯Python的矩阵乘法（三层循环）
def matrix_multiplication_python(X, Y):
    result = [[0] * len(Y[0]) for _ in range(len(X))]
    for i in range(len(X)):
        for j in range(len(Y[0])):
            for k in range(len(Y)):
                result[i][j] += X[i][k] * Y[k][j]
    return result

# 计时：NumPy
start_np = time.time()
for _ in range(10):
    np_result = a @ b
end_np = time.time()
np_time = end_np - start_np

# 计时：纯Python
start_py = time.time()
for _ in range(10):
    py_result = matrix_multiplication_python(a.tolist(), b.tolist())
end_py = time.time()
py_time = end_py - start_py

print(f"NumPy耗时: {np_time:.4f}秒")
print(f"纯Python耗时: {py_time:.4f}秒")
print(f"NumPy比纯Python快 {py_time/np_time:.1f}倍！")

# 随着矩阵增大，这个差距会呈指数级增长
# 对于1000×1000的矩阵，NumPy可能比纯Python快1000倍以上！
```

## 第八章：实用技巧与常见陷阱

### 8.1 元素级运算

```python
# 创建示例数组
a = np.array([[1, 2], [3, 4]], dtype=np.float32)

# 数学函数（逐元素操作）
print("原始数组:\n", a)
print("\n自然对数:\n", np.log(a))
print("\n指数函数:\n", np.exp(a))
print("\n正弦函数:\n", np.sin(a))
print("\n平方根:\n", np.sqrt(a))

# 与标量的运算（自动广播到每个元素）
print("\n每个元素乘以3:\n", a * 3)
print("\n每个元素加10:\n", a + 10)
print("\n每个元素的平方:\n", a ** 2)

# 比较运算（返回布尔数组）
print("\n大于2的元素:\n", a > 2)
print("\n等于3的元素:\n", a == 3)
```

### 8.2 常见陷阱与解决方案

```python
# 陷阱1：视图 vs 拷贝
original = np.array([1, 2, 3, 4, 5])
view = original[:3]  # 切片创建的是视图
view[0] = 999
print(f"陷阱1 - 修改视图影响原始数组: {original}")  # [999, 2, 3, 4, 5]

# 解决方案：明确拷贝
original = np.array([1, 2, 3, 4, 5])
copy = original[:3].copy()  # 显式拷贝
copy[0] = 999
print(f"解决方案 - 拷贝不影响原始: {original}")  # [1, 2, 3, 4, 5]

# 陷阱2：整数除法
int_array = np.array([1, 2, 3, 4])
result = int_array / 2  # Python 3中返回浮点数
print(f"\n陷阱2 - 整数除法结果: {result.dtype}")  # float64

# 解决方案：使用地板除法或指定类型
result_floor = int_array // 2
result_float = int_array / 2.0

# 陷阱3：广播形状不匹配
try:
    a = np.ones((3, 4))
    b = np.ones((4, 3))
    result = a + b  # 会报错！
except ValueError as e:
    print(f"\n陷阱3 - 广播错误: {e}")

# 解决方案：调整形状
a = np.ones((3, 4))
b = np.ones((4, 3))
result = a + b.T  # 转置b以匹配形状
print(f"解决方案 - 转置后可以广播")
```

## 第九章：综合实战应用

### 9.1 数据标准化（归一化）

```python
# 创建模拟数据：100个样本，每个样本5个特征
data = np.random.randn(100, 5) * 10 + 5  # 均值5，标准差10
print(f"原始数据 - 形状: {data.shape}")
print(f"原始数据 - 均值: {np.mean(data, axis=0)}")
print(f"原始数据 - 标准差: {np.std(data, axis=0)}")

# Z-score标准化：使每个特征均值为0，标准差为1
mean = np.mean(data, axis=0, keepdims=True)  # keepdims保持维度
std = np.std(data, axis=0, keepdims=True)
data_normalized = (data - mean) / std

print(f"\n标准化后 - 均值: {np.mean(data_normalized, axis=0)}")
print(f"标准化后 - 标准差: {np.std(data_normalized, axis=0)}")
```

### 9.2 图像处理简单示例

```python
# 创建简单的"图像"（10×10像素）
image = np.random.randint(0, 256, (10, 10), dtype=np.uint8)
print("原始图像（部分）:\n", image[:3, :3])

# 图像翻转
flipped_horizontal = image[:, ::-1]  # 水平翻转
flipped_vertical = image[::-1, :]    # 垂直翻转

# 图像旋转90度
rotated_90 = np.rot90(image)

# 提取颜色通道（假设是灰度图，但演示多通道处理）
# 如果是RGB图像，可以这样提取通道
rgb_image = np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8)
red_channel = rgb_image[:, :, 0]
green_channel = rgb_image[:, :, 1]
blue_channel = rgb_image[:, :, 2]

# 将单通道转换为三通道（灰度图伪彩色化）
gray_to_rgb = np.stack([image, image, image], axis=2)
print(f"\n灰度转RGB形状: {gray_to_rgb.shape}")  # (10, 10, 3)
```

