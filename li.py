#!/usr/bin/env python3
"""
NXTools License System - Self-Hosted Version
ALWAYS checks your POWER server. No Pastebin. No caching.
"""

import hashlib
import os
import subprocess
import platform
import requests
from datetime import datetime
import sys
import json
import re

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

class NXLicense:
    def __init__(self, tool_name="nxtools", secret_word="naha",
                 server_url="http://153.75.248.106:8000"):
        """
        server_url: your POWER server's base URL.
        """
        self.tool_name = tool_name
        self.secret_word = secret_word
        self.server_url = server_url.rstrip('/')
        # No caching - we always check the server

    def get_device_id(self):
        """Get unique device ID - PERMANENT for this device"""
        # Method 1: Android ID (Termux/Android)
        try:
            result = subprocess.run(
                ['content', 'query', '--uri', 'content://settings/secure',
                 '--where', "name='android_id'"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                match = re.search(r'value=([a-f0-9]+)', result.stdout)
                if match:
                    android_id = match.group(1)
                    if android_id and len(android_id) > 5:
                        return f"ANDROID:{android_id}"
        except:
            pass

        # Method 2: Windows Machine GUID
        try:
            result = subprocess.run(
                ['wmic', 'csproduct', 'get', 'uuid'],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                uuid = lines[1].strip()
                if uuid and len(uuid) > 5:
                    return f"WINDOWS:{uuid}"
        except:
            pass

        # Method 3: Linux machine-id
        try:
            with open('/etc/machine-id', 'r') as f:
                machine_id = f.read().strip()
                if machine_id and len(machine_id) > 5:
                    return f"LINUX:{machine_id}"
        except:
            pass

        # Method 4: Build fingerprint (Android)
        try:
            result = subprocess.run(
                ['getprop', 'ro.build.fingerprint'],
                capture_output=True, text=True, timeout=5
            )
            fingerprint = result.stdout.strip()
            if fingerprint and len(fingerprint) > 10:
                return f"FINGERPRINT:{hashlib.md5(fingerprint.encode()).hexdigest()[:16]}"
        except:
            pass

        # Method 5: Permanent fallback
        try:
            username = os.getenv('USER', os.getenv('USERNAME', 'user'))
            hostname = platform.node()
            home = os.path.expanduser("~")
            unique = f"{username}|{home}|{hostname}"
            return f"DEVICE:{hashlib.md5(unique.encode()).hexdigest()[:16]}"
        except:
            return f"DEVICE:{hashlib.md5(str(os.getpid()).encode()).hexdigest()[:16]}"

    def get_device_model(self):
        """Get device model"""
        # Try Android model
        try:
            result = subprocess.run(
                ['getprop', 'ro.product.model'],
                capture_output=True, text=True, timeout=5
            )
            model = result.stdout.strip()
            if model:
                return model
        except:
            pass

        # Try Windows model
        try:
            result = subprocess.run(
                ['wmic', 'csproduct', 'get', 'name'],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                model = lines[1].strip()
                if model:
                    return model
        except:
            pass

        # Try manufacturer + model (Android)
        try:
            result = subprocess.run(
                ['getprop', 'ro.product.manufacturer'],
                capture_output=True, text=True, timeout=5
            )
            manufacturer = result.stdout.strip()
            result = subprocess.run(
                ['getprop', 'ro.product.model'],
                capture_output=True, text=True, timeout=5
            )
            model = result.stdout.strip()
            if manufacturer and model:
                return f"{manufacturer} {model}"
        except:
            pass

        return platform.node() or "Unknown_Device"

    def generate_key(self):
        """
        Generate PERMANENT license key from device info.
        This is the code the user sends YOU (the admin) so you can
        paste it into the "Issue license" form on your dashboard.

        FORMULA: request_code = SHA256(Device_ID + Device_Model + Secret_Word + Tool_Name)
        """
        device_id = self.get_device_id()
        device_model = self.get_device_model()

        raw_data = f"{device_id}|{device_model}|{self.secret_word}|{self.tool_name}"
        hash_obj = hashlib.sha256(raw_data.encode())
        hash_hex = hash_obj.hexdigest()

        request_code = f"REQ-{hash_hex[:12].upper()}"

        return {
            "request_code": request_code,
            "device_id": device_id,
            "device_model": device_model
        }

    def check_server(self, request_code):
        """Check license status against your POWER server's /api/check endpoint"""
        try:
            response = requests.post(
                f"{self.server_url}/api/check",
                data={  # Use form data (FastAPI expects this)
                    "tool_name": self.tool_name,
                    "request_code": request_code
                },
                timeout=10
            )
            
            if response.status_code != 200:
                return {
                    "status": "error",
                    "message": f"Server error: {response.status_code}"
                }
            
            return response.json()
            
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "message": f"Cannot connect to server: {self.server_url}"
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "message": "Connection timeout"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error: {str(e)}"
            }

    def check(self):
        """
        Check license status - generates key and checks your server.
        ALWAYS checks the server - NO CACHING.
        """
        key_info = self.generate_key()
        request_code = key_info["request_code"]

        # ALWAYS check the server (no caching)
        server_data = self.check_server(request_code)

        if server_data is None:
            return {
                "status": "error",
                "message": "Could not reach the license server.",
                "request_code": request_code
            }

        if server_data.get("status") == "error":
            return {
                "status": "error",
                "message": server_data.get("message", "Unknown error"),
                "request_code": request_code
            }

        status = server_data.get("status")

        if status == "not_found":
            return {
                "status": "denied",
                "message": "Not approved yet",
                "request_code": request_code,
                "device_id": key_info["device_id"],
                "device_model": key_info["device_model"]
            }

        if status == "expired":
            return {
                "status": "expired",
                "message": "License has expired",
                "request_code": request_code,
                "expiry_date": server_data.get("expiry")
            }

        if status in ("revoked", "banned"):
            return {
                "status": "denied",
                "message": f"License {status}",
                "request_code": request_code
            }

        if status == "active":
            expiry_date = server_data.get("expiry")
            remaining = None
            if expiry_date:
                try:
                    expiry = datetime.fromisoformat(expiry_date)
                    remaining = (expiry - datetime.now()).days
                except:
                    remaining = None

            return {
                "status": "active",
                "message": "✅ License approved!",
                "request_code": request_code,
                "user_info": server_data.get("owner"),
                "expiry_date": expiry_date,
                "remaining_days": remaining
            }

        return {
            "status": "denied",
            "message": "Unknown status from server",
            "request_code": request_code
        }

    def require(self):
        """Main function - check license and show status"""
        result = self.check()

        print("\n" + "="*60)
        print(f"{Colors.CYAN}{Colors.BOLD}  🔐 {self.tool_name.upper()} License{Colors.RESET}")
        print("="*60)

        if result["status"] == "active":
            print(f"{Colors.GREEN}✅ {result['message']}{Colors.RESET}")
            if result.get("user_info"):
                print(f"  {Colors.DIM}User:{Colors.RESET}     {result['user_info']}")
            if result.get("remaining_days") is not None:
                print(f"  {Colors.DIM}Remaining:{Colors.RESET} {result['remaining_days']} days")
            if result.get("expiry_date"):
                print(f"  {Colors.DIM}Expires:{Colors.RESET}  {result['expiry_date']}")
            print("="*60)
            print(f"{Colors.GREEN}🎉 Access Granted!{Colors.RESET}")
            return True

        elif result["status"] == "expired":
            print(f"{Colors.RED}❌ {result['message']}{Colors.RESET}")
            if result.get("expiry_date"):
                print(f"  {Colors.DIM}Expired on:{Colors.RESET} {result['expiry_date']}")
            print("="*60)
            print(f"{Colors.YELLOW}💡 Contact admin for extension{Colors.RESET}")
            return False

        elif result["status"] == "denied":
            print(f"{Colors.RED}❌ {result['message']}{Colors.RESET}")
            print(f"\n{Colors.YELLOW}📤 Send this request code to admin:{Colors.RESET}")
            print(f"  {Colors.BOLD}{Colors.CYAN}{result['request_code']}{Colors.RESET}")
            if result.get("device_id"):
                print(f"\n  {Colors.DIM}Device ID:{Colors.RESET}   {result['device_id'][:20]}...")
            if result.get("device_model"):
                print(f"  {Colors.DIM}Device Model:{Colors.RESET} {result['device_model']}")
            print(f"\n{Colors.DIM}Admin will issue your license on the POWER dashboard{Colors.RESET}")
            print("="*60)
            return False

        elif result["status"] == "error":
            print(f"{Colors.RED}❌ {result['message']}{Colors.RESET}")
            print("="*60)
            print(f"{Colors.YELLOW}💡 Check your internet connection and server status{Colors.RESET}")
            print(f"   {Colors.DIM}Server: {self.server_url}{Colors.RESET}")
            return False

        else:
            print(f"{Colors.RED}❌ Unknown error{Colors.RESET}")
            return False


# ============================================
# Simple function for quick use
# ============================================

def require_license(tool_name="nxtools", server_url="http://153.75.248.106:8000"):
    """Quick function to check license"""
    license = NXLicense(tool_name=tool_name, server_url=server_url)
    return license.require()


def get_license_key(tool_name="nxtools", secret_word="naha"):
    """Generate and return the request code only"""
    license = NXLicense(tool_name=tool_name, secret_word=secret_word)
    key_info = license.generate_key()
    return key_info["request_code"]


# ============================================
# Example Usage
# ============================================

if __name__ == "__main__":
    SERVER_URL = "http://153.75.248.106:8000"
    TOOL_NAME = "intramirror"  # Change to your tool name

    print("\n" + "="*50)
    print(f"{Colors.BOLD}POWER License System{Colors.RESET}")
    print("="*50)
    
    # Generate and show request code
    license = NXLicense(tool_name=TOOL_NAME, server_url=SERVER_URL)
    key_info = license.generate_key()
    
    print(f"\n{Colors.DIM}Tool:{Colors.RESET}       {TOOL_NAME}")
    print(f"{Colors.DIM}Server:{Colors.RESET}     {SERVER_URL}")
    print(f"{Colors.DIM}Device:{Colors.RESET}     {key_info['device_model']}")
    print(f"\n{Colors.YELLOW}Your Request Code:{Colors.RESET}")
    print(f"  {Colors.CYAN}{Colors.BOLD}{key_info['request_code']}{Colors.RESET}")
    
    print("\n" + "="*50)
    
    # Check license
    if license.require():
        print("\n✅ Tool is ready to use!")
        sys.exit(0)
    else:
        print("\n❌ Access Denied")
        sys.exit(1)
