#!/usr/bin/env python3
"""
IntraMirror OTP Sender - Auto-Check License System
Checks Pastebin automatically for approval
"""

import hashlib
import json
import os
import subprocess
import platform
import requests
from datetime import datetime, timedelta
import sys
import time

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

class AutoLicenseManager:
    def __init__(self, secret_word="naha"):
        """
        Initialize with Pastebin URL
        """
        self.secret_word = secret_word
        self.license_file = os.path.expanduser("~/.intramirror_license.json")
        
        # ========================================
        # UPDATE THIS WITH YOUR PASTEBIN RAW URL
        # ========================================
        self.pastebin_url = "https://pastebin.com/raw/ez5BKAbT"
        # ========================================
        
        self.load_license()
    
    def get_device_id(self):
        """
        Get unique device ID for Termux/Android
        Multiple fallback methods
        """
        # Method 1: Try Android ID via content provider
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
        
        # Method 2: Use build fingerprint
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
        
        # Method 3: Use serial number
        try:
            result = subprocess.run(
                ['getprop', 'ro.serialno'],
                capture_output=True, text=True, timeout=5
            )
            serial = result.stdout.strip()
            if serial and len(serial) > 5:
                return f"SERIAL:{hashlib.md5(serial.encode()).hexdigest()[:16]}"
        except:
            pass
        
        # Method 4: Fallback - Use system info
        try:
            import socket
            username = os.getenv('USER', 'termux')
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
        
        return platform.node() or "Termux_Device"
    
    def generate_request_code(self):
        """
        Generate request code from device info
        """
        device_id = self.get_device_id()
        device_model = self.get_device_model()
        timestamp = datetime.now().strftime("%Y%m%d")
        
        raw_data = f"{device_id}|{device_model}|{self.secret_word}|{timestamp}"
        hash_obj = hashlib.sha256(raw_data.encode())
        hash_hex = hash_obj.hexdigest()
        
        request_code = f"REQ-{hash_hex[:12].upper()}"
        
        return {
            "request_code": request_code,
            "device_id": device_id,
            "device_model": device_model,
            "timestamp": timestamp
        }
    
    def check_pastebin(self, request_code):
        """
        Check if request code exists in Pastebin
        
        Returns:
            dict: Approval data or None
        """
        try:
            response = requests.get(self.pastebin_url, timeout=10)
            
            if response.status_code != 200:
                return None
            
            content = response.text.strip()
            
            if not content:
                return None
            
            # Try JSON format
            try:
                data = json.loads(content)
                approved_devices = data.get("approved_devices", {})
                for key, approval in approved_devices.items():
                    if approval.get("request_code") == request_code:
                        return approval
            except:
                # Try plain text format
                lines = content.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
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
            
        except Exception as e:
            return None
    
    def check_license(self):
        """
        Check license status - AUTO APPROVAL
        
        Returns:
            dict: License status
        """
        # Generate request code for this device
        request_info = self.generate_request_code()
        request_code = request_info["request_code"]
        
        # Check if already have local license
        if self.license_data and self.license_data.get("status") == "active":
            # Verify device matches
            if self.license_data.get("device_id") == request_info["device_id"]:
                # Check expiry
                expiry = self.license_data.get("expiry_date")
                if expiry:
                    try:
                        expiry_date = datetime.fromisoformat(expiry)
                        if datetime.now() > expiry_date:
                            return {
                                "status": "expired",
                                "message": f"License expired on {expiry}",
                                "request_code": request_code,
                                "device_id": request_info["device_id"],
                                "device_model": request_info["device_model"]
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
                    "device_id": request_info["device_id"],
                    "device_model": request_info["device_model"],
                    "remaining_days": remaining,
                    "expiry_date": expiry,
                    "user_info": self.license_data.get("user_info")
                }
        
        # Check Pastebin for approval
        print(f"\n{Colors.DIM}🔍 Checking approval status...{Colors.RESET}")
        approval_data = self.check_pastebin(request_code)
        
        if not approval_data:
            return {
                "status": "denied",
                "message": "❌ Not approved! Contact admin.",
                "request_code": request_code,
                "device_id": request_info["device_id"],
                "device_model": request_info["device_model"]
            }
        
        # Check expiry
        expiry_date = approval_data.get("expiry_date")
        if expiry_date:
            try:
                expiry = datetime.fromisoformat(expiry_date)
                if datetime.now() > expiry:
                    return {
                        "status": "expired",
                        "message": f"❌ License expired on {expiry_date}",
                        "request_code": request_code,
                        "device_id": request_info["device_id"],
                        "device_model": request_info["device_model"],
                        "expiry_date": expiry_date
                    }
                remaining = (expiry - datetime.now()).days
            except:
                remaining = None
        else:
            remaining = None
        
        # ✅ APPROVED!
        # Save license locally
        license_data = {
            "request_code": request_code,
            "device_id": request_info["device_id"],
            "device_model": request_info["device_model"],
            "activated_date": datetime.now().isoformat(),
            "expiry_date": expiry_date,
            "status": "active",
            "user_info": approval_data.get("user_info", "Unknown")
        }
        self.save_license(license_data)
        
        return {
            "status": "active",
            "message": "✅ License approved!",
            "request_code": request_code,
            "device_id": request_info["device_id"],
            "device_model": request_info["device_model"],
            "remaining_days": remaining,
            "expiry_date": expiry_date,
            "user_info": approval_data.get("user_info", "Unknown")
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
    
    def get_license_status(self):
        """
        Get license status for display
        """
        result = self.check_license()
        
        return result
    
    def display_status(self):
        """
        Display license status to user
        """
        status = self.get_license_status()
        
        print("\n" + "="*60)
        print(f"{Colors.CYAN}{Colors.BOLD}  🔐 License Status{Colors.RESET}")
        print("="*60)
        
        if status["status"] == "active":
            print(f"\n{Colors.GREEN}✅ {status['message']}{Colors.RESET}")
            print(f"  🆔 Device: {status.get('device_model', 'Unknown')}")
            print(f"  🔑 Request: {status.get('request_code', 'Unknown')}")
            if status.get("remaining_days") is not None:
                print(f"  ⏰ Remaining: {status['remaining_days']} days")
            if status.get("expiry_date"):
                print(f"  📅 Expires: {status['expiry_date']}")
            if status.get("user_info"):
                print(f"  👤 User: {status['user_info']}")
            return True
            
        elif status["status"] == "expired":
            print(f"\n{Colors.RED}❌ {status['message']}{Colors.RESET}")
            print(f"  🆔 Device: {status.get('device_model', 'Unknown')}")
            print(f"  🔑 Request: {status.get('request_code', 'Unknown')}")
            print(f"\n{Colors.YELLOW}💡 Contact admin for extension{Colors.RESET}")
            return False
            
        elif status["status"] == "denied":
            print(f"\n{Colors.RED}❌ {status['message']}{Colors.RESET}")
            print(f"  🆔 Device: {status.get('device_model', 'Unknown')}")
            print(f"  🔑 Request: {status.get('request_code', 'Unknown')}")
            print(f"\n{Colors.YELLOW}📤 Send this request code to admin:{Colors.RESET}")
            print(f"  {Colors.BOLD}{status['request_code']}{Colors.RESET}")
            print(f"\n{Colors.DIM}Admin will add your device to Pastebin{Colors.RESET}")
            return False
            
        else:
            print(f"\n{Colors.RED}❌ Unknown status{Colors.RESET}")
            return False


# ============================================
# Admin Tool
# ============================================

class AdminPastebinTool:
    def __init__(self, secret_word="naha"):
        self.secret_word = secret_word
        self.pastebin_url = "https://pastebin.com/ez5BKAbT"
    
    def generate_approval_entry(self, request_code, device_id, device_model, 
                                user_info, duration_days=30):
        """Generate approval entry for Pastebin"""
        # Generate approval code (optional, for future use)
        timestamp = datetime.now().strftime("%Y%m%d")
        raw_data = f"{request_code}|{self.secret_word}|{timestamp}"
        hash_obj = hashlib.sha256(raw_data.encode())
        hash_hex = hash_obj.hexdigest()
        approval_code = f"APP-{hash_hex[:12].upper()}"
        
        expiry_date = (datetime.now() + timedelta(days=duration_days)).strftime("%Y-%m-%d")
        
        # Plain text format for Pastebin
        entry_text = f"{request_code}|{approval_code}|{expiry_date}|{user_info}"
        
        # JSON format
        entry_json = {
            "request_code": request_code,
            "approval_code": approval_code,
            "device_id": device_id,
            "device_model": device_model,
            "user_info": user_info,
            "approval_date": datetime.now().isoformat(),
            "expiry_date": expiry_date,
            "status": "active"
        }
        
        return entry_text, entry_json
    
    def generate_pastebin_content(self, entries):
        """Generate content for Pastebin"""
        lines = []
        for entry in entries:
            line = f"{entry['request_code']}|{entry['approval_code']}|{entry['expiry_date']}|{entry['user_info']}"
            lines.append(line)
        return '\n'.join(lines)


def admin_cli():
    print("="*60)
    print(f"{Colors.CYAN}{Colors.BOLD}  🔐 Admin Tool - Auto Approval System{Colors.RESET}")
    print("="*60)
    print(f"{Colors.DIM}Pastebin URL: https://pastebin.com/ez5BKAbT{Colors.RESET}")
    print("="*60)
    
    admin = AdminPastebinTool(secret_word="naha")
    entries = []
    
    while True:
        print("\n" + "="*40)
        print("Options:")
        print("1. Add new device (create approval entry)")
        print("2. Generate Pastebin content")
        print("3. Show all entries")
        print("4. Test check from Pastebin")
        print("5. Exit")
        print("="*40)
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == "1":
            print("\n📝 Enter user details:")
            request_code = input("Request Code: ").strip().upper()
            device_id = input("Device ID: ").strip()
            device_model = input("Device Model: ").strip()
            user_info = input("User Info (email/username): ").strip()
            duration = int(input("Duration (days) [30]: ").strip() or "30")
            
            entry_text, entry_json = admin.generate_approval_entry(
                request_code, device_id, device_model, user_info, duration
            )
            entries.append(entry_json)
            
            print(f"\n{Colors.GREEN}✅ Entry created!{Colors.RESET}")
            print(f"📋 Add this to Pastebin:{Colors.RESET}")
            print(f"{Colors.DIM}{entry_text}{Colors.RESET}")
            
        elif choice == "2":
            if not entries:
                print(f"{Colors.YELLOW}⚠️ No entries yet.{Colors.RESET}")
                continue
            
            content = admin.generate_pastebin_content(entries)
            
            print("\n" + "="*60)
            print(f"{Colors.CYAN}📄 PASTEBIN CONTENT{Colors.RESET}")
            print("="*60)
            print(content)
            print("="*60)
            print(f"\n{Colors.YELLOW}📋 Copy this to: https://pastebin.com/ez5BKAbT{Colors.RESET}")
            
        elif choice == "3":
            if not entries:
                print(f"{Colors.YELLOW}⚠️ No entries yet.{Colors.RESET}")
                continue
            
            print("\n📋 All Entries:")
            for i, entry in enumerate(entries, 1):
                print(f"\n{i}. {entry['user_info']}")
                print(f"   Request: {entry['request_code']}")
                print(f"   Device: {entry.get('device_model', 'Unknown')}")
                print(f"   Expires: {entry['expiry_date']}")
                print(f"   Status: {entry['status']}")
                
        elif choice == "4":
            print("\n🔍 Testing Pastebin check...")
            test_manager = AutoLicenseManager()
            test_code = input("Enter request code to check: ").strip().upper()
            result = test_manager.check_pastebin(test_code)
            if result:
                print(f"{Colors.GREEN}✅ Found in Pastebin!{Colors.RESET}")
                print(json.dumps(result, indent=2))
                print(f"\n{Colors.DIM}User will be automatically approved{Colors.RESET}")
            else:
                print(f"{Colors.RED}❌ Not found in Pastebin{Colors.RESET}")
                print(f"{Colors.YELLOW}Add this request code using option 1{Colors.RESET}")
                
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print(f"{Colors.RED}Invalid choice{Colors.RESET}")


# ============================================
# Main Program
# ============================================

def main():
    """Main entry point"""
    print("\n" + "="*60)
    print(f"{Colors.CYAN}{Colors.BOLD}  IntraMirror OTP Sender{Colors.RESET}")
    print("="*60)
    
    # Initialize license manager
    license_manager = AutoLicenseManager(secret_word="naha")
    
    # Display license status
    if not license_manager.display_status():
        print(f"\n{Colors.RED}❌ Access Denied{Colors.RESET}")
        print(f"{Colors.YELLOW}Contact admin to get approved.{Colors.RESET}")
        return
    
    # ============================================
    # YOUR MAIN TOOL CODE HERE
    # ============================================
    print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 Access Granted! Running tool...{Colors.RESET}")
    
    # Show license info
    status = license_manager.get_license_status()
    print(f"\n{Colors.CYAN}📋 License Info:{Colors.RESET}")
    print(f"  User: {status.get('user_info', 'Unknown')}")
    print(f"  Device: {status.get('device_model', 'Unknown')}")
    if status.get('remaining_days') is not None:
        print(f"  Remaining: {status['remaining_days']} days")
    if status.get('expiry_date'):
        print(f"  Expires: {status['expiry_date']}")
    
    # ============================================
    # YOUR ACTUAL OTP SENDER CODE HERE
    # ============================================
    
    print(f"\n{Colors.GREEN}✅ Tool ready!{Colors.RESET}")
    # ... your OTP sending code ...


if __name__ == "__main__":
    try:
        # Check if running as admin
        if len(sys.argv) > 1 and sys.argv[1] == "--admin":
            admin_cli()
        else:
            main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️ Interrupted{Colors.RESET}")
        sys.exit(0)
