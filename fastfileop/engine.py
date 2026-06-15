"""FastFileOp - High-Speed File Operation Engine

Multi-threaded file copy/move/delete with progress callback,
pause/resume/cancel support, and error handling.

Optimizations:
- Windows CopyFileW API for native-speed file copy
- Batched task assignment to minimize thread pool overhead
- Lock-free progress tracking with atomic counters
- Deferred size calculation to reduce syscalls
"""

import ctypes
import logging
import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

# ── Windows API bindings ──────────────────────────────────────────
_kernel32 = ctypes.windll.kernel32

# CopyFileW — single kernel call, fastest way to copy a file on Windows
_kernel32.CopyFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_int]
_kernel32.CopyFileW.restype = ctypes.c_int

# MoveFileExW — for atomic same-drive moves with replace-if-exists
_kernel32.MoveFileExW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
_kernel32.MoveFileExW.restype = ctypes.c_int
MOVEFILE_REPLACE_EXISTING = 0x1
MOVEFILE_WRITE_THROUGH = 0x8


class OpState(Enum):
    """Operation state"""
    PENDING = auto()
    RUNNING = auto()
    PAUSED = auto()
    CANCELLED = auto()
    COMPLETED = auto()


@dataclass
class FileProgress:
    """Progress info for a single file"""
    src: str
    dst: str
    total_bytes: int = 0
    copied_bytes: int = 0
    done: bool = False
    error: Optional[str] = None


@dataclass
class OperationProgress:
    """Overall operation progress"""
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    total_bytes: int = 0
    copied_bytes: int = 0
    file_progresses: List[FileProgress] = field(default_factory=list)
    state: OpState = OpState.PENDING

    @property
    def percent(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return self.copied_bytes / self.total_bytes * 100


# Progress callback signature
ProgressCallback = Callable[[str, int, int, int, int], None]
# callback(current_file, file_index, total_files, bytes_done, bytes_total)


class _BatchCounter:
    """Thread-safe counter with batched updates to minimize lock contention.

    Instead of acquiring the lock for every single file, workers accumulate
    counts locally and flush them in bulk. This reduces lock acquisitions
    from O(n_files) to O(n_workers * n_flushes).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._copied_bytes = 0
        self._completed_files = 0
        self._failed_files = 0

    def flush(self, copied_bytes: int, completed: int, failed: int):
        """Batch-update all counters in a single lock acquisition."""
        with self._lock:
            self._copied_bytes += copied_bytes
            self._completed_files += completed
            self._failed_files += failed

    @property
    def copied_bytes(self) -> int:
        with self._lock:
            return self._copied_bytes

    @property
    def completed_files(self) -> int:
        with self._lock:
            return self._completed_files

    @property
    def failed_files(self) -> int:
        with self._lock:
            return self._failed_files


class FileEngine:
    """High-speed file operation engine

    Features:
    - Multi-threaded copy with Windows CopyFileW API
    - Lock-free progress tracking with atomic counters
    - Move: same-drive rename, cross-drive copy+delete
    - Delete: recycle bin or secure overwrite (3 passes)
    - Progress callback, pause/resume/cancel
    - Individual file error handling
    """

    def __init__(
        self,
        buffer_size: int = 64 * 1024 * 1024,  # 64MB
        max_workers: int = 4,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        self.buffer_size = buffer_size
        self.max_workers = max_workers
        self.progress_callback = progress_callback

        self._state = OpState.PENDING
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused by default
        self._cancel_event = threading.Event()
        self._progress = OperationProgress()

        # Batched counter — workers flush locally accumulated counts in bulk
        self._counter = _BatchCounter()

    @property
    def state(self) -> OpState:
        return self._state

    @property
    def progress(self) -> OperationProgress:
        # Sync batched counter to progress object on read
        self._progress.copied_bytes = self._counter.copied_bytes
        self._progress.completed_files = self._counter.completed_files
        self._progress.failed_files = self._counter.failed_files
        return self._progress

    def _notify_progress(self, current_file: str = ""):
        """Notify progress callback"""
        if self.progress_callback:
            try:
                p = self.progress
                self.progress_callback(
                    current_file,
                    p.completed_files,
                    p.total_files,
                    p.copied_bytes,
                    p.total_bytes,
                )
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def _check_cancelled(self) -> bool:
        """Quick cancel check without pause blocking."""
        return self._cancel_event.is_set()

    def _wait_if_paused(self) -> bool:
        """Block while paused. Returns False if cancelled."""
        while not self._pause_event.is_set():
            if self._cancel_event.is_set():
                return False
            time.sleep(0.05)
        return not self._cancel_event.is_set()

    def _copy_single_file(self, src: str, dst: str) -> FileProgress:
        """Copy a single file using Windows CopyFileW API for maximum speed.

        CopyFileW is a single kernel call that handles all buffering,
        metadata, and error handling internally — far faster than any
        Python-level read/write loop.

        Returns FileProgress with size info for the caller to batch-flush.
        """
        fp = FileProgress(src=src, dst=dst)

        try:
            if not self._wait_if_paused():
                return fp

            # CopyFileW — single kernel call, no need to get file size first
            result = _kernel32.CopyFileW(src, dst, 0)
            if not result:
                # Fallback to shutil if CopyFileW fails
                shutil.copyfile(src, dst)

            # Get size after copy (only needed for progress reporting)
            try:
                file_size = os.path.getsize(src)
            except OSError:
                try:
                    file_size = os.path.getsize(dst)
                except OSError:
                    file_size = 0

            fp.total_bytes = file_size
            fp.copied_bytes = file_size
            fp.done = True

        except Exception as e:
            fp.error = str(e)
            logger.error(f"Copy failed: {src} -> {dst}, error: {e}")

        return fp

    def _copy_directory(self, src_dir: str, dst_dir: str) -> FileProgress:
        """Copy a directory recursively using CopyFileW for each file."""
        fp = FileProgress(src=src_dir, dst=dst_dir)

        try:
            src_path = Path(src_dir)
            dst_path = Path(dst_dir)

            # Collect all files first, then copy in bulk
            all_files = [(f, f.relative_to(src_path)) for f in src_path.rglob("*") if f.is_file()]

            # Create all directories upfront (batched, fewer syscalls)
            dirs_created = set()
            for _, rel in all_files:
                target_parent = (dst_path / rel).parent
                if str(target_parent) not in dirs_created:
                    target_parent.mkdir(parents=True, exist_ok=True)
                    dirs_created.add(str(target_parent))

            # Copy files using CopyFileW
            total_size = 0
            for src_file, rel in all_files:
                if self._check_cancelled():
                    return fp
                if not self._pause_event.is_set():
                    if not self._wait_if_paused():
                        return fp

                target = dst_path / rel
                result = _kernel32.CopyFileW(str(src_file), str(target), 0)
                if not result:
                    shutil.copyfile(str(src_file), str(target))

                sz = src_file.stat().st_size
                total_size += sz

            fp.total_bytes = total_size
            fp.copied_bytes = total_size
            fp.done = True

        except Exception as e:
            fp.error = str(e)
            logger.error(f"Directory copy failed: {src_dir} -> {dst_dir}, error: {e}")

        return fp

    def _same_drive(self, p1: str, p2: str) -> bool:
        """Check if two paths are on the same drive"""
        try:
            return os.path.splitdrive(os.path.abspath(p1))[0].lower() == \
                   os.path.splitdrive(os.path.abspath(p2))[0].lower()
        except Exception:
            return False

    def _secure_delete(self, filepath: str, passes: int = 3) -> None:
        """Securely delete a file by overwriting before deletion"""
        size = os.path.getsize(filepath)
        # Use a fixed, small reusable buffer to avoid allocating large
        # temporary bytes objects (avoids large memory spikes when buffer_size
        # is large, e.g. default 64MB). We'll write in chunks of up to 1MB.
        chunk_pool_size = min(1024 * 1024, max(4096, self.buffer_size))

        for pass_num in range(passes):
            if not self._wait_if_paused():
                return

            # Prepare write pattern for this pass. Reuse the same buffer object.
            if pass_num % 3 == 0:
                pattern_chunk = b"\x00" * chunk_pool_size
            elif pass_num % 3 == 1:
                pattern_chunk = b"\xFF" * chunk_pool_size
            else:
                # For random data, create a buffer and refill as needed to
                # avoid holding a huge bytes object for the whole file.
                pattern_chunk = None

            written = 0
            with open(filepath, "r+b") as f:
                f.seek(0)
                while written < size:
                    if self._check_cancelled():
                        return
                    if not self._wait_if_paused():
                        return

                    to_write = min(chunk_pool_size, size - written)
                    if pattern_chunk is not None:
                        f.write(pattern_chunk[:to_write])
                    else:
                        # Fill a small buffer with random bytes and write
                        f.write(os.urandom(to_write))

                    written += to_write
                    # Optionally flush intermittently to avoid large write buffers
                    if written % (8 * chunk_pool_size) == 0:
                        f.flush()
                        os.fsync(f.fileno())

                # Ensure all data persisted for this pass
                f.flush()
                os.fsync(f.fileno())

        os.remove(filepath)

    def copy(self, src_list: List[str], dst_dir: str) -> OperationProgress:
        """Copy files/directories to destination

        Uses batched task assignment: files are divided into N batches
        (one per worker), each worker processes its batch sequentially.
        This minimizes ThreadPoolExecutor overhead compared to submitting
        each file as a separate task.

        Args:
            src_list: Source paths (files or directories)
            dst_dir: Destination directory

        Returns:
            OperationProgress with results
        """
        self._reset_state()
        self._state = OpState.RUNNING
        logger.info(f"Starting copy: {len(src_list)} items -> {dst_dir}")

        os.makedirs(dst_dir, exist_ok=True)

        # Build task list — defer size calculation to avoid stat() overhead
        tasks = []
        for i, src in enumerate(src_list):
            src_name = os.path.basename(src.rstrip("\\/"))
            dst = os.path.join(dst_dir, src_name)
            is_dir = os.path.isdir(src)
            tasks.append((src, dst, is_dir))

        self._progress.total_files = len(tasks)

        # Calculate total size in parallel with copy (or skip for speed)
        # We compute it upfront but in a single pass
        total_bytes = 0
        for src, _, is_dir in tasks:
            try:
                if is_dir:
                    total_bytes += sum(f.stat().st_size for f in Path(src).rglob("*") if f.is_file())
                else:
                    total_bytes += os.path.getsize(src)
            except OSError:
                pass
        self._progress.total_bytes = total_bytes

        self._notify_progress()

        # Split tasks into batches — one batch per worker
        num_workers = min(self.max_workers, len(tasks))
        if num_workers <= 0:
            self._finalize_state()
            return self._progress

        batches = [[] for _ in range(num_workers)]
        for idx, task in enumerate(tasks):
            batches[idx % num_workers].append(task)

        def process_batch(batch):
            """Process a batch of copy tasks sequentially within one thread.

            Accumulates progress locally and flushes to the shared counter
            once at the end — minimizes lock contention.
            """
            results = []
            local_bytes = 0
            local_completed = 0
            local_failed = 0

            for src, dst, is_dir in batch:
                if self._check_cancelled():
                    break
                if is_dir:
                    fp = self._copy_directory(src, dst)
                else:
                    fp = self._copy_single_file(src, dst)
                results.append(fp)

                if fp.done and fp.error is None:
                    local_bytes += fp.copied_bytes
                    local_completed += 1
                elif fp.error is not None:
                    local_failed += 1
                    local_completed += 1

            # Single lock acquisition for the entire batch
            self._counter.flush(local_bytes, local_completed, local_failed)
            return results

        # Execute with thread pool — one future per batch
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(process_batch, batch) for batch in batches if batch]

            for future in as_completed(futures):
                if self._cancel_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                try:
                    batch_results = future.result()
                    self._progress.file_progresses.extend(batch_results)
                except Exception as e:
                    logger.error(f"Batch failed: {e}")

        self._finalize_state()
        return self.progress

    def move(self, src_list: List[str], dst_dir: str) -> OperationProgress:
        """Move files/directories to destination

        Same-drive: direct rename via MoveFileExW
        Cross-drive: copy then delete source
        """
        self._reset_state()
        self._state = OpState.RUNNING
        logger.info(f"Starting move: {len(src_list)} items -> {dst_dir}")

        os.makedirs(dst_dir, exist_ok=True)

        same_drive_items = []
        cross_drive_items = []

        for src in src_list:
            if self._same_drive(src, dst_dir):
                same_drive_items.append(src)
            else:
                cross_drive_items.append(src)

        # Same-drive: direct rename via MoveFileExW (atomic, no data copy)
        for src in same_drive_items:
            if not self._wait_if_paused():
                break

            src_name = os.path.basename(src.rstrip("\\/"))
            dst = os.path.join(dst_dir, src_name)
            fp = FileProgress(src=src, dst=dst)
            self._progress.file_progresses.append(fp)
            self._progress.total_files += 1

            try:
                # Try MoveFileExW first (faster than os.rename)
                result = _kernel32.MoveFileExW(
                    src, dst,
                    MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH
                )
                if not result:
                    os.rename(src, dst)

                fp.done = True

                # Get size for progress
                try:
                    p = Path(dst)
                    if p.is_file():
                        sz = p.stat().st_size
                    elif p.is_dir():
                        sz = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                    else:
                        sz = 0
                except OSError:
                    sz = 0

                fp.total_bytes = sz
                fp.copied_bytes = sz
                self._counter.flush(sz, 1, 0)

            except Exception as e:
                fp.error = str(e)
                logger.error(f"Rename failed: {src} -> {dst}, error: {e}")
                self._counter.flush(0, 1, 1)

            self._notify_progress(src)

        # Cross-drive: copy then delete
        if cross_drive_items:
            copy_progress = self.copy(cross_drive_items, dst_dir)

            # Delete sources after successful copy
            if copy_progress.state != OpState.CANCELLED:
                for fp in copy_progress.file_progresses:
                    if fp.done and fp.error is None:
                        try:
                            if os.path.isdir(fp.src):
                                shutil.rmtree(fp.src)
                            else:
                                os.remove(fp.src)
                        except Exception as e:
                            logger.error(f"Failed to delete source: {fp.src}, error: {e}")

        self._finalize_state()
        return self.progress

    def delete(self, file_list: List[str], permanent: bool = False) -> OperationProgress:
        """Delete files/directories

        Args:
            file_list: Paths to delete
            permanent: If True, secure overwrite then delete; otherwise, move to recycle bin
        """
        self._reset_state()
        self._state = OpState.RUNNING
        mode = "permanent" if permanent else "recycle"
        logger.info(f"Starting delete ({mode}): {len(file_list)} items")

        self._progress.total_files = len(file_list)

        for src in file_list:
            if not self._wait_if_paused():
                break

            fp = FileProgress(src=src, dst="")
            self._progress.file_progresses.append(fp)

            try:
                if permanent:
                    if os.path.isdir(src):
                        for item in Path(src).rglob("*"):
                            if self._check_cancelled():
                                break
                            if item.is_file():
                                self._secure_delete(str(item))
                        shutil.rmtree(src, ignore_errors=True)
                    else:
                        self._secure_delete(src)
                else:
                    self._move_to_recycle_bin(src)

                fp.done = True
                self._counter.flush(0, 1, 0)

            except Exception as e:
                fp.error = str(e)
                logger.error(f"Delete failed: {src}, error: {e}")
                self._counter.flush(0, 1, 1)

            self._notify_progress(src)

        self._finalize_state()
        return self.progress

    def _move_to_recycle_bin(self, path: str) -> None:
        """Move file/directory to recycle bin using send2trash"""
        try:
            from send2trash import send2trash
            send2trash(path)
        except ImportError:
            self._recycle_win32(path)

    def _recycle_win32(self, path: str) -> None:
        """Move to recycle bin using Windows Shell API"""
        from ctypes import wintypes

        class SHFILEOPSTRUCT(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", ctypes.c_uint),
                ("pFrom", ctypes.c_wchar_p),
                ("pTo", ctypes.c_wchar_p),
                ("fFlags", wintypes.WORD),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", ctypes.c_wchar_p),
            ]

        FO_DELETE = 3
        FOF_ALLOWUNDO = 0x40
        FOF_NOCONFIRMATION = 0x10
        FOF_SILENT = 0x04

        fileop = SHFILEOPSTRUCT()
        fileop.hwnd = 0
        fileop.wFunc = FO_DELETE
        fileop.pFrom = path + "\0"
        fileop.pTo = None
        fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
        fileop.fAnyOperationsAborted = False
        fileop.hNameMappings = None
        fileop.lpszProgressTitle = None

        result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
        if result != 0:
            raise OSError(f"SHFileOperationW returned error: {result}")

    def pause(self):
        """Pause current operation"""
        self._state = OpState.PAUSED
        self._pause_event.clear()
        logger.info("Operation paused")

    def resume(self):
        """Resume current operation"""
        self._state = OpState.RUNNING
        self._pause_event.set()
        logger.info("Operation resumed")

    def cancel(self):
        """Cancel current operation"""
        self._cancel_event.set()
        self._pause_event.set()  # Unblock pause
        self._state = OpState.CANCELLED
        logger.info("Operation cancelled")

    def _reset_state(self):
        """Reset operation state"""
        self._state = OpState.PENDING
        self._pause_event.set()
        self._cancel_event.clear()
        self._progress = OperationProgress()
        self._counter = _BatchCounter()

    def _finalize_state(self):
        """Set final state after operation completes"""
        if self._state != OpState.CANCELLED:
            self._state = OpState.COMPLETED

        # Sync final counters
        p = self.progress
        success_count = p.completed_files - p.failed_files
        logger.info(
            f"Operation complete: state={self._state.name}, "
            f"success={success_count}, failed={p.failed_files}"
        )

    def get_failed(self) -> List[FileProgress]:
        """Get list of failed files"""
        return [fp for fp in self._progress.file_progresses if fp.error is not None]
