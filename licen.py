#!/usr/bin/env python3
"""
NXTools License System - Proper Key Generation
Key is PERMANENT for each device
"""

import hashlib
import os
import subprocess
import platform
import requests
from datetime import datetime
import sys
import json

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
                 pastebin_url="https://pastebin.com/raw/ez5BKAbT"):
        self.tool_name = tool_name
        self.secret_word = secret_word
        self.pastebin_url = pastebin_url
        self.license_file = os.path.expanduser(f"~/.{tool_name}_license.json")
        self.load_license()
    
    def get_device_id(self):
        """Get unique device ID - PERMANENT for this device"""
        print(f"\n{Colors.DIM}🔍 Getting Device ID...{Colors.RESET}")
        
        # Method 1: Android ID (Best for Termux/Android)
        try:
            result = subprocess.run(
                ['content', 'query', '--uri', 'content://settings/secure', 
                 '--where', "name='android_id'"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                import re
                match = re.search(r'value=([a-f0-9]+)', result.stdout)
                if match:
                    android_id = match.group(1)
                    if android_id and len(android_id) > 5:
                        device_id = f"ANDROID:{android_id}"
                        print(f"{Colors.GREEN}✅ Device ID: {device_id}{Colors.RESET}")
                        return device_id
        except:
            pass
        
        # Method 2: Build fingerprint
        try:
            result = subprocess.run(
                ['getprop', 'ro.build.fingerprint'],
                capture_output=True, text=True, timeout=5
            )
            fingerprint = result.stdout.strip()
            if fingerprint and len(fingerprint) > 10:
                device_id = f"FINGERPRINT:{hashlib.md5(fingerprint.encode()).hexdigest()[:16]}"
                print(f"{Colors.GREEN}✅ Device ID: {device_id}{Colors.RESET}")
                return device_id
        except:
            pass
        
        # Method 3: Permanent fallback (based on system info)
        try:
            username = os.getenv('USER', 'user')
            hostname = platform.node()
            home = os.path.expanduser("~")
            # This combination is PERMANENT for the device
            unique = f"{username}|{home}|{hostname}"
            device_id = f"DEVICE:{hashlib.md5(unique.encode()).hexdigest()[:16]}"
            print(f"{Colors.YELLOW}⚠️ Using fallback Device ID: {device_id}{Colors.RESET}")
            return device_id
        except:
            device_id = f"DEVICE:{hashlib.md5(str(os.getpid()).encode()).hexdigest()[:16]}"
            print(f"{Colors.YELLOW}⚠️ Using emergency Device ID: {device_id}{Colors.RESET}")
            return device_id
    
    def get_device_model(self):
        """Get device model"""
        print(f"{Colors.DIM}🔍 Getting Device Model...{Colors.RESET}")
        
        try:
            result = subprocess.run(
                ['getprop', 'ro.product.model'],
                capture_output=True, text=True, timeout=5
            )
            model = result.stdout.strip()
            if model:
                print(f"{Colors.GREEN}✅ Device Model: {model}{Colors.RESET}")
                return model
        except:
            pass
        
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
                model = f"{manufacturer} {model}"
                print(f"{Colors.GREEN}✅ Device Model: {model}{Colors.RESET}")
                return model
        except:
            pass
        
        model = platform.node() or "Unknown_Device"
        print(f"{Colors.YELLOW}⚠️ Using fallback Model: {model}{Colors.RESET}")
        return model
    
    def generate_key(self):
        """
        Generate PERMANENT license key from device info
        
        FORMULA: LICENSE KEY = SHA256(Device_ID + Device_Model + Secret_Word)
        
        NO RANDOM SALT - so key is ALWAYS the same for this device!
        Result: 16-digit key (XXXX-XXXX-XXXX-XXXX)
        """
        print(f"\n{Colors.CYAN}🔑 Generating License Key...{Colors.RESET}")
        print("="*50)
        
        # Get device info
        device_id = self.get_device_id()
        device_model = self.get_device_model()
        
        # Show what's being used
        print(f"\n{Colors.YELLOW}📋 Key Generation Data:{Colors.RESET}")
        print(f"  {Colors.DIM}Device ID:{Colors.RESET}    {device_id}")
        print(f"  {Colors.DIM}Device Model:{Colors.RESET} {device_model}")
        print(f"  {Colors.DIM}Secret Word:{Colors.RESET}  {self.secret_word}")
        print(f"  {Colors.DIM}Tool Name:{Colors.RESET}   {self.tool_name}")
        
        # ============================================
        # PROPER KEY GENERATION - NO RANDOM SALT
        # ============================================
        raw_data = f"{device_id}|{device_model}|{self.secret_word}|{self.tool_name}"
        
        # Hash it
        hash_obj = hashlib.sha256(raw_data.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Take first 12 chars for request code
        request_code = f"REQ-{hash_hex[:12].upper()}"
        
        print(f"\n{Colors.GREEN}✅ License Key Generated:{Colors.RESET}")
        print(f"  {Colors.BOLD}{Colors.CYAN}{request_code}{Colors.RESET}")
        print("="*50)
        
        return {
            "request_code": request_code,
            "device_id": device_id,
            "device_model": device_model,
            "raw_hash": hash_hex  # For debugging
        }
    
    def check_pastebin(self, request_code):
        """Check if request code exists in Pastebin"""
        print(f"\n{Colors.DIM}🔍 Checking Pastebin for approval...{Colors.RESET}")
        
        try:
            response = requests.get(self.pastebin_url, timeout=10)
            if response.status_code != 200:
                print(f"{Colors.RED}❌ Could not reach Pastebin (Status: {response.status_code}){Colors.RESET}")
                return None
            
            content = response.text.strip()
            if not content:
                print(f"{Colors.YELLOW}⚠️ Pastebin is empty{Colors.RESET}")
                return None
            
            print(f"{Colors.GREEN}✅ Pastebin reached! Checking entries...{Colors.RESET}")
            
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split('|')
                if len(parts) >= 5:
                    tool, req, app, expiry, user = parts[:5]
                    if req == request_code and tool == self.tool_name:
                        print(f"{Colors.GREEN}✅ Found matching entry!{Colors.RESET}")
                        return {
                            "tool": tool,
                            "request_code": req,
                            "approval_code": app,
                            "expiry_date": expiry,
                            "user_info": user
                        }
            
            print(f"{Colors.YELLOW}⚠️ No matching entry found{Colors.RESET}")
            return None
        except Exception as e:
            print(f"{Colors.RED}❌ Error checking Pastebin: {e}{Colors.RESET}")
            return None
    
    def check(self):
        """Check license status - generates key and checks Pastebin"""
        # Generate PERMANENT key for this device
        key_info = self.generate_key()
        request_code = key_info["request_code"]
        
        # Check local cache first
        if self.license_data and self.license_data.get("status") == "active":
            if self.license_data.get("device_id") == key_info["device_id"]:
                expiry = self.license_data.get("expiry_date")
                if expiry:
                    try:
                        expiry_date = datetime.fromisoformat(expiry)
                        if datetime.now() > expiry_date:
                            return {
                                "status": "expired",
                                "message": f"License expired on {expiry}",
                                "request_code": request_code,
                                "device_id": key_info["device_id"],
                                "device_model": key_info["device_model"]
                            }
                        remaining = (expiry_date - datetime.now()).days
                    except:
                        remaining = None
                else:
                    remaining = None
                
                return {
                    "status": "active",
                    "message": "License valid (cached)",
                    "request_code": request_code,
                    "user_info": self.license_data.get("user_info"),
                    "expiry_date": expiry,
                    "remaining_days": remaining,
                    "device_id": key_info["device_id"],
                    "device_model": key_info["device_model"]
                }
        
        # Check Pastebin
        approval_data = self.check_pastebin(request_code)
        
        if not approval_data:
            return {
                "status": "denied",
                "message": "Not approved",
                "request_code": request_code,
                "device_id": key_info["device_id"],
                "device_model": key_info["device_model"]
            }
        
        # Check expiry
        expiry_date = approval_data.get("expiry_date")
        if expiry_date:
            try:
                expiry = datetime.fromisoformat(expiry_date)
                if datetime.now() > expiry:
                    return {
                        "status": "expired",
                        "message": f"License expired on {expiry_date}",
                        "request_code": request_code,
                        "expiry_date": expiry_date,
                        "device_id": key_info["device_id"],
                        "device_model": key_info["device_model"]
                    }
                remaining = (expiry - datetime.now()).days
            except:
                remaining = None
        else:
            remaining = None
        
        # ✅ Approved! Save license locally
        license_data = {
            "tool_name": self.tool_name,
            "request_code": request_code,
            "device_id": key_info["device_id"],
            "device_model": key_info["device_model"],
            "user_info": approval_data.get("user_info"),
            "expiry_date": expiry_date,
            "activated_date": datetime.now().isoformat(),
            "status": "active"
        }
        self.save_license(license_data)
        
        return {
            "status": "active",
            "message": "✅ License approved!",
            "request_code": request_code,
            "user_info": approval_data.get("user_info"),
            "expiry_date": expiry_date,
            "remaining_days": remaining,
            "device_id": key_info["device_id"],
            "device_model": key_info["device_model"]
        }
    
    def save_license(self, license_data):
        """Save license locally"""
        try:
            with open(self.license_file, 'w') as f:
                json.dump(license_data, f, indent=2)
        except:
            pass
    
    def load_license(self):
        """Load existing license"""
        if os.path.exists(self.license_file):
            try:
                with open(self.license_file, 'r') as f:
                    self.license_data = json.load(f)
                return self.license_data
            except:
                self.license_data = None
                return None
        self.license_data = None
        return None
    
    def require(self):
        """Main function - check license and show status"""
        result = self.check()
        
        print("\n" + "="*60)
        print(f"{Colors.CYAN}{Colors.BOLD}  🔐 {self.tool_name.upper()} License{Colors.RESET}")
        print("="*60)
        
        if result["status"] == "active":
            print(f"{Colors.GREEN}✅ {result['message']}{Colors.RESET}")
            print(f"  {Colors.DIM}Device:{Colors.RESET}   {result.get('device_model', 'Unknown')}")
            print(f"  {Colors.DIM}Device ID:{Colors.RESET} {result.get('device_id', 'Unknown')[:20]}...")
            print(f"  {Colors.DIM}User:{Colors.RESET}     {result.get('user_info', 'Unknown')}")
            if result.get("remaining_days") is not None:
                print(f"  {Colors.DIM}Remaining:{Colors.RESET} {result['remaining_days']} days")
            if result.get("expiry_date"):
                print(f"  {Colors.DIM}Expires:{Colors.RESET}  {result['expiry_date']}")
            print("="*60)
            print(f"{Colors.GREEN}🎉 Access Granted!{Colors.RESET}")
            return True
            
        elif result["status"] == "expired":
            print(f"{Colors.RED}❌ {result['message']}{Colors.RESET}")
            print(f"  {Colors.DIM}Device:{Colors.RESET}   {result.get('device_model', 'Unknown')}")
            print("="*60)
            print(f"{Colors.YELLOW}💡 Contact admin for extension{Colors.RESET}")
            return False
            
        elif result["status"] == "denied":
            print(f"{Colors.RED}❌ {result['message']}{Colors.RESET}")
            print(f"  {Colors.DIM}Device:{Colors.RESET}   {result.get('device_model', 'Unknown')}")
            print(f"  {Colors.DIM}Device ID:{Colors.RESET} {result.get('device_id', 'Unknown')[:20]}...")
            print(f"\n{Colors.YELLOW}📤 Send this request code to admin:{Colors.RESET}")
            print(f"  {Colors.BOLD}{Colors.CYAN}{result['request_code']}{Colors.RESET}")
            print(f"\n{Colors.DIM}Admin will add this code to Pastebin{Colors.RESET}")
            print("="*60)
            return False
            
        else:
            print(f"{Colors.RED}❌ Unknown error{Colors.RESET}")
            return False


# ============================================
# Quick Test Function
# ============================================

def test_license():
    """Test the license system and show device info"""
    print("\n" + "="*60)
    print(f"{Colors.CYAN}{Colors.BOLD}  🧪 NXTools License Test{Colors.RESET}")
    print("="*60)
    
    license = NXLicense(tool_name="intramirror")
    
    # Show device info
    print(f"\n{Colors.YELLOW}📱 Device Information:{Colors.RESET}")
    print(f"  Device ID: {license.get_device_id()}")
    print(f"  Device Model: {license.get_device_model()}")
    
    # Generate key
    key_info = license.generate_key()
    print(f"\n{Colors.YELLOW}🔑 Generated License Key:{Colors.RESET}")
    print(f"  {Colors.BOLD}{Colors.CYAN}{key_info['request_code']}{Colors.RESET}")
    
    # Check approval
    print(f"\n{Colors.YELLOW}🔍 Checking Approval Status:{Colors.RESET}")
    result = license.check_pastebin(key_info['request_code'])
    
    if result:
        print(f"{Colors.GREEN}✅ APPROVED!{Colors.RESET}")
        print(f"  User: {result['user_info']}")
        print(f"  Expires: {result['expiry_date']}")
    else:
        print(f"{Colors.RED}❌ NOT APPROVED{Colors.RESET}")
        print(f"  Send this to admin: {key_info['request_code']}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    test_license()
