#!/usr/bin/env python3
"""
Cleanup script to kill all test server processes and free up ports.
"""

from test_server_manager import cleanup_test_ports

def main():
    """Clean up all test ports used in the project."""
    print("Cleaning up test server ports...")
    
    # All ports used by test scripts
    test_ports = [
        8001,  # test_integration.py
        8002,  # final_test.py  
        8003,  # test_phase2_complete.py
        8004,  # test_api_with_rag.py
        8005,  # test_authentication.py
        8006,  # test_auth_simple.py
        8007,  # test_auth_working.py
        9000,  # test_api.py
    ]
    
    cleanup_test_ports(test_ports)
    print("Port cleanup complete!")

if __name__ == "__main__":
    main()