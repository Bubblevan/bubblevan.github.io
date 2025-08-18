# Python 编程学习笔记

## 课程概述

Python 是生物医学工程专业的重要编程语言，广泛应用于数据分析、信号处理、机器学习等领域。

## 学习目标

- 掌握 Python 基本语法和编程思想
- 学会使用 Python 进行科学计算
- 能够处理生物医学数据
- 为后续专业课程打下编程基础

## 核心内容

### 基础语法

#### 变量和数据类型
```python
# 基本数据类型
name = "包博文"          # 字符串
age = 25               # 整数
height = 175.5         # 浮点数
is_student = True      # 布尔值

# 复合数据类型
hobbies = ["编程", "阅读", "运动"]  # 列表
info = {"name": "包博文", "age": 25}  # 字典
coordinates = (10, 20)  # 元组
```

#### 控制结构
```python
# 条件语句
if age >= 18:
    print("成年人")
elif age >= 12:
    print("青少年")
else:
    print("儿童")

# 循环语句
for hobby in hobbies:
    print(f"爱好: {hobby}")

# while 循环
count = 0
while count < 5:
    print(count)
    count += 1
```

#### 函数定义
```python
def greet(name, greeting="Hello"):
    """问候函数"""
    return f"{greeting}, {name}!"

# 调用函数
result = greet("包博文")
print(result)  # Hello, 包博文!

# 带默认参数的函数
def calculate_bmi(weight, height):
    """计算BMI指数"""
    bmi = weight / (height / 100) ** 2
    return round(bmi, 2)

bmi = calculate_bmi(70, 175)
print(f"BMI: {bmi}")
```

### 面向对象编程

#### 类和对象
```python
class Student:
    """学生类"""
    
    def __init__(self, name, age, major):
        self.name = name
        self.age = age
        self.major = major
        self.courses = []
    
    def add_course(self, course):
        """添加课程"""
        self.courses.append(course)
        print(f"{self.name} 添加了课程: {course}")
    
    def get_info(self):
        """获取学生信息"""
        return {
            "name": self.name,
            "age": self.age,
            "major": self.major,
            "courses": self.courses
        }

# 创建学生对象
student = Student("包博文", 25, "生物医学工程")
student.add_course("Python编程")
student.add_course("生物信号处理")
print(student.get_info())
```

#### 继承和多态
```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
    
    def introduce(self):
        return f"我是 {self.name}，今年 {self.age} 岁"

class Student(Person):
    def __init__(self, name, age, student_id):
        super().__init__(name, age)
        self.student_id = student_id
    
    def introduce(self):
        return f"{super().introduce()}，学号是 {self.student_id}"

# 多态示例
person = Person("张三", 30)
student = Student("包博文", 25, "2021001")

print(person.introduce())
print(student.introduce())
```

### 数据处理

#### NumPy 基础
```python
import numpy as np

# 创建数组
arr1 = np.array([1, 2, 3, 4, 5])
arr2 = np.zeros((3, 3))
arr3 = np.ones((2, 4))
arr4 = np.arange(0, 10, 2)

# 数组操作
print(arr1.shape)  # (5,)
print(arr1.dtype)  # int64
print(arr1.mean())  # 平均值
print(arr1.std())   # 标准差

# 矩阵运算
matrix1 = np.array([[1, 2], [3, 4]])
matrix2 = np.array([[5, 6], [7, 8]])
result = np.dot(matrix1, matrix2)
print(result)
```

#### Pandas 数据处理
```python
import pandas as pd

# 创建数据框
data = {
    '姓名': ['包博文', '张三', '李四'],
    '年龄': [25, 30, 28],
    '专业': ['生物医学工程', '计算机科学', '机械工程'],
    '成绩': [85, 92, 78]
}
df = pd.DataFrame(data)

# 数据查看
print(df.head())
print(df.describe())

# 数据筛选
young_students = df[df['年龄'] < 30]
high_scores = df[df['成绩'] > 80]

# 数据统计
print(f"平均年龄: {df['年龄'].mean()}")
print(f"成绩标准差: {df['成绩'].std()}")
```

### 科学计算

#### 信号处理
```python
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

# 生成模拟心电信号
t = np.linspace(0, 10, 1000)
# 模拟心跳信号
heartbeat = np.sin(2 * np.pi * 1.2 * t) * np.exp(-0.5 * t)
noise = np.random.normal(0, 0.1, len(t))
ecg_signal = heartbeat + noise

# 滤波处理
b, a = signal.butter(4, 0.1, 'low')
filtered_signal = signal.filtfilt(b, a, ecg_signal)

# 绘制结果
plt.figure(figsize=(12, 6))
plt.subplot(2, 1, 1)
plt.plot(t, ecg_signal, label='原始信号')
plt.title('原始心电信号')
plt.legend()

plt.subplot(2, 1, 2)
plt.plot(t, filtered_signal, label='滤波后信号', color='red')
plt.title('滤波后心电信号')
plt.legend()
plt.tight_layout()
plt.show()
```

#### 图像处理
```python
import cv2
import numpy as np
import matplotlib.pyplot as plt

# 读取图像
image = cv2.imread('medical_image.jpg')
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# 图像预处理
# 高斯模糊
blurred = cv2.GaussianBlur(gray, (5, 5), 0)

# 边缘检测
edges = cv2.Canny(blurred, 50, 150)

# 显示结果
plt.figure(figsize=(15, 5))
plt.subplot(1, 3, 1)
plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
plt.title('原始图像')

plt.subplot(1, 3, 2)
plt.imshow(blurred, cmap='gray')
plt.title('高斯模糊')

plt.subplot(1, 3, 3)
plt.imshow(edges, cmap='gray')
plt.title('边缘检测')
plt.show()
```

### 机器学习基础

#### 数据预处理
```python
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

# 加载数据（示例）
# 假设我们有医疗数据
X = np.random.randn(100, 5)  # 特征
y = np.random.randint(0, 2, 100)  # 标签

# 数据分割
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 数据标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 训练模型
model = LogisticRegression()
model.fit(X_train_scaled, y_train)

# 预测和评估
y_pred = model.predict(X_test_scaled)
accuracy = accuracy_score(y_test, y_pred)
print(f"准确率: {accuracy:.2f}")
```

## 实践项目

### 项目一：生物信号分析器
```python
class BioSignalAnalyzer:
    """生物信号分析器"""
    
    def __init__(self, signal, sampling_rate):
        self.signal = np.array(signal)
        self.sampling_rate = sampling_rate
        self.time = np.arange(len(signal)) / sampling_rate
    
    def filter_signal(self, low_freq=0.5, high_freq=50):
        """带通滤波"""
        from scipy.signal import butter, filtfilt
        
        nyquist = self.sampling_rate / 2
        low = low_freq / nyquist
        high = high_freq / nyquist
        
        b, a = butter(4, [low, high], btype='band')
        filtered = filtfilt(b, a, self.signal)
        return filtered
    
    def find_peaks(self, height=None, distance=None):
        """峰值检测"""
        from scipy.signal import find_peaks
        
        peaks, properties = find_peaks(self.signal, height=height, distance=distance)
        return peaks, properties
    
    def calculate_hrv(self):
        """计算心率变异性"""
        peaks, _ = self.find_peaks(height=0.5, distance=50)
        rr_intervals = np.diff(peaks) / self.sampling_rate * 1000  # 转换为毫秒
        
        hrv_metrics = {
            'mean_rr': np.mean(rr_intervals),
            'std_rr': np.std(rr_intervals),
            'rmssd': np.sqrt(np.mean(np.diff(rr_intervals) ** 2))
        }
        return hrv_metrics
    
    def plot_signal(self, filtered=False):
        """绘制信号"""
        plt.figure(figsize=(12, 6))
        
        if filtered:
            signal_to_plot = self.filter_signal()
            title = "滤波后信号"
        else:
            signal_to_plot = self.signal
            title = "原始信号"
        
        plt.plot(self.time, signal_to_plot)
        plt.title(title)
        plt.xlabel('时间 (秒)')
        plt.ylabel('幅值')
        plt.grid(True)
        plt.show()

# 使用示例
# 生成模拟心电信号
t = np.linspace(0, 10, 1000)
ecg = np.sin(2 * np.pi * 1.2 * t) * np.exp(-0.1 * t) + 0.1 * np.random.randn(1000)

analyzer = BioSignalAnalyzer(ecg, 100)
analyzer.plot_signal()
analyzer.plot_signal(filtered=True)

hrv = analyzer.calculate_hrv()
print("心率变异性指标:", hrv)
```

## 学习资源

### 官方文档
- [Python 官方文档](https://docs.python.org/)
- [NumPy 文档](https://numpy.org/doc/)
- [Pandas 文档](https://pandas.pydata.org/docs/)
- [SciPy 文档](https://scipy.org/)

### 在线课程
- Python 官方教程
- Coursera Python 课程
- 慕课网 Python 课程

### 实践平台
- Jupyter Notebook
- Google Colab
- Kaggle

## 学习心得

### 学习建议
1. **多写代码**: 通过实践掌握语法
2. **项目驱动**: 通过项目学习应用
3. **阅读源码**: 学习优秀的代码风格
4. **参与社区**: 加入 Python 社区

### 常见问题
1. **环境配置**: 正确安装 Python 和相关库
2. **版本兼容**: 注意不同版本的差异
3. **性能优化**: 学习提高代码效率的方法
4. **调试技巧**: 掌握调试工具的使用 