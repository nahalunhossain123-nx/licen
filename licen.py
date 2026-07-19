#!/usr/bin/env python3
"""
NXTools License Tester - Check if a request code is approved
"""

import requests
from datetime import datetime
import sys

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

def check_license(request_code, pastebin_url="https://pastebin.com/raw/ez5BKAbT"):
    """
    Check if a request code exists in Pastebin
    
    Format: TOOL|REQUEST|APPROVAL|EXPIRY|USER
    """
    try:
        response = requests.get(pastebin_url, timeout=10)
        if response.status_code != 200:
            return {"status": "error", "message": "Could not reach Pastebin"}
        
        content = response.text.strip()
        if not content:
            return {"status": "error", "message": "Pastebin is empty"}
        
        # Search for the request code
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('|')
            if len(parts) >= 5:
                tool, req, app, expiry, user = parts[:5]
                if req == request_code:
                    return {
                        "status": "found",
                        "tool": tool,
                        "request_code": req,
                        "approval_code": app,
                        "expiry_date": expiry,
                        "user_info": user
                    }
        
        return {"status": "not_found", "message": f"Request code {request_code} not found"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

def main():
    print("\n" + "="*60)
    print(f"{Colors.CYAN}{Colors.BOLD}  🔐 NXTools License Checker{Colors.RESET}")
    print("="*60)
    print(f"{Colors.DIM}Check if a request code is approved in Pastebin{Colors.RESET}")
    print("="*60)
    
    # Get request code from user
    print(f"\n{Colors.YELLOW}📝 Enter request code to check:{Colors.RESET}")
    print(f"{Colors.DIM}Example: REQ-0B4C060D0576{Colors.RESET}")
    
    request_code = input(f"\n{Colors.GREEN}➜ {Colors.RESET}").strip().upper()
    
    if not request_code:
        print(f"\n{Colors.RED}❌ No code entered{Colors.RESET}")
        return
    
    # Check
    print(f"\n{Colors.DIM}🔍 Checking Pastebin...{Colors.RESET}")
    result = check_license(request_code)
    
    print("\n" + "="*60)
    
    if result["status"] == "found":
        print(f"{Colors.GREEN}{Colors.BOLD}✅ LICENSE FOUND!{Colors.RESET}")
        print("="*60)
        print(f"{Colors.CYAN}📋 License Details:{Colors.RESET}")
        print(f"  {Colors.DIM}Tool:{Colors.RESET}       {result['tool']}")
        print(f"  {Colors.DIM}User:{Colors.RESET}       {result['user_info']}")
        print(f"  {Colors.DIM}Request:{Colors.RESET}    {result['request_code']}")
        print(f"  {Colors.DIM}Approval:{Colors.RESET}   {result['approval_code']}")
        print(f"  {Colors.DIM}Expires:{Colors.RESET}    {result['expiry_date']}")
        
        # Check if expired
        try:
            expiry = datetime.fromisoformat(result['expiry_date'])
            now = datetime.now()
            if now > expiry:
                print(f"  {Colors.RED}Status:{Colors.RESET}     {Colors.RED}❌ EXPIRED{Colors.RESET}")
                days = (now - expiry).days
                print(f"  {Colors.DIM}Expired:{Colors.RESET}    {days} days ago")
            else:
                days = (expiry - now).days
                print(f"  {Colors.GREEN}Status:{Colors.RESET}     {Colors.GREEN}✅ ACTIVE{Colors.RESET}")
                print(f"  {Colors.DIM}Remaining:{Colors.RESET}   {days} days")
        except:
            print(f"  {Colors.YELLOW}Status:{Colors.RESET}     {Colors.YELLOW}⚠️ UNKNOWN (invalid date){Colors.RESET}")
        
        print("="*60)
        print(f"{Colors.GREEN}🎉 This license is valid!{Colors.RESET}")
        
    elif result["status"] == "not_found":
        print(f"{Colors.RED}{Colors.BOLD}❌ NOT FOUND{Colors.RESET}")
        print("="*60)
        print(f"{Colors.RED}Request code {request_code} is not approved{Colors.RESET}")
        print(f"\n{Colors.YELLOW}💡 To approve this user:{Colors.RESET}")
        print(f"  1. Open {Colors.CYAN}license_manager.html{Colors.RESET}")
        print(f"  2. Enter the request code")
        print(f"  3. Copy to {Colors.CYAN}https://pastebin.com/ez5BKAbT{Colors.RESET}")
        print("="*60)
        
    elif result["status"] == "error":
        print(f"{Colors.RED}{Colors.BOLD}❌ ERROR{Colors.RESET}")
        print("="*60)
        print(f"{Colors.RED}{result['message']}{Colors.RESET}")
        print(f"\n{Colors.YELLOW}💡 Check:{Colors.RESET}")
        print(f"  • Internet connection")
        print(f"  • Pastebin URL: {Colors.CYAN}https://pastebin.com/ez5BKAbT{Colors.RESET}")
        print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️ Interrupted{Colors.RESET}")
        sys.exit(0)
