import random
import string
import subprocess
from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange, IPVersion

def get_code(n):
	return ''.join(random.choices(string.ascii_letters, k=n))

def pair_device(address, pair_port, connect_port, password, status_cb=None):
	"""
	Pair using pair_port, then connect using connect_port (may be different!), then fetch details.
	"""
	import time
	print(f"[DEBUG] Pairing device on {address}:{pair_port}...")
	if status_cb:
		status_cb(f"Pairing device on {address}:{pair_port}...")
	args = ["adb", "pair", f"{address}:{pair_port}", password]
	print(f"[DEBUG] Running: {' '.join(args)}")
	proc = subprocess.run(args, capture_output=True, text=True)
	print(f"[DEBUG] Pairing returncode: {proc.returncode}")
	print(f"[DEBUG] Pairing stdout: {proc.stdout.strip()}")
	print(f"[DEBUG] Pairing stderr: {proc.stderr.strip()}")
	paired = proc.returncode == 0
	if paired:
		if status_cb:
			status_cb(f"Paired with {address}:{pair_port}")
	else:
		if status_cb:
			status_cb(f"[Warning] Pairing failed: {proc.stderr.strip() or proc.stdout.strip()}")
	# Always attempt to connect, even if pairing failed (as in cli.py)
	print(f"[DEBUG] Connecting to device on {address}:{connect_port}...")
	if status_cb:
		status_cb(f"Connecting to device on {address}:{connect_port}...")
	connected = False
	connect_out = ""
	for attempt in range(5):
		connect_args = ["adb", "connect", f"{address}:{connect_port}"]
		print(f"[DEBUG] Attempt {attempt+1}: Running: {' '.join(connect_args)}")
		connect_proc = subprocess.run(connect_args, capture_output=True, text=True)
		print(f"[DEBUG] Connect stdout: {connect_proc.stdout.strip()}")
		print(f"[DEBUG] Connect stderr: {connect_proc.stderr.strip()}")
		connect_out = connect_proc.stdout.lower() + connect_proc.stderr.lower()
		if ("connected" in connect_out or "already connected" in connect_out) and "unable" not in connect_out:
			connected = True
			print(f"[DEBUG] Connected on attempt {attempt+1}")
			break
		time.sleep(1)
	if not connected:
		print(f"[DEBUG] Could not connect to {address}:{connect_port}. Output: {connect_out.strip()}")
		if status_cb:
			status_cb(f"[Error] Could not connect to {address}:{connect_port}. Output: {connect_out.strip()}")
		return False
	print(f"[DEBUG] Connected to {address}:{connect_port}. Fetching device details...")
	if status_cb:
		status_cb(f"Connected to {address}:{connect_port}. Fetching device details...")
	# Only fetch details if connected
	device_info = {
		"address": address,
		"pair_port": pair_port,
		"connect_port": connect_port,
		"password": password
	}
	serial = f"{address}:{connect_port}"
	try:
		# Get market name (friendly name) and device code
		print("[DEBUG] Fetching ro.product.marketname...")
		marketname_proc = subprocess.run(["adb","-s", serial, "shell", "getprop", "ro.product.marketname"], capture_output=True, text=True)
		marketname = marketname_proc.stdout.strip()
		print(f"[DEBUG] marketname: {marketname}")
		print("[DEBUG] Fetching ro.product.device...")
		model_proc = subprocess.run(["adb","-s", serial, "shell", "getprop", "ro.product.device"], capture_output=True, text=True)
		model = model_proc.stdout.strip()
		print(f"[DEBUG] model: {model}")
		# Compose device name as 'marketname (model)' if marketname exists, else fallback to model
		if marketname:
			device_info["name"] = f"{marketname} ({model})"
		else:
			device_info["name"] = model or address
		print("[DEBUG] Fetching ro.build.version.release...")
		android_version = subprocess.run(["adb","-s", serial, "shell", "getprop", "ro.build.version.release"], capture_output=True, text=True)
		device_info["android_version"] = android_version.stdout.strip()
		print(f"[DEBUG] android_version: {device_info['android_version']}")
		print("[DEBUG] Fetching ro.product.manufacturer...")
		manufacturer = subprocess.run(["adb","-s", serial, "shell", "getprop", "ro.product.manufacturer"], capture_output=True, text=True)
		device_info["manufacturer"] = manufacturer.stdout.strip()
		print(f"[DEBUG] manufacturer: {device_info['manufacturer']}")
		# Store device model as well
		device_info["model"] = model
		print(f"[DEBUG] device_info: {device_info}")
		if status_cb:
			status_cb(f"Device details: {device_info['name']}, Android {device_info['android_version']}, {device_info['manufacturer']}")
	except Exception as e:
		print(f"[DEBUG] Exception while fetching device details: {e}")
		if status_cb:
			status_cb(f"[Warning] Could not fetch device details: {e}")
	try:
		from .device_store import save_paired_device
		print(f"[DEBUG] Saving device info: {device_info}")
		save_paired_device(device_info)
	except Exception as e:
		print(f"[DEBUG] Exception while saving device: {e}")
		if status_cb:
			status_cb(f"[Warning] Could not save device: {e}")
	return True

def connect_device(address, port, status_cb=None):
	if status_cb:
		status_cb("Connecting device...")
	args = ["adb", "connect", f"{address}:{port}"]
	proc = subprocess.run(args, capture_output=True)
	if proc.returncode == 0:
		if status_cb:
			status_cb("Connected successfully!")
		return True
	else:
		if status_cb:
			status_cb(f"Connect failed: {proc.stderr.decode()}")
		return False

def auto_connect_recent_device(status_cb=None):
	try:
		from .device_store import get_most_recent_device
		device = get_most_recent_device()
		if device:
			return connect_device(device["address"], device.get("pair_port", 5555), status_cb)
	except Exception as e:
		if status_cb:
			status_cb(f"[Warning] Auto-connect failed: {e}")
	return False

def start_mdns_pairing(password, on_pair_and_connect, device_ports=None):
	"""
	Starts mDNS ServiceBrowser for ADB pairing. Calls on_pair_and_connect(addr, pair_port, connect_port) when ready.
	Returns Zeroconf instance and device_ports list.
	"""
	if device_ports is None:
		device_ports = []
	zc = Zeroconf(ip_version=IPVersion.V4Only)

	last_pair = {"addr": None, "pair_port": None}
	def on_service_state_change(zeroconf, service_type, name, state_change):
		if state_change is ServiceStateChange.Added:
			info = zeroconf.get_service_info(service_type, name)
			if not info:
				return
			addr = info.parsed_addresses()[0]
			if service_type == "_adb-tls-pairing._tcp.local.":
				last_pair["addr"] = addr
				last_pair["pair_port"] = info.port or 5555
			elif service_type == "_adb-tls-connect._tcp.local.":
				device_ports.append(info.port)
			# Only call on_pair_and_connect if both are available
			if last_pair["addr"] is not None and device_ports:
				# Use the latest connect port
				on_pair_and_connect(last_pair["addr"], last_pair["pair_port"], device_ports[-1], password)
				# Reset so we don't call it multiple times
				last_pair["addr"] = None
				last_pair["pair_port"] = None

	ServiceBrowser(zc, "_adb-tls-pairing._tcp.local.", handlers=[on_service_state_change])
	ServiceBrowser(zc, "_adb-tls-connect._tcp.local.", handlers=[on_service_state_change])
	return zc, device_ports


