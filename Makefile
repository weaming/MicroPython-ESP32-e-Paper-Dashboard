deploy: build
	python3 deploy.py

# 编译：将 Python 文件转换为字节码以节省内存
# 排除 main.py, boot.py, config.py 以便灵活修改
build:
	@echo "Compiling library and system files..."
	@find lib system -name "*.py" | while read -r file; do \
		mpy-cross "$$file"; \
	done

gen-font-file:
	python3 tools/generate_unified_font.py

debug:
	mpremote connect /dev/tty.usbserial-10 run debug.py

clean:
	rm -f lib/*.mpy system/*.mpy

deploy-font:
	mpremote connect /dev/tty.usbserial-10 cp unified_font.bin :unified_font.bin

build-mem-kv-http:
	cd mem-kv; GOOS=linux GOARCH=amd64 go build -ldflags "-s -w" -o ~/bin-weaming/mem-kv-linux .
