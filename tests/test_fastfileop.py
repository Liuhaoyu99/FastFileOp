"""FastFileOp - Test Suite

Unit tests for core components.
"""

import os
import sys
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastfileop.config import ConfigManager
from fastfileop.engine import FileEngine, OpState


class TestFileEngine(unittest.TestCase):
    """Test file operation engine"""

    def setUp(self):
        """Create temp directories for testing"""
        self.temp_dir = tempfile.mkdtemp(prefix="fastfileop_test_")
        self.src_dir = os.path.join(self.temp_dir, "src")
        self.dst_dir = os.path.join(self.temp_dir, "dst")
        os.makedirs(self.src_dir)
        os.makedirs(self.dst_dir)
        self.engine = FileEngine(buffer_size=64*1024*1024, max_workers=2)

    def tearDown(self):
        """Clean up temp directories"""
        self.engine = None
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_file(self, name: str, size: int = 1024) -> str:
        """Create a test file with random content"""
        path = os.path.join(self.src_dir, name)
        with open(path, "wb") as f:
            f.write(os.urandom(size))
        return path

    def test_copy_single_file(self):
        """Test copying a single file"""
        src = self._create_test_file("test1.txt", 1024)
        self.engine.copy([src], self.dst_dir)
        
        dst = os.path.join(self.dst_dir, "test1.txt")
        self.assertTrue(os.path.exists(dst))
        self.assertEqual(os.path.getsize(dst), 1024)
        
        # Verify content
        with open(src, "rb") as f1, open(dst, "rb") as f2:
            self.assertEqual(f1.read(), f2.read())

    def test_copy_multiple_files(self):
        """Test copying multiple files"""
        files = [
            self._create_test_file(f"file{i}.txt", 1024 * (i + 1))
            for i in range(5)
        ]
        self.engine.copy(files, self.dst_dir)
        
        for i, src in enumerate(files):
            dst = os.path.join(self.dst_dir, f"file{i}.txt")
            self.assertTrue(os.path.exists(dst), f"File {i} not copied")

    def test_copy_directory(self):
        """Test copying a directory"""
        # Create nested structure
        subdir = os.path.join(self.src_dir, "subdir")
        os.makedirs(subdir)
        self._create_test_file("root.txt")
        self._create_test_file("subdir/nested.txt")
        
        self.engine.copy([self.src_dir], self.dst_dir)
        
        # Verify structure
        self.assertTrue(os.path.exists(os.path.join(self.dst_dir, "src", "root.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.dst_dir, "src", "subdir", "nested.txt")))

    def test_move_file(self):
        """Test moving a file"""
        src = self._create_test_file("move_test.txt", 2048)
        original_content = open(src, "rb").read()
        
        self.engine.move([src], self.dst_dir)
        
        dst = os.path.join(self.dst_dir, "move_test.txt")
        self.assertTrue(os.path.exists(dst))
        self.assertFalse(os.path.exists(src))  # Original should be gone
        
        with open(dst, "rb") as f:
            self.assertEqual(f.read(), original_content)

    def test_delete_to_recycle(self):
        """Test deleting file to recycle bin"""
        src = self._create_test_file("delete_test.txt", 512)
        self.assertTrue(os.path.exists(src))
        
        self.engine.delete([src], permanent=False)
        
        # File should be gone (moved to recycle)
        self.assertFalse(os.path.exists(src))

    def test_delete_permanent(self):
        """Test permanent delete"""
        src = self._create_test_file("permanent_delete.txt", 256)
        self.assertTrue(os.path.exists(src))
        
        self.engine.delete([src], permanent=True)
        
        self.assertFalse(os.path.exists(src))

    def test_large_file_copy(self):
        """Test copying a large file (10MB)"""
        src = self._create_test_file("large_file.bin", 10 * 1024 * 1024)
        
        start_time = time.time()
        self.engine.copy([src], self.dst_dir)
        elapsed = time.time() - start_time
        
        dst = os.path.join(self.dst_dir, "large_file.bin")
        self.assertTrue(os.path.exists(dst))
        self.assertEqual(os.path.getsize(dst), 10 * 1024 * 1024)
        
        print(f"\nLarge file copy (10MB): {elapsed:.2f}s")

    def test_pause_resume_cancel(self):
        """Test pause, resume, and cancel operations"""
        # Create multiple files for a longer operation
        files = [self._create_test_file(f"big{i}.bin", 5*1024*1024) for i in range(3)]
        
        # Start copy in background
        def do_copy():
            self.engine.copy(files, self.dst_dir)
        
        thread = threading.Thread(target=do_copy)
        thread.start()
        
        time.sleep(0.1)
        
        # Test pause
        self.engine.pause()
        time.sleep(0.2)
        self.assertEqual(self.engine.state, OpState.PAUSED)
        
        # Test resume
        self.engine.resume()
        time.sleep(0.1)
        self.assertEqual(self.engine.state, OpState.RUNNING)
        
        # Test cancel
        self.engine.cancel()
        thread.join(timeout=2)
        
        self.assertIn(self.engine.state, [OpState.CANCELLED, OpState.IDLE])

    def test_error_handling(self):
        """Test error handling for non-existent files"""
        non_existent = os.path.join(self.src_dir, "does_not_exist.txt")
        self.engine.copy([non_existent], self.dst_dir)
        
        failed = self.engine.get_failed()
        self.assertEqual(len(failed), 1)
        self.assertIn("does_not_exist.txt", failed[0].src)


class TestConfigManager(unittest.TestCase):
    """Test configuration management"""

    def setUp(self):
        """Use temp directory for config"""
        self.temp_dir = tempfile.mkdtemp(prefix="fastfileop_config_")
        self.original_appdata = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = self.temp_dir

    def tearDown(self):
        """Restore environment"""
        if self.original_appdata:
            os.environ["LOCALAPPDATA"] = self.original_appdata
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_config(self):
        """Test default configuration values"""
        config = ConfigManager()
        config.load()
        
        self.assertEqual(config.config.buffer_size_mb, 64)
        self.assertEqual(config.config.worker_threads, 4)
        self.assertTrue(config.config.hook_copy)
        self.assertTrue(config.config.hook_delete)

    def test_config_save_load(self):
        """Test saving and loading configuration"""
        config1 = ConfigManager()
        config1.load()
        config1.update(
            buffer_size_mb=128,
            worker_threads=8,
            hook_copy=False,
            debug_mode=True
        )
        
        # Create new instance to test persistence
        config2 = ConfigManager()
        config2.load()
        
        self.assertEqual(config2.config.buffer_size_mb, 128)
        self.assertEqual(config2.config.worker_threads, 8)
        self.assertFalse(config2.config.hook_copy)
        self.assertTrue(config2.config.debug_mode)

    def test_is_hooking_enabled(self):
        """Test hooking enabled check"""
        config = ConfigManager()
        config.load()
        
        # Default: all hooks enabled, not paused
        self.assertTrue(config.is_hooking_enabled())
        
        # Paused
        config.update(paused=True)
        self.assertFalse(config.is_hooking_enabled())
        
        # All hooks disabled
        config.update(paused=False, hook_copy=False, hook_delete=False, hook_drag=False)
        self.assertFalse(config.is_hooking_enabled())


class TestPipeServer(unittest.TestCase):
    """Test named pipe server"""

    def test_server_running_check(self):
        """Test checking if server is running"""
        from fastfileop.pipe_server import PipeServer
        
        # Should not be running initially
        self.assertFalse(PipeServer.is_server_running())

    def test_server_start_stop(self):
        """Test starting and stopping server"""
        from fastfileop.pipe_server import PipeServer
        
        def dummy_engine_factory():
            return FileEngine(buffer_size=64*1024*1024, max_workers=2)
        
        server = PipeServer(
            engine_factory=dummy_engine_factory,
            on_instability=lambda: None,
        )
        
        # Start server
        server.start()
        self.assertTrue(server.is_running)
        self.assertTrue(PipeServer.is_server_running())
        
        # Stop server
        server.stop()
        time.sleep(0.5)
        self.assertFalse(server.is_running)


class TestClipboardMonitor(unittest.TestCase):
    """Test clipboard monitoring"""

    def test_get_clipboard_files_empty(self):
        """Test getting files from empty clipboard"""
        from fastfileop.clipboard import ClipboardMonitor
        
        monitor = ClipboardMonitor()
        result = monitor.get_clipboard_files()
        
        # Should return None if no files in clipboard
        # (or the actual files if there are some)
        # This test just verifies the method doesn't crash
        self.assertIsNotNone(monitor)


class TestIntegration(unittest.TestCase):
    """Integration tests"""

    def setUp(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp(prefix="fastfileop_integration_")

    def tearDown(self):
        """Cleanup"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_copy_workflow(self):
        """Test complete copy workflow"""
        # Create source files
        src_dir = os.path.join(self.temp_dir, "source")
        dst_dir = os.path.join(self.temp_dir, "destination")
        os.makedirs(src_dir)
        
        files = []
        for i in range(10):
            path = os.path.join(src_dir, f"file_{i}.dat")
            with open(path, "wb") as f:
                f.write(os.urandom(1024 * (i + 1)))
            files.append(path)
        
        # Create engine and copy
        engine = FileEngine(buffer_size=64*1024*1024, max_workers=4)
        engine.copy(files, dst_dir)
        
        # Verify all files copied
        for i in range(10):
            dst = os.path.join(dst_dir, f"file_{i}.dat")
            self.assertTrue(os.path.exists(dst))
            self.assertEqual(os.path.getsize(dst), 1024 * (i + 1))
        
        # Check no failures
        failed = engine.get_failed()
        self.assertEqual(len(failed), 0)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFileEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigManager))
    suite.addTests(loader.loadTestsFromTestCase(TestPipeServer))
    suite.addTests(loader.loadTestsFromTestCase(TestClipboardMonitor))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
