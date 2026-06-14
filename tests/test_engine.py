"""FastFileOp - FileEngine Unit Tests

Tests FileEngine copy/move/delete/pause/resume/cancel/error handling.
Uses temp directories, no dependencies on other components.
"""

import os
import sys
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastfileop.engine import FileEngine, OpState


class TestFileEngine(unittest.TestCase):
    """FileEngine unit tests - 10 test cases"""

    def setUp(self):
        """Create temp directories"""
        self.temp_dir = tempfile.mkdtemp(prefix="ffo_engine_test_")
        self.src_dir = os.path.join(self.temp_dir, "src")
        self.dst_dir = os.path.join(self.temp_dir, "dst")
        os.makedirs(self.src_dir)
        os.makedirs(self.dst_dir)
        self.engine = FileEngine(buffer_size=64*1024*1024, max_workers=4)
        self.test_results = []

    def tearDown(self):
        """Cleanup temp directories"""
        self.engine = None
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_file(self, name: str, size: int = 1024) -> str:
        """Create test file with random content"""
        path = os.path.join(self.src_dir, name)
        with open(path, "wb") as f:
            f.write(os.urandom(size))
        return path

    def _verify_file(self, path: str, expected_size: int = None) -> bool:
        """Verify file exists and optionally check size"""
        if not os.path.exists(path):
            return False
        if expected_size is not None:
            return os.path.getsize(path) == expected_size
        return True

    # ==================== Test Cases ====================

    def test_01_copy_single_file(self):
        """Test 1: Copy single file"""
        src = self._create_file("single.txt", 4096)
        self.engine.copy([src], self.dst_dir)
        
        dst = os.path.join(self.dst_dir, "single.txt")
        self.assertTrue(self._verify_file(dst, 4096), "File not copied correctly")
        
        # Verify content integrity
        with open(src, "rb") as f1, open(dst, "rb") as f2:
            self.assertEqual(f1.read(), f2.read(), "Content mismatch")

    def test_02_copy_multiple_files(self):
        """Test 2: Copy multiple files"""
        files = [self._create_file(f"file{i}.dat", 1024 * (i+1)) for i in range(5)]
        self.engine.copy(files, self.dst_dir)
        
        for i in range(5):
            dst = os.path.join(self.dst_dir, f"file{i}.dat")
            self.assertTrue(self._verify_file(dst, 1024 * (i+1)), f"File {i} not copied")

    def test_03_copy_nested_directory(self):
        """Test 3: Copy directory with nested structure"""
        # Create nested structure
        subdir = os.path.join(self.src_dir, "level1", "level2")
        os.makedirs(subdir)
        self._create_file("root.txt", 512)
        self._create_file("level1/mid.txt", 512)
        with open(os.path.join(subdir, "deep.txt"), "wb") as f:
            f.write(b"deep content")
        
        self.engine.copy([self.src_dir], self.dst_dir)
        
        # Verify structure preserved
        self.assertTrue(os.path.exists(os.path.join(self.dst_dir, "src", "root.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.dst_dir, "src", "level1", "mid.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.dst_dir, "src", "level1", "level2", "deep.txt")))

    def test_04_move_file(self):
        """Test 4: Move file (cut-paste simulation)"""
        src = self._create_file("move_me.txt", 2048)
        content = open(src, "rb").read()
        
        self.engine.move([src], self.dst_dir)
        
        dst = os.path.join(self.dst_dir, "move_me.txt")
        self.assertTrue(os.path.exists(dst), "Destination file not created")
        self.assertFalse(os.path.exists(src), "Source file not removed")
        
        with open(dst, "rb") as f:
            self.assertEqual(f.read(), content, "Content changed during move")

    def test_05_delete_to_recycle(self):
        """Test 5: Delete file to recycle bin"""
        src = self._create_file("to_recycle.txt", 1024)
        self.assertTrue(os.path.exists(src))
        
        self.engine.delete([src], permanent=False)
        
        self.assertFalse(os.path.exists(src), "File not moved to recycle bin")

    def test_06_delete_permanent(self):
        """Test 6: Permanent delete (secure)"""
        src = self._create_file("permanent.txt", 512)
        self.assertTrue(os.path.exists(src))
        
        self.engine.delete([src], permanent=True)
        
        self.assertFalse(os.path.exists(src), "File not permanently deleted")

    def test_07_large_file_performance(self):
        """Test 7: Large file copy performance (100MB)"""
        size = 100 * 1024 * 1024  # 100MB
        src = self._create_file("large.bin", size)
        
        start = time.perf_counter()
        self.engine.copy([src], self.dst_dir)
        elapsed = time.perf_counter() - start
        
        dst = os.path.join(self.dst_dir, "large.bin")
        self.assertTrue(self._verify_file(dst, size), "Large file not copied correctly")
        
        # Calculate speed
        speed_mbps = (size / 1024 / 1024) / elapsed
        print(f"\n  100MB copy: {elapsed:.2f}s ({speed_mbps:.1f} MB/s)")

    def test_08_pause_resume(self):
        """Test 8: Pause and resume operation"""
        # Create files for longer operation
        files = [self._create_file(f"big{i}.bin", 10*1024*1024) for i in range(3)]
        
        result = {"paused": False, "resumed": False}
        
        def do_copy():
            self.engine.copy(files, self.dst_dir)
        
        thread = threading.Thread(target=do_copy)
        thread.start()
        
        time.sleep(0.05)  # Let it start
        
        # Pause
        self.engine.pause()
        time.sleep(0.1)
        result["paused"] = (self.engine.state == OpState.PAUSED)
        
        # Resume
        self.engine.resume()
        time.sleep(0.05)
        result["resumed"] = (self.engine.state == OpState.RUNNING)
        
        thread.join(timeout=10)
        
        self.assertTrue(result["paused"], "Pause did not work")
        self.assertTrue(result["resumed"], "Resume did not work")

    def test_09_cancel_operation(self):
        """Test 9: Cancel ongoing operation"""
        files = [self._create_file(f"cancel{i}.bin", 20*1024*1024) for i in range(5)]
        
        cancelled = False
        
        def do_copy():
            self.engine.copy(files, self.dst_dir)
        
        thread = threading.Thread(target=do_copy)
        thread.start()
        
        time.sleep(0.1)
        self.engine.cancel()
        
        thread.join(timeout=5)
        cancelled = (self.engine.state == OpState.CANCELLED)
        
        self.assertTrue(cancelled, "Cancel did not work")

    def test_10_error_handling(self):
        """Test 10: Error handling for invalid files"""
        # Non-existent file
        fake_file = os.path.join(self.src_dir, "nonexistent.txt")
        self.engine.copy([fake_file], self.dst_dir)
        
        failed = self.engine.get_failed()
        self.assertEqual(len(failed), 1, "Should have one failed item")
        self.assertIn("nonexistent.txt", failed[0].src)


def run_tests():
    """Run all tests and print summary"""
    print("=" * 60)
    print("FastFileOp - FileEngine Unit Tests")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestFileEngine)
    
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
        for test, trace in result.failures + result.errors:
            print(f"\nFailed: {test}")
            print(trace)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
