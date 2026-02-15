deploy:
	python3 manage_device.py

debug:
	mpremote connect /dev/tty.usbserial-10 run debug.py