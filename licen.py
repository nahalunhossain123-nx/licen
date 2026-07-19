#!/usr/bin/env python3
"""
IntraMirror License System - Pastebin Approval
Demo Version
"""

import hashlib
import json
import os
import subprocess
import platform
import requests
from datetime import datetime, timedelta
import sys
import re

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

class PastebinLicenseManager:
    def __init__(self, secret_word="naha"):
        """
        Initialize with Pastebin URL
        
        IMPORTANT: Update this URL with your Pastebin raw URL
        """
        self.secret_word = secret_word
        self.license_file = os.path.expanduser("~/.intramirror_license.json")
        
        # ========================================
        # UPDATE THIS WITH YOUR PASTEBIN RAW URL
        # ========================================
        # Your Pastebin: https://pastebin.com/ez5BKAbT
        # Raw URL format: https://pastebin.com/raw/ez5BKAbT
        self.pastebin_url = "https://pastebin.com/raw/ez5BKAbT"
        # ========================================
        
        self.load_license()
    
    def get_device_id(self):
        """Get unique device ID from Android/Termux"""
        try:
            # Try Android ID
            result = subprocess.run(
                ['settings', 'get', 'secure', 'android_id'],
                capture_output=True, text=True
            )
            android_id = result.stdout.strip()
            if android_id:
                return f"ANDROID:{android_id}"
        except:
            pass
        
        # Fallback: Use system info
        try:
            import uuid
            return f"FALLBACK:{uuid.getnode()}"
        except:
            return f"FALLBACK:{hashlib.md5(platform.node().encode()).hexdigest()[:16]}"
    
    def get_device_model(self):
        """Get device model"""
        try:
            result = subprocess.run(
                ['getprop', 'ro.product.model'],
                capture_output=True, text=True
            )
            model = result.stdout.strip()
            if model:
                return model
        except:
            pass
        
        return platform.node() or "Unknown_Device"
    
    def generate_request_code(self):
        """
        Generate request code for approval
        
        Formula: SHA256(Device_ID + Device_Model + Secret_Word + Timestamp)
        """
        device_id = self.get_device_id()
        device_model = self.get_device_model()
        timestamp = datetime.now().strftime("%Y%m%d")
        
        raw_data = f"{device_id}|{device_model}|{self.secret_word}|{timestamp}"
        hash_obj = hashlib.sha256(raw_data.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Take first 12 chars for request code
        request_code = f"REQ-{hash_hex[:12].upper()}"
        
        return {
            "request_code": request_code,
            "device_id": device_id,
            "device_model": device_model,
            "timestamp": timestamp
        }
    
    def check_pastebin_approval(self, request_code):
        """
        Check if request code exists in Pastebin
        
        Format in Pastebin:
        REQ-XXXX-XXXX|APP-XXXX-XXXX|2024-03-15|user@email.com
        """
        try:
            # Fetch from Pastebin
            response = requests.get(self.pastebin_url, timeout=10)
            
            if response.status_code != 200:
                print(f"{Colors.YELLOW}⚠️ Could not reach Pastebin{Colors.RESET}")
                return None
            
            content = response.text.strip()
            
            # Check if content is JSON
            try:
                data = json.loads(content)
                # JSON format
                approved_devices = data.get("approved_devices", {})
                for key, approval in approved_devices.items():
                    if approval.get("request_code") == request_code:
                        return approval
            except:
                # Plain text format
                lines = content.strip().split('\n')
                for line in lines:
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
            print(f"{Colors.YELLOW}⚠️ Could not check approval: {e}{Colors.RESET}")
            return None
    
    def generate_approval_code(self, request_code):
        """
        Generate approval code from request code
        
        NOTE: This is for ADMIN use only - not in user's tool
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        raw_data = f"{request_code}|{self.secret_word}|{timestamp}"
        hash_obj = hashlib.sha256(raw_data.encode())
        hash_hex = hash_obj.hexdigest()
        
        approval_code = f"APP-{hash_hex[:12].upper()}"
        return approval_code
    
    def validate_approval(self, request_code, approval_code):
        """
        Validate approval code against Pastebin
        """
        # Check Pastebin for approval
        approval_data = self.check_pastebin_approval(request_code)
        
        if not approval_data:
            return {
                "status": "error",
                "message": "❌ Not approved! Contact admin."
            }
        
        # Check approval code matches
        expected_approval = approval_data.get("approval_code")
        if not expected_approval or approval_code != expected_approval:
            return {
                "status": "error",
                "message": "❌ Invalid approval code"
            }
        
        # Check expiry
        expiry_date = approval_data.get("expiry_date")
        if expiry_date:
            try:
                expiry = datetime.fromisoformat(expiry_date)
                if datetime.now() > expiry:
                    return {
                        "status": "error",
                        "message": "❌ License expired on " + expiry_date
                    }
            except:
                pass
        
        # Save license
        license_data = {
            "request_code": request_code,
            "approval_code": approval_code,
            "device_id": self.get_device_id(),
            "device_model": self.get_device_model(),
            "activated_date": datetime.now().isoformat(),
            "expiry_date": expiry_date,
            "status": "active",
            "user_info": approval_data.get("user_info", "Unknown")
        }
        
        self.save_license(license_data)
        
        return {
            "status": "success",
            "message": "✅ License activated successfully!",
            "data": license_data
        }
    
    def save_license(self, license_data):
        """Save license locally"""
        try:
            with open(self.license_file, 'w') as f:
                json.dump(license_data, f, indent=2)
            os.chmod(self.license_file, 0o600)
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
    
    def check_license(self):
        """
        Check if license is valid
        """
        if not self.license_data:
            self.load_license()
        
        if not self.license_data:
            return {
                "status": "not_activated",
                "message": "No license found."
            }
        
        if self.license_data.get("status") != "active":
            return {
                "status": "error",
                "message": "License not active"
            }
        
        # Check device
        device_id = self.get_device_id()
        if self.license_data.get("device_id") != device_id:
            return {
                "status": "error",
                "message": "License for different device"
            }
        
        # Check expiry
        expiry = self.license_data.get("expiry_date")
        if expiry:
            try:
                expiry_date = datetime.fromisoformat(expiry)
                if datetime.now() > expiry_date:
                    self.license_data["status"] = "expired"
                    self.save_license(self.license_data)
                    return {
                        "status": "expired",
                        "message": "License expired"
                    }
                remaining = (expiry_date - datetime.now()).days
            except:
                remaining = None
        else:
            remaining = None
        
        return {
            "status": "success",
            "message": "License valid",
            "remaining_days": remaining,
            "expiry_date": expiry,
            "user_info": self.license_data.get("user_info")
        }
    
    def request_approval_flow(self):
        """
        Complete approval flow for user
        """
        print("\n" + "="*60)
        print(f"{Colors.CYAN}{Colors.BOLD}  🔐 IntraMirror License - Activation{Colors.RESET}")
        print("="*60)
        
        # Check existing license
        license_status = self.check_license()
        if license_status["status"] == "success":
            print(f"\n{Colors.GREEN}✅ License already active!{Colors.RESET}")
            print(f"{Colors.DIM}User: {license_status.get('user_info', 'Unknown')}{Colors.RESET}")
            if license_status.get("remaining_days") is not None:
                print(f"⏰ Remaining: {license_status['remaining_days']} days")
            if license_status.get("expiry_date"):
                print(f"📅 Expires: {license_status['expiry_date']}")
            return True
        
        if license_status["status"] == "expired":
            print(f"\n{Colors.RED}❌ License expired on {license_status.get('expiry_date')}{Colors.RESET}")
            print(f"{Colors.YELLOW}Please contact admin for extension.{Colors.RESET}")
            return False
        
        # Generate request code
        request_info = self.generate_request_code()
        request_code = request_info["request_code"]
        
        print(f"\n{Colors.YELLOW}📋 Step 1: Get Your Request Code{Colors.RESET}")
        print(f"{Colors.DIM}Device Information:{Colors.RESET}")
        print(f"  📱 Model: {request_info['device_model']}")
        print(f"  🆔 ID: {request_info['device_id'][:20]}...")
        
        print(f"\n{Colors.CYAN}🔑 Your Request Code:{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}{request_code}{Colors.RESET}")
        
        print(f"\n{Colors.YELLOW}📤 Step 2: Send to Admin{Colors.RESET}")
        print(f"  {Colors.DIM}Copy this request code:{Colors.RESET}")
        print(f"  {Colors.DIM}Send to admin via WhatsApp/Telegram/Email{Colors.RESET}")
        print(f"  {Colors.DIM}Wait for approval code{Colors.RESET}")
        
        print(f"\n{Colors.YELLOW}📥 Step 3: Enter Approval Code{Colors.RESET}")
        print(f"{Colors.DIM}After admin adds you to Pastebin:{Colors.RESET}")
        
        approval_code = input(f"\n{Colors.GREEN}Enter approval code: {Colors.RESET}").strip().upper()
        
        if not approval_code:
            print(f"{Colors.RED}❌ No code entered.{Colors.RESET}")
            return False
        
        # Validate
        result = self.validate_approval(request_code, approval_code)
        
        if result["status"] == "success":
            print(f"\n{Colors.GREEN}{result['message']}{Colors.RESET}")
            if result["data"].get("expiry_date"):
                print(f"📅 Expires: {result['data']['expiry_date']}")
            if result["data"].get("user_info"):
                print(f"👤 User: {result['data']['user_info']}")
            return True
        else:
            print(f"\n{Colors.RED}{result['message']}{Colors.RESET}")
            return False


# ============================================
# Admin Tool (For YOU)
# ============================================

class AdminPastebinTool:
    def __init__(self, secret_word="naha"):
        self.secret_word = secret_word
    
    def generate_approval_code(self, request_code):
        """Generate approval code from request code"""
        timestamp = datetime.now().strftime("%Y%m%d")
        raw_data = f"{request_code}|{self.secret_word}|{timestamp}"
        hash_obj = hashlib.sha256(raw_data.encode())
        hash_hex = hash_obj.hexdigest()
        approval_code = f"APP-{hash_hex[:12].upper()}"
        return approval_code
    
    def generate_approval_entry(self, request_code, device_id, device_model, 
                                user_info, duration_days=30):
        """Generate approval entry for Pastebin"""
        approval_code = self.generate_approval_code(request_code)
        expiry_date = (datetime.now() + timedelta(days=duration_days)).strftime("%Y-%m-%d")
        
        # Plain text format for Pastebin
        entry_text = f"{request_code}|{approval_code}|{expiry_date}|{user_info}"
        
        # JSON format (alternative)
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
            lines.append(entry)
        return '\n'.join(lines)
    
    def generate_pastebin_json(self, entries):
        """Generate JSON content for Pastebin"""
        approvals = {
            "approved_devices": {},
            "last_updated": datetime.now().isoformat()
        }
        
        for i, entry in enumerate(entries, 1):
            approvals["approved_devices"][f"device_{i}"] = entry
        
        return json.dumps(approvals, indent=2)


def admin_cli():
    print("="*60)
    print(f"{Colors.CYAN}{Colors.BOLD}  🔐 Admin Approval Tool - Pastebin{Colors.RESET}")
    print("="*60)
    print(f"{Colors.DIM}Pastebin URL: https://pastebin.com/ez5BKAbT{Colors.RESET}")
    print("="*60)
    
    admin = AdminPastebinTool(secret_word="naha")
    entries = []  # Store entries for bulk generation
    
    while True:
        print("\n" + "="*40)
        print("Options:")
        print("1. Generate single approval code")
        print("2. Create approval entry (add to Pastebin)")
        print("3. Generate Pastebin content (plain text)")
        print("4. Generate Pastebin content (JSON)")
        print("5. Show all entries")
        print("6. Test license check")
        print("7. Exit")
        print("="*40)
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == "1":
            request_code = input("Enter request code: ").strip().upper()
            approval_code = admin.generate_approval_code(request_code)
            print(f"\n{Colors.GREEN}✅ Approval Code: {approval_code}{Colors.RESET}")
            print(f"{Colors.YELLOW}📤 Send this to user{Colors.RESET}")
        
        elif choice == "2":
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
            print(f"🔑 Approval Code: {entry_json['approval_code']}")
            print(f"📤 Send approval code to user")
            print(f"\n{Colors.YELLOW}📋 Add this to Pastebin:{Colors.RESET}")
            print(f"{Colors.DIM}{entry_text}{Colors.RESET}")
        
        elif choice == "3":
            if not entries:
                print(f"{Colors.YELLOW}⚠️ No entries yet. Create some first.{Colors.RESET}")
                continue
            
            content = admin.generate_pastebin_content(
                [f"{e['request_code']}|{e['approval_code']}|{e['expiry_date']}|{e['user_info']}" 
                 for e in entries]
            )
            
            print("\n" + "="*60)
            print(f"{Colors.CYAN}📄 PASTEBIN CONTENT (Plain Text){Colors.RESET}")
            print("="*60)
            print(content)
            print("="*60)
            print(f"\n{Colors.YELLOW}📋 Copy this entire content to: https://pastebin.com/ez5BKAbT{Colors.RESET}")
        
        elif choice == "4":
            if not entries:
                print(f"{Colors.YELLOW}⚠️ No entries yet. Create some first.{Colors.RESET}")
                continue
            
            json_content = admin.generate_pastebin_json(entries)
            
            print("\n" + "="*60)
            print(f"{Colors.CYAN}📄 PASTEBIN CONTENT (JSON){Colors.RESET}")
            print("="*60)
            print(json_content)
            print("="*60)
            print(f"\n{Colors.YELLOW}📋 Copy this entire content to: https://pastebin.com/ez5BKAbT{Colors.RESET}")
        
        elif choice == "5":
            if not entries:
                print(f"{Colors.YELLOW}⚠️ No entries yet.{Colors.RESET}")
                continue
            
            print("\n📋 All Entries:")
            for i, entry in enumerate(entries, 1):
                print(f"\n{i}. {entry['user_info']}")
                print(f"   Request: {entry['request_code']}")
                print(f"   Approval: {entry['approval_code']}")
                print(f"   Expires: {entry['expiry_date']}")
        
        elif choice == "6":
            print("\n🔍 Testing license check...")
            test_manager = PastebinLicenseManager()
            test_code = input("Enter request code to check: ").strip().upper()
            result = test_manager.check_pastebin_approval(test_code)
            if result:
                print(f"{Colors.GREEN}✅ Found in Pastebin!{Colors.RESET}")
                print(json.dumps(result, indent=2))
            else:
                print(f"{Colors.RED}❌ Not found in Pastebin{Colors.RESET}")
        
        elif choice == "7":
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
    print(f"{Colors.CYAN}{Colors.BOLD}  IntraMirror OTP Sender - License Demo{Colors.RESET}")
    print("="*60)
    
    # Initialize license manager
    license_manager = PastebinLicenseManager(secret_word="naha")
    
    # Check license flow
    if not license_manager.request_approval_flow():
        print(f"\n{Colors.RED}❌ Cannot continue without valid license{Colors.RESET}")
        print(f"{Colors.YELLOW}Please contact admin to get approval.{Colors.RESET}")
        return
    
    # ============================================
    # YOUR MAIN TOOL CODE HERE
    # ============================================
    print(f"\n{Colors.GREEN}{Colors.BOLD}✅ License Verified! Running tool...{Colors.RESET}")
    print(f"{Colors.DIM}This is where your OTP sender logic would go{Colors.RESET}")
    
    # Example: Show user info
    license_data = license_manager.load_license()
    if license_data:
        print(f"\n{Colors.CYAN}📋 License Info:{Colors.RESET}")
        print(f"  User: {license_data.get('user_info', 'Unknown')}")
        print(f"  Device: {license_data.get('device_model', 'Unknown')}")
        if license_data.get('expiry_date'):
            print(f"  Expires: {license_data['expiry_date']}")
    
    # ============================================
    # YOUR ACTUAL TOOL CODE HERE
    # ============================================
    
    print(f"\n{Colors.GREEN}🎉 Tool ready to use!{Colors.RESET}")


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
