# ESP32 E-Paper Dashboard

基于 MicroPython + ESP32 的 7.5 英寸三色墨水屏仪表盘。

## 硬件配置

- **主控**: ESP32-D0WD-V3
- **显示**: 7.5 英寸三色墨水屏 (800×480, 黑/白/黄)
- **传感器**: SHT30 温湿度传感器 (I2C)
- **电池**: 10000mAh (2S 锂电池, 续航约1年)
- **接口**: Type-C (充电与固件升级)

## 功能特性

- ✅ 温湿度显示 (SHT30 传感器)
- ✅ 电池电量监测 (2S 锂电池)
- ✅ WiFi 连接和 NTP 时间同步
- ✅ 深度睡眠调度 (超低功耗)
- ✅ 三色墨水屏显示

## 项目结构

```
├── boot.py              # 启动引导
├── main.py              # 主程序
├── config.py            # WiFi 配置
├── debug.py             # 硬件调试脚本
├── manage_device.py     # 部署工具
├── font5x8.bin          # 位图字体
├── lib/                 # 驱动库
│   ├── epaper7in5b.py   # 墨水屏驱动
│   └── framebuf2.py     # 帧缓冲库
├── system/              # 系统模块
│   ├── hardware.py      # 硬件抽象
│   ├── network.py       # 网络功能
│   ├── power.py         # 电源管理
│   └── sensor.py        # 传感器驱动
└── docs/                # 项目文档
    ├── device.md        # 硬件说明
    └── gemini-handoff.md # 开发指导
```

## 快速开始

### 1. 配置 WiFi

编辑 `config.py`：

```python
WIFI_SSID = '你的WiFi名称'
WIFI_PASSWORD = '你的WiFi密码'
```

### 2. 部署到设备

```bash
python3 manage_device.py
```

部署工具会自动：
- 格式化设备文件系统
- 上传所有代码文件
- 验证文件完整性
- 重启设备

### 3. 硬件调试

```bash
mpremote connect /dev/tty.usbserial-10 run debug.py
```

调试脚本会测试：
- 内存状态
- 电池电压
- 传感器读数
- 网络连接
- 墨水屏显示

## 传感器读数

- **温度**: 约 30°C (室温)
- **湿度**: 约 43%
- **电池**: 7.2V (约 50% 电量)

## 深度睡眠

默认每 5 分钟刷新一次显示，其余时间进入深度睡眠以节省电量。

修改刷新间隔：编辑 `main.py` 中的 `REFRESH_INTERVAL` 常量。

## 文档

- [硬件说明](docs/device.md) - 引脚定义和硬件配置
- [开发指导](docs/gemini-handoff.md) - 后续开发建议

## 技术栈

- **语言**: MicroPython 1.20.0
- **硬件**: ESP32, SHT30, 7.5" E-Paper
- **协议**: SPI (墨水屏), I2C (传感器)

## 许可

MIT License
