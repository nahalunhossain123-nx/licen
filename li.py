#!/usr/bin/env python3
"""
Quick test for POWER license system
Using Windows PC IP: 192.168.0.72
"""

import hashlib
import os
import platform
import requests
from datetime import datetime
import sys
import json
import subprocess
import re

# ============================================
# === YOUR WINDOWS PC IP ===
# ============================================
SERVER_URL = "http://192.168.0.72:8000"  # <-- YOUR IP
TOOL_NAME = "intramirror"
SECRET_WORD = "naha"
# ============================================


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def get_device_id():
    """Get unique device ID"""
    try:
        # Windows: Use machine GUID
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
    
    # Fallback
    try:
        username = os.getenv('USERNAME', 'user')
        hostname = platform.node()
        home = os.path.expanduser("~")
        unique = f"{username}|{home}|{hostname}"
        return f"DEVICE:{hashlib.md5(unique.encode()).hexdigest()[:16]}"
    except:
        return f"DEVICE:{hashlib.md5(str(os.getpid()).encode()).hexdigest()[:16]}"


def get_device_model():
    """Get device model"""
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
    
    return platform.node() or "Unknown_Device"


def generate_key(tool_name, secret_word):
    """Generate request code"""
    device_id = get_device_id()
    device_model = get_device_model()
    
    raw_data = f"{device_id}|{device_model}|{secret_word}|{tool_name}"
    hash_obj = hashlib.sha256(raw_data.encode())
    hash_hex = hash_obj.hexdigest()
    
    request_code = f"REQ-{hash_hex[:12].upper()}"
    
    return {
        "request_code": request_code,
        "device_id": device_id,
        "device_model": device_model
    }


def check_with_server(tool_name, request_code, server_url):
    """Check license with POWER server"""
    try:
        response = requests.post(
            f"{server_url}/api/check",
            json={
                "tool_name": tool_name,
                "request_code": request_code
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"Server error: {response.status_code}"
            }
        
        data = response.json()
        
        if data.get("status") == "active":
            return {
                "status": "active",
                "message": "✅ License valid!",
                "owner": data.get("owner"),
                "expiry": data.get("expiry")
            }
        elif data.get("status") == "expired":
            return {
                "status": "expired",
                "message": f"❌ License expired on {data.get('expiry')}",
                "expiry": data.get("expiry")
            }
        elif data.get("status") in ["revoked", "banned"]:
            return {
                "status": data.get("status"),
                "message": f"❌ License {data.get('status')}"
            }
        else:
            return {
                "status": "not_found",
                "message": "❌ License not found in system"
            }
            
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": f"❌ Cannot connect to server: {server_url}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Error: {str(e)}"
        }


def get_license_key(tool_name="intramirror", secret_word="naha"):
    """Get request code only"""
    key_info = generate_key(tool_name, secret_word)
    return key_info["request_code"]


def require_license(tool_name="intramirror", secret_word="naha", server_url=SERVER_URL):
    """Main license check function"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}🔐 POWER License Check{Colors.RESET}")
    print("="*50)
    
    # Generate key
    key_info = generate_key(tool_name, secret_word)
    request_code = key_info["request_code"]
    
    print(f"{Colors.DIM}Tool:{Colors.RESET}     {tool_name}")
    print(f"{Colors.DIM}Server:{Colors.RESET}   {server_url}")
    print(f"{Colors.DIM}Code:{Colors.RESET}     {request_code}")
    print("="*50)
    
    # Check with server
    result = check_with_server(tool_name, request_code, server_url)
    
    if result["status"] == "active":
        print(f"{Colors.GREEN}{result['message']}{Colors.RESET}")
        if result.get("owner"):
            print(f"  {Colors.DIM}Owner:{Colors.RESET}  {result['owner']}")
        if result.get("expiry"):
            print(f"  {Colors.DIM}Expires:{Colors.RESET} {result['expiry']}")
        print("="*50)
        print(f"{Colors.GREEN}🎉 Access Granted!{Colors.RESET}")
        return True
        
    elif result["status"] == "not_found":
        print(f"{Colors.YELLOW}⚠️  {result['message']}{Colors.RESET}")
        print(f"\n{Colors.BOLD}📤 Send this request code to admin:{Colors.RESET}")
        print(f"  {Colors.CYAN}{Colors.BOLD}{request_code}{Colors.RESET}")
        print(f"\n{Colors.DIM}Admin will create a license in the POWER dashboard{Colors.RESET}")
        print("="*50)
        return False
        
    else:
        print(f"{Colors.RED}{result['message']}{Colors.RESET}")
        print("="*50)
        return False


# ============================================
# RUN THE TEST
# ============================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print(f"{Colors.BOLD}POWER License Test{Colors.RESET}")
    print("="*50)
    
    # First, get the request code
    print(f"\n{Colors.YELLOW}Step 1: Generate Request Code{Colors.RESET}")
    request_code = get_license_key(TOOL_NAME, SECRET_WORD)
    print(f"  {Colors.BOLD}Your Request Code:{Colors.RESET} {Colors.CYAN}{request_code}{Colors.RESET}")
    
    print(f"\n{Colors.YELLOW}Step 2: Check with Server{Colors.RESET}")
    print(f"  Server: {SERVER_URL}")
    
    # Check license
    if require_license(TOOL_NAME, SECRET_WORD, SERVER_URL):
        print("\n✅ Tool is ready to use!")
    else:
        print("\n❌ Access Denied")
        print(f"\n{Colors.DIM}💡 Go to POWER Dashboard → Licenses → Issue License{Colors.RESET}")
        print(f"   {Colors.DIM}Enter the request code above{Colors.RESET}")
    
    print("\n" + "="*50)
