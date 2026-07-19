#!/usr/bin/env python3
"""
IntraMirror OTP Sender - Auto-Check License System
"""

import hashlib
import json
import os
import subprocess
import platform
import requests
from datetime import datetime
import sys

class AutoLicenseManager:
    def __init__(self, secret_word="naha"):
        self.secret_word = secret_word
        self.license_file = os.path.expanduser("~/.intramirror_license.json")
        self.pastebin_url = "https://pastebin.com/raw/ez5BKAbT"  # ← YOUR URL
        self.load_license()
    
    # ... (rest of the code without admin functions)
    
    def check_pastebin(self, request_code):
        """Check if request code exists in Pastebin"""
        try:
            response = requests.get(self.pastebin_url, timeout=10)
            if response.status_code != 200:
                return None
            
            content = response.text.strip()
            if not content:
                return None
            
            # Check each line
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith(request_code):
                    parts = line.split('|')
                    if len(parts) >= 4:
                        return {
                            "request_code": parts[0],
                            "approval_code": parts[1],
                            "expiry_date": parts[2],
                            "user_info": parts[3]
                        }
            return None
        except:
            return None
    
    def check_license(self):
        """Check license status"""
        request_info = self.generate_request_code()
        request_code = request_info["request_code"]
        
        # Check Pastebin
        approval_data = self.check_pastebin(request_code)
        
        if not approval_data:
            return {
                "status": "denied",
                "request_code": request_code
            }
        
        # Check expiry
        expiry_date = approval_data.get("expiry_date")
        if expiry_date:
            expiry = datetime.fromisoformat(expiry_date)
            if datetime.now() > expiry:
                return {
                    "status": "expired",
                    "request_code": request_code,
                    "expiry_date": expiry_date
                }
        
        # Approved!
        return {
            "status": "active",
            "request_code": request_code,
            "user_info": approval_data.get("user_info"),
            "expiry_date": expiry_date
        }

# ============================================
# Main Program
# ============================================

def main():
    license_manager = AutoLicenseManager()
    status = license_manager.check_license()
    
    if status["status"] == "active":
        print("✅ License approved!")
        print(f"User: {status.get('user_info')}")
        print(f"Expires: {status.get('expiry_date')}")
        # ... YOUR OTP CODE HERE
    else:
        print("❌ Not approved")
        print(f"Request code: {status['request_code']}")
        print("Contact admin to add you to Pastebin")

if __name__ == "__main__":
    main()
