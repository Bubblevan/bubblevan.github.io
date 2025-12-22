---
id: embeded-debug-optimize
title: 调试与优化
sidebar_label: 07-调试与优化
---

# 调试与优化

> 调试是开发过程中必不可少的环节，优化让机器人运行得更好。

## 调试方法

### 串口调试

最基础的调试方法：

```cpp
#define DEBUG_LEVEL 1  // 0=关闭, 1=基础, 2=详细

#if DEBUG_LEVEL >= 1
    #define DEBUG_PRINT(x) Serial.print(x)
    #define DEBUG_PRINTLN(x) Serial.println(x)
#else
    #define DEBUG_PRINT(x)
    #define DEBUG_PRINTLN(x)
#endif

#if DEBUG_LEVEL >= 2
    #define DEBUG_VERBOSE(x) Serial.print(x)
    #define DEBUG_VERBOSE_LN(x) Serial.println(x)
#else
    #define DEBUG_VERBOSE(x)
    #define DEBUG_VERBOSE_LN(x)
#endif

// 使用示例
DEBUG_PRINT("Servo angle: ");
DEBUG_PRINTLN(angle);
```

### 日志系统

更完善的日志系统：

```cpp
enum LogLevel {
    LOG_ERROR,
    LOG_WARNING,
    LOG_INFO,
    LOG_DEBUG
};

void log(LogLevel level, String message) {
    String prefix;
    switch(level) {
        case LOG_ERROR:   prefix = "[ERROR] "; break;
        case LOG_WARNING: prefix = "[WARN] "; break;
        case LOG_INFO:    prefix = "[INFO] "; break;
        case LOG_DEBUG:   prefix = "[DEBUG] "; break;
    }
    
    Serial.print(prefix);
    Serial.println(message);
}

// 使用示例
log(LOG_INFO, "Robot initialized");
log(LOG_ERROR, "Servo timeout");
```

### 性能分析

测量代码执行时间：

```cpp
unsigned long startTime, endTime;

void measureTime(String label) {
    startTime = micros();
}

void endMeasure(String label) {
    endTime = micros();
    DEBUG_PRINT(label + ": ");
    DEBUG_PRINTLN(endTime - startTime);
}

// 使用示例
measureTime("Gait update");
updateGait();
endMeasure("Gait update");
```

## 硬件调试

### 舵机测试

```cpp
void testAllServos() {
    Serial.println("Testing all servos...");
    
    for (int i = 0; i < 12; i++) {
        Serial.print("Servo ");
        Serial.print(i);
        Serial.println(": 0 -> 90 -> 180");
        
        servos[i].write(0);
        delay(1000);
        servos[i].write(90);
        delay(1000);
        servos[i].write(180);
        delay(1000);
        servos[i].write(90);
        delay(500);
    }
    
    Serial.println("Test complete");
}
```

### 单腿测试

```cpp
void testLeg(int legIndex) {
    Serial.print("Testing leg ");
    Serial.println(legIndex);
    
    // 测试运动范围
    Point3D testPoints[] = {
        {50, 0, -80},   // 前
        {0, 50, -80},   // 右
        {-50, 0, -80},  // 后
        {0, -50, -80},  // 左
        {0, 0, -60},    // 上
        {0, 0, -100}    // 下
    };
    
    for (int i = 0; i < 6; i++) {
        Serial.print("Moving to point ");
        Serial.println(i);
        setLegPosition(legIndex, testPoints[i]);
        delay(2000);
    }
    
    // 恢复初始位置
    setLegPosition(legIndex, {0, 0, -80});
}
```

### 传感器校准

```cpp
void calibrateIMU() {
    Serial.println("Calibrating IMU...");
    Serial.println("Keep robot still for 5 seconds");
    
    float sum_ax = 0, sum_ay = 0, sum_az = 0;
    int samples = 100;
    
    for (int i = 0; i < samples; i++) {
        float ax, ay, az;
        readIMU(ax, ay, az, 0, 0, 0);
        sum_ax += ax;
        sum_ay += ay;
        sum_az += az;
        delay(50);
    }
    
    // 计算偏移量
    offset_ax = sum_ax / samples;
    offset_ay = sum_ay / samples;
    offset_az = (sum_az / samples) - 1.0;  // 重力加速度
    
    Serial.print("Offsets: ");
    Serial.print(offset_ax);
    Serial.print(", ");
    Serial.print(offset_ay);
    Serial.print(", ");
    Serial.println(offset_az);
}
```

## 软件优化

### 内存优化

```cpp
// 避免动态内存分配
// 不好：
String message = "Hello " + name;

// 好：
char message[50];
sprintf(message, "Hello %s", name);

// 使用固定大小数组
#define MAX_COMMANDS 10
String commandQueue[MAX_COMMANDS];
int queueHead = 0, queueTail = 0;
```

### 计算优化

```cpp
// 预计算常量
const float PI_OVER_180 = PI / 180.0;

// 使用查找表（LUT）
float sinLUT[360];
void initSinLUT() {
    for (int i = 0; i < 360; i++) {
        sinLUT[i] = sin(i * PI_OVER_180);
    }
}

float fastSin(int angle) {
    angle = angle % 360;
    if (angle < 0) angle += 360;
    return sinLUT[angle];
}
```

### 控制频率优化

```cpp
// 使用定时器中断，保证控制频率
hw_timer_t * timer = NULL;

void IRAM_ATTR onTimer() {
    // 在中断中更新关键控制
    updateGait();
    updateServos();
}

void setupTimer() {
    timer = timerBegin(0, 80, true);  // 1MHz
    timerAttachInterrupt(timer, &onTimer, true);
    timerAlarmWrite(timer, 20000, true);  // 20ms = 50Hz
    timerAlarmEnable(timer);
}
```

## 稳定性优化

### 平滑控制

```cpp
// 使用低通滤波器平滑控制信号
class LowPassFilter {
private:
    float alpha;
    float lastValue;
    
public:
    LowPassFilter(float alpha) : alpha(alpha), lastValue(0) {}
    
    float filter(float input) {
        lastValue = alpha * input + (1 - alpha) * lastValue;
        return lastValue;
    }
};

LowPassFilter angleFilter(0.1);  // 平滑系数

void smoothServoControl(int servoIndex, float targetAngle) {
    float currentAngle = servos[servoIndex].read();
    float filteredAngle = angleFilter.filter(targetAngle);
    servos[servoIndex].write(filteredAngle);
}
```

### 错误恢复

```cpp
void checkServoError() {
    for (int i = 0; i < 12; i++) {
        // 检查舵机是否响应
        int currentAngle = servos[i].read();
        int targetAngle = targetAngles[i];
        
        if (abs(currentAngle - targetAngle) > 10) {
            // 误差过大，尝试重新设置
            log(LOG_WARNING, "Servo " + String(i) + " error detected");
            servos[i].write(targetAngle);
        }
    }
}
```

## 测试流程

### 单元测试

```cpp
void testInverseKinematics() {
    // 测试逆运动学计算
    Point3D testPoints[] = {
        {50, 0, -80},
        {0, 50, -80},
        {-50, 0, -80}
    };
    
    for (int i = 0; i < 3; i++) {
        LegAngles angles = inverseKinematics(testPoints[i], 60, 80);
        
        // 验证角度范围
        assert(angles.hip >= -90 && angles.hip <= 90);
        assert(angles.knee >= 0 && angles.knee <= 180);
        assert(angles.ankle >= -90 && angles.ankle <= 90);
        
        // 验证正运动学（可选）
        Point3D result = forwardKinematics(angles, 60, 80);
        float error = distance(testPoints[i], result);
        assert(error < 1.0);  // 误差小于1mm
    }
}
```

### 集成测试

```cpp
void testWalkCycle() {
    // 测试完整行走周期
    startWalk(10);  // 走10步
    
    int stepCount = 0;
    while (isMoving()) {
        update();
        if (stepCompleted()) {
            stepCount++;
            log(LOG_INFO, "Step " + String(stepCount) + " completed");
        }
        delay(20);
    }
    
    assert(stepCount == 10);
    log(LOG_INFO, "Walk test passed");
}
```

## 性能指标

### 关键指标

- **控制频率**：目标50Hz（20ms周期）
- **响应时间**：命令响应 < 100ms
- **稳定性**：能稳定行走 > 1分钟
- **精度**：位置误差 < 5mm

### 监控方法

```cpp
struct PerformanceMetrics {
    unsigned long loopTime;
    unsigned long maxLoopTime;
    int servoUpdateCount;
    int errorCount;
};

PerformanceMetrics metrics;

void updateMetrics() {
    static unsigned long lastTime = 0;
    unsigned long currentTime = micros();
    
    metrics.loopTime = currentTime - lastTime;
    if (metrics.loopTime > metrics.maxLoopTime) {
        metrics.maxLoopTime = metrics.loopTime;
    }
    
    lastTime = currentTime;
}

void printMetrics() {
    Serial.print("Loop time: ");
    Serial.print(metrics.loopTime);
    Serial.print("us, Max: ");
    Serial.print(metrics.maxLoopTime);
    Serial.print("us, Errors: ");
    Serial.println(metrics.errorCount);
}
```

## 常见问题排查

### 问题1：机器人抖动

**可能原因**：
- 电源不稳定
- 控制频率过高
- 机械结构松动

**解决方法**：
- 增加滤波电容
- 降低控制频率
- 检查机械连接

### 问题2：行走不稳定

**可能原因**：
- 重心偏移
- 步态参数不当
- 地面不平

**解决方法**：
- 调整重心位置
- 优化步态参数
- 增加平衡控制

### 问题3：通信延迟

**可能原因**：
- 数据传输量大
- 处理速度慢
- 信号干扰

**解决方法**：
- 减少数据传输
- 优化处理算法
- 改善天线设计
