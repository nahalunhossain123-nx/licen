#!/usr/bin/env python3
"""
NXTools Universal License System
Can be used with ANY Python tool
"""

import hashlib
import json
import os
import subprocess
import platform
import requests
from datetime import datetime, timedelta
import sys

class NXLicense:
    """
    Universal License Manager for NXTools
    
    Usage:
        license = NXLicense(tool_name="intramirror")
        if license.check():
            # Run your tool
        else:
            print("License required")
    """
    
    def __init__(self, tool_name="nxtools", secret_word="naha", 
                 pastebin_url="https://pastebin.com/raw/ez5BKAbT"):
        """
        Initialize license manager
        
        Args:
            tool_name: Name of your tool (e.g., "intramirror", "nxtools")
            secret_word: Your master secret (default: "naha")
            pastebin_url: URL to your Pastebin raw content
        """
        self.tool_name = tool_name
        self.secret_word = secret_word
        self.pastebin_url = pastebin_url
        self.license_file = os.path.expanduser(f"~/.nxtools_license_{tool_name}.json")
        self.load_license()
    
    def get_device_id(self):
        """Get unique device ID"""
        # Method 1: Android ID
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
                        return f"ANDROID:{android_id}"
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
                return f"FINGERPRINT:{hashlib.md5(fingerprint.encode()).hexdigest()[:16]}"
        except:
            pass
        
        # Method 3: Fallback
        try:
            username = os.getenv('USER', 'user')
            hostname = platform.node()
            home = os.path.expanduser("~")
            unique = f"{username}|{home}|{hostname}|{datetime.now().year}"
            return f"FALLBACK:{hashlib.md5(unique.encode()).hexdigest()[:16]}"
        except:
            return f"FALLBACK:{hashlib.md5(str(os.getpid()).encode()).hexdigest()[:16]}"
    
    def get_device_model(self):
        """Get device model"""
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
        return platform.node() or "Unknown_Device"
    
    def generate_request_code(self):
        """Generate request code from device info"""
        device_id = self.get_device_id()
        device_model = self.get_device_model()
        timestamp = datetime.now().strftime("%Y%m%d")
        
        raw_data = f"{device_id}|{device_model}|{self.secret_word}|{timestamp}|{self.tool_name}"
        hash_obj = hashlib.sha256(raw_data.encode())
        hash_hex = hash_obj.hexdigest()
        
        request_code = f"REQ-{hash_hex[:12].upper()}"
        
        return {
            "request_code": request_code,
            "device_id": device_id,
            "device_model": device_model,
            "timestamp": timestamp,
            "tool_name": self.tool_name
        }
    
    def check_pastebin(self, request_code):
        """
        Check if request code exists in Pastebin
        
        Format: TOOL|REQUEST|APPROVAL|EXPIRY|USER
        """
        try:
            response = requests.get(self.pastebin_url, timeout=10)
            if response.status_code != 200:
                return None
            
            content = response.text.strip()
            if not content:
                return None
            
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split('|')
                if len(parts) >= 5:
                    tool, req, app, expiry, user = parts[:5]
                    if req == request_code and tool == self.tool_name:
                        return {
                            "tool": tool,
                            "request_code": req,
                            "approval_code": app,
                            "expiry_date": expiry,
                            "user_info": user
                        }
            return None
        except:
            return None
    
    def check(self):
        """
        Check license status
        
        Returns:
            dict: {
                "status": "active" | "expired" | "denied" | "error",
                "message": "Description",
                "request_code": "REQ-XXXX",
                "user_info": "User name",
                "expiry_date": "YYYY-MM-DD",
                "remaining_days": int
            }
        """
        request_info = self.generate_request_code()
        request_code = request_info["request_code"]
        
        # Check local cached license first
        if self.license_data and self.license_data.get("status") == "active":
            if self.license_data.get("device_id") == request_info["device_id"]:
                expiry = self.license_data.get("expiry_date")
                if expiry:
                    try:
                        expiry_date = datetime.fromisoformat(expiry)
                        if datetime.now() > expiry_date:
                            return {
                                "status": "expired",
                                "message": f"License expired on {expiry}",
                                "request_code": request_code
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
                    "remaining_days": remaining
                }
        
        # Check Pastebin
        approval_data = self.check_pastebin(request_code)
        
        if not approval_data:
            return {
                "status": "denied",
                "message": "Not approved. Contact admin.",
                "request_code": request_code
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
                        "expiry_date": expiry_date
                    }
                remaining = (expiry - datetime.now()).days
            except:
                remaining = None
        else:
            remaining = None
        
        # Approved!
        license_data = {
            "tool_name": self.tool_name,
            "request_code": request_code,
            "device_id": request_info["device_id"],
            "device_model": request_info["device_model"],
            "user_info": approval_data.get("user_info"),
            "expiry_date": expiry_date,
            "activated_date": datetime.now().isoformat(),
            "status": "active"
        }
        self.save_license(license_data)
        
        return {
            "status": "active",
            "message": "License approved!",
            "request_code": request_code,
            "user_info": approval_data.get("user_info"),
            "expiry_date": expiry_date,
            "remaining_days": remaining
        }
    
    def save_license(self, license_data):
        """Save license locally"""
        try:
            with open(self.license_file, 'w') as f:
                json.dump(license_data, f, indent=2)
            try:
                os.chmod(self.license_file, 0o600)
            except:
                pass
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
    
    def display_status(self):
        """Display license status to user"""
        result = self.check()
        
        print("\n" + "="*60)
        print(f"🔐 NXTools License - {self.tool_name.upper()}")
        print("="*60)
        
        if result["status"] == "active":
            print(f"✅ {result['message']}")
            print(f"  User: {result.get('user_info', 'Unknown')}")
            print(f"  Request: {result.get('request_code', 'Unknown')}")
            if result.get("remaining_days") is not None:
                print(f"  Remaining: {result['remaining_days']} days")
            if result.get("expiry_date"):
                print(f"  Expires: {result['expiry_date']}")
            return True
            
        elif result["status"] == "expired":
            print(f"❌ {result['message']}")
            print(f"\n💡 Contact admin for extension")
            print(f"  Request: {result.get('request_code', 'Unknown')}")
            return False
            
        elif result["status"] == "denied":
            print(f"❌ {result['message']}")
            print(f"  Request: {result.get('request_code', 'Unknown')}")
            print(f"\n📤 Send this request code to admin:")
            print(f"  {result['request_code']}")
            return False
            
        else:
            print(f"❌ Unknown status")
            return False


# ============================================
# Quick Usage Functions
# ============================================

def require_license(tool_name="nxtools", secret_word="naha", 
                    pastebin_url="https://pastebin.com/raw/ez5BKAbT"):
    """
    Quick wrapper to check license and exit if not valid
    
    Usage:
        if not require_license("intramirror"):
            sys.exit(1)
        # Continue with tool
    """
    license = NXLicense(tool_name, secret_word, pastebin_url)
    if license.display_status():
        return True
    else:
        print("\n❌ Access Denied")
        return False


# ============================================
# Example Usage
# ============================================

if __name__ == "__main__":
    # Test the license system
    print("\n🧪 Testing NXTools License System\n")
    
    # Test with different tools
    tools = ["intramirror", "nxtools", "custom"]
    
    for tool in tools:
        print(f"\n{'='*50}")
        print(f"Testing: {tool}")
        print('='*50)
        
        license = NXLicense(tool_name=tool)
        result = license.check()
        print(f"Status: {result['status']}")
        if result.get("request_code"):
            print(f"Request: {result['request_code']}")
        if result.get("remaining_days") is not None:
            print(f"Remaining: {result['remaining_days']} days")
