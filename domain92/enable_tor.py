#!/usr/bin/env python3
"""
Simple script to enable Tor in domain92
Run this if you want to use Tor for anonymity
"""

def enable_tor():
    """Enable Tor in the domain92 configuration"""
    try:
        with open('domain92/__main__.py', 'r') as f:
            content = f.read()
        
        # Replace the Tor setting
        content = content.replace('use_tor = False  # Changed to False to avoid connection issues', 'use_tor = True  # Tor enabled for anonymity')
        
        with open('domain92/__main__.py', 'w') as f:
            f.write(content)
        
        print("✅ Tor has been enabled in domain92!")
        print("Make sure you have Tor running locally on port 9050")
        print("You can download Tor from: https://www.torproject.org/")
        
    except Exception as e:
        print(f"❌ Error enabling Tor: {e}")

def disable_tor():
    """Disable Tor in the domain92 configuration"""
    try:
        with open('domain92/__main__.py', 'r') as f:
            content = f.read()
        
        # Replace the Tor setting
        content = content.replace('use_tor = True  # Tor enabled for anonymity', 'use_tor = False  # Tor disabled to avoid connection issues')
        
        with open('domain92/__main__.py', 'w') as f:
            f.write(content)
        
        print("✅ Tor has been disabled in domain92!")
        print("The script will now use direct connection")
        
    except Exception as e:
        print(f"❌ Error disabling Tor: {e}")

if __name__ == "__main__":
    print("Domain92 Tor Configuration Tool")
    print("=" * 30)
    print("1. Enable Tor (requires Tor running on port 9050)")
    print("2. Disable Tor (use direct connection)")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        enable_tor()
    elif choice == "2":
        disable_tor()
    elif choice == "3":
        print("Exiting...")
    else:
        print("Invalid choice. Please run the script again.")
