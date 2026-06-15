"""FastFileOp - Localization (Chinese / English)"""

LANG_ZH = "zh"
LANG_EN = "en"

_STRINGS = {
    LANG_ZH: {
        "window_title": "FastFileOp",
        "copy_move": "复制 / 移动",
        "source": "源路径:",
        "target": "目标路径:",
        "browse": "浏览...",
        "options": "选项",
        "multi_workers": "多线程加速（SSD 优化，同时复制多个文件）",
        "override_newer": "仅当源文件更新或大小不同时覆盖（断点续传支持）",
        "mirror_folder": "在目标目录下创建与源目录同名的文件夹",
        "start": "开始",
        "pause": "暂停",
        "resume": "继续",
        "cancel": "取消",
        "file_progress": "文件进度",
        "file_name": "文件名",
        "file_size": "大小",
        "status": "状态",
        "status_copying": "复制中...",
        "ready": "就绪",
        "starting": "正在启动...",
        "completed_success": "操作成功完成",
        "completed_fail": "已完成，%d 个文件失败",
        "error_prefix": "错误:",
        "cancelled": "已取消",
        "warn_no_source": "请选择源路径。",
        "warn_no_target": "请选择目标路径。",
        "warn_source_not_exist": "源路径不存在:\n%s",
        "confirm_close_title": "确认",
        "confirm_close_msg": "正在执行操作，确定要关闭吗？",
        "speed": "速度",
        "files_progress": "%d/%d 个文件  %.1f%%  %s",
    },
    LANG_EN: {
        "window_title": "FastFileOp",
        "copy_move": "Copy / Move",
        "source": "Source:",
        "target": "Target:",
        "browse": "Browse...",
        "options": "Options",
        "multi_workers": "Multi-workers (SSD optimization, copy files simultaneously)",
        "override_newer": "Override only if newer or size differs (resume support)",
        "mirror_folder": "Create the same source folder under target directory",
        "start": "Start",
        "pause": "Pause",
        "resume": "Resume",
        "cancel": "Cancel",
        "file_progress": "File Progress",
        "file_name": "File Name",
        "file_size": "Size",
        "status": "Status",
        "status_copying": "Copying...",
        "ready": "Ready",
        "starting": "Starting...",
        "completed_success": "Completed successfully",
        "completed_fail": "Completed with %d failures",
        "error_prefix": "Error:",
        "cancelled": "Cancelled",
        "warn_no_source": "Please select a source path.",
        "warn_no_target": "Please select a target path.",
        "warn_source_not_exist": "Source path does not exist:\n%s",
        "confirm_close_title": "Confirm",
        "confirm_close_msg": "An operation is in progress. Close anyway?",
        "speed": "Speed",
        "files_progress": "%d/%d files  %.1f%%  %s",
    },
}


def get_text(key: str, lang: str = LANG_EN) -> str:
    """Get localized string by key and language code"""
    table = _STRINGS.get(lang, _STRINGS[LANG_EN])
    return table.get(key, key)


def get_available_languages():
    """Return list of (code, display_name) tuples"""
    return [
        (LANG_ZH, "中文"),
        (LANG_EN, "English"),
    ]
