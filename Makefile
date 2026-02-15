deploy: build
	python3 deploy.py

# 编译：将 Python 文件转换为字节码以节省内存
# 排除 main.py, boot.py, config.py 以便灵活修改
build:
	@echo "Compiling library and system files..."
	@find lib system -name "*.py" | while read -r file; do \
		mpy-cross "$$file"; \
	done

gen-font:
	python3 tools/generate_unified_font.py

debug:
	mpremote connect /dev/tty.usbserial-10:115200 run debug.py

clean:
	rm -f lib/*.mpy system/*.mpy

build-mem-kv-http:
	cd mem-kv; GOOS=linux GOARCH=amd64 go build -ldflags "-s -w" -o ~/bin-weaming/mem-kv-linux .

logs:
	mpremote connect /dev/tty.usbserial-10:115200 repl

tail:
	python3 -c "import serial, sys, time; s=serial.Serial('/dev/tty.usbserial-10', 115200, timeout=0); print('--- Tailing logs (Ctrl+C to stop) ---'); exec('while True:\n try:\n  data=s.read(s.in_waiting or 1)\n  if data: sys.stdout.write(data.decode(\'utf-8\', \'replace\')); sys.stdout.flush()\n  else: time.sleep(0.01)\n except KeyboardInterrupt: break')"
