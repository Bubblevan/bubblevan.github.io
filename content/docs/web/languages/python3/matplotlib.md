# Python Day4 Matplotlib库

在数据科学和分析领域，**可视化是我们与数据对话的桥梁**。想象一下，你面前有一张满是数字的表格，理解其中的模式、趋势和异常值就像在黑暗中摸索。而当你将这些数字转化为图形时，瞬间就能看到故事的展开。Matplotlib正是Python生态系统中**最强大、最灵活的可视化工具**，它就像是数据科学家的画笔，让我们能够将抽象的数据转化为直观的见解。

我在学习数据科学的初期，常常陷入"分析瘫痪"——我能计算出各种统计指标，但却难以向他人传达我的发现。直到掌握了Matplotlib，我才真正学会了如何**用图形讲故事**。这篇笔记将分享我学习Matplotlib的完整旅程，希望能帮助你在数据可视化的道路上少走弯路。

## 第一章：Matplotlib初探——不只是绘图工具

### 1.1 Matplotlib到底是什么？

很多人把Matplotlib简单理解为"Python的绘图库"，但这种认识太片面了。经过长时间的使用，我认为Matplotlib更像是一个**完整的可视化生态系统**。它由三个层次构成：

1. **后端层**：处理如何将图形渲染到屏幕或文件
2. **艺术家层**：负责创建图形元素（线条、文本、形状等）
3. **脚本层**：我们最常接触的pyplot接口，提供类似MATLAB的简易绘图命令

这种分层架构使得Matplotlib既适合快速绘图，也适合创建高度定制化的出版级图形。记住这一点很重要：**Matplotlib的设计哲学是"让简单的事情简单，让复杂的事情可能"**。

### 1.2 为什么选择Matplotlib？

市场上可视化工具众多，为什么Matplotlib依然占据主导地位？

- **历史悠久，社区强大**：诞生于2003年，经过近20年的发展，几乎每个数据科学家都用过它
- **完全免费和开源**：没有许可费用，源代码完全透明
- **高度可定制**：从颜色到线条样式，从图例到坐标轴，几乎每个元素都可以调整
- **与其他库完美集成**：Pandas、NumPy、SciPy等科学计算库都与Matplotlib无缝对接
- **多输出格式支持**：支持PNG、PDF、SVG、EPS等多种格式，适合各种出版需求

我个人的经验是：**掌握Matplotlib后，学习其他可视化库（如Seaborn、Plotly）会变得异常轻松**，因为它们的底层思想是相通的。

## 第二章：环境搭建与基础导入

### 2.1 安装Matplotlib

如果你使用的是Anaconda（我强烈推荐数据科学初学者使用），Matplotlib已经预装了。如果需要单独安装：

```bash
# 使用pip安装
pip install matplotlib

# 使用conda安装
conda install matplotlib

# 安装开发版本（不推荐初学者）
pip install git+https://github.com/matplotlib/matplotlib.git
```

### 2.2 神奇的导入语句

```python
import matplotlib.pyplot as plt
```

这行简单的导入语句背后有着深思熟虑的设计：
- **为什么是`plt`**？这是社区约定俗成的缩写，就像`np`代表NumPy，`pd`代表Pandas
- **`pyplot`是什么**？它是Matplotlib的"脚本接口"，提供了类似MATLAB的绘图命令
- **为什么不直接导入整个matplotlib**？为了保持命名空间整洁，避免名称冲突

我个人的习惯是**永远使用这个标准导入方式**，这样我的代码在任何机器上都能运行，其他开发者也能轻松理解。

### 2.3 魔术命令（Jupyter Notebook用户必看）

如果你在Jupyter Notebook中使用Matplotlib，这两行代码能极大改善体验：

```python
%matplotlib inline
%config InlineBackend.figure_format = 'retina'
```

- `%matplotlib inline`：**让图形直接显示在Notebook单元格下方**
- `%config InlineBackend.figure_format = 'retina'`：**使用高分辨率显示**，图形更清晰

这两个命令不是必须的，但强烈推荐使用。我刚开始学习时忽略了它们，结果图形显示在单独的窗口中，打断了我的工作流程。

## 第三章：第一个图形——折线图

### 3.1 最简单的折线图

让我们从最基础开始：

```python
# 创建数据
x = [1, 2, 3]
y = [1, 3, 2]

# 绘制图形
plt.plot(x, y)
plt.show()
```

这三行代码包含了Matplotlib绘图的三个基本步骤：
1. **准备数据**：创建x和y坐标
2. **调用绘图函数**：`plt.plot()`是最基础的绘图命令
3. **显示图形**：`plt.show()`在非交互环境中必须调用

**重要提示**：在Jupyter Notebook中，如果你使用了`%matplotlib inline`，则不需要`plt.show()`，图形会自动显示。

### 3.2 理解`plot()`函数的工作原理

`plt.plot(x, y)`看似简单，实际上内部执行了复杂的操作：

1. **创建图形和坐标轴**：如果当前没有活动的图形，Matplotlib会自动创建一个
2. **数据转换**：将数据点转换为图形坐标
3. **渲染线条**：在坐标点之间绘制连线
4. **设置默认样式**：应用默认的颜色、线宽等样式

### 3.3 折线图的变体

折线图不仅仅是连接点与点的直线，Matplotlib提供了丰富的选项：

```python
import numpy as np

# 生成更密集的数据点
x = np.linspace(0, 10, 100)  # 从0到10生成100个均匀分布的点
y = np.sin(x)

# 不同的线条样式
plt.figure(figsize=(10, 6))

# 实线
plt.subplot(2, 2, 1)
plt.plot(x, y, '-', label='实线')
plt.title('实线')
plt.legend()

# 虚线
plt.subplot(2, 2, 2)
plt.plot(x, y, '--', label='虚线')
plt.title('虚线')
plt.legend()

# 点划线
plt.subplot(2, 2, 3)
plt.plot(x, y, '-.', label='点划线')
plt.title('点划线')
plt.legend()

# 点线
plt.subplot(2, 2, 4)
plt.plot(x, y, ':', label='点线')
plt.title('点线')
plt.legend()

plt.tight_layout()
```

这段代码展示了：
- **`np.linspace()`**：生成等间距数组，比手动创建列表方便得多
- **线条样式参数**：`'-'`（实线）、`'--'`（虚线）、`'-.'`（点划线）、`':'`（点线）
- **子图**：使用`plt.subplot()`创建多个子图
- **`plt.tight_layout()`**：自动调整子图参数，避免标签重叠

## 第四章：散点图——观察数据关系

### 4.1 基础散点图

当我们需要观察两个变量之间的关系，特别是数据点之间没有顺序关系时，散点图是最佳选择：

```python
# 创建数据
x = [1, 2, 3, 4, 5]
y = [2, 4, 1, 5, 3]

# 绘制散点图
plt.scatter(x, y)
plt.title('基础散点图')
plt.xlabel('X轴')
plt.ylabel('Y轴')
```

### 4.2 散点图的强大之处

散点图的真正威力在于它的**多维度表达能力**。一个散点图可以同时展示四个维度的信息：

```python
import numpy as np

# 生成随机数据
np.random.seed(42)  # 设置随机种子，确保结果可重复
n = 50
x = np.random.randn(n)
y = x * 2 + np.random.randn(n) * 0.5

# 第三维：颜色（表示大小）
sizes = np.random.randint(10, 100, n)

# 第四维：颜色（表示类别）
categories = np.random.choice(['A', 'B', 'C'], n)
colors = {'A': 'red', 'B': 'blue', 'C': 'green'}
color_values = [colors[c] for c in categories]

# 绘制多维度散点图
plt.figure(figsize=(10, 8))
scatter = plt.scatter(x, y, s=sizes, c=color_values, alpha=0.6, edgecolors='black', linewidth=0.5)

# 添加图例
# 由于scatter不支持内置图例，我们需要手动创建
import matplotlib.patches as mpatches
legend_elements = [mpatches.Patch(color='red', label='类别 A'),
                   mpatches.Patch(color='blue', label='类别 B'),
                   mpatches.Patch(color='green', label='类别 C')]
plt.legend(handles=legend_elements, title='类别')

plt.title('多维度散点图示例')
plt.xlabel('X变量')
plt.ylabel('Y变量')

# 添加网格
plt.grid(True, alpha=0.3)

# 添加颜色条（如果需要表示连续变量）
# 这里我们使用大小已经表示了连续变量，所以不需要颜色条
```

这个例子展示了散点图如何同时表达：
- **X轴和Y轴**：两个主要变量
- **点的大小**：第三个变量（如销售额、数量等）
- **点的颜色**：第四个变量（如类别、区域等）
- **透明度**：使用`alpha`参数处理点重叠问题

### 4.3 散点图与折线图的区别

初学者常常混淆散点图和折线图。**关键区别在于数据是否有序**：
- 折线图：数据点有顺序关系，通常用于时间序列
- 散点图：数据点没有顺序关系，用于观察两个变量的相关性

## 第五章：条形图——分类数据可视化

### 5.1 基础条形图

条形图是展示分类数据的最佳选择，特别适合比较不同类别的数值：

```python
# 创建数据
categories = ['苹果', '香蕉', '橙子', '葡萄', '芒果']
values = [25, 17, 32, 28, 19]

# 绘制条形图
plt.bar(categories, values)
plt.title('水果销量')
plt.xlabel('水果种类')
plt.ylabel('销量（千克）')
```

### 5.2 条形图的多种变体

条形图不只是简单的垂直条形，Matplotlib提供了多种变体：

```python
import numpy as np

# 创建数据
categories = ['第一季度', '第二季度', '第三季度', '第四季度']
values_2022 = [120, 135, 148, 165]
values_2023 = [130, 142, 160, 180]

x = np.arange(len(categories))  # 类别位置
width = 0.35  # 条形宽度

# 创建分组条形图
fig, ax = plt.subplots(figsize=(10, 6))

# 绘制两组条形
rects1 = ax.bar(x - width/2, values_2022, width, label='2022年', color='skyblue', edgecolor='black')
rects2 = ax.bar(x + width/2, values_2023, width, label='2023年', color='lightcoral', edgecolor='black')

# 添加标签和标题
ax.set_xlabel('季度')
ax.set_ylabel('销售额（万元）')
ax.set_title('2022年与2023年季度销售额对比')
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.legend()

# 在条形上方添加数值标签
def autolabel(rects):
    """在条形上方显示数值"""
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3个点的垂直偏移
                    textcoords="offset points",
                    ha='center', va='bottom')

autolabel(rects1)
autolabel(rects2)

plt.tight_layout()
```

### 5.3 水平条形图

当类别名称较长或类别数量较多时，水平条形图是更好的选择：

```python
# 创建数据
languages = ['Python', 'JavaScript', 'Java', 'C#', 'PHP', 'C++', 'TypeScript', 'Ruby', 'Swift', 'Kotlin']
popularity = [100, 97, 88, 79, 72, 65, 60, 55, 50, 45]

# 创建水平条形图
fig, ax = plt.subplots(figsize=(10, 8))

# 绘制条形，按受欢迎程度排序
# 先将数据按值排序
combined = list(zip(languages, popularity))
combined.sort(key=lambda x: x[1])
languages_sorted, popularity_sorted = zip(*combined)

y_pos = np.arange(len(languages_sorted))

ax.barh(y_pos, popularity_sorted, align='center', color='steelblue')
ax.set_yticks(y_pos)
ax.set_yticklabels(languages_sorted)
ax.invert_yaxis()  # 反转Y轴，使最高的在顶部
ax.set_xlabel('受欢迎程度指数')
ax.set_title('编程语言受欢迎程度排名')

plt.tight_layout()
```

## 第六章：图形配置详解——让图表更专业

### 6.1 完整的图形配置示例

现在让我们看一个完整的配置示例，理解每个配置项的作用：

```python
import numpy as np

# 创建数据
x = np.array([1, 2, 3, 4, 5])
y1 = np.array([1, 3, 2, 4, 5])
y2 = np.array([4, 2, 1, 3, 4])

# 第一步：设置图形大小
# figsize参数的单位是英寸，(宽度, 高度)
# 注意：DPI（每英寸点数）会影响最终图像的质量和大小
plt.figure(figsize=(10, 8), dpi=100)

# 第二步：设置坐标轴范围
# 这会改变图形的视角，可以突出显示数据的特定区域
plt.xlim(0, 6)  # X轴从0到6
plt.ylim(0, 6)  # Y轴从0到6

# 第三步：设置坐标轴标签
# 标签应该清晰描述坐标轴的含义
plt.xlabel("时间（月）", fontsize=12, fontweight='bold')
plt.ylabel("销售额（万元）", fontsize=12, fontweight='bold')

# 第四步：添加标题
# 标题应该简洁明了地概括图形内容
plt.title("2023年产品A与产品B销售额对比", 
           fontsize=16, 
           fontweight='bold',
           pad=20)  # pad参数控制标题与图形的距离

# 第五步：绘制数据系列
# 第一个数据系列：产品A
plt.plot(x, y1, 
         label="产品A", 
         color="red", 
         marker="*", 
         markersize=10,
         linewidth=2,
         linestyle="-",
         alpha=0.8)

# 第二个数据系列：产品B
plt.plot(x, y2, 
         label="产品B", 
         color="green", 
         marker="o", 
         markersize=8,
         linewidth=2,
         linestyle="--",
         alpha=0.8)

# 第六步：添加图例
# 图例帮助读者区分不同的数据系列
plt.legend(loc='upper left',  # 位置：左上角
           fontsize=10,
           title="产品类型",
           title_fontsize=11,
           shadow=True,  # 添加阴影效果
           framealpha=0.9)  # 设置背景透明度

# 第七步：添加网格
# 网格帮助读者更准确地读取数值
plt.grid(True, 
         linestyle='--', 
         alpha=0.5, 
         which='both')  # both表示主网格和次网格都显示

# 第八步：自定义坐标轴刻度
# 使刻度更易读
plt.xticks(np.arange(0, 7, 1), fontsize=10)
plt.yticks(np.arange(0, 7, 1), fontsize=10)

# 第九步：添加注释
# 突出显示重要数据点
plt.annotate('最高点', 
             xy=(5, 5),  # 箭头指向的点
             xytext=(4, 5.5),  # 文本位置
             arrowprops=dict(arrowstyle='->', color='blue', lw=1.5),
             fontsize=10,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.3))

# 第十步：调整布局
# 确保所有元素都不重叠
plt.tight_layout()

# 显示图形
plt.show()
```

### 6.2 配置项详细解析

#### 6.2.1 图形大小与DPI

```python
plt.figure(figsize=(宽度, 高度), dpi=分辨率)
```

- **figsize**：控制图形的物理尺寸，单位是英寸
- **dpi**：每英寸点数，控制图形的分辨率
- **黄金比例**：许多设计师使用1.618:1的黄金比例，如`figsize=(10, 6.18)`

#### 6.2.2 颜色系统

Matplotlib支持多种颜色格式：

```python
# 颜色名称
colors = ['red', 'green', 'blue', 'cyan', 'magenta', 'yellow', 'black']

# 十六进制颜色
hex_colors = ['#FF5733', '#33FF57', '#3357FF', '#F033FF']

# RGB/RGBA元组
rgb_colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0, 0.5)]  # 最后一个是RGBA，包含透明度

# 灰度值
gray_colors = ['0.1', '0.5', '0.9']  # 0是黑色，1是白色
```

#### 6.2.3 标记符号

标记符号用于突出显示数据点：

```python
markers = [
    '.',  # 点
    ',',  # 像素
    'o',  # 圆圈
    'v',  # 倒三角形
    '^',  # 正三角形
    '<',  # 左三角形
    '>',  # 右三角形
    '1',  # 三脚架下
    '2',  # 三脚架上
    '3',  # 三脚架左
    '4',  # 三脚架右
    's',  # 正方形
    'p',  # 五边形
    '*',  # 星形
    'h',  # 六边形1
    'H',  # 六边形2
    '+',  # 加号
    'x',  # X
    'D',  # 菱形
    'd',  # 薄菱形
    '|',  # 竖线
    '_',  # 横线
]
```

#### 6.2.4 线型样式

```python
linestyles = [
    '-',   # 实线
    '--',  # 虚线
    '-.',  # 点划线
    ':',   # 点线
    'None' # 无线条（只显示标记）
]
```

#### 6.2.5 图例位置

图例的位置可以通过字符串或代码指定：

```python
# 字符串方式
locations = [
    'best',           # 自动选择最佳位置
    'upper right',    # 右上
    'upper left',     # 左上
    'lower left',     # 左下
    'lower right',    # 右下
    'right',          # 右侧中间
    'center left',    # 左侧中间
    'center right',   # 右侧中间
    'lower center',   # 底部中间
    'upper center',   # 顶部中间
    'center'          # 正中心
]

# 数值方式（使用边界框坐标）
# plt.legend(bbox_to_anchor=(x, y))
```

## 第七章：高级技巧与最佳实践

### 7.1 面向对象API vs 函数式API

Matplotlib提供了两种编程接口：

```python
# 函数式API（适合快速绘图）
plt.figure()
plt.plot([1, 2, 3], [1, 4, 9])
plt.title('函数式API')
plt.show()

# 面向对象API（适合复杂图形）
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [1, 4, 9])
ax.set_title('面向对象API')
plt.show()
```

**建议**：对于简单图形使用函数式API，对于复杂图形或需要多次重用的代码使用面向对象API。

### 7.2 多子图创建

创建多个子图是Matplotlib的常见需求：

```python
# 方法1：使用subplot
plt.figure(figsize=(12, 8))

# 创建2行3列的子图网格
for i in range(1, 7):
    plt.subplot(2, 3, i)  # (行, 列, 位置)
    plt.plot([0, 1], [0, i])
    plt.title(f'子图 {i}')

plt.tight_layout()
plt.show()

# 方法2：使用subplots（更推荐）
fig, axes = plt.subplots(2, 3, figsize=(12, 8))

# axes是一个2x3的数组
for i in range(2):
    for j in range(3):
        ax = axes[i, j]
        ax.plot([0, 1], [0, (i*3 + j + 1)])
        ax.set_title(f'子图 {i*3 + j + 1}')

plt.tight_layout()
plt.show()

# 方法3：创建不均匀的子图网格
fig = plt.figure(figsize=(12, 8))

# 使用GridSpec创建复杂布局
gs = fig.add_gridspec(3, 3)

# 左上角的大图
ax1 = fig.add_subplot(gs[0, :2])
ax1.plot([0, 1], [0, 1])
ax1.set_title('主图')

# 右上角的小图
ax2 = fig.add_subplot(gs[0, 2])
ax2.plot([0, 1], [1, 0])
ax2.set_title('辅助图1')

# 底部左侧图
ax3 = fig.add_subplot(gs[1:, 0])
ax3.plot([1, 0], [0, 1])
ax3.set_title('辅助图2')

# 底部右侧图（占两行两列）
ax4 = fig.add_subplot(gs[1:, 1:])
ax4.plot([0, 1, 0], [0, 1, 0])
ax4.set_title('辅助图3')

plt.tight_layout()
plt.show()
```

### 7.3 样式表的使用

Matplotlib提供了多种预定义的样式表，可以快速改变图形外观：

```python
# 查看所有可用的样式
print(plt.style.available)

# 应用样式
plt.style.use('ggplot')

# 创建图形
fig, ax = plt.subplots(figsize=(10, 6))
x = [1, 2, 3, 4, 5]
y1 = [2, 4, 6, 8, 10]
y2 = [1, 3, 5, 7, 9]

ax.plot(x, y1, label='系列1')
ax.plot(x, y2, label='系列2')
ax.set_title('使用ggplot样式')
ax.legend()
plt.show()

# 恢复默认样式
plt.style.use('default')
```

### 7.4 保存图形

保存图形是数据可视化工作流中的重要步骤：

```python
# 创建图形
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot([1, 2, 3], [1, 4, 9])
ax.set_title('示例图形')

# 保存为不同格式
fig.savefig('plot.png', dpi=300, bbox_inches='tight')  # PNG格式，高DPI
fig.savefig('plot.pdf', bbox_inches='tight')           # PDF格式，矢量图
fig.savefig('plot.svg', bbox_inches='tight')           # SVG格式，矢量图
fig.savefig('plot.jpg', dpi=300, quality=90, bbox_inches='tight')  # JPEG格式

# 关键参数解释：
# dpi: 分辨率，越高图片越清晰，但文件越大
# bbox_inches: 'tight'会自动剪裁空白边缘
# quality: JPEG格式的质量，1-100，越高质量越好
# transparent: 是否透明背景
# facecolor/edgecolor: 图形背景/边框颜色
```

### 7.5 常见问题与解决方案

#### 问题1：中文显示乱码

```python
# 解决方案：设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
```

#### 问题2：图形显示太小或太大

```python
# 调整图形大小
plt.figure(figsize=(宽度, 高度))

# 调整DPI
plt.figure(dpi=数值)

# 保存时调整大小和DPI
fig.savefig('filename.png', dpi=300, bbox_inches='tight')
```

#### 问题3：图例被裁剪

```python
# 使用tight_layout自动调整
plt.tight_layout()

# 手动调整子图间距
plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1, wspace=0.4, hspace=0.4)

# 保存时使用bbox_inches参数
fig.savefig('filename.png', bbox_inches='tight')
```

#### 问题4：颜色不清晰或打印效果差

```python
# 使用打印友好的颜色方案
colors = ['#000000', '#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00', '#CC79A7']

# 使用灰度模式检查打印效果
plt.gray()  # 临时切换到灰度模式
```

## 第八章：实战案例——完整的数据分析可视化项目

让我们通过一个完整的案例，将所学知识融会贯通：

```python
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 创建模拟数据
np.random.seed(42)
dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
n_days = len(dates)

# 模拟三种产品的日销售额
product_A = np.random.normal(5000, 1000, n_days).cumsum() + 100000
product_B = np.random.normal(3000, 800, n_days).cumsum() + 80000
product_C = np.random.normal(2000, 600, n_days).cumsum() + 60000

# 添加季节性因素
seasonality = 1000 * np.sin(2 * np.pi * np.arange(n_days) / 365)
product_A += seasonality
product_B += seasonality * 0.8
product_C += seasonality * 0.6

# 创建DataFrame
df = pd.DataFrame({
    '日期': dates,
    '产品A': product_A,
    '产品B': product_B,
    '产品C': product_C
})

# 计算月度数据
df['月份'] = df['日期'].dt.month
monthly_data = df.groupby('月份').agg({
    '产品A': 'mean',
    '产品B': 'mean',
    '产品C': 'mean'
})

# 创建仪表板式图形
fig = plt.figure(figsize=(16, 12))

# 1. 总体趋势图（顶部，占3列）
ax1 = plt.subplot(3, 3, (1, 3))  # 占据第一行的1-3列
ax1.plot(df['日期'], df['产品A'], label='产品A', linewidth=2)
ax1.plot(df['日期'], df['产品B'], label='产品B', linewidth=2)
ax1.plot(df['日期'], df['产品C'], label='产品C', linewidth=2)
ax1.set_title('2023年产品销售额趋势', fontsize=16, fontweight='bold')
ax1.set_xlabel('日期')
ax1.set_ylabel('累计销售额（万元）')
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)
ax1.tick_params(axis='x', rotation=45)

# 2. 月度对比条形图（中间左侧，占2列）
ax2 = plt.subplot(3, 3, (4, 5))
months = ['1月', '2月', '3月', '4月', '5月', '6月', 
          '7月', '8月', '9月', '10月', '11月', '12月']
x = np.arange(len(months))
width = 0.25

ax2.bar(x - width, monthly_data['产品A'], width, label='产品A', alpha=0.8)
ax2.bar(x, monthly_data['产品B'], width, label='产品B', alpha=0.8)
ax2.bar(x + width, monthly_data['产品C'], width, label='产品C', alpha=0.8)

ax2.set_title('月平均销售额对比', fontsize=14)
ax2.set_xlabel('月份')
ax2.set_ylabel('平均销售额（万元）')
ax2.set_xticks(x)
ax2.set_xticklabels(months)
ax2.legend()
ax2.grid(True, alpha=0.3, axis='y')

# 3. 占比饼图（中间右侧）
ax3 = plt.subplot(3, 3, 6)
total_sales = [df['产品A'].iloc[-1], df['产品B'].iloc[-1], df['产品C'].iloc[-1]]
labels = ['产品A', '产品B', '产品C']
colors = ['#ff9999', '#66b3ff', '#99ff99']
explode = (0.05, 0, 0)  # 突出显示产品A

ax3.pie(total_sales, labels=labels, colors=colors, explode=explode,
        autopct='%1.1f%%', shadow=True, startangle=90)
ax3.set_title('年度销售额占比', fontsize=14)
ax3.axis('equal')  # 确保饼图是圆形

# 4. 增长率折线图（底部左侧）
ax4 = plt.subplot(3, 3, (7, 8))
# 计算月度增长率
monthly_growth_A = monthly_data['产品A'].pct_change() * 100
monthly_growth_B = monthly_data['产品B'].pct_change() * 100
monthly_growth_C = monthly_data['产品C'].pct_change() * 100

ax4.plot(months[1:], monthly_growth_A[1:], marker='o', label='产品A', linewidth=2)
ax4.plot(months[1:], monthly_growth_B[1:], marker='s', label='产品B', linewidth=2)
ax4.plot(months[1:], monthly_growth_C[1:], marker='^', label='产品C', linewidth=2)

ax4.set_title('月增长率对比（%）', fontsize=14)
ax4.set_xlabel('月份')
ax4.set_ylabel('增长率（%）')
ax4.legend()
ax4.grid(True, alpha=0.3)
ax4.axhline(y=0, color='black', linestyle='-', alpha=0.3)

# 5. 箱线图（底部右侧）
ax5 = plt.subplot(3, 3, 9)
monthly_values = [df[df['月份'] == i]['产品A'].values for i in range(1, 13)]
bp = ax5.boxplot(monthly_values, labels=months)
ax5.set_title('产品A月度分布箱线图', fontsize=14)
ax5.set_xlabel('月份')
ax5.set_ylabel('销售额（万元）')
ax5.tick_params(axis='x', rotation=45)
ax5.grid(True, alpha=0.3)

# 添加整体标题
fig.suptitle('2023年度产品销售分析仪表板', fontsize=20, fontweight='bold', y=0.98)

# 调整布局
plt.tight_layout(rect=[0, 0, 1, 0.96])  # 为总标题留出空间

# 保存图形
plt.savefig('销售分析仪表板.png', dpi=300, bbox_inches='tight')

# 显示图形
plt.show()
```

这个案例展示了如何：
1. 创建真实感强的模拟数据
2. 使用多种图形类型展示不同方面的信息
3. 创建复杂的多子图布局
4. 应用专业的数据可视化最佳实践
5. 保存高质量的图形文件

## 第九章：学习路线图与资源推荐

### 9.1 学习路线图

1. **第一阶段：基础掌握（1-2周）**
   - 安装和环境配置
   - 掌握基础图形：折线图、散点图、条形图
   - 理解基本配置：标题、坐标轴、图例

2. **第二阶段：进阶技巧（2-3周）**
   - 学习多子图创建
   - 掌握样式和颜色配置
   - 学习保存和导出图形

3. **第三阶段：实战应用（3-4周）**
   - 结合Pandas进行数据分析可视化
   - 创建复杂的仪表板
   - 学习性能优化技巧

4. **第四阶段：精通（持续学习）**
   - 学习Matplotlib高级特性
   - 探索扩展库（Seaborn、Plotly等）
   - 参与开源项目或创建自己的可视化库

### 9.2 推荐资源

#### 在线教程
- **官方文档**：https://matplotlib.org/stable/contents.html
- **Matplotlib教程（斯坦福大学）**：https://stanford.edu/~mgorkove/cgi-bin/rpython_tutorials/
- **Real Python Matplotlib指南**：https://realpython.com/python-matplotlib-guide/

#### 书籍推荐
- 《Python数据可视化之Matplotlib实践》
- 《Matplotlib 3.0 Cookbook》
- 《Python数据科学手册》（第4章专门讲解Matplotlib）

#### 实践平台
- **Kaggle**：参与数据可视化竞赛
- **GitHub**：查看优秀的数据可视化项目
- **Observable**：探索交互式可视化示例

### 9.3 常见错误与避免方法

1. **错误**：图形元素重叠
   **解决**：使用`plt.tight_layout()`或调整子图间距

2. **错误**：图形保存不完整
   **解决**：使用`bbox_inches='tight'`参数

3. **错误**：颜色不清晰或打印效果差
   **解决**：使用打印友好的调色板，并用灰度模式检查

4. **错误**：代码混乱，难以维护
   **解决**：使用面向对象API，将图形创建代码封装成函数

5. **错误**：图形加载或渲染缓慢
   **解决**：减少数据点数量，使用`rasterized=True`参数，或使用更高效的图形格式
