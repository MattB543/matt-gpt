#!/usr/bin/env python3
"""
Test Server Manager - Utility for managing test servers with proper cleanup.

This module provides a context manager for starting and stopping test servers
with automatic port cleanup and process management.
"""

import subprocess
import time
import psutil
import signal
import os
import requests
from contextlib import contextmanager
from typing import Optional, List
import atexit


class TestServerManager:
    """Manages test server lifecycle with proper cleanup."""
    
    def __init__(self):
        self.active_processes: List[subprocess.Popen] = []
        # Register cleanup on exit
        atexit.register(self.cleanup_all)
    
    def find_process_using_port(self, port: int) -> Optional[psutil.Process]:
        """Find process using a specific port."""
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                connections = proc.info.get('connections', [])
                if connections:
                    for conn in connections:
                        if hasattr(conn, 'laddr') and conn.laddr.port == port:
                            return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return None
    
    def kill_port(self, port: int) -> bool:
        """Kill any process using the specified port."""
        print(f"Checking for processes on port {port}...")
        proc = self.find_process_using_port(port)
        if proc:
            try:
                print(f"Found process {proc.pid} ({proc.name()}) using port {port}")
                proc.terminate()
                proc.wait(timeout=5)
                print(f"Successfully terminated process on port {port}")
                return True
            except (psutil.TimeoutExpired, psutil.NoSuchProcess, psutil.AccessDenied):
                try:
                    proc.kill()
                    print(f"Force killed process on port {port}")
                    return True
                except:
                    print(f"Failed to kill process on port {port}")
                    return False
        else:
            print(f"No process found on port {port}")
            return True
    
    def start_server(self, port: int, timeout: int = 10) -> subprocess.Popen:
        """Start a FastAPI server on the specified port with proper cleanup."""
        # First, clean up any existing process on this port
        self.kill_port(port)
        
        print(f"Starting server on port {port}...")
        process = subprocess.Popen(
            ["poetry", "run", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Track the process for cleanup
        self.active_processes.append(process)
        
        # Wait for server to be ready
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"http://127.0.0.1:{port}/health", timeout=1)
                if response.status_code == 200:
                    print(f"Server ready on port {port}")
                    return process
            except requests.exceptions.RequestException:
                pass
            time.sleep(0.5)
        
        # If we get here, server didn't start properly
        self.stop_server(process)
        raise RuntimeError(f"Server failed to start on port {port} within {timeout} seconds")
    
    def stop_server(self, process: subprocess.Popen):
        """Stop a server process gracefully."""
        if process in self.active_processes:
            self.active_processes.remove(process)
        
        if process.poll() is None:  # Process is still running
            try:
                process.terminate()
                process.wait(timeout=5)
                print("Server terminated gracefully")
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                print("Server force killed")
    
    def cleanup_all(self):
        """Clean up all active processes."""
        print("Cleaning up all active test servers...")
        for process in self.active_processes[:]:  # Copy list to avoid modification during iteration
            self.stop_server(process)
        self.active_processes.clear()


# Global instance for easy usage
server_manager = TestServerManager()


@contextmanager
def test_server(port: int, timeout: int = 10):
    """Context manager for running a test server."""
    process = None
    try:
        process = server_manager.start_server(port, timeout)
        yield process
    finally:
        if process:
            server_manager.stop_server(process)


def cleanup_test_ports(ports: List[int]):
    """Clean up multiple ports at once."""
    print(f"Cleaning up ports: {ports}")
    for port in ports:
        server_manager.kill_port(port)


if __name__ == "__main__":
    # Test the server manager
    print("Testing server manager...")
    
    # Test common ports used in tests
    test_ports = [8001, 8002, 8003, 8004, 8005, 8006, 8007, 9000]
    cleanup_test_ports(test_ports)
    
    # Test starting and stopping a server
    with test_server(8999) as server:
        print("Server is running, testing health endpoint...")
        response = requests.get("http://127.0.0.1:8999/health")
        print(f"Health check: {response.status_code}")
    
    print("Test completed - server should be cleaned up")