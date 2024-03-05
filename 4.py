from flask import Flask, render_template, jsonify
import subprocess
import re
import threading
import time

app = Flask(__name__)

def get_network_info():
    result = subprocess.run(["ifconfig"], capture_output=True, text=True)
    lines = result.stdout.split("\n")
    network_info = {}
    for line in lines:
        if "gateway" in line:
            network_info["gateway"] = re.search(r"gateway (\S+)", line).group(1)
        elif "inet " in line and "netmask" in line:
            parts = line.split()
            network_info["ip"] = parts[1]
            network_info["mask"] = parts[3]
    return network_info

def scan_devices(ip, mask):
    devices = set()  # Use a set to store unique devices

    subnet = ".".join(ip.split(".")[:-1]) + "." + mask.split(".")[-1]
    arp_command = ["arp", "-an"]
    arp_result = subprocess.run(arp_command, capture_output=True, text=True).stdout
    arp_lines = arp_result.split("\n")
    for line in arp_lines:
        match = re.search(r"\((.*?)\) at (.*?) on", line)
        if match:
            ip = match.group(1)
            mac = match.group(2)
            if mac != "00:00:00:00:00:00" and "incomplete" not in mac and mac != "ff:ff:ff:ff:ff:ff":  
                ip_parts = ip.split(".")
                if ip_parts[2] == subnet.split(".")[2]:
                    devices.add((ip, mac))  # Store device as a tuple (ip, mac)

    return [{"ip": ip, "mac": mac} for ip, mac in devices]

def clear_arp_cache():
    subprocess.run(["arp", "-d"], capture_output=True, text=True)

def manual_clear():
    clear_arp_cache()
    time.sleep(5) # Wait for ARP cache to clear
    scan_devices_thread = threading.Timer(1, scan_devices, args=(network_info["ip"], network_info["mask"]))
    scan_devices_thread.start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/devices", methods=["GET"])
def get_devices():
    network_info = get_network_info()
    ip = network_info["ip"]
    mask = network_info["mask"]
    devices = scan_devices(ip, mask)
    return jsonify(devices)

if __name__ == "__main__":
    network_info = get_network_info()
    scan_devices_thread = threading.Timer(1, scan_devices, args=(network_info["ip"], network_info["mask"]))
    scan_devices_thread.start()

    manual_clear_thread = threading.Thread(target=manual_clear)
    manual_clear_thread.daemon = True
    manual_clear_thread.start()

    app.run(debug=True)
