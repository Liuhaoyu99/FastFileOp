"""FastFileOp - High-Speed File Operation Engine

Multi-threaded file copy/move/delete with progress callback,
pause/resume/cancel support, and error handling.
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
from typing import Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Windows CopyFileW API - fastest single-file copy on Windows
_kernel32 = ctypes.windll.kernel32
_kernel32.CopyFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_int]
_kernel32.CopyFileW.restype = ctypes.c_int


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


class FileEngine:
    """High-speed file operation engine

    Features:
    - Multi-threaded copy with configurable buffer size
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
        self._lock = threading.Lock()

    @property
    def state(self) -> OpState:
        return self._state

    @property
    def progress(self) -> OperationProgress:
        return self._progress

    def _notify_progress(self, current_file: str = ""):
        """Notify progress callback"""
        if self.progress_callback:
            try:
                self.progress_callback(
                    current_file,
                    self._progress.completed_files,
                    self._progress.total_files,
                    self._progress.copied_bytes,
                    self._progress.total_bytes,
                )
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def _check_pause_cancel(self) -> bool:
        """Check pause and cancel state, block if paused

        Returns:
            True if should continue, False if cancelled
        """
        while not self._pause_event.is_set():
            if self._cancel_event.is_set():
                return False
            time.sleep(0.05)
        return not self._cancel_event.is_set()

    def _copy_single_file(self, src: str, dst: str, file_index: int) -> FileProgress:
        """Copy a single file using Windows CopyFileW API for maximum speed"""
        fp = FileProgress(src=src, dst=dst)

        try:
            if not self._check_pause_cancel():
                return fp

            src_size = os.path.getsize(src)
            fp.total_bytes = src_size

            # Use Windows CopyFileW API - single kernel call, much faster
            # than Python's read/write loop or shutil.copyfile
            result = _kernel32.CopyFileW(src, dst, 0)
            if not result:
                # Fallback to shutil if CopyFileW fails
                shutil.copyfile(src, dst)

            fp.copied_bytes = src_size
            with self._lock:
                self._progress.copied_bytes += src_size
            fp.done = True
            self._notify_progress(src)

        except Exception as e:
            fp.error = str(e)
            logger.error(f"Copy failed: {src} -> {dst}, error: {e}")
            with self._lock:
                self._progress.failed_files += 1

        finally:
            with self._lock:
                self._progress.completed_files += 1

        return fp

    def _copy_directory(self, src_dir: str, dst_dir: str, file_index: int) -> FileProgress:
        """Copy a directory recursively"""
        fp = FileProgress(src=src_dir, dst=dst_dir)

        try:
            src_path = Path(src_dir)

            # Calculate total size
            total_size = sum(f.stat().st_size for f in src_path.rglob("*") if f.is_file())
            fp.total_bytes = total_size

            for item in src_path.rglob("*"):
                if not self._check_pause_cancel():
                    return fp

                rel = item.relative_to(src_path)
                target = Path(dst_dir) / rel

                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(str(item), str(target))

                    sz = item.stat().st_size
                    fp.copied_bytes += sz
                    with self._lock:
                        self._progress.copied_bytes += sz

                    self._notify_progress(str(item))

            fp.done = True

        except Exception as e:
            fp.error = str(e)
            logger.error(f"Directory copy failed: {src_dir} -> {dst_dir}, error: {e}")
            with self._lock:
                self._progress.failed_files += 1

        finally:
            with self._lock:
                self._progress.completed_files += 1
            self._notify_progress(src_dir)

        return fp

    def _same_drive(self, p1: str, p2: str) -> bool:
        """Check if two paths are on the same drive"""
        try:
            return os.path.splitdrive(os.path.abspath(p1))[0].lower() == \
                   os.path.splitdrive(os.path.abspath(p2))[0].lower()
        except Exception:
            return False

    def _secure_delete(self, filepath: str, passes: int = 3) -> None:
        """Securely delete a file by overwriting before deletion

        Args:
            filepath: Path to file
            passes: Number of overwrite passes (default 3)
        """
        size = os.path.getsize(filepath)

        for pass_num in range(passes):
            if not self._check_pause_cancel():
                return

            with open(filepath, "wb") as f:
                remaining = size
                while remaining > 0:
                    if not self._check_pause_cancel():
                        return
                    chunk_size = min(remaining, self.buffer_size)
                    # Alternate between different patterns
                    if pass_num % 3 == 0:
                        f.write(b"\x00" * chunk_size)
                    elif pass_num % 3 == 1:
                        f.write(b"\xFF" * chunk_size)
                    else:
                        f.write(os.urandom(chunk_size))
                    remaining -= chunk_size

            # Force flush to disk
            with open(filepath, "rb+") as f:
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

        # Calculate total size
        total_bytes = 0
        for src in src_list:
            p = Path(src)
            if p.is_file():
                total_bytes += p.stat().st_size
            elif p.is_dir():
                total_bytes += sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

        self._progress.total_files = len(src_list)
        self._progress.total_bytes = total_bytes

        # Build tasks
        tasks = []
        for i, src in enumerate(src_list):
            src_name = os.path.basename(src.rstrip("\\/"))
            dst = os.path.join(dst_dir, src_name)
            tasks.append((src, dst, i))

        self._notify_progress()

        # Split tasks into batches - one batch per worker
        # This reduces ThreadPoolExecutor overhead from O(n) to O(workers)
        num_workers = min(self.max_workers, len(tasks))
        if num_workers <= 0:
            self._finalize_state()
            return self._progress

        batches = [[] for _ in range(num_workers)]
        for idx, task in enumerate(tasks):
            batches[idx % num_workers].append(task)

        def process_batch(batch):
            """Process a batch of copy tasks sequentially within one thread."""
            results = []
            for src, dst, i in batch:
                if self._cancel_event.is_set():
                    break
                if os.path.isdir(src):
                    fp = self._copy_directory(src, dst, i)
                else:
                    fp = self._copy_single_file(src, dst, i)
                results.append(fp)
            return results

        # Execute with thread pool - one future per batch
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
        return self._progress

    def move(self, src_list: List[str], dst_dir: str) -> OperationProgress:
        """Move files/directories to destination

        Same-drive: direct rename
        Cross-drive: copy then delete source

        Args:
            src_list: Source paths
            dst_dir: Destination directory

        Returns:
            OperationProgress with results
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

        # Same-drive: direct rename
        for src in same_drive_items:
            if not self._check_pause_cancel():
                break

            src_name = os.path.basename(src.rstrip("\\/"))
            dst = os.path.join(dst_dir, src_name)
            fp = FileProgress(src=src, dst=dst)
            self._progress.file_progresses.append(fp)
            self._progress.total_files += 1

            try:
                os.rename(src, dst)
                fp.done = True

                # Calculate size for progress
                p = Path(dst)
                if p.is_file():
                    sz = p.stat().st_size
                elif p.is_dir():
                    sz = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                else:
                    sz = 0

                fp.total_bytes = sz
                fp.copied_bytes = sz
                with self._lock:
                    self._progress.completed_files += 1
                    self._progress.copied_bytes += sz

            except Exception as e:
                fp.error = str(e)
                logger.error(f"Rename failed: {src} -> {dst}, error: {e}")
                with self._lock:
                    self._progress.failed_files += 1
                    self._progress.completed_files += 1

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
        return self._progress

    def delete(self, file_list: List[str], permanent: bool = False) -> OperationProgress:
        """Delete files/directories

        Args:
            file_list: Paths to delete
            permanent: If True, secure overwrite then delete; otherwise, move to recycle bin

        Returns:
            OperationProgress with results
        """
        self._reset_state()
        self._state = OpState.RUNNING
        mode = "permanent" if permanent else "recycle"
        logger.info(f"Starting delete ({mode}): {len(file_list)} items")

        self._progress.total_files = len(file_list)

        for src in file_list:
            if not self._check_pause_cancel():
                break

            fp = FileProgress(src=src, dst="")
            self._progress.file_progresses.append(fp)

            try:
                if permanent:
                    if os.path.isdir(src):
                        # Secure delete all files in directory
                        for item in Path(src).rglob("*"):
                            if not self._check_pause_cancel():
                                break
                            if item.is_file():
                                self._secure_delete(str(item))
                        shutil.rmtree(src, ignore_errors=True)
                    else:
                        self._secure_delete(src)
                else:
                    self._move_to_recycle_bin(src)

                fp.done = True
                with self._lock:
                    self._progress.completed_files += 1

            except Exception as e:
                fp.error = str(e)
                logger.error(f"Delete failed: {src}, error: {e}")
                with self._lock:
                    self._progress.failed_files += 1
                    self._progress.completed_files += 1

            self._notify_progress(src)

        self._finalize_state()
        return self._progress

    def _move_to_recycle_bin(self, path: str) -> None:
        """Move file/directory to recycle bin using send2trash"""
        try:
            from send2trash import send2trash
            send2trash(path)
        except ImportError:
            # Fallback to Windows API
            self._recycle_win32(path)

    def _recycle_win32(self, path: str) -> None:
        """Move to recycle bin using Windows Shell API"""
        import ctypes
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
        fileop.pFrom = path + "\0"  # Double-null terminated
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

    def _finalize_state(self):
        """Set final state after operation completes"""
        if self._state != OpState.CANCELLED:
            self._state = OpState.COMPLETED

        success_count = self._progress.completed_files - self._progress.failed_files
        logger.info(
            f"Operation complete: state={self._state.name}, "
            f"success={success_count}, failed={self._progress.failed_files}"
        )

    def get_failed(self) -> List[FileProgress]:
        """Get list of failed files"""
        return [fp for fp in self._progress.file_progresses if fp.error is not None]
