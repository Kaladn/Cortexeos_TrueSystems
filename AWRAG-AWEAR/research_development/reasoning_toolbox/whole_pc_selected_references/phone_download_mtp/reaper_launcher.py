#!/usr/bin/env python3
"""
Reaper Guardian Launcher
Main entry point for CortexOS Zero Trust Security

Usage:
    python3 reaper_launcher.py [options]

Designed by Lee Mercey for CortexOS Protection
"""

import os
import sys
import argparse
import signal
from pathlib import Path

# Add core to path
sys.path.append(str(Path(__file__).parent / 'core'))

from reaper_guardian import ReaperGuardian

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print("\n🛑 Reaper Guardian shutdown requested...")
    sys.exit(0)

def main():
    """Main launcher for Reaper Guardian."""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Reaper Guardian - Zero Trust Security for CortexOS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 reaper_launcher.py                    # Start with default settings
    python3 reaper_launcher.py --test             # Run security tests
    python3 reaper_launcher.py --no-cortexos      # Start without CortexOS
    python3 reaper_launcher.py --simulate-threat  # Test threat response
        """
    )
    
    parser.add_argument('--test', action='store_true',
                       help='Run security system tests')
    parser.add_argument('--no-cortexos', action='store_true',
                       help='Start without launching CortexOS')
    parser.add_argument('--simulate-threat', action='store_true',
                       help='Simulate security threat for testing')
    parser.add_argument('--config', type=str,
                       help='Path to configuration file')
    parser.add_argument('--cortexos-path', type=str,
                       help='Path to CortexOS executable')
    
    args = parser.parse_args()
    
    # Display banner
    print_banner()
    
    try:
        # Create configuration
        config = create_config(args)
        
        # Run tests if requested
        if args.test:
            run_security_tests()
            return
        
        # Create and start Reaper Guardian
        reaper = ReaperGuardian(config)
        
        # Initialize security components
        if not reaper.initialize_security_components():
            print("❌ Failed to initialize security components")
            return 1
        
        # Simulate threat if requested
        if args.simulate_threat:
            print("🧪 Running threat simulation...")
            reaper.simulate_threat()
            return
        
        # Start monitoring
        if not reaper.start_monitoring():
            print("❌ Failed to start monitoring")
            return 1
        
        # Run interactive mode
        run_interactive_mode(reaper)
        
        # Cleanup
        reaper.stop_monitoring()
        print("\n✅ Reaper Guardian stopped successfully")
        return 0
        
    except KeyboardInterrupt:
        print("\n🛑 Reaper Guardian interrupted by user")
        return 0
    except Exception as e:
        print(f"❌ Reaper Guardian error: {e}")
        return 1

def print_banner():
    """Print Reaper Guardian banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    🛡️  REAPER GUARDIAN  🛡️                    ║
║                                                              ║
║              Zero Trust Cognitive-Hardware Security          ║
║                     for CortexOS Protection                  ║
║                                                              ║
║                  Designed by Lee Mercey                      ║
╚══════════════════════════════════════════════════════════════╝

🔐 Features:
   • Hardware Event Monitoring (USB, Network, Bluetooth)
   • Cognitive User Authentication (Behavioral Patterns)
   • Immediate Lockdown on Threats
   • Forensic Event Logging
   • Daily Rotating Passphrases
   • Zero Trust Architecture

🚀 Initializing security systems...
"""
    print(banner)

def create_config(args):
    """Create configuration from command line arguments."""
    config = {
        'hardware_monitoring': True,
        'cognitive_authentication': True,
        'immediate_lockdown': True,
        'cortexos_auto_start': not args.no_cortexos,
        'forensic_logging': True,
        'emergency_override': True
    }
    
    # Set CortexOS path if provided
    if args.cortexos_path:
        config['cortexos_path'] = args.cortexos_path
    
    return config

def run_security_tests():
    """Run comprehensive security system tests."""
    print("🧪 Running Reaper Guardian Security Tests")
    print("=" * 60)
    
    try:
        # Test hardware monitoring
        print("\n1. Testing Hardware Event Monitor...")
        from modules.hardware_event_monitor import test_hardware_monitor
        test_hardware_monitor()
        
        # Test cognitive authentication
        print("\n2. Testing Cognitive Authenticator...")
        from modules.cognitive_authenticator import test_cognitive_authenticator
        test_cognitive_authenticator()
        
        # Test integration
        print("\n3. Testing Reaper Guardian Integration...")
        reaper = ReaperGuardian()
        
        if reaper.initialize_security_components():
            print("✅ Security components initialized")
        else:
            print("❌ Security component initialization failed")
            return
        
        # Test threat simulation
        print("\n4. Testing Threat Response...")
        reaper.simulate_threat("USB_CHANGE")
        
        print("\n✅ All security tests completed successfully!")
        print("🛡️ Reaper Guardian is ready for deployment")
        
    except Exception as e:
        print(f"❌ Security test failed: {e}")

def run_interactive_mode(reaper):
    """Run interactive command mode."""
    print("\n✅ Reaper Guardian is now protecting your system")
    print("🔍 Hardware monitoring active")
    print("🧠 Cognitive authentication ready")
    print("🛡️ Zero Trust security engaged")
    
    print("\n" + "="*60)
    print("REAPER GUARDIAN - INTERACTIVE MODE")
    print("="*60)
    print("Commands:")
    print("  status      - Show system status")
    print("  test        - Simulate security threat")
    print("  unlock      - Manual unlock (if locked)")
    print("  users       - Show authenticated users")
    print("  events      - Show security events")
    print("  help        - Show this help")
    print("  quit        - Stop Reaper Guardian")
    print("="*60)
    
    while True:
        try:
            command = input("\n🛡️ Reaper> ").strip().lower()
            
            if command in ['quit', 'exit', 'q']:
                break
            elif command == 'status':
                show_status(reaper)
            elif command == 'test':
                run_threat_test(reaper)
            elif command == 'unlock':
                handle_unlock(reaper)
            elif command == 'users':
                show_users(reaper)
            elif command == 'events':
                show_events(reaper)
            elif command in ['help', 'h']:
                show_help()
            elif command == '':
                continue
            else:
                print(f"❌ Unknown command: {command}")
                print("Type 'help' for available commands")
                
        except KeyboardInterrupt:
            print("\nUse 'quit' to exit")
        except EOFError:
            break

def show_status(reaper):
    """Show system status."""
    import json
    status = reaper.get_system_status()
    
    print("\n🔍 SYSTEM STATUS")
    print("-" * 30)
    print(f"System Locked: {'🔐 YES' if status['system_locked'] else '✅ NO'}")
    print(f"Lockdown Active: {'🚨 YES' if status['lockdown_active'] else '✅ NO'}")
    print(f"CortexOS Running: {'✅ YES' if status['cortexos_running'] else '❌ NO'}")
    print(f"Hardware Monitoring: {'✅ ACTIVE' if status['hardware_monitoring'] else '❌ INACTIVE'}")
    print(f"Cognitive Auth: {'✅ ACTIVE' if status['cognitive_auth'] else '❌ INACTIVE'}")
    print(f"Authenticated Users: {len(status['authenticated_users'])}")
    print(f"Security Events: {status['security_events']}")
    print(f"Uptime: {status['uptime']}")

def run_threat_test(reaper):
    """Run threat simulation test."""
    print("\n🧪 THREAT SIMULATION TEST")
    print("-" * 30)
    print("Available threat types:")
    print("  1. USB_CHANGE")
    print("  2. NETWORK_CHANGE")
    print("  3. BLUETOOTH_CHANGE")
    
    try:
        choice = input("Select threat type (1-3): ").strip()
        
        threat_map = {
            '1': 'USB_CHANGE',
            '2': 'NETWORK_CHANGE',
            '3': 'BLUETOOTH_CHANGE'
        }
        
        if choice in threat_map:
            threat_type = threat_map[choice]
            print(f"🚨 Simulating {threat_type} threat...")
            reaper.simulate_threat(threat_type)
        else:
            print("❌ Invalid choice")
            
    except Exception as e:
        print(f"❌ Threat test error: {e}")

def handle_unlock(reaper):
    """Handle manual unlock request."""
    if reaper.system_locked:
        print("\n🔐 System is locked - starting authentication...")
        reaper._start_authentication_challenge()
    else:
        print("\n✅ System is not locked")

def show_users(reaper):
    """Show authenticated users."""
    users = reaper.authenticated_users
    
    print("\n👥 AUTHENTICATED USERS")
    print("-" * 30)
    
    if users:
        for username, info in users.items():
            print(f"User: {username}")
            print(f"  Authenticated: {info['authenticated_at']}")
            print(f"  Session Active: {'✅ YES' if info['session_active'] else '❌ NO'}")
    else:
        print("No authenticated users")

def show_events(reaper):
    """Show security events."""
    events = reaper.security_events
    
    print("\n📊 SECURITY EVENTS")
    print("-" * 30)
    
    if events:
        for i, event in enumerate(events[-10:], 1):  # Show last 10 events
            print(f"{i}. {event['type']} - {event['timestamp']}")
            if 'event' in event and 'forensic_trace_id' in event['event']:
                print(f"   Trace ID: {event['event']['forensic_trace_id']}")
    else:
        print("No security events recorded")

def show_help():
    """Show help information."""
    help_text = """
🛡️ REAPER GUARDIAN COMMANDS

status      Show current system status including lock state,
            monitoring status, and authenticated users

test        Simulate security threats to test system response
            (USB, Network, Bluetooth device changes)

unlock      Manually unlock system if locked due to security event
            Requires cognitive authentication + daily passphrase

users       Show list of currently authenticated users and their
            session information

events      Show recent security events with forensic trace IDs
            for audit and investigation purposes

help        Show this help information

quit        Stop Reaper Guardian and exit (also: exit, q)

🔐 SECURITY FEATURES:
• Hardware monitoring detects device changes in real-time
• Cognitive authentication uses behavioral patterns
• Immediate lockdown on any hardware threat
• Forensic logging for all security events
• Daily rotating passphrases for enhanced security
"""
    print(help_text)

if __name__ == "__main__":
    sys.exit(main())

