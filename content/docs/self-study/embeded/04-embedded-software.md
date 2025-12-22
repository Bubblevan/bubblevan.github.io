---
id: embeded-software
title: 嵌入式软件
sidebar_label: 04-嵌入式软件
---

# 嵌入式软件开发

> 软件是机器人的"大脑"，控制硬件实现各种功能。

## 开发环境搭建

### 选项1：Arduino IDE

**优点**：
- 简单易用
- 库丰富
- 社区支持好

**缺点**：
- 代码管理不够方便
- 调试功能较弱

**安装步骤**：
1. 下载Arduino IDE
2. 添加ESP32开发板支持
3. 安装必要库

### 选项2：PlatformIO

**优点**：
- 专业的嵌入式开发环境
- 代码管理方便
- 调试功能强
- 支持多平台

**缺点**：
- 学习曲线稍陡

**推荐使用PlatformIO**（VS Code插件）

### 选项3：ESP-IDF

**优点**：
- 官方框架
- 功能最全
- 性能最优

**缺点**：
- 学习曲线陡
- 配置复杂

## 项目结构

```
quadruped-robot/
├── src/
│   ├── main.cpp          # 主程序
│   ├── servo.h/cpp       # 舵机驱动
│   ├── kinematics.h/cpp  # 运动学
│   ├── gait.h/cpp        # 步态规划
│   ├── communication.h/cpp # 通信协议
│   └── sensor.h/cpp      # 传感器驱动
├── include/
│   └── config.h          # 配置文件
├── platformio.ini        # PlatformIO配置
└── README.md
```

## 舵机驱动

### PWM控制原理

舵机通过PWM信号控制角度：
- **周期**：20ms（50Hz）
- **脉宽**：0.5ms - 2.5ms
- **角度范围**：0° - 180°

```
0.5ms  → 0°
1.5ms  → 90°
2.5ms  → 180°
```

### ESP32 PWM配置

```cpp
// 使用ESP32的LEDC（PWM）功能
#include "driver/ledc.h"

#define SERVO_PIN 2
#define SERVO_CHANNEL LEDC_CHANNEL_0
#define SERVO_FREQ 50  // 50Hz
#define SERVO_RESOLUTION LEDC_TIMER_13_BIT  // 8192级

void setupServo() {
    ledcSetup(SERVO_CHANNEL, SERVO_FREQ, SERVO_RESOLUTION);
    ledcAttachPin(SERVO_PIN, SERVO_CHANNEL);
}

void setServoAngle(int angle) {
    // 角度转脉宽：0.5ms + angle * 2ms / 180
    int pulseWidth = 500 + (angle * 2000 / 180);
    // 转换为PWM值
    int pwmValue = (pulseWidth * 8192) / 20000;
    ledcWrite(SERVO_CHANNEL, pwmValue);
}
```

### 舵机类封装

```cpp
class Servo {
private:
    int pin;
    int channel;
    int currentAngle;
    
public:
    Servo(int pin, int channel);
    void attach();
    void write(int angle);
    void writeMicroseconds(int us);
    int read();
};
```

## 传感器驱动

### MPU6050 (IMU)

```cpp
#include "Wire.h"
#include "MPU6050.h"

MPU6050 mpu;

void setupIMU() {
    Wire.begin();
    mpu.initialize();
    // 校准（可选）
}

void readIMU(float &ax, float &ay, float &az, 
             float &gx, float &gy, float &gz) {
    int16_t acc[3], gyro[3];
    mpu.getMotion6(&acc[0], &acc[1], &acc[2],
                   &gyro[0], &gyro[1], &gyro[2]);
    
    // 转换为实际单位
    ax = acc[0] / 16384.0;  // ±2g范围
    // ... 其他轴类似
}
```

## 通信协议

### 蓝牙通信

```cpp
#include "BluetoothSerial.h"

BluetoothSerial SerialBT;

void setupBluetooth() {
    SerialBT.begin("QuadrupedRobot");
}

void handleBluetooth() {
    if (SerialBT.available()) {
        String command = SerialBT.readString();
        // 解析命令并执行
        parseCommand(command);
    }
}
```

### 命令协议设计

```
格式：<动作类型>:<参数1>,<参数2>,...

示例：
- "walk:forward,10"  # 向前走10步
- "gait:trot"        # 切换到trot步态
- "pose:stand"       # 站立姿态
- "action:wave"      # 挥手动作
```

## 主程序框架

```cpp
#include "servo.h"
#include "kinematics.h"
#include "gait.h"
#include "communication.h"
#include "sensor.h"

void setup() {
    Serial.begin(115200);
    
    // 初始化各模块
    setupServos();
    setupIMU();
    setupBluetooth();
    
    // 初始化姿态
    stand();
    
    Serial.println("Robot Ready!");
}

void loop() {
    // 读取传感器
    updateSensors();
    
    // 处理通信
    handleBluetooth();
    
    // 更新步态（如果正在运动）
    if (isMoving()) {
        updateGait();
    }
    
    // 更新舵机位置
    updateServos();
    
    delay(20);  // 50Hz控制频率
}
```

## 调试技巧

### 串口调试

```cpp
#define DEBUG 1

#if DEBUG
    #define DEBUG_PRINT(x) Serial.print(x)
    #define DEBUG_PRINTLN(x) Serial.println(x)
#else
    #define DEBUG_PRINT(x)
    #define DEBUG_PRINTLN(x)
#endif
```

### 舵机测试

```cpp
void testServo(int servoIndex) {
    for (int angle = 0; angle <= 180; angle += 10) {
        servos[servoIndex].write(angle);
        delay(500);
    }
}
```

### 单腿测试

```cpp
void testLeg(int legIndex) {
    // 测试单条腿的运动范围
    // 验证逆运动学计算
}
```

## 性能优化

1. **减少延迟**：优化控制循环
2. **PWM频率**：根据舵机特性调整
3. **传感器采样**：合理设置采样率
4. **通信优化**：减少数据传输量

## 常见问题

### Q: 舵机不响应？
A:
- 检查电源是否足够
- 检查PWM信号是否正确
- 检查接线是否牢固

### Q: 程序运行不稳定？
A:
- 检查内存使用（避免动态分配）
- 检查看门狗设置
- 添加异常处理

### Q: 通信延迟大？
A:
- 优化通信协议
- 减少数据传输频率
- 使用更高效的编码方式
