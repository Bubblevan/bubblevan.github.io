---
id: embeded-communication
title: 通信与交互
sidebar_label: 06-通信与交互
---

# 通信与交互

> 通信是机器人与外界交互的桥梁，实现远程控制和状态反馈。

## 蓝牙通信

### ESP32蓝牙配置

ESP32支持经典蓝牙（BT）和低功耗蓝牙（BLE），推荐使用BLE（功耗更低）。

```cpp
#include "BLEDevice.h"
#include "BLEServer.h"
#include "BLEUtils.h"

BLEServer* pServer = NULL;
BLECharacteristic* pCharacteristic = NULL;

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        Serial.println("Client connected");
    }
    
    void onDisconnect(BLEServer* pServer) {
        Serial.println("Client disconnected");
        BLEDevice::startAdvertising();
    }
};

class MyCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        std::string value = pCharacteristic->getValue();
        if (value.length() > 0) {
            Serial.println("Received: " + String(value.c_str()));
            handleCommand(String(value.c_str()));
        }
    }
};

void setupBluetooth() {
    BLEDevice::init("QuadrupedRobot");
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());
    
    BLEService *pService = pServer->createService(SERVICE_UUID);
    
    pCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_UUID,
        BLECharacteristic::PROPERTY_READ |
        BLECharacteristic::PROPERTY_WRITE
    );
    
    pCharacteristic->setCallbacks(new MyCallbacks());
    pService->start();
    
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06);
    BLEDevice::startAdvertising();
    
    Serial.println("BLE Server started");
}
```

## 通信协议设计

### 命令格式

采用简单的文本协议，易于解析和调试：

```
格式：<命令>:<参数1>,<参数2>,...

示例：
- "walk:forward,10"      # 向前走10步
- "walk:backward,5"       # 向后走5步
- "walk:left,3"           # 向左转3步
- "walk:right,3"          # 向右转3步
- "gait:trot"             # 切换到trot步态
- "gait:walk"             # 切换到walk步态
- "pose:stand"            # 站立
- "pose:sit"              # 坐下
- "pose:lie"              # 趴下
- "action:wave"           # 挥手
- "action:nod"            # 点头
- "action:dance"          # 跳舞
- "stop"                  # 停止
- "status"                # 查询状态
```

### 命令解析

```cpp
void handleCommand(String command) {
    int colonIndex = command.indexOf(':');
    String cmd = command.substring(0, colonIndex);
    String params = command.substring(colonIndex + 1);
    
    if (cmd == "walk") {
        handleWalk(params);
    } else if (cmd == "gait") {
        handleGait(params);
    } else if (cmd == "pose") {
        handlePose(params);
    } else if (cmd == "action") {
        handleAction(params);
    } else if (cmd == "stop") {
        stop();
    } else if (cmd == "status") {
        sendStatus();
    }
}

void handleWalk(String params) {
    int commaIndex = params.indexOf(',');
    String direction = params.substring(0, commaIndex);
    int steps = params.substring(commaIndex + 1).toInt();
    
    if (direction == "forward") {
        walkForward(steps);
    } else if (direction == "backward") {
        walkBackward(steps);
    } else if (direction == "left") {
        turnLeft(steps);
    } else if (direction == "right") {
        turnRight(steps);
    }
}
```

## 状态反馈

### 状态数据结构

```cpp
struct RobotStatus {
    float batteryVoltage;
    float roll, pitch, yaw;  // 姿态
    bool isMoving;
    String currentGait;
    int stepCount;
};

RobotStatus status;

void updateStatus() {
    status.batteryVoltage = readBatteryVoltage();
    readIMUAttitude(status.roll, status.pitch, status.yaw);
    status.isMoving = isMoving();
    status.currentGait = getCurrentGait();
    status.stepCount = getStepCount();
}

void sendStatus() {
    String statusStr = "status:";
    statusStr += "battery=" + String(status.batteryVoltage) + ",";
    statusStr += "roll=" + String(status.roll) + ",";
    statusStr += "pitch=" + String(status.pitch) + ",";
    statusStr += "moving=" + String(status.isMoving ? "true" : "false");
    
    pCharacteristic->setValue(statusStr.c_str());
    pCharacteristic->notify();
}
```

## 上位机开发（可选）

### 简单的手机APP

可以使用MIT App Inventor或React Native开发简单的控制APP。

**功能**：
- 连接蓝牙
- 发送控制命令
- 显示机器人状态
- 实时控制（摇杆）

### Python控制脚本

```python
import bluetooth
import time

def connect_robot():
    # 搜索设备
    devices = bluetooth.discover_devices()
    robot_addr = None
    for addr in devices:
        if "QuadrupedRobot" in bluetooth.lookup_name(addr):
            robot_addr = addr
            break
    
    if robot_addr:
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        sock.connect((robot_addr, 1))
        return sock
    return None

def send_command(sock, command):
    sock.send(command + "\n")
    time.sleep(0.1)

# 使用示例
sock = connect_robot()
if sock:
    send_command(sock, "walk:forward,5")
    send_command(sock, "action:wave")
    sock.close()
```

## 交互功能

### 触摸响应

```cpp
#define TOUCH_PIN 4

void setupTouch() {
    pinMode(TOUCH_PIN, INPUT);
}

void checkTouch() {
    if (digitalRead(TOUCH_PIN) == HIGH) {
        // 触摸响应
        performRandomAction();
    }
}

void performRandomAction() {
    int action = random(0, 3);
    switch(action) {
        case 0: wave(0); break;
        case 1: nod(); break;
        case 2: dance(); break;
    }
}
```

### LED状态指示

```cpp
#define LED_PIN 2

void setupLED() {
    pinMode(LED_PIN, OUTPUT);
}

void updateLED() {
    if (isMoving()) {
        // 运动时闪烁
        digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    } else {
        // 静止时常亮
        digitalWrite(LED_PIN, HIGH);
    }
}
```

## 安全机制

### 超时保护

```cpp
unsigned long lastCommandTime = 0;
#define COMMAND_TIMEOUT 5000  // 5秒

void checkTimeout() {
    if (millis() - lastCommandTime > COMMAND_TIMEOUT) {
        if (isMoving()) {
            stop();  // 超时自动停止
        }
    }
}

void handleCommand(String command) {
    lastCommandTime = millis();
    // ... 处理命令
}
```

### 边界检查

```cpp
bool isValidCommand(String command) {
    // 检查命令格式
    if (command.length() > 100) return false;
    
    // 检查命令类型
    String validCommands[] = {"walk", "gait", "pose", "action", "stop", "status"};
    bool valid = false;
    for (String cmd : validCommands) {
        if (command.startsWith(cmd)) {
            valid = true;
            break;
        }
    }
    
    return valid;
}
```

## 性能优化

1. **减少数据传输**：只传输必要信息
2. **批量命令**：支持命令队列
3. **压缩数据**：使用二进制协议（可选）
4. **异步处理**：命令处理不阻塞主循环

## 常见问题

### Q: 蓝牙连接不稳定？
A:
- 检查距离和障碍物
- 检查电源是否稳定
- 优化天线设计

### Q: 命令延迟大？
A:
- 减少数据传输量
- 优化命令解析
- 使用更高效的协议

### Q: 多设备连接？
A:
- BLE支持多连接（需要配置）
- 或使用WiFi（ESP32支持）
