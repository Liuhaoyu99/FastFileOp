"""FastFileOp - 高速文件操作引擎模块"""

import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, List, Optional

from .logger import get_logger

logger = get_logger(__name__)

# 默认缓冲区大小 64MB
DEFAULT_BUFFER_SIZE = 64 * 1024 * 1024


class OpState(Enum):
    """操作状态"""
    PENDING = auto()
    RUNNING = auto()
    PAUSED = auto()
    CANCELLED = auto()
    COMPLETED = auto()


@dataclass
class FileProgress:
    """单个文件的进度信息"""
    src: str
    dst: str
    total_bytes: int = 0
    copied_bytes: int = 0
    done: bool = False
    error: Optional[str] = None


@dataclass
class OperationProgress:
    """整体操作进度"""
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


class FileEngine:
    """高速文件操作引擎

    支持：
    - copy: 多线程异步复制，大文件分块读写
    - move: 同盘直接 rename，跨盘先复制再删除
    - delete: 移到回收站或永久删除（覆写后删除）

    所有操作支持进度回调、暂停/恢复/取消。
    """

    def __init__(
        self,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
        max_workers: int = 4,
        on_progress: Optional[Callable[[OperationProgress], None]] = None,
    ):
        self.buffer_size = buffer_size
        self.max_workers = max_workers
        self.on_progress = on_progress

        self._state = OpState.PENDING
        self._pause_event = threading.Event()
        self._pause_event.set()  # 默认不暂停
        self._cancel_event = threading.Event()
        self._progress = OperationProgress()
        self._lock = threading.Lock()

    @property
    def state(self) -> OpState:
        return self._state

    def _notify_progress(self):
        if self.on_progress:
            try:
                self.on_progress(self._progress)
            except Exception:
                pass

    def _check_pause_cancel(self):
        """检查暂停和取消状态，阻塞等待暂停恢复"""
        while self._pause_event.is_set() is False:
            if self._cancel_event.is_set():
                return False
            time.sleep(0.05)
        return not self._cancel_event.is_set()

    def _copy_single_file(self, src: str, dst: str, fp: FileProgress) -> None:
        """复制单个文件，大文件分块读写"""
        try:
            src_size = os.path.getsize(src)
            fp.total_bytes = src_size

            # 小文件直接用 copyfile
            if src_size < self.buffer_size:
                if not self._check_pause_cancel():
                    return
                shutil.copyfile(src, dst)
                fp.copied_bytes = src_size
                with self._lock:
                    self._progress.copied_bytes += src_size
                fp.done = True
                self._notify_progress()
                return

            # 大文件分块读写
            with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                while True:
                    if not self._check_pause_cancel():
                        return
                    buf = fsrc.read(self.buffer_size)
                    if not buf:
                        break
                    fdst.write(buf)
                    n = len(buf)
                    fp.copied_bytes += n
                    with self._lock:
                        self._progress.copied_bytes += n
                    self._notify_progress()

            fp.done = True
        except Exception as e:
            fp.error = str(e)
            logger.error(f"复制文件失败: {src} -> {dst}, 错误: {e}")
            with self._lock:
                self._progress.failed_files += 1
        finally:
            with self._lock:
                self._progress.completed_files += 1
            self._notify_progress()

    def _copy_directory(self, src_dir: str, dst_dir: str, fp: FileProgress) -> None:
        """复制整个目录"""
        try:
            src_path = Path(src_dir)
            total_size = sum(f.stat().st_size for f in src_path.rglob("*") if f.is_file())
            fp.total_bytes = total_size

            for item in src_path.rglob("*"):
                if not self._check_pause_cancel():
                    return
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
                    self._notify_progress()

            fp.done = True
        except Exception as e:
            fp.error = str(e)
            logger.error(f"复制目录失败: {src_dir} -> {dst_dir}, 错误: {e}")
            with self._lock:
                self._progress.failed_files += 1
        finally:
            with self._lock:
                self._progress.completed_files += 1
            self._notify_progress()

    def _same_drive(self, p1: str, p2: str) -> bool:
        """判断两个路径是否在同一驱动器"""
        try:
            return os.path.splitdrive(os.path.abspath(p1))[0].lower() == \
                   os.path.splitdrive(os.path.abspath(p2))[0].lower()
        except Exception:
            return False

    def _overwrite_delete(self, filepath: str) -> None:
        """覆写文件内容后删除（永久删除模式）"""
        try:
            size = os.path.getsize(filepath)
            with open(filepath, "wb") as f:
                # 分块覆写零
                remaining = size
                while remaining > 0:
                    if not self._check_pause_cancel():
                        return
                    chunk = min(remaining, self.buffer_size)
                    f.write(b"\x00" * chunk)
                    remaining -= chunk
            os.remove(filepath)
        except Exception as e:
            logger.error(f"覆写删除失败: {filepath}, 错误: {e}")
            raise

    def copy(self, src_list: List[str], dst_dir: str) -> OperationProgress:
        """多线程异步复制文件/目录列表到目标目录

        Args:
            src_list: 源路径列表（文件或目录）
            dst_dir: 目标目录

        Returns:
            OperationProgress: 操作进度结果
        """
        self._reset_state()
        self._state = OpState.RUNNING
        logger.info(f"开始复制: {len(src_list)} 个项目 -> {dst_dir}")

        os.makedirs(dst_dir, exist_ok=True)

        # 计算总大小
        total_bytes = 0
        for src in src_list:
            p = Path(src)
            if p.is_file():
                total_bytes += p.stat().st_size
            elif p.is_dir():
                total_bytes += sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

        self._progress.total_files = len(src_list)
        self._progress.total_bytes = total_bytes

        # 构建任务
        tasks = []
        for src in src_list:
            src_name = os.path.basename(src.rstrip("\\/"))
            dst = os.path.join(dst_dir, src_name)
            fp = FileProgress(src=src, dst=dst)
            self._progress.file_progresses.append(fp)
            tasks.append((src, dst, fp))

        self._notify_progress()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for src, dst, fp in tasks:
                if os.path.isdir(src):
                    future = executor.submit(self._copy_directory, src, dst, fp)
                else:
                    future = executor.submit(self._copy_single_file, src, dst, fp)
                futures[future] = fp

            for future in as_completed(futures):
                if self._cancel_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

        self._finalize_state()
        return self._progress

    def move(self, src_list: List[str], dst_dir: str) -> OperationProgress:
        """移动文件/目录列表到目标目录

        同盘直接 rename，跨盘先复制再删除源文件。

        Args:
            src_list: 源路径列表
            dst_dir: 目标目录

        Returns:
            OperationProgress: 操作进度结果
        """
        self._reset_state()
        self._state = OpState.RUNNING
        logger.info(f"开始移动: {len(src_list)} 个项目 -> {dst_dir}")

        os.makedirs(dst_dir, exist_ok=True)

        same_drive_items = []
        cross_drive_items = []

        for src in src_list:
            if self._same_drive(src, dst_dir):
                same_drive_items.append(src)
            else:
                cross_drive_items.append(src)

        # 同盘：直接 rename
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
                src_size = 0
                p = Path(dst)
                if p.is_file():
                    src_size = p.stat().st_size
                elif p.is_dir():
                    src_size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                fp.copied_bytes = src_size
                fp.total_bytes = src_size
                with self._lock:
                    self._progress.completed_files += 1
                    self._progress.copied_bytes += src_size
            except Exception as e:
                fp.error = str(e)
                logger.error(f"重命名失败: {src} -> {dst}, 错误: {e}")
                with self._lock:
                    self._progress.failed_files += 1
                    self._progress.completed_files += 1
            self._notify_progress()

        # 跨盘：先复制再删除
        if cross_drive_items:
            copy_progress = self.copy(cross_drive_items, dst_dir)
            # 复制完成后删除源文件
            if copy_progress.state != OpState.CANCELLED:
                for fp in copy_progress.file_progresses:
                    if fp.done and fp.error is None:
                        try:
                            if os.path.isdir(fp.src):
                                shutil.rmtree(fp.src)
                            else:
                                os.remove(fp.src)
                        except Exception as e:
                            logger.error(f"删除源文件失败: {fp.src}, 错误: {e}")

        self._finalize_state()
        return self._progress

    def delete(self, file_list: List[str], permanent: bool = False) -> OperationProgress:
        """删除文件/目录列表

        Args:
            file_list: 要删除的路径列表
            permanent: True 时覆写后彻底删除，False 时移到回收站

        Returns:
            OperationProgress: 操作进度结果
        """
        self._reset_state()
        self._state = OpState.RUNNING
        mode = "永久" if permanent else "回收站"
        logger.info(f"开始删除({mode}): {len(file_list)} 个项目")

        self._progress.total_files = len(file_list)

        for src in file_list:
            if not self._check_pause_cancel():
                break
            fp = FileProgress(src=src, dst="")
            self._progress.file_progresses.append(fp)
            try:
                if permanent:
                    if os.path.isdir(src):
                        # 目录下每个文件覆写删除
                        for item in Path(src).rglob("*"):
                            if not self._check_pause_cancel():
                                break
                            if item.is_file():
                                self._overwrite_delete(str(item))
                        shutil.rmtree(src, ignore_errors=True)
                    else:
                        self._overwrite_delete(src)
                else:
                    self._recycle(src)
                fp.done = True
                with self._lock:
                    self._progress.completed_files += 1
            except Exception as e:
                fp.error = str(e)
                logger.error(f"删除失败: {src}, 错误: {e}")
                with self._lock:
                    self._progress.failed_files += 1
                    self._progress.completed_files += 1
            self._notify_progress()

        self._finalize_state()
        return self._progress

    def _recycle(self, path: str) -> None:
        """将文件/目录移到回收站"""
        import ctypes
        # 使用 Windows Shell API 移到回收站
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
        # pFrom 需要双 null 结尾
        fileop.pFrom = path + "\0"
        fileop.pTo = None
        fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
        fileop.fAnyOperationsAborted = False
        fileop.hNameMappings = None
        fileop.lpszProgressTitle = None

        result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
        if result != 0:
            raise OSError(f"SHFileOperationW 返回错误码: {result}")

    def pause(self):
        """暂停当前操作"""
        self._state = OpState.PAUSED
        self._pause_event.clear()
        logger.info("操作已暂停")

    def resume(self):
        """恢复当前操作"""
        self._state = OpState.RUNNING
        self._pause_event.set()
        logger.info("操作已恢复")

    def cancel(self):
        """取消当前操作"""
        self._cancel_event.set()
        self._pause_event.set()  # 解除暂停阻塞
        self._state = OpState.CANCELLED
        logger.info("操作已取消")

    def _reset_state(self):
        """重置操作状态"""
        self._state = OpState.PENDING
        self._pause_event.set()
        self._cancel_event.clear()
        self._progress = OperationProgress()

    def _finalize_state(self):
        """完成操作后设置最终状态"""
        if self._state != OpState.CANCELLED:
            self._state = OpState.COMPLETED
        logger.info(
            f"操作完成: 状态={self._state.name}, "
            f"成功={self._progress.completed_files - self._progress.failed_files}, "
            f"失败={self._progress.failed_files}"
        )

    def get_failed(self) -> List[FileProgress]:
        """获取失败的文件列表"""
        return [fp for fp in self._progress.file_progresses if fp.error is not None]
