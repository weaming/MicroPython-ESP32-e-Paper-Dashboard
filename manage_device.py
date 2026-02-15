# manage_device.py
# ESP32 MicroPython 设备管理工具：格式化、上传文件、验证、重启

import sys
import os
import time
import serial

BAUDRATE = 115200
TARGET_PORT = '/dev/tty.usbserial-10'
PROJECT_ROOT = os.path.expanduser('~/src/MicroPython-ESP32-e-Paper-Dashboard')

FILES_TO_UPLOAD = [
    'boot.py',
    'main.py',
    'config.py',
    'debug.py',
    'font5x8.bin',
]

DIRS_TO_UPLOAD = ['lib', 'system']


class DeviceManager:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self):
        print(f"Connecting to {self.port}...")
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            print("Connected.")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect: {e}")
            return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Disconnected.")

    def hard_reset(self):
        """通过 DTR/RTS 引脚复位 ESP32"""
        print("Hard reset via DTR/RTS...")
        self.ser.dtr = False
        self.ser.rts = False
        time.sleep(0.1)
        self.ser.rts = True
        self.ser.dtr = False
        time.sleep(0.1)
        self.ser.rts = False
        self.ser.dtr = False
        time.sleep(0.5)

    def drain(self):
        """清空串口接收缓冲区，丢弃所有未读数据"""
        while self.ser.in_waiting:
            self.ser.read(self.ser.in_waiting)
            time.sleep(0.01)

    def read_until(self, marker, timeout=5):
        """读取串口直到遇到 marker 或超时"""
        start = time.time()
        buf = b''
        while time.time() - start < timeout:
            if self.ser.in_waiting:
                buf += self.ser.read(self.ser.in_waiting)
                if marker in buf:
                    return buf
            time.sleep(0.01)
        return buf

    def interrupt_and_enter_raw_repl(self):
        """中断当前执行并进入 Raw REPL 模式"""
        print("Interrupting device and entering Raw REPL...")

        for attempt in range(10):
            self.ser.write(b'\x03')
            time.sleep(0.1)

        self.drain()

        for attempt in range(5):
            self.ser.write(b'\x03\x03')
            time.sleep(0.1)
            self.ser.write(b'\r\x01')
            time.sleep(0.3)

            buf = b''
            while self.ser.in_waiting:
                buf += self.ser.read(self.ser.in_waiting)
                time.sleep(0.01)

            if b'raw REPL; CTRL-B' in buf:
                print("Entered Raw REPL.")
                return True

        print("Failed to enter Raw REPL.")
        return False

    def exec_raw(self, cmd, timeout=10):
        """在 Raw REPL 中执行命令并返回 stdout 输出。

        Raw REPL 协议：
        发送: <code bytes> + \\x04
        接收: OK<stdout>\\x04<stderr>\\x04>
        """
        # 关键：先清空缓冲区，避免上一条命令的残留数据干扰
        self.drain()

        self.ser.write(cmd.encode('utf-8'))
        self.ser.write(b'\x04')

        # 读取完整响应，等待 \x04> 结束标记
        start = time.time()
        resp = b''
        while time.time() - start < timeout:
            if self.ser.in_waiting:
                resp += self.ser.read(self.ser.in_waiting)
                if b'\x04>' in resp:
                    break
            time.sleep(0.01)

        # 协议解析: OK<stdout>\x04<stderr>\x04>
        parts = resp.split(b'\x04')
        stdout_part = b''
        stderr_part = b''

        if len(parts) >= 1 and parts[0].startswith(b'OK'):
            stdout_part = parts[0][2:]
        if len(parts) >= 2:
            stderr_part = parts[1]

        stdout_str = stdout_part.decode('utf-8', errors='replace').strip()
        stderr_str = stderr_part.decode('utf-8', errors='replace').strip()

        if stderr_str:
            print(f"[STDERR] {stderr_str}")

        return stdout_str

    def write_file(self, local_path, remote_path):
        """通过 Raw REPL 将本地文件写入设备"""
        print(f"  Uploading {os.path.basename(local_path)} -> {remote_path} ... ", end='', flush=True)
        try:
            with open(local_path, 'rb') as f:
                content = f.read()

            resp = self.exec_raw(f"f = open('{remote_path}', 'wb')")
            if 'Traceback' in resp or 'Error' in resp:
                print(f"FAILED (open: {resp})")
                return False

            chunk_size = 256
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                self.exec_raw(f"f.write({repr(chunk)})")

            self.exec_raw("f.close()")
            print(f"OK ({len(content)} bytes)")
            return True

        except Exception as e:
            print(f"ERROR: {e}")
            return False

    def format_filesystem(self):
        """格式化设备文件系统并重新挂载"""
        print("\n--- Formatting Filesystem ---")
        resp = self.exec_raw("""
import os, flashbdev
try:
    os.VfsFat.mkfs(flashbdev.bdev)
    vfs = os.VfsFat(flashbdev.bdev)
    os.mount(vfs, '/')
    print('OK')
except Exception as e:
    print('FAIL:', e)
""", timeout=15)
        print(f"  Format result: {resp}")

        if 'OK' not in resp:
            print("  WARNING: Format may have failed. Trying LFS2...")
            resp = self.exec_raw("""
import os, flashbdev
try:
    os.VfsLfs2.mkfs(flashbdev.bdev)
    vfs = os.VfsLfs2(flashbdev.bdev)
    os.mount(vfs, '/')
    print('OK')
except Exception as e:
    print('FAIL:', e)
""", timeout=15)
            print(f"  LFS2 result: {resp}")

        listing = self.exec_raw("import os; print(os.listdir('/'))")
        print(f"  Root listing after format: {listing}")

    def create_dir(self, dirname):
        """在设备上创建目录"""
        resp = self.exec_raw(f"import os\ntry:\n os.mkdir('{dirname}')\n print('OK')\nexcept Exception as e:\n print(e)")
        if 'OK' in resp:
            print(f"  Directory '{dirname}': OK")
            return True
        elif 'EEXIST' in resp:
            print(f"  Directory '{dirname}': already exists")
            return True
        else:
            print(f"  Directory '{dirname}': FAILED ({resp})")
            return False

    def verify(self):
        """验证设备上的文件结构"""
        print("\n--- Verification ---")

        root = self.exec_raw("import os; print(os.listdir('/'))")
        print(f"  Root: {root}")

        for d in DIRS_TO_UPLOAD:
            listing = self.exec_raw(f"import os\ntry:\n print(os.listdir('{d}'))\nexcept:\n print('MISSING')")
            print(f"  {d}/: {listing}")

        print("\n  Import test:")
        for mod in ['system.power', 'system.network', 'system.hardware', 'lib.epaper7in5b']:
            result = self.exec_raw(f"try:\n import {mod}\n print('OK')\nexcept Exception as e:\n print(e)")
            status = "✓" if 'OK' in result else f"✗ ({result})"
            print(f"    {mod}: {status}")

    def monitor(self, duration=15):
        """监控设备串口输出"""
        print(f"\n--- Monitoring ({duration}s) ---")
        start = time.time()
        while time.time() - start < duration:
            if self.ser.in_waiting:
                data = self.ser.read(self.ser.in_waiting)
                sys.stdout.write(data.decode('utf-8', errors='replace'))
                sys.stdout.flush()
            time.sleep(0.01)
        print()

    def run(self):
        if not self.connect():
            return

        # 1. 复位设备
        self.hard_reset()

        # 2. 中断启动脚本，进入 Raw REPL
        if not self.interrupt_and_enter_raw_repl():
            print("Could not enter REPL. Please replug device and retry.")
            self.disconnect()
            return

        # 3. 连接测试
        test = self.exec_raw("print('hello')")
        print(f"Connection test: {'OK' if 'hello' in test else 'FAILED (' + test + ')'}")

        # 4. 格式化文件系统
        self.format_filesystem()

        # 5. 创建目录（不重新进入 Raw REPL，保持当前 session）
        print("\n--- Creating Directories ---")
        for d in DIRS_TO_UPLOAD:
            self.create_dir(d)

        # 6. 上传文件
        print("\n--- Uploading Files ---")
        for f in FILES_TO_UPLOAD:
            local = os.path.join(PROJECT_ROOT, f)
            if os.path.exists(local):
                self.write_file(local, f)

        for d in DIRS_TO_UPLOAD:
            local_dir = os.path.join(PROJECT_ROOT, d)
            if not os.path.exists(local_dir):
                continue
            for f in sorted(os.listdir(local_dir)):
                local_f = os.path.join(local_dir, f)
                if os.path.isfile(local_f) and (f.endswith('.py') or f.endswith('.bin')):
                    self.write_file(local_f, f"{d}/{f}")

        # 7. 验证
        self.verify()

        # 8. 重启设备并监控输出
        print("\nResetting device...")
        self.exec_raw("import machine; machine.reset()")
        self.monitor()

        self.disconnect()
        print("Done.")


if __name__ == '__main__':
    dm = DeviceManager(TARGET_PORT, BAUDRATE)
    dm.run()
