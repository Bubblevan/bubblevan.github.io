---
id: embeded-control-algorithm
title: 控制算法
sidebar_label: 05-控制算法
---

# 控制算法

> 控制算法是机器人的"智慧"，决定了机器人的运动能力和稳定性。

## 逆运动学

### 基本原理

逆运动学（Inverse Kinematics, IK）是根据末端执行器的目标位置，计算各个关节的角度。

对于四足机器人，每条腿有3个自由度：
- **髋关节**（α）：控制腿的前后摆动
- **膝关节**（β）：控制腿的弯曲
- **踝关节**（γ）：控制足部的角度

### 坐标系定义

```
身体坐标系（Body Frame）：
  X: 前后方向（前为正）
  Y: 左右方向（右为正）
  Z: 上下方向（上为正）

腿坐标系（Leg Frame）：
  以髋关节为原点
```

### 单腿逆运动学

#### 几何参数

```
L1: 大腿长度
L2: 小腿长度
L3: 足部长度（可选）
```

#### 计算步骤

给定目标位置 `(x, y, z)`：

1. **计算髋关节角度 α**
   ```cpp
   α = atan2(y, x)
   ```

2. **计算投影距离**
   ```cpp
   r = sqrt(x² + y²)  // 在X-Y平面的投影
   s = sqrt(r² + z²)  // 到髋关节的距离
   ```

3. **计算膝关节角度 β**
   ```cpp
   // 使用余弦定理
   cos_β = (L1² + L2² - s²) / (2 * L1 * L2)
   β = acos(cos_β)
   ```

4. **计算踝关节角度 γ**
   ```cpp
   // 先计算中间角度
   θ1 = atan2(z, r)
   θ2 = acos((L1² + s² - L2²) / (2 * L1 * s))
   γ = θ1 + θ2
   ```

#### 代码实现

```cpp
struct Point3D {
    float x, y, z;
};

struct LegAngles {
    float hip;      // α
    float knee;     // β
    float ankle;    // γ
};

LegAngles inverseKinematics(Point3D target, float L1, float L2) {
    LegAngles angles;
    
    // 髋关节角度
    angles.hip = atan2(target.y, target.x);
    
    // 投影距离
    float r = sqrt(target.x * target.x + target.y * target.y);
    float s = sqrt(r * r + target.z * target.z);
    
    // 检查是否可达
    if (s > (L1 + L2) || s < abs(L1 - L2)) {
        // 不可达，返回错误或限制值
        return angles;
    }
    
    // 膝关节角度
    float cos_beta = (L1 * L1 + L2 * L2 - s * s) / (2 * L1 * L2);
    angles.knee = acos(cos_beta);
    
    // 踝关节角度
    float theta1 = atan2(target.z, r);
    float theta2 = acos((L1 * L1 + s * s - L2 * L2) / (2 * L1 * s));
    angles.ankle = theta1 + theta2;
    
    return angles;
}
```

## 步态规划

### 步态类型

#### 1. 站立（Stand）

所有腿同时支撑，保持稳定。

```cpp
void stand() {
    // 设置所有腿到站立位置
    Point3D standPos = {0, legOffsetY, -standHeight};
    for (int i = 0; i < 4; i++) {
        setLegPosition(i, standPos);
    }
}
```

#### 2. 行走（Walk）

四足交替移动，始终有3条腿支撑。

**步态序列**：
```
1. 左前腿抬起 → 前进 → 放下
2. 右后腿抬起 → 前进 → 放下
3. 右前腿抬起 → 前进 → 放下
4. 左后腿抬起 → 前进 → 放下
循环...
```

#### 3. 小跑（Trot）

对角腿同步，速度快。

**步态序列**：
```
支撑相：左前+右后 支撑，右前+左后 摆动
摆动相：右前+左后 支撑，左前+右后 摆动
```

#### 4. 转向（Turn）

通过调整各腿的步幅实现转向。

### 轨迹生成

#### 摆动相轨迹

使用抛物线或正弦曲线生成平滑轨迹：

```cpp
Point3D generateSwingTrajectory(float t, Point3D start, Point3D end, float liftHeight) {
    // t: 0.0 - 1.0
    Point3D pos;
    
    // 水平方向线性插值
    pos.x = start.x + (end.x - start.x) * t;
    pos.y = start.y + (end.y - start.y) * t;
    
    // 垂直方向抛物线
    float z_base = start.z + (end.z - start.z) * t;
    float z_lift = 4 * liftHeight * t * (1 - t);  // 抛物线
    pos.z = z_base + z_lift;
    
    return pos;
}
```

#### 支撑相轨迹

身体相对于支撑腿移动：

```cpp
void updateSupportPhase(int legIndex, float t, float stepLength) {
    // t: 0.0 - 1.0
    Point3D footPos = getFootPosition(legIndex);
    
    // 身体向前移动，足部相对向后
    footPos.x -= stepLength * t;
    
    setLegPosition(legIndex, footPos);
}
```

## 姿态控制

### 身体姿态调整

通过调整各腿的长度，实现身体姿态控制：

```cpp
void setBodyPose(float roll, float pitch, float yaw) {
    // roll: 左右倾斜
    // pitch: 前后倾斜
    // yaw: 左右转向
    
    for (int i = 0; i < 4; i++) {
        Point3D offset = calculatePoseOffset(i, roll, pitch, yaw);
        Point3D currentPos = getLegPosition(i);
        currentPos.z += offset.z;
        setLegPosition(i, currentPos);
    }
}
```

### 平衡控制

使用IMU传感器进行平衡控制：

```cpp
void balanceControl() {
    float roll, pitch;
    readIMUAttitude(roll, pitch);
    
    // PID控制
    float rollCorrection = pidRoll.compute(0 - roll);
    float pitchCorrection = pidPitch.compute(0 - pitch);
    
    setBodyPose(rollCorrection, pitchCorrection, 0);
}
```

## 动作库

### 基础动作

#### 挥手

```cpp
void wave(int legIndex) {
    Point3D startPos = getLegPosition(legIndex);
    Point3D wavePos = startPos;
    
    for (int i = 0; i < 3; i++) {
        // 抬起
        wavePos.z += 30;
        setLegPosition(legIndex, wavePos);
        delay(200);
        
        // 左右摆动
        wavePos.y += (i % 2 == 0 ? 20 : -20);
        setLegPosition(legIndex, wavePos);
        delay(200);
    }
    
    // 恢复
    setLegPosition(legIndex, startPos);
}
```

#### 点头

```cpp
void nod() {
    float originalHeight = standHeight;
    
    for (int i = 0; i < 2; i++) {
        // 降低
        setStandHeight(originalHeight - 20);
        delay(300);
        
        // 恢复
        setStandHeight(originalHeight);
        delay(300);
    }
}
```

### 动作序列

```cpp
class ActionSequence {
private:
    struct Action {
        String name;
        void (*func)();
        int duration;
    };
    
    Action actions[10];
    int count;
    
public:
    void add(String name, void (*func)(), int duration) {
        actions[count] = {name, func, duration};
        count++;
    }
    
    void play() {
        for (int i = 0; i < count; i++) {
            actions[i].func();
            delay(actions[i].duration);
        }
    }
};
```

## 参数调优

### 关键参数

- **步长（Step Length）**：影响移动速度
- **步高（Step Height）**：影响越障能力
- **周期（Cycle Time）**：影响步频
- **支撑相比例**：影响稳定性

### 调优方法

1. **单参数扫描**：固定其他参数，调整一个参数
2. **正交实验**：系统性地测试参数组合
3. **实际测试**：在真实环境中测试和调整

## 常见问题

### Q: 机器人行走不稳定？
A:
- 检查重心位置
- 调整步态参数
- 增加平衡控制

### Q: 逆运动学计算错误？
A:
- 检查坐标系定义
- 验证几何参数
- 添加边界检查

### Q: 动作不流畅？
A:
- 增加轨迹插值点
- 调整舵机速度
- 优化控制频率
