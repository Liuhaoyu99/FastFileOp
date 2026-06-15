"""FastFileOp - Named Pipe Server Module

Multi-client named pipe server for receiving requests from the C++ DLL.
Supports concurrent connections with one thread per pipe instance.
Includes watchdog mechanism for automatic recovery.
"""

import json
import logging
import threading
import time
from collections import deque
from typing import Callable, Optional, List

import pywintypes
import win32file
import win32pipe

logger = logging.getLogger(__name__)

PIPE_NAME = r"\\.\pipe\FastFileOpPipe"
BUFFER_SIZE = 65536
MAX_INSTANCES = 4  # Maximum concurrent pipe instances

# Watchdog settings
WATCHDOG_WINDOW_SECONDS = 30  # Time window to count disconnections
WATCHDOG_MAX_DISCONNECTS = 3  # Max disconnections before instability
WATCHDOG_RECONNECT_DELAY = 2  # Seconds to wait before reconnecting


class PipeWatchdog:
    """Watchdog for monitoring pipe stability

    Tracks disconnection events and triggers instability callback
    when threshold is exceeded.
    """

    def __init__(self, on_instability: Optional[Callable] = None):
        """
        Args:
            on_instability: Callback when instability is detected
        """
        self._disconnect_times: deque = deque()
        self._lock = threading.Lock()
        self._on_instability = on_instability
        self._is_stable = True

    def record_disconnect(self) -> bool:
        """Record a disconnection event

        Returns:
            True if system is still stable, False if instability detected
        """
        now = time.time()

        with self._lock:
            # Remove old entries outside the time window
            while self._disconnect_times and (now - self._disconnect_times[0]) > WATCHDOG_WINDOW_SECONDS:
                self._disconnect_times.popleft()

            # Add current disconnect time
            self._disconnect_times.append(now)

            disconnect_count = len(self._disconnect_times)

            logger.warning(f"Pipe disconnect recorded ({disconnect_count}/{WATCHDOG_MAX_DISCONNECTS} in {WATCHDOG_WINDOW_SECONDS}s)")

            if disconnect_count >= WATCHDOG_MAX_DISCONNECTS and self._is_stable:
                self._is_stable = False
                logger.error(f"Instability detected: {disconnect_count} disconnections in {WATCHDOG_WINDOW_SECONDS} seconds")

                if self._on_instability:
                    try:
                        self._on_instability()
                    except Exception as e:
                        logger.error(f"Instability callback error: {e}")

                return False

        return True

    def is_stable(self) -> bool:
        """Check if system is stable"""
        with self._lock:
            return self._is_stable

    def reset(self):
        """Reset watchdog state (after manual resume)"""
        with self._lock:
            self._disconnect_times.clear()
            self._is_stable = True
            logger.info("Watchdog reset, system marked as stable")


class PipeServer:
    """Named pipe server

    Accepts connections from the C++ DLL, receives JSON requests,
    executes file operations, and returns JSON responses.

    Supports multiple concurrent clients (one thread per instance).
    Includes watchdog for automatic recovery and instability detection.
    """

    def __init__(
        self,
        engine_factory: Callable,
        progress_callback: Optional[Callable] = None,
        on_instability: Optional[Callable] = None,
    ):
        """
        Args:
            engine_factory: Factory function to create FileEngine instances
            progress_callback: Optional progress callback
            on_instability: Callback when instability is detected
        """
        self.engine_factory = engine_factory
        self.progress_callback = progress_callback

        self._running = False
        self._threads: List[threading.Thread] = []
        self._stop_event = threading.Event()

        # Watchdog
        self._watchdog = PipeWatchdog(on_instability=on_instability)

    def start(self):
        """Start the pipe server"""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()
        self._watchdog.reset()

        # Start multiple pipe instance threads
        for i in range(MAX_INSTANCES):
            thread = threading.Thread(
                target=self._pipe_instance_loop,
                args=(i,),
                daemon=True,
                name=f"PipeInstance-{i}",
            )
            thread.start()
            self._threads.append(thread)

        logger.info(f"Named pipe server started: {PIPE_NAME} ({MAX_INSTANCES} instances)")

    def stop(self):
        """Stop the pipe server"""
        self._running = False
        self._stop_event.set()

        # Wait for threads to finish
        for thread in self._threads:
            thread.join(timeout=2)

        self._threads.clear()
        logger.info("Named pipe server stopped")

    @property
    def is_running(self) -> bool:
        """Check if pipe server is running"""
        return self._running

    def is_stable(self) -> bool:
        """Check if pipe server is stable"""
        return self._watchdog.is_stable()

    def reset_watchdog(self):
        """Reset watchdog (after manual resume)"""
        self._watchdog.reset()
        logger.info("Pipe server watchdog reset")

    def _pipe_instance_loop(self, instance_id: int):
        """Main loop for a single pipe instance

        Args:
            instance_id: Instance identifier for logging
        """
        while self._running:
            pipe_handle = None

            try:
                # Check if system is stable before creating pipe
                if not self._watchdog.is_stable():
                    logger.debug(f"[Instance {instance_id}] System unstable, waiting...")
                    time.sleep(WATCHDOG_RECONNECT_DELAY)
                    continue

                # Create named pipe
                pipe_handle = win32pipe.CreateNamedPipe(
                    PIPE_NAME,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE
                    | win32pipe.PIPE_READMODE_MESSAGE
                    | win32pipe.PIPE_WAIT,
                    MAX_INSTANCES,
                    BUFFER_SIZE,
                    BUFFER_SIZE,
                    0,  # Default timeout
                    None,
                )

                if pipe_handle == win32file.INVALID_HANDLE_VALUE:
                    logger.error(f"[Instance {instance_id}] Failed to create named pipe")
                    self._watchdog.record_disconnect()
                    time.sleep(WATCHDOG_RECONNECT_DELAY)
                    continue

                logger.debug(f"[Instance {instance_id}] Waiting for connection...")

                # Wait for client connection
                win32pipe.ConnectNamedPipe(pipe_handle, None)
                logger.debug(f"[Instance {instance_id}] Client connected")

                # Handle client request
                self._handle_client(pipe_handle, instance_id)

            except pywintypes.error as e:
                if self._running:
                    logger.error(f"[Instance {instance_id}] Pipe error: {e}")
                    self._watchdog.record_disconnect()
                    time.sleep(WATCHDOG_RECONNECT_DELAY)

            except Exception as e:
                if self._running:
                    logger.error(f"[Instance {instance_id}] Unexpected error: {e}")
                    self._watchdog.record_disconnect()
                    time.sleep(WATCHDOG_RECONNECT_DELAY)

            finally:
                if pipe_handle:
                    try:
                        win32file.CloseHandle(pipe_handle)
                    except Exception:
                        pass

    def _handle_client(self, pipe_handle, instance_id: int):
        """Handle a client connection

        Args:
            pipe_handle: Handle to the named pipe
            instance_id: Instance identifier for logging
        """
        try:
            # Read request - win32file.ReadFile returns (error_code, data) for message mode
            error_code, data = win32file.ReadFile(pipe_handle, BUFFER_SIZE)
            while error_code == 234:  # ERROR_MORE_DATA
                _, more_data = win32file.ReadFile(pipe_handle, BUFFER_SIZE)
                data += more_data

            request = data.decode("utf-8").strip()
            if not request:
                return

            logger.debug(f"[Instance {instance_id}] Received: {request[:200]}...")

            # Process request
            response = self._process_request(request)

            # Send response
            response_data = (response + "\n").encode("utf-8")
            win32file.WriteFile(pipe_handle, response_data)

            logger.debug(f"[Instance {instance_id}] Response sent")

        except pywintypes.error as e:
            logger.error(f"[Instance {instance_id}] Client communication error: {e}")
            self._watchdog.record_disconnect()

        except Exception as e:
            logger.error(f"[Instance {instance_id}] Error handling client: {e}")
            self._watchdog.record_disconnect()

    def _process_request(self, request: str) -> str:
        """Process a JSON request

        Args:
            request: JSON request string

        Returns:
            JSON response string
        """
        try:
            data = json.loads(request)
            action = data.get("action", "")
            src_list = data.get("src", [])
            dst = data.get("dst", "")

            # Handle ping
            if action == "ping":
                return json.dumps({"status": "pong"})

            # Handle status
            if action == "status":
                return json.dumps({"status": "ok"})

            # Validate request
            if not action:
                return json.dumps({"status": "error", "failed": [], "message": "Missing action"})

            if action not in ("copy", "move", "delete", "delete_permanent"):
                return json.dumps({"status": "error", "failed": [], "message": f"Unknown action: {action}"})

            if not src_list:
                return json.dumps({"status": "error", "failed": [], "message": "Missing src"})

            # Create engine and execute operation
            engine = self.engine_factory()

            if action == "copy":
                logger.info(f"Pipe request: Copy {len(src_list)} items -> {dst}")
                progress = engine.copy(src_list, dst)

            elif action == "move":
                logger.info(f"Pipe request: Move {len(src_list)} items -> {dst}")
                progress = engine.move(src_list, dst)

            elif action == "delete":
                logger.info(f"Pipe request: Delete {len(src_list)} items (recycle)")
                progress = engine.delete(src_list, permanent=False)

            elif action == "delete_permanent":
                logger.info(f"Pipe request: Delete {len(src_list)} items (permanent)")
                progress = engine.delete(src_list, permanent=True)

            # Build response
            failed = [fp.src for fp in progress.file_progresses if fp.error]
            success = len(failed) == 0

            if success:
                logger.info(f"Operation complete: {progress.completed_files} files")
                return json.dumps({"status": "ok", "failed": []})
            else:
                logger.warning(f"Operation complete: {len(failed)} files failed")
                return json.dumps({"status": "error", "failed": failed})

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return json.dumps({"status": "error", "failed": [], "message": "Invalid JSON"})

        except Exception as e:
            logger.error(f"Request processing error: {e}")
            return json.dumps({"status": "error", "failed": [], "message": str(e)})

    @staticmethod
    def is_server_running() -> bool:
        """Check if a pipe server is already running

        Returns:
            True if another instance is running
        """
        try:
            handle = win32file.CreateFile(
                PIPE_NAME,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,
                None,
                win32file.OPEN_EXISTING,
                0,
                None,
            )
            win32file.CloseHandle(handle)
            return True
        except pywintypes.error:
            return False
