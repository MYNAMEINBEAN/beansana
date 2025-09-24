from PIL import Image
from io import BytesIO
import time
import requests as req
import re
import random
import string
from art import *
import freedns
import sys
import argparse
import pytesseract
import copy
from PIL import ImageFilter
import os
import platform
from importlib.metadata import version
import lolpython
import time
import json
import pickle
from datetime import datetime, timedelta
import socket
from stem import Signal
from stem.control import Controller
import subprocess
import ctypes
import sys

# Configuration class - will be populated by user input
class Config:
    def __init__(self):
        self.ip = None
        self.use_tor = True  # Automatically use Tor for anonymity
        self.auto = True
        self.webhook = "none"
        self.proxy = False
        self.silent = False
        self.outfile = "domainlist.txt"
        self.type = "A"
        self.pages = "0-230"  # Scrape all available pages
        self.subdomains = None
        self.number = None
        self.cache_file = "domain_cache.json"
        self.cache_duration_hours = 24  # Cache expires after 24 hours

# Admin and Tor management functions
def is_admin():
    """Check if script is running with administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def require_admin():
    """
    Compatibility stub kept for code that expects this function.
    It no longer exits — instead it returns whether admin rights are present.
    """
    if not is_admin():
        print("\n" + "="*60)
        print("               ⚠️  ADMIN NOT PRESENT  ⚠️")
        print("="*60)
        print("This script no longer requires Administrator privileges to run.")
        print("However, automatic Tor service startup (if requested) requires admin rights on Windows.")
        print("If you want Tor to be auto-started by this script, run it as Administrator.")
        print("="*60)
        # Do not exit; caller can decide what to do
        return False
    return True

def cleanup_tor():
    """Clean up Tor process on script exit"""
    try:
        checkprint("🧹 Cleaning up Tor processes...")
        # Do not kill Tor automatically since user might want to keep it running
        if check_tor_process():
            checkprint("ℹ️ Tor is still running in background")
            checkprint("💡 To stop Tor manually: taskkill /F /IM tor.exe")
    except:
        pass

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n🛑 Script interrupted by user")
    cleanup_tor()
    print("👋 Goodbye!")
    sys.exit(0)

# Set up signal handling for graceful exit
import signal
signal.signal(signal.SIGINT, signal_handler)

def check_tor_process():
    """Check if Tor process is already running"""
    try:
        # Check if tor.exe process is running
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq tor.exe'],
                                capture_output=True, text=True, timeout=10)
        return 'tor.exe' in result.stdout
    except:
        return False

def start_tor_service():
    """Automatically start Tor service in a new Command Prompt window"""
    checkprint("🚀 Starting Tor service in new window...")
    
    # Check if Tor is already running
    if check_tor_process():
        checkprint("ℹ️ Tor process already running, checking connection...")
        time.sleep(2)  # Give it a moment
        return check_tor_connection()
    
    # Check if Tor directory exists
    tor_path = "C:\\tor"
    tor_exe = os.path.join(tor_path, "tor.exe")
    torrc_file = os.path.join(tor_path, "torrc")
    
    if not os.path.exists(tor_exe):
        checkprint(f"❌ Tor executable not found at: {tor_exe}")
        checkprint("💡 Please run the setup script first to install Tor")
        return False
    
    if not os.path.exists(torrc_file):
        checkprint(f"❌ Tor configuration not found at: {torrc_file}")
        checkprint("💡 Please run the setup script first to configure Tor")
        return False
    
    try:
        # Create command to run Tor in new window
        cmd_command = f'start "Tor Service" /D "C:\\tor" cmd /k "echo Starting Tor Service... && echo Keep this window open while using the script! && echo. && tor.exe -f torrc"'
        
        checkprint(f"🔧 Opening new Command Prompt window for Tor...")
        checkprint("💡 A new window will open - keep it running!")
        
        # Execute the command to open new window with Tor
        subprocess.run(cmd_command, shell=True, check=True)
        
        checkprint("⏳ Waiting for Tor to initialize in the new window...")
        checkprint("💡 You should see a new Command Prompt window with Tor starting")
        
        # Wait for Tor to start (up to 60 seconds)
        max_wait = 60
        for attempt in range(max_wait):
            time.sleep(1)
            
            if check_tor_connection():
                checkprint(f"✅ Tor started successfully! (took {attempt + 1} seconds)")
                checkprint("💡 Keep the Tor Command Prompt window open!")
                return True
            
            # Show progress every 10 seconds
            if (attempt + 1) % 10 == 0:
                checkprint(f"⏳ Still waiting for Tor... ({attempt + 1}/{max_wait} seconds)")
                if attempt + 1 == 30:
                    checkprint("💡 Make sure the Tor window opened and is connecting...")
        
        checkprint("❌ Tor failed to start within 60 seconds")
        checkprint("💡 Check the Tor Command Prompt window for error messages")
        return False
        
    except subprocess.CalledProcessError as e:
        checkprint(f"❌ Failed to open Tor window: {e}")
        return False
    except Exception as e:
        checkprint(f"❌ Failed to start Tor: {e}")
        return False

# Cache management functions
def save_domain_cache(domainlist, domainnames, cache_file):
    """Save domain data to cache file"""
    try:
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "domainlist": domainlist,
            "domainnames": domainnames,
            "total_domains": len(domainlist)
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        print(f"✅ Saved {len(domainlist)} domains to cache: {cache_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to save cache: {e}")
        return False

def load_domain_cache(cache_file, cache_duration_hours):
    """Load domain data from cache if it exists and is recent"""
    try:
        if not os.path.exists(cache_file):
            print("🔍 No cache file found")
            return None, None, False
        
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        # Check if cache is still valid
        cache_time = datetime.fromisoformat(cache_data["timestamp"])
        current_time = datetime.now()
        age_hours = (current_time - cache_time).total_seconds() / 3600
        
        if age_hours > cache_duration_hours:
            print(f"⏰ Cache is {age_hours:.1f} hours old (max: {cache_duration_hours}h) - will refresh")
            return None, None, False
        
        domainlist = cache_data["domainlist"]
        domainnames = cache_data["domainnames"]
        
        print(f"✅ Loaded {len(domainlist)} domains from cache (age: {age_hours:.1f}h)")
        return domainlist, domainnames, True
        
    except Exception as e:
        print(f"❌ Failed to load cache: {e}")
        return None, None, False

def should_refresh_cache():
    """Ask user if they want to refresh the cache"""
    while True:
        response = input("\n🔄 Do you want to refresh the domain cache? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("❌ Please enter 'y' or 'n'")

def check_cache_status(cache_file, cache_duration_hours):
    """Check and display cache status"""
    if not os.path.exists(cache_file):
        print("🔍 No cache file exists - will scrape fresh data")
        return False
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        cache_time = datetime.fromisoformat(cache_data["timestamp"])
        current_time = datetime.now()
        age_hours = (current_time - cache_time).total_seconds() / 3600
        
        print(f"\n📊 Cache status:")
        print(f"   📅 Last updated: {cache_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   ⏰ Age: {age_hours:.1f} hours")
        print(f"   🔗 Domains cached: {cache_data.get('total_domains', 'unknown')}")
        print(f"   📄 Cache file: {cache_file}")
        
        if age_hours > cache_duration_hours:
            print(f"   ❌ Cache expired (max age: {cache_duration_hours}h)")
            return False
        else:
            print(f"   ✅ Cache is valid (expires in {cache_duration_hours - age_hours:.1f}h)")
            return True
            
    except Exception as e:
        print(f"❌ Error reading cache: {e}")
        return False

def get_external_ip(use_tor=False):
    """Get current external IP - can use Tor or direct connection with retry logic"""
    max_attempts = 3
    
    for attempt in range(1, max_attempts + 1):
        try:
            if use_tor and args.use_tor and hasattr(client, 'session') and client.session.proxies:
                # Use Tor proxy for IP check
                response = client.session.get("https://httpbin.org/ip", timeout=20)
            else:
                # Use direct connection for IP check
                response = req.get("https://httpbin.org/ip", timeout=10)
                
            if response.status_code == 200:
                return response.json().get('origin', 'unknown')
                
        except Exception as e:
            if attempt < max_attempts:
                time.sleep(2)  # Brief wait before retry
                continue
            
            # Try fallback service on last attempt
            try:
                if use_tor and args.use_tor and hasattr(client, 'session') and client.session.proxies:
                    # Fallback with Tor
                    response = client.session.get("https://icanhazip.com", timeout=20)
                else:
                    # Fallback direct
                    response = req.get("https://icanhazip.com", timeout=10)
                    
                if response.status_code == 200:
                    return response.text.strip()
            except:
                pass
                
    return "unknown"

# Tor Functions
def check_tor_connection():
    """Check if Tor SOCKS proxy is available"""
    try:
        sock = socket.socket()
        sock.settimeout(5)
        result = sock.connect_ex(('127.0.0.1', 9050))
        sock.close()
        
        if result == 0:
            checkprint("✅ Tor SOCKS proxy (port 9050) is available")
            return True
        else:
            checkprint("❌ Tor SOCKS proxy (port 9050) is not available")
            return False
    except Exception as e:
        checkprint(f"❌ Error checking Tor SOCKS proxy: {e}")
        return False

def debug_tor_circuits():
    """Debug function to show Tor circuit information"""
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()
            circuits = controller.get_circuits()
            
            built_circuits = [c for c in circuits if c.status == 'BUILT']
            checkprint(f"📊 Tor circuits: {len(circuits)} total, {len(built_circuits)} built")
            
            if built_circuits:
                # Show a few circuit details
                for i, circuit in enumerate(built_circuits[:3]):  # Show first 3
                    path = " → ".join([f"{hop.fingerprint[:8]}({hop.nickname})" for hop in circuit.path])
                    checkprint(f"🔄 Circuit {i+1}: {path}")
            
    except Exception as e:
        checkprint(f"⚠️ Could not get circuit info: {e}")

def change_tor_identity():
    """Change Tor identity with improved IP checking and retry logic"""
    try:
        # Get current IP through Tor
        old_ip = get_external_ip(use_tor=True)
        checkprint(f"🔄 Changing Tor identity (current Tor IP: {old_ip})...")
        
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()  # Uses cookie authentication
            
            # Show current circuit info for debugging
            old_circuits = controller.get_circuits()
            old_built = len([c for c in old_circuits if c.status == 'BUILT'])
            checkprint(f"📊 Current circuits: {len(old_circuits)} total, {old_built} built")
            
            # Force close existing circuits for faster change
            checkprint("🔄 Closing existing circuits...")
            for circuit in controller.get_circuits():
                try:
                    controller.close_circuit(circuit.id)
                except:
                    pass  # Ignore errors closing circuits
            
            # Send new identity signal
            controller.signal(Signal.NEWNYM)
            
            # Wait for the change with longer timeout
            wait_time = controller.get_newnym_wait()
            checkprint(f"⏳ Waiting {wait_time + 10} seconds for new circuits to build...")
            time.sleep(wait_time + 10)  # More time for circuit building
            
            # Try multiple times to get a new IP
            max_attempts = 5
            for attempt in range(1, max_attempts + 1):
                checkprint(f"🔍 Checking new IP (attempt {attempt}/{max_attempts})...")
                new_ip = get_external_ip(use_tor=True)
                
                if new_ip != old_ip and new_ip != "unknown" and old_ip != "unknown":
                    checkprint(f"✅ Tor identity changed successfully: {old_ip} → {new_ip}")
                    return True
                elif attempt < max_attempts:
                    checkprint(f"⏳ IP unchanged ({old_ip} → {new_ip}), waiting 8 more seconds...")
                    time.sleep(8)
                    
                    # Send another NEWNYM signal if needed
                    if attempt >= 3:
                        checkprint("🔄 Sending additional identity change signal...")
                        controller.signal(Signal.NEWNYM)
                        time.sleep(5)
            
            # If we get here, IP didn't change after all attempts
            final_ip = get_external_ip(use_tor=True)
            checkprint(f"⚠️ IP appears unchanged after {max_attempts} attempts: {old_ip} → {final_ip}")
            
            # Check if we're actually using different circuits even with same exit IP
            new_circuits = controller.get_circuits()
            new_built = len([c for c in new_circuits if c.status == 'BUILT'])
            
            if new_built > 0:
                checkprint(f"💡 {new_built} new circuits built - identity change successful")
                checkprint("💡 Same exit IP is normal with limited exit nodes")
                debug_tor_circuits()  # Show circuit details
                return True
            else:
                checkprint("⚠️ No new circuits detected - identity change may have failed")
                debug_tor_circuits()  # Show circuit details for debugging
                return False
                    
    except Exception as e:
        checkprint(f"❌ Failed to change Tor identity: {e}")
        checkprint("💡 Continuing with current identity...")
        return False

def setup_tor_connection():
    """Enhanced Tor setup with automatic startup if allowed"""
    checkprint("🔒 Setting up Tor connection for anonymity...")
    
    # Check if Tor services are available
    if not check_tor_connection():
        checkprint("🔍 Tor SOCKS proxy not available - attempting auto-start...")
        
        # Try to start Tor automatically only if allowed (admin)
        if allow_tor_auto_start:
            if start_tor_service():
                checkprint("✅ Tor auto-start successful!")
            else:
                checkprint("❌ Tor auto-start failed!")
                checkprint("💡 Troubleshooting options:")
                checkprint("   1. Check if Tor is installed in C:\\tor\\")
                checkprint("   2. Run the setup script to install Tor")
                checkprint("   3. Manually start Tor with: cd C:\\tor && tor.exe -f torrc")
                checkprint("   4. Check Windows Firewall settings")
                return False
        else:
            checkprint("⚠️ Auto-start of Tor is disabled because the script is not running as Administrator.")
            checkprint("💡 Start Tor manually (e.g. run tor.exe) or run this script as Administrator to enable auto-start.")
            return False
    
    try:
        proxies = {
            "http": "socks5h://127.0.0.1:9050",
            "https": "socks5h://127.0.0.1:9050",
        }
        client.session.proxies.update(proxies)
        checkprint("✅ Tor proxy configured successfully!")
        return True
    except Exception as e:
        checkprint(f"❌ Failed to set Tor proxy: {e}")
        return False

def test_tor_connection():
    """Test Tor connection with IP verification"""
    checkprint("🔍 Testing Tor connection...")
    
    try:
        # Test direct connection first
        direct_ip = get_external_ip(use_tor=False)
        checkprint(f"🌐 Direct connection IP: {direct_ip}")
        
        # Test Tor connection
        if client.session.proxies:
            tor_ip = get_external_ip(use_tor=True)
            checkprint(f"🔒 Tor connection IP: {tor_ip}")
            
            if tor_ip != direct_ip and tor_ip != "unknown" and direct_ip != "unknown":
                checkprint("✅ Tor is working! Your IP is being masked.")
                return True
            else:
                checkprint("⚠️ Tor might not be working - IPs appear the same")
                return False
        else:
            checkprint("❌ No Tor proxy configured")
            return False
            
    except Exception as e:
        checkprint(f"❌ Tor connection test failed: {e}")
        return False

# Function to get user inputs
def get_user_inputs(config, force_refresh):
    print("\n" + "="*50)
    print("DOMAIN MAKER - TOR EDITION")
    print("="*50)
    
    # Check cache status first
    cache_valid = check_cache_status(config.cache_file, config.cache_duration_hours)
    user_force_refresh = False
    
    # Only ask about cache refresh if command line didn't force it and cache is valid
    if cache_valid and not force_refresh:
        user_force_refresh = should_refresh_cache()
        if not user_force_refresh:
            print("📋 Will use cached domain data")
    elif force_refresh:
        print("🔄 Cache refresh forced via command line")
        user_force_refresh = True
    
    # Get IP address
    while True:
        ip_input = input("\nEnter the IP address you want to register domains for: ").strip()
        if ip_input and len(ip_input.split('.')) == 4:
            try:
                # Basic IP validation
                parts = ip_input.split('.')
                for part in parts:
                    if not (0 <= int(part) <= 255):
                        raise ValueError
                break
            except ValueError:
                print("❌ Invalid IP address format. Please enter a valid IP address (e.g., 192.168.1.1)")
        else:
            print("❌ Invalid IP address format. Please enter a valid IP address (e.g., 192.168.1.1)")
    
    # Get subdomain preference
    print("\nSubdomain options:")
    print("1. Use random subdomains")
    print("2. Use bean names from GitHub")
    print("3. Enter custom subdomains (comma-separated)")
    
    while True:
        subdomain_choice = input("\nChoose subdomain option (1-3): ").strip()
        if subdomain_choice == "1":
            subdomain_setting = "random"
            break
        elif subdomain_choice == "2":
            subdomain_setting = "bean"
            break
        elif subdomain_choice == "3":
            custom_subdomains = input("Enter subdomains separated by commas: ").strip()
            if custom_subdomains:
                subdomain_setting = custom_subdomains
                break
            else:
                print("❌ Please enter at least one subdomain")
        else:
            print("❌ Please enter 1, 2, or 3")
    
    # Get number of links
    while True:
        try:
            num_links = int(input("\nHow many domain links do you want to create? "))
            if num_links > 0:
                break
            else:
                print("❌ Please enter a positive number")
        except ValueError:
            print("❌ Please enter a valid number")
    
    # Ask about Tor usage
    print("\nAnonymity options:")
    print("1. Use Tor (recommended for anonymity)")
    print("2. Use direct connection (faster but no anonymity)")
    
    while True:
        anonymity_choice = input("\nChoose anonymity option (1-2): ").strip()
        if anonymity_choice == "1":
            use_tor = True
            print("🔒 Tor will be used for anonymity")
            print("🚀 Tor will auto-start if not running and this script has admin rights")
            break
        elif anonymity_choice == "2":
            use_tor = False
            print("🌐 Direct connection will be used")
            break
        else:
            print("❌ Please enter 1 or 2")
    
    final_force_refresh = force_refresh or user_force_refresh
    accounts_needed = (num_links + 4) // 5  # Each account makes 5 domains
    
    print(f"\n✅ Configuration complete!")
    print(f"   📍 IP Address: {ip_input}")
    print(f"   🏷️  Subdomains: {subdomain_setting}")
    print(f"   🔗 Links to create: {num_links}")
    print(f"   👥 Accounts needed: {accounts_needed}")
    print(f"   🔗 Domains per account: 5")
    if use_tor:
        ip_changes = num_links // 25  # IP changes every 25 domains
        print(f"   🔄 Tor identity changes: {ip_changes} (every 25 domains)")
        print(f"   🔒 Anonymity: Tor enabled")
    else:
        print(f"   🌐 Anonymity: Direct connection")
    print(f"   📊 Domain pages: 0-230 (cached: {not final_force_refresh})")
    print(f"\n🚀 Starting domain creation process...\n")
    
    return ip_input, subdomain_setting, num_links, final_force_refresh, use_tor

# Create a mock args object to maintain compatibility
class MockArgs:
    def __init__(self, config):
        self.ip = config.ip
        self.use_tor = config.use_tor
        self.auto = config.auto
        self.webhook = config.webhook
        self.proxy = config.proxy
        self.silent = config.silent
        self.outfile = config.outfile
        self.type = config.type
        self.pages = config.pages
        self.subdomains = config.subdomains
        self.number = config.number
        self.single_tld = None

# Initialize configuration
config = Config()

# Determine whether auto-start of Tor is allowed (requires admin)
allow_tor_auto_start = is_admin()
if not allow_tor_auto_start:
    print("⚠️ Running without Administrator privileges. Tor auto-start will be disabled.")

# NOTE: The script no longer exits when not run as admin. It will continue, but auto-start features
# that require admin rights are disabled. If you need Tor to be auto-started by the script, run as admin.

# Initialize force_refresh as a global variable
force_refresh = False

# Check for command line arguments first
if len(sys.argv) > 1:
    if sys.argv[1] in ['--refresh-cache', '-r']:
        print("🔄 Force refresh flag detected - will refresh domain cache")
        force_refresh = True
    elif sys.argv[1] in ['--help', '-h']:
        print("\nDomain Maker - Tor Edition:")
        print("python script.py           - Normal run with cache")
        print("python script.py -r        - Force refresh domain cache")
        print("python script.py --help    - Show this help")
        print("\nNotes:")
        print("• Administrator privileges are NOT required to run this script.")
        print("• Automatic Tor startup (start/stop) requires Administrator privileges on Windows.")
        print("• Tor files should be installed in C:\\tor\\ if you want auto-start.")
        print("• Python dependencies: pip install stem pysocks")
        print("\nFeatures:")
        print("• Changes IP via Tor if available")
        print("• 5 domains per account")
        print("• Optional anonymity with Tor")
        sys.exit(0)

# Get user inputs
user_ip, user_subdomains, user_number, user_force_refresh, use_tor = get_user_inputs(config, force_refresh)

# Use command line force_refresh if set, otherwise use user's choice
if not force_refresh:
    force_refresh = user_force_refresh

# Update config with user inputs
config.ip = user_ip
config.subdomains = user_subdomains
config.number = user_number
config.use_tor = use_tor

args = MockArgs(config)

ip = args.ip
if not args.silent:
    lolpython.lol_py(text2art("domainmaker"))
    print("made with <3 by Cbass92")
    if args.use_tor:
        print("🔒 Tor Mode: ENABLED")
        if allow_tor_auto_start:
            print("💡 Tor will auto-start if not running and admin rights are present")
        else:
            print("💡 Tor auto-start disabled (no admin) — start Tor manually if needed")
    else:
        print("🌐 Direct Mode: ENABLED")
        print("💡 No anonymity - using your real IP address")
    time.sleep(2)

def checkprint(input_text):
    global args
    if not args.silent:
        print(input_text)

client = freedns.Client()
checkprint("client initialized")

def get_data_path():
    script_dir = os.path.dirname(__file__)
    checkprint("checking os")
    if platform.system() == "Windows":
        filename = os.path.join(script_dir, "data", "windows", "tesseract")
    elif platform.system() == "Linux":
        filename = os.path.join(script_dir, "data", "tesseract-linux")
    else:
        print(
            "Unsupported OS. This could cause errors with captcha solving. Please install tesseract manually."
        )
        return None
    os.environ["TESSDATA_PREFIX"] = os.path.join(script_dir, "data")
    return filename

path = get_data_path()
if path:
    pytesseract.pytesseract.tesseract_cmd = path
    checkprint(f"Using tesseract executable: {path}")
else:
    checkprint("No valid tesseract file for this OS.")

domainlist = []
domainnames = []
checkprint("getting ip list")
iplist = req.get(
    "https://raw.githubusercontent.com/sebastian-92/byod-ip/refs/heads/master/byod.json"
).text
iplist = eval(iplist)

# Load bean names from GitHub
def load_bean_names():
    try:
        response = req.get("https://raw.githubusercontent.com/MYNAMEINBEAN/all-names/refs/heads/main/for-void.txt")
        if response.status_code == 200:
            bean_names = response.text.strip().split(',')
            checkprint(f"Loaded {len(bean_names)} bean names from GitHub")
            return bean_names
        else:
            checkprint("Failed to load bean names from GitHub, using random subdomains")
            return None
    except Exception as e:
        checkprint(f"Error loading bean names: {e}, using random subdomains")
        return None

# Load bean names at startup if needed
bean_names = None
if args.subdomains == "bean":
    bean_names = load_bean_names()

def test_connection():
    """Test if we can connect to freedns.afraid.org with retry logic"""
    checkprint("🔍 Testing connection to freedns.afraid.org...")
    
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            checkprint(f"🌐 Connection attempt {attempt}/{max_attempts}...")
            
            # Use the same session as the client to test with Tor if enabled
            if args.use_tor and client.session.proxies:
                checkprint("🔒 Testing connection through Tor...")
                response = client.session.get("https://freedns.afraid.org", timeout=20)
            else:
                checkprint("🌐 Testing direct connection...")
                response = req.get("https://freedns.afraid.org", timeout=15)
            
            if response.status_code == 200:
                checkprint("✅ Connection test successful!")
                
                # Show current IP
                if args.use_tor and client.session.proxies:
                    current_ip = get_external_ip(use_tor=True)
                    checkprint(f"🔒 Connected through Tor! External IP: {current_ip}")
                else:
                    current_ip = get_external_ip(use_tor=False)
                    checkprint(f"🌐 Direct connection! External IP: {current_ip}")
                return True
            else:
                checkprint(f"⚠️ Connection test returned status code: {response.status_code}")
                
        except Exception as e:
            checkprint(f"⚠️ Connection attempt {attempt} failed: {e}")
            
            if attempt < max_attempts:
                if args.use_tor:
                    checkprint("💡 This might be a Tor connection issue - trying again...")
                    checkprint("💡 Tor connections can be slower and less reliable")
                else:
                    checkprint("💡 Network issue detected - retrying...")
                    
                checkprint(f"⏳ Waiting 5 seconds before retry...")
                time.sleep(5)
            
    # All attempts failed
    checkprint(f"❌ All {max_attempts} connection attempts failed")
    if args.use_tor:
        checkprint("💡 This is common with Tor - the script should still work")
        checkprint("💡 Make sure Tor is running and has established circuits")
    else:
        checkprint("💡 Check your internet connection")
        
    return False

def getpagelist(arg):
    arg = arg.strip()
    if "," in arg:
        arglist = arg.split(",")
        pagelist = []
        for item in arglist:
            if "-" in item:
                sublist = item.split("-")
                if len(sublist) == 2:
                    sp = int(sublist[0])
                    ep = int(sublist[1])
                    if sp < 0 or sp > ep:
                        checkprint("Invalid page range: " + item)
                        sys.exit()
                    pagelist.extend(range(sp, ep + 1))
                else:
                    checkprint("Invalid page range: " + item)
                    sys.exit()
        return pagelist
    elif "-" in arg:
        pagelist = []
        sublist = arg.split("-")
        if len(sublist) == 2:
            sp = int(sublist[0])
            ep = int(sublist[1])
            if sp < 0 or sp > ep:  # Allow starting from 0
                checkprint("Invalid page range: " + arg)
                sys.exit()
            pagelist.extend(range(sp, ep + 1))
        else:
            checkprint("Invalid page range: " + arg)
            sys.exit()
        return pagelist
    else:
        return [int(arg)]

def getdomains(arg):
    global domainlist, domainnames
    pages = getpagelist(arg)
    total_pages = len(pages)
    
    # Estimate time (roughly 0.5 seconds per page with delays)
    estimated_minutes = (total_pages * 0.5) / 60
    checkprint(f"🔍 Scraping {total_pages} pages (estimated time: {estimated_minutes:.1f} minutes)...")
    
    start_time = time.time()
    
    for i, sp in enumerate(pages):
        # Progress update every 10 pages and for first few pages
        if i % 10 == 0 or i < 5 or i == total_pages - 1:
            progress = ((i + 1) / total_pages) * 100
            elapsed = time.time() - start_time
            if i > 0:
                avg_time_per_page = elapsed / (i + 1)
                remaining_pages = total_pages - (i + 1)
                eta_seconds = remaining_pages * avg_time_per_page
                eta_minutes = eta_seconds / 60
                checkprint(f"📊 Progress: {i + 1}/{total_pages} pages ({progress:.1f}%) - ETA: {eta_minutes:.1f}min")
            else:
                checkprint(f"📊 Progress: {i + 1}/{total_pages} pages ({progress:.1f}%)")
        
        try:
            html = req.get(
                "https://freedns.afraid.org/domain/registry/?page="
                + str(sp)
                + "&sort=2&q=",
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Cache-Control": "max-age=0",
                    "Connection": "keep-alive",
                    "DNT": "1",
                    "Host": "freedns.afraid.org",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Upgrade-Insecure-Requests": "1",
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    "sec-ch-ua": '"Not;A=Brand";v="24", "Chromium";v="128"',
                    "sec-ch-ua-platform": "Linux",
                },
                timeout=10
            ).text
            
            pattern = r"<a href=\/subdomain\/edit\.php\?edit_domain_id=(\d+)>([\w.-]+)<\/a>(.+\..+)<td>public<\/td>"
            matches = re.findall(pattern, html)
            
            if matches:
                domainnames.extend([match[1] for match in matches])
                domainlist.extend([match[0] for match in matches])
            
            # Small delay to be respectful to the server
            time.sleep(0.1)
            
        except Exception as e:
            checkprint(f"❌ Error scraping page {sp}: {e}")
            continue
    
    elapsed_total = time.time() - start_time
    checkprint(f"✅ Scraping complete! Found {len(domainlist)} available domains in {elapsed_total/60:.1f} minutes")

def find_domain_id(domain_name):
    page = 1
    html = req.get(
        "https://freedns.afraid.org/domain/registry/?page="
        + str(page)
        + "&q="
        + domain_name,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "DNT": "1",
            "Host": "freedns.afraid.org",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not;A=Brand";v="24", "Chromium";v="128"',
                "sec-ch-ua-platform": "Linux",
        },
    ).text
    pattern = r"<a href=\/subdomain\/edit\.php\?edit_domain_id=([0-9]+)><font color=red>(?:.+\..+)<\/font><\/a>"
    matches = re.findall(pattern, html)
    if len(matches) > 0:
        checkprint(f"Found domain ID: {matches[0]}")
    else:
        raise Exception("Domain ID not found")
    return matches[0]

hookbool = False
webhook = ""
if args.subdomains not in ["random", "bean"] and args.subdomains:
    checkprint("Subdomains set to:")
    checkprint(args.subdomains.split(","))
checkprint("ready")

def getcaptcha():
    return Image.open(BytesIO(client.get_captcha()))

def denoise(img):
    imgarr = img.load()
    newimg = Image.new("RGB", img.size)
    newimgarr = newimg.load()
    dvs = []
    for y in range(img.height):
        for x in range(img.width):
            r = imgarr[x, y][0]
            g = imgarr[x, y][1]
            b = imgarr[x, y][2]
            if (r, g, b) == (255, 255, 255):
                newimgarr[x, y] = (r, g, b)
            elif ((r + g + b) / 3) == (112):
                newimgarr[x, y] = (255, 255, 255)
                dvs.append((x, y))
            else:
                newimgarr[x, y] = (0, 0, 0)

    backup = copy.deepcopy(newimg)
    backup = backup.load()
    for y in range(img.height):
        for x in range(img.width):
            if newimgarr[x, y] == (255, 255, 255):
                continue
            black_neighbors = 0
            for ny in range(max(0, y - 2), min(img.height, y + 2)):
                for nx in range(max(0, x - 2), min(img.width, x + 2)):
                    if backup[nx, ny] == (0, 0, 0):
                        black_neighbors += 1
            if black_neighbors <= 5:
                newimgarr[x, y] = (255, 255, 255)
    for x, y in dvs:
        black_neighbors = 0
        for ny in range(max(0, y - 2), min(img.height, y + 2)):
            for nx in range(max(0, x - 1), min(img.width, x + 1)):
                if newimgarr[nx, ny] == (0, 0, 0):
                    black_neighbors += 1
            if black_neighbors >= 5:
                newimgarr[x, y] = (0, 0, 0)
            else:
                newimgarr[x, y] = (255, 255, 255)
    width, height = newimg.size
    black_pixels = set()
    for y in range(height):
        for x in range(width):
            if newimgarr[x, y] == (0, 0, 0):
                black_pixels.add((x, y))

    for x, y in list(black_pixels):
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in black_pixels:
                newimgarr[nx, ny] = 0
    backup = copy.deepcopy(newimg)
    backup = backup.load()
    for y in range(img.height):
        for x in range(img.width):
            if newimgarr[x, y] == (255, 255, 255):
                continue
            black_neighbors = 0
            for ny in range(max(0, y - 2), min(img.height, y + 2)):
                for nx in range(max(0, x - 2), min(img.width, x + 2)):
                    if backup[nx, ny] == (0, 0, 0):
                        black_neighbors += 1
            if black_neighbors <= 6:
                newimgarr[x, y] = (255, 255, 255)
    return newimg

def solve(image):
    image = denoise(image)
    text = pytesseract.image_to_string(
        image.filter(ImageFilter.GaussianBlur(1))
        .convert("1")
        .filter(ImageFilter.RankFilter(3, 3)),
        config="-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ --psm 13 -l freednsocr",
    )
    text = text.strip().upper()
    checkprint("captcha solved: " + text)
    if len(text) != 5 and len(text) != 4:
        checkprint("captcha doesn't match correct pattern, trying different captcha")
        text = solve(getcaptcha())
    return text

def generate_random_string(length):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))

def login():
    while True:
        try:
            checkprint("getting captcha")
            image = getcaptcha()
            if args.auto:
                capcha = solve(image)
                checkprint("captcha solved (hopefully)")
            else:
                checkprint("showing captcha")
                image.show()
                capcha = input("Enter the captcha code: ")
            checkprint("generating email")
            stuff = req.get(
                "https://api.guerrillamail.com/ajax.php?f=get_email_address"
            ).json()
            email = stuff["email_addr"]
            checkprint("email address generated email:" + email)
            checkprint(email)
            checkprint("creating account")
            username = generate_random_string(13)
            client.create_account(
                capcha,
                generate_random_string(13),
                generate_random_string(13),
                username,
                "pegleg1234",
                email,
            )
            checkprint("activation email sent")
            checkprint("waiting for email")
            hasnotreceived = True
            while hasnotreceived:
                nerd = req.get(
                    "https://api.guerrillamail.com/ajax.php?f=check_email&seq=0&sid_token="
                    + str(stuff["sid_token"])
                ).json()

                if int(nerd["count"]) > 0:
                    checkprint("email received")
                    mail = req.get(
                        "https://api.guerrillamail.com/ajax.php?f=fetch_email&email_id="
                        + str(nerd["list"][0]["mail_id"])
                        + "&sid_token="
                        + str(stuff["sid_token"])
                    ).json()
                    match = re.search(r'\?([^">]+)"', mail["mail_body"])
                    if match:
                        checkprint("code found")
                        checkprint("verification code: " + match.group(1))
                        checkprint("activating account")
                        client.activate_account(match.group(1))
                        checkprint("accout activated")
                        time.sleep(1)
                        checkprint("attempting login")
                        client.login(email, "pegleg1234")
                        checkprint("login successful")
                        hasnotreceived = False
                    else:
                        checkprint(
                            "no match in email! you should generally never get this."
                        )
                        checkprint("error!")

                else:
                    checkprint("checked email")
                    time.sleep(2)
        except KeyboardInterrupt:
            sys.exit()
        except Exception as e:
            checkprint("Got error while creating account: " + repr(e))
            if "Connection" in str(e) or "SOCKS" in str(e):
                checkprint("Connection error detected - this might be a proxy/Tor issue")
                if args.use_tor:
                    checkprint("Disabling Tor and trying direct connection")
                    args.use_tor = False
                    client.session.proxies.clear()
                    checkprint("Retrying with direct connection...")
                    continue
                else:
                    checkprint("Already using direct connection, this might be a network issue")
                    checkprint("Waiting 10 seconds before retry...")
                    time.sleep(10)
                    continue
            elif args.use_tor:
                checkprint("attempting to change tor identity")
                try:
                    success = change_tor_identity()
                    if success:
                        checkprint("tor identity changed")
                    else:
                        checkprint("tor identity change failed, but continuing")
                except Exception as e:
                    checkprint("Got error while changing tor identity: " + repr(e))
                    continue
            continue
        else:
            break

def createlinks(number):
    """Create the specified number of links, creating a new account every 5 links and changing IP every 25 domains"""
    links_created = 0
    account_count = 1
    
    checkprint(f"\n🚀 Starting creation of {number} links...")
    checkprint(f"📊 Will create {(number + 4) // 5} accounts total")
    checkprint(f"🔗 Each account will create up to 5 domains")
    
    if args.use_tor:
        ip_changes = number // 25
        checkprint(f"🔒 Tor will change identity every 25 domains")
        if ip_changes > 0:
            checkprint(f"🔄 Expected {ip_changes} IP changes during this session")
    
    while links_created < number:
        # Check if we need to change IP (every 25 domains)
        if args.use_tor and links_created > 0 and links_created % 25 == 0:
            checkprint(f"\n🎯 Reached {links_created} domains - triggering IP change!")
            success = change_tor_identity()
            if not success:
                checkprint("⚠️ Identity change failed, but continuing...")
        
        # Create new account for every batch of 5 (or at the start)
        if links_created % 5 == 0:
            checkprint(f"\n👤 Creating account #{account_count}...")
            login()
            account_count += 1
        
        # Create domain
        current_account = account_count - 1
        domains_in_current_account = (links_created % 5) + 1
        checkprint(f"\n🔗 Creating link {links_created + 1}/{number} (Account #{current_account}, Domain {domains_in_current_account}/5)...")
        createdomain()
        links_created += 1
        
        # Progress update every 5 domains (end of each account) or at the end
        if links_created % 5 == 0 or links_created == number:
            accounts_completed = links_created // 5
            if links_created % 5 != 0:
                accounts_completed += 1
            
            checkprint(f"✅ Progress: {links_created}/{number} links created ({accounts_completed} accounts completed)")
            
            # Show next IP change info
            if args.use_tor and links_created < number:
                domains_until_next_ip_change = 25 - (links_created % 25)
                if domains_until_next_ip_change == 25:
                    domains_until_next_ip_change = 0
                
                if domains_until_next_ip_change == 0:
                    checkprint("🔄 Next domain will trigger an IP change!")
                else:
                    checkprint(f"📊 {domains_until_next_ip_change} more domains until next IP change")
    
    checkprint(f"\n🎉 Domain creation completed!")
    checkprint(f"📈 Final stats: {links_created} domains created using {account_count - 1} accounts")
    
    # Clean up on completion
    cleanup_tor()

def createmax():
    login()
    checkprint("logged in")
    checkprint("creating domains")
    createdomain()
    createdomain()
    createdomain()
    createdomain()
    createdomain()  # Added 5th domain

#!/usr/bin/env python3
import os, sys, argparse, random, requests as req

# === helper functions you already had ===
def checkprint(msg):
    print(msg)

def generate_random_string(length):
    return ''.join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(length))

# --- your arg parsing section (unchanged except outfile default kept) ---
parser = argparse.ArgumentParser()
parser.add_argument("--outfile", default="domainlist.txt", help="Where to save domain links")
parser.add_argument("--auto", action="store_true")
parser.add_argument("--single_tld")
parser.add_argument("--subdomains", default="random")
parser.add_argument("--type", default="A")
args = parser.parse_args()

# dummy placeholders for stuff your script loads (replace with your real ones)
domainlist = ["example.com", "example.net", "example.org"]
domainnames = domainlist
non_random_domain_id = domainlist[0]
bean_names = ["bean", "coolbean", "superbean"]
ip = "127.0.0.1"
hookbool = False
webhook = ""

# stub client object (replace with your real client.create_subdomain implementation)
class DummyClient:
    def create_subdomain(self, captcha, dtype, subdomain, tld, ip):
        checkprint(f"Created subdomain {subdomain}.{tld} -> {ip}")

client = DummyClient()

# stub captcha (replace with your getcaptcha/solve code)
def getcaptcha():
    return "dummy_image"

def solve(img):
    return "abcd"

# === patched createdomain function ===
def createdomain():
    while True:
        try:
            image = getcaptcha()
            if args.auto:
                capcha = solve(image)
                checkprint("captcha solved")
            else:
                checkprint("showing captcha")
                capcha = input("Enter the captcha code: ")

            if args.single_tld:
                random_domain_id = non_random_domain_id
            else:
                random_domain_id = random.choice(domainlist)

            # Determine subdomain based on user choice
            if args.subdomains == "random":
                subdomainy = generate_random_string(10)
            elif args.subdomains == "bean" and bean_names:
                subdomainy = random.choice(bean_names)
            elif args.subdomains not in ["random", "bean"]:
                subdomainy = random.choice(args.subdomains.split(","))
            else:
                subdomainy = generate_random_string(10)

            client.create_subdomain(capcha, args.type, subdomainy, random_domain_id, ip)
            tld = args.single_tld or random_domain_id
            full_domain = "http://" + subdomainy + "." + tld
            checkprint("domain created")
            checkprint("link: " + full_domain)

            # Write to original file
            with open(args.outfile, "a") as domainsdb:
                domainsdb.write("\n" + full_domain)

            # Also write to Downloads/domainscreated.txt
            downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(downloads_path, exist_ok=True)
            downloads_file = os.path.join(downloads_path, "domainscreated.txt")
            with open(downloads_file, "a") as f:
                f.write(full_domain + "\n")

            if hookbool:
                checkprint("notifying webhook")
                req.post(
                    webhook,
                    json={"content": f"Domain created:\n{full_domain}\n ip: {ip}"},
                )
                checkprint("webhook notified")
        except KeyboardInterrupt:
            sys.exit()
        except Exception as e:
            checkprint("Got error while creating domain: " + repr(e))
            continue
        else:
            break

# === run ===
if __name__ == "__main__":
    createdomain()

non_random_domain_id = None

def finddomains(pagearg, force_refresh=False):
    global domainlist, domainnames
    
    # Try to load from cache first
    if not force_refresh:
        cached_domainlist, cached_domainnames, cache_loaded = load_domain_cache(
            config.cache_file, config.cache_duration_hours
        )
        
        if cache_loaded:
            domainlist = cached_domainlist
            domainnames = cached_domainnames
            return
    
    # If no cache or force refresh, scrape fresh data
    checkprint("🌐 Scraping fresh domain data from freedns.afraid.org...")
    domainlist = []
    domainnames = []
    
    pages = pagearg.split(",")
    for page in pages:
        getdomains(page)
    
    # Save to cache after successful scraping
    if domainlist:
        save_domain_cache(domainlist, domainnames, config.cache_file)
    else:
        checkprint("⚠️ No domains found - cache not updated")

def init():
    global args, ip, iplist, webhook, hookbool, non_random_domain_id
    
    # Set IP from user input
    ip = args.ip
    checkprint(f"Using IP: {ip}")
    
    # Set webhook to none
    hookbool = False
    webhook = "none"
    checkprint("Webhook disabled")
    
    # Set proxy to false (using Tor instead)
    args.proxy = False
    checkprint("Proxy disabled, using Tor anonymity system" if args.use_tor else "Using direct connection")
    
    # Set auto captcha solving
    args.auto = True
    checkprint("Auto captcha solving enabled")
    
    # Set up Tor proxy with improved handling
    if args.use_tor:
        tor_success = setup_tor_connection()
        
        if tor_success:
            # Test the Tor connection
            if test_tor_connection():
                checkprint("🎉 Tor setup complete and working!")
            else:
                checkprint("⚠️ Tor setup complete but connection test failed")
                checkprint("💡 Will attempt to continue anyway...")
        else:
            checkprint("❌ Tor setup failed!")
            checkprint("🔄 Falling back to direct connection...")
            args.use_tor = False
            client.session.proxies.clear()
    else:
        checkprint("🌐 Using direct connection (no anonymity)")
        client.session.proxies.clear()
    
    # Final connection test
    if not test_connection():
        checkprint("❌ Final connection test failed!")
        checkprint("💡 This might cause issues, but continuing anyway...")
    else:
        checkprint("✅ Ready to proceed!")
    
    # Load domains (with caching)
    finddomains(args.pages, force_refresh)
    
    # Create the specified number of links
    if args.number:
        createlinks(args.number)

def chooseFrom(dictionary, message):
    checkprint(message)
    for i, key in enumerate(dictionary.keys()):
        checkprint(f"{i+1}. {key}")
    choice = int(input("Choose an option by number: "))
    return list(dictionary.keys())[choice - 1]

if __name__ == "__main__":
    try:
        init()
    except KeyboardInterrupt:
        print("\n\n🛑 Script interrupted by user")
        cleanup_tor()
        print("👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Script failed with error: {e}")
        cleanup_tor()
    finally:
        # Final cleanup
        cleanup_tor()
