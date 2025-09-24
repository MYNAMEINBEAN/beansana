#!/usr/bin/env python3
"""
Script to check if Tor is running and accessible
"""

import requests
import socket

def check_tor_port():
    """Check if Tor is listening on port 9050"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', 9050))
        sock.close()
        return result == 0
    except:
        return False

def test_tor_connection():
    """Test if we can actually connect through Tor"""
    try:
        proxies = {
            "http": "socks5h://127.0.0.1:9050",
            "https": "socks5h://127.0.0.1:9050",
        }
        response = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, data.get('origin', 'Unknown')
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    print("🔒 Tor Connection Checker")
    print("=" * 30)
    
    # Check if port is open
    print("🔍 Checking if Tor is listening on port 9050...")
    if check_tor_port():
        print("✅ Port 9050 is open - Tor service detected!")
    else:
        print("❌ Port 9050 is closed - Tor is not running")
        print("💡 To fix this:")
        print("   1. Download Tor Browser from https://www.torproject.org/")
        print("   2. Start Tor and make sure it's running")
        print("   3. Or install Tor service for your operating system")
        return
    
    # Test actual connection
    print("\n🌐 Testing connection through Tor...")
    success, result = test_tor_connection()
    
    if success:
        print("✅ Tor connection successful!")
        print(f"🌐 Your IP through Tor: {result}")
        print("🎉 You're ready to run domain92 with Tor!")
    else:
        print("❌ Tor connection failed!")
        print(f"💡 Error: {result}")
        print("💡 This might mean:")
        print("   - Tor is running but not properly configured")
        print("   - Firewall is blocking the connection")
        print("   - Tor needs to be restarted")

if __name__ == "__main__":
    main()
