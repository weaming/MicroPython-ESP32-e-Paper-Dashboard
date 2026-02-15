# 开发指导文档

## 项目现状 (2026-02-15)

### ✅ 已完成功能

- **部署工具**: `manage_device.py` 可靠部署代码到设备
- **墨水屏驱动**: 三色显示正常工作 (黑/白/黄)
- **传感器支持**: SHT30 温湿度传感器 (I2C)
- **电源管理**: 深度睡眠调度和电池监测
- **网络功能**: WiFi 连接和 NTP 时间同步
- **内存优化**: 提前分配缓冲区，避免碎片化

### 📊 实测数据

- **传感器**: 29-31°C, 42-44%RH
- **电池**: 7.2V (约 50% 电量, 2S 锂电池)
- **内存**: 启动 85KB → 分配后 36KB 可用
- **显示**: 刷新时间约 15 秒

## 核心技术要点

### 1. 内存管理（关键）

ESP32 可用 RAM 约 111KB，帧缓冲区需要 48KB。

**重要原则**：
- ✅ 启动时立即分配缓冲区（避免碎片化）
- ✅ 复用单个缓冲区（先黑色层，清空，再黄色层）
- ✅ 传感器读取后立即释放 I2C 资源
- ✅ 关键操作前调用 `gc.collect()`
- ❌ 不要双缓冲（会 OOM）

**代码示例**：
```python
# main.py
buf = hw.get_buffer()  # 立即分配
sensor.init_sensor()
temp, humi = sensor.read_sensor()
sensor.cleanup()  # 释放 I2C
gc.collect()  # 强制回收
```

### 2. 传感器驱动（简化版）

只支持 SHT30，移除了自动探测和其他传感器类型。

**配置**：
- I2C: SCL=GPIO22, SDA=GPIO21
- 地址: 0x44
- 频率: 100kHz

**使用**：
```python
import system.sensor as sensor

sensor.init_sensor()  # 初始化
temp, humi = sensor.read_sensor()  # 读取
sensor.cleanup()  # 释放资源
```

### 3. 电池监测（2S 配置）

10000mAh 电池为两节锂电池串联（2S）。

**电压范围**：
- 充满: 8.4V (4.2V × 2)
- 标称: 7.4V (3.7V × 2)
- 放空: 6.0V (3.0V × 2)

**校准方法**：
如果电压读数不准，修改 `system/power.py` 中的 `VOLTAGE_DIVIDER` 常数。

### 4. 墨水屏驱动

**引脚配置**：
- CS=5, DC=19, RST=16, BUSY=17
- SCK=18, MOSI=23, MISO=12(占位)

**注意事项**：
- 刷新需要 15 秒，不要频繁刷新
- BUSY 引脚 LOW=忙碌，程序会等待
- 调试输出已移除，提升性能

### 5. 深度睡眠

**配置**：
- 默认 5 分钟刷新一次
- 睡眠功耗 < 0.05mA
- RTC 内存保存唤醒计数

**修改刷新间隔**：
编辑 `main.py` 中的 `REFRESH_INTERVAL` 常量（单位：秒）。

**当前状态**：测试模式，深度睡眠已禁用。

**恢复方法**：
取消注释 `main.py` 中的：
```python
epd.sleep()
gc.collect()
scheduler.schedule_next_wake(REFRESH_INTERVAL)
```

## 部署和调试

### 完整部署

```bash
python3 manage_device.py
```

自动执行：格式化 → 上传 → 验证 → 重启

### 快速测试

```bash
# 上传单个文件
mpremote connect /dev/tty.usbserial-10 cp main.py :main.py

# 运行调试脚本
mpremote connect /dev/tty.usbserial-10 run debug.py

# 进入 REPL
mpremote connect /dev/tty.usbserial-10 repl
```

### 常见问题

**端口占用**：
```bash
pkill -f mpremote
```

**查看文件**：
```bash
mpremote connect /dev/tty.usbserial-10 ls
mpremote connect /dev/tty.usbserial-10 ls :system/
```

**内存监控**：
```python
import gc
gc.collect()
print(gc.mem_free())
```

## 后续开发建议

### 1. 显示内容扩展

当前只显示基础信息，可以添加：
- 天气预报（HTTP API）
- 日历事件
- 加密货币价格
- 自定义图标和图片

### 2. 网络功能

- HTTP 请求获取数据
- MQTT 订阅消息
- OTA 固件更新

### 3. 电源优化

- 根据电量调整刷新频率
- 低电量警告
- 充电状态检测

### 4. 用户界面

- 多页面切换
- 按钮交互（如果有硬件按钮）
- 配置界面

## 代码结构

```
├── boot.py              # 启动引导
├── main.py              # 主程序
├── config.py            # WiFi 配置
├── debug.py             # 硬件调试
├── manage_device.py     # 部署工具
├── lib/                 # 驱动库
│   ├── epaper7in5b.py   # 墨水屏驱动
│   └── framebuf2.py     # 帧缓冲
└── system/              # 系统模块
    ├── hardware.py      # 硬件抽象
    ├── network.py       # 网络功能
    ├── power.py         # 电源管理
    └── sensor.py        # 传感器驱动
```

## 重要提醒

1. **内存限制**: 总是提前分配大缓冲区
2. **资源释放**: I2C/SPI 使用后立即释放
3. **垃圾回收**: 关键操作前调用 `gc.collect()`
4. **墨水屏寿命**: 避免频繁刷新
5. **深度睡眠**: 唤醒后需要重新初始化

## 参考资料

- [硬件配置](device.md) - 引脚定义和实测数据
- [MicroPython 文档](https://docs.micropython.org/)
- [ESP32 数据手册](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_cn.pdf)
