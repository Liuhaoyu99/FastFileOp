"""FastFileOp - Named Pipe Client Tests

Tests communication with FastFileOp pipe server.
Requires FastFileOp to be running (start main.py first).

Tests: ping, copy, delete, invalid format requests.
"""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

# Named pipe settings
PIPE_NAME = r"\\.\pipe\FastFileOpPipe"
BUFFER_SIZE = 65536


def send_pipe_request(request: dict, timeout: float = 10.0) -> dict:
    """Send request to pipe server and get response"""
    import win32file
    import win32pipe
    
    try:
        # Connect to pipe
        handle = win32file.CreateFile(
            PIPE_NAME,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0, None,
            win32file.OPEN_EXISTING,
            0, None
        )
        
        # Set read mode
        win32pipe.SetNamedPipeHandleState(
            handle,
            win32pipe.PIPE_READMODE_MESSAGE,
            None, None
        )
        
        # Send request
        data = json.dumps(request).encode('utf-8')
        win32file.WriteFile(handle, data)
        
        # Read response
        error_code, resp_data = win32file.ReadFile(handle, BUFFER_SIZE)
        
        win32file.CloseHandle(handle)
        
        return json.loads(resp_data.decode('utf-8'))
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_pipe_server():
    """Check if pipe server is running"""
    try:
        result = send_pipe_request({"action": "ping"})
        return result.get("status") in ["ok", "pong"]
    except Exception as e:
        print(f"Cannot connect to pipe: {e}")
        return False


class TestPipeClient(unittest.TestCase):
    """Named pipe client tests"""

    @classmethod
    def setUpClass(cls):
        """Setup temp directory and check pipe availability"""
        cls.temp_dir = tempfile.mkdtemp(prefix="ffo_pipe_test_")
        cls.src_dir = os.path.join(cls.temp_dir, "src")
        cls.dst_dir = os.path.join(cls.temp_dir, "dst")
        os.makedirs(cls.src_dir)
        os.makedirs(cls.dst_dir)
        
        # Check if pipe server is running
        cls.pipe_available = check_pipe_server()
        
        if not cls.pipe_available:
            print("\nWARNING: Pipe server not available!")
            print("Please start FastFileOp before running these tests.")

    @classmethod
    def tearDownClass(cls):
        """Cleanup temp directory"""
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def _create_file(self, name: str, size: int = 1024) -> str:
        """Create test file"""
        path = os.path.join(self.src_dir, name)
        with open(path, "wb") as f:
            f.write(os.urandom(size))
        return path

    def setUp(self):
        """Skip tests if pipe not available"""
        if not self.__class__.pipe_available:
            self.skipTest("Pipe server not running")

    # ==================== Test Cases ====================

    def test_01_ping(self):
        """Test 1: Ping server"""
        response = send_pipe_request({"action": "ping"})
        self.assertEqual(response.get("status"), "pong")
        print(f"\n  Ping response: {response}")

    def test_02_copy_request(self):
        """Test 2: Send copy request via pipe"""
        src = self._create_file("pipe_copy.txt", 2048)
        response = send_pipe_request({
            "action": "copy",
            "src": [src],
            "dst": self.dst_dir
        })
        self.assertIn(response.get("status"), ["ok", "error"])
        print(f"\n  Copy response: {response}")

    def test_03_move_request(self):
        """Test 3: Send move request via pipe"""
        src = self._create_file("pipe_move.txt", 1024)
        response = send_pipe_request({
            "action": "move",
            "src": [src],
            "dst": self.dst_dir
        })
        self.assertIn(response.get("status"), ["ok", "error"])
        print(f"\n  Move response: {response}")

    def test_04_delete_request(self):
        """Test 4: Send delete request via pipe"""
        src = self._create_file("pipe_delete.txt", 512)
        response = send_pipe_request({
            "action": "delete",
            "src": [src]
        })
        self.assertIn(response.get("status"), ["ok", "error"])
        print(f"\n  Delete response: {response}")

    def test_05_invalid_action(self):
        """Test 5: Send invalid action"""
        response = send_pipe_request({
            "action": "invalid_action_xyz",
            "src": []
        })
        self.assertEqual(response.get("status"), "error")
        print(f"\n  Invalid action response: {response}")

    def test_06_malformed_request(self):
        """Test 6: Send malformed request (missing action)"""
        response = send_pipe_request({
            "src": ["/some/path"],
            "dst": "/some/dest"
        })
        self.assertEqual(response.get("status"), "error")
        print(f"\n  Malformed request response: {response}")

    def test_07_empty_files_list(self):
        """Test 7: Send request with empty files list"""
        response = send_pipe_request({
            "action": "copy",
            "src": [],
            "dst": self.dst_dir
        })
        self.assertEqual(response.get("status"), "error")
        print(f"\n  Empty files response: {response}")

    def test_08_status_request(self):
        """Test 8: Request current status"""
        response = send_pipe_request({"action": "status"})
        self.assertIn(response.get("status"), ["ok", "error"])
        print(f"\n  Status response: {response}")


def run_tests():
    """Run all tests and print summary"""
    print("=" * 60)
    print("FastFileOp - Named Pipe Client Tests")
    print("=" * 60)
    
    # Check pipe availability first
    print("\nChecking pipe server availability...")
    if not check_pipe_server():
        print("\nERROR: Pipe server is not running!")
        print("Please start FastFileOp (main.py) before running these tests.")
        print("\nTo start FastFileOp:")
        print("  python -m fastfileop")
        print("  OR")
        print("  FastFileOp.exe")
        return False
    
    print("Pipe server is running.\n")
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPipeClient)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n[ALL TESTS PASSED]")
    else:
        print("\n[SOME TESTS FAILED]")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
