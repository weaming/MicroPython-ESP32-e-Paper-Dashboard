deploy: build
	python3 deploy.py

# 编译：将 Python 文件转换为字节码以节省内存
build:
	mpy-cross -o lib/framebuf2.mpy lib/framebuf2.py

gen-font-file:
	python3 tools/generate_unified_font.py

debug:
	mpremote connect /dev/tty.usbserial-10 run debug.py

clean:
	rm -f lib/*.mpy

build-mem-kv-http:
	cd mem-kv; GOOS=linux GOARCH=amd64 go build -ldflags "-s -w" -o ~/bin-weaming/mem-kv-linux .