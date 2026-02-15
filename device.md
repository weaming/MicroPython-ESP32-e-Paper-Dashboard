# 设备硬件说明 (Device Specification)

## 1. 核心硬件 (Core Hardware)
- **主控模组**: ESP32 (乐鑫官方订货)
- **显示屏幕**: 7.5英寸 电子墨水屏 (E-Paper Display)
  - 分辨率: 800 x 480
  - 颜色支持: 黑、白、黄 (或红) 三色显示
  - 驱动 IC: GDEY075Z08 / GDEW075C64
- **接口**: Type-C (充电与固件升级)
- **电池**: 10000mAh (续航约1年，配合超低功耗休眠)
- **外壳**: 高精度 3D 打印外壳

## 2. 硬件连接 (Pinout)
基于 `device.py` 的定义，ESP32 与墨水屏的连接如下：

| 功能 (Function) | 引脚 (Pin) | 备注 (Note) |
| :--- | :--- | :--- |
| **CS** (Chip Select) | GPIO 5 | 片选信号 |
| **DC** (Data/Command) | GPIO 19 | 数据/命令控制 |
| **RST** (Reset) | GPIO 16 | 复位信号 |
| **BUSY** | GPIO 17 | 忙碌状态检测 |
| **SCK** (Serial Clock) | GPIO 18 | SPI 时钟 |
| **MOSI** (SDA) | GPIO 23 | SPI 主出从入 |
| **MISO** | GPIO 19 | (与 DC 复用或未使用) |
| **SPI Bus** | SPI 2 | 波特率 20MHz |

## 3. 功能特性 (Features)
- **联网能力**: 
  - 2.4G Wi-Fi 支持
  - 自动 NTP 时间同步 (阿里云 NTP, UTC+8)
  - 手机端配网
- **功耗管理**: 
  - 支持 Deep Sleep (深度休眠) 模式
  - 休眠功耗 < 0.05mA
  - 采用 RTC Memory 保存任务队列，支持休眠唤醒后的任务调度
- **传感器**: 
  - 内置室内温湿度传感器 (硬件具备，软件驱动需确认)

## 4. 软件架构 (Software Architecture)
- **开发语言**: MicroPython
- **核心模块**:
  - `boot.py`: 启动引导，负责冷启动调度
  - `device.py`: 硬件抽象层，定义引脚和初始化逻辑
  - `epaper7in5b.py`: 墨水屏驱动程序
  - `sleepscheduler.py`: 休眠调度器，管理任务队列和低功耗模式
