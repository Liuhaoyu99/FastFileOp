"""FastFileOp - Localization (Chinese / English)

Every UI string in the entire application lives here.
"""

LANG_ZH = "zh"
LANG_EN = "en"

_STRINGS = {
    # ── Chinese ──────────────────────────────────────────────────
    LANG_ZH: {
        # ---- Main Window ----
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
        "status_col": "状态",
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
        "files_progress": "%d/%d 个文件  %.1f%%  %s",

        # ---- Settings Window ----
        "settings_title": "FastFileOp 设置",
        "engine_settings": "引擎设置",
        "buffer_size": "缓冲区大小:",
        "worker_threads": "工作线程数:",
        "interception_settings": "拦截设置",
        "intercept_copy": "拦截复制/移动 (Ctrl+C/X, Ctrl+V)",
        "intercept_delete": "拦截删除 (Delete, Shift+Delete)",
        "intercept_drag": "拦截拖放（需要 FastFileOpShim.dll）",
        "language": "语言",
        "security": "安全",
        "confirm_delete": "删除文件前显示确认对话框",
        "system_settings": "系统设置",
        "start_with_windows": "开机自启",
        "debug_mode": "调试模式（详细日志）",
        "save": "保存",
        "cancel_settings": "取消",
        "settings_saved": "设置已保存。",
        "settings_success": "成功",
        "settings_error": "保存设置失败: %s",
        "settings_error_title": "错误",

        # ---- Tray Menu ----
        "tray_status_active": "状态: 运行中",
        "tray_status_paused": "状态: 已暂停",
        "tray_open": "打开 FastFileOp...",
        "tray_view_log": "查看日志",
        "tray_pause": "暂停拦截",
        "tray_resume": "恢复拦截",
        "tray_settings": "设置...",
        "tray_dll_registered": "DLL: 已注册",
        "tray_register_dll": "注册 Shell 扩展...",
        "tray_exit": "退出",
        "tray_unstable": "状态: 不稳定",
        "tray_unstable_msg": "拦截已暂停",
        "tray_resume_interception": "恢复拦截",

        # ---- Operation Log ----
        "log_title": "FastFileOp - 操作日志",
        "log_close": "关闭",

        # ---- Progress Window ----
        "progress_title": "FastFileOp - %s",
        "progress_preparing": "准备中...",
        "progress_files": "%d / %d 个文件 (%.1f%%)",
        "progress_speed": "速度: %s/秒",
        "progress_eta": "剩余时间: %s",
        "progress_done_success": "操作成功完成！",
        "progress_done_fail": "操作失败",
        "progress_completed": "%d 个文件已处理",
        "progress_close": "关闭",

        # ---- Delete Confirmation ----
        "confirm_delete_title": "FastFileOp - 确认删除",
        "confirm_delete_msg": "确定要删除 %d 个项目吗？\n\n%s\n\n模式: %s",
        "delete_mode_recycle": "回收站",
        "delete_mode_permanent": "永久删除",
        "delete_cancelled": "删除已取消",

        # ---- Notifications ----
        "notify_copy": "复制",
        "notify_move": "移动",
        "notify_delete": "删除",
        "notify_deleting": "正在删除 %d 个项目（%s）",
        "notify_done": "完成 — %d 个文件（%s）",
        "notify_warning": "完成，%d 个文件失败",
        "notify_error": "操作失败: %s",
        "notify_first_run": "FastFileOp 已设置为开机自启。可以在设置中修改。",
        "notify_dll_missing": "Shell 扩展未注册。请以管理员身份运行以注册。",
    },

    # ── English ───────────────────────────────────────────────────
    LANG_EN: {
        # ---- Main Window ----
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
        "status_col": "Status",
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
        "files_progress": "%d/%d files  %.1f%%  %s",

        # ---- Settings Window ----
        "settings_title": "FastFileOp Settings",
        "engine_settings": "Engine Settings",
        "buffer_size": "Buffer Size:",
        "worker_threads": "Worker Threads:",
        "interception_settings": "Interception Settings",
        "intercept_copy": "Intercept Copy/Move (Ctrl+C/X, Ctrl+V)",
        "intercept_delete": "Intercept Delete (Delete, Shift+Delete)",
        "intercept_drag": "Intercept Drag & Drop (requires FastFileOpShim.dll)",
        "language": "Language",
        "security": "Security",
        "confirm_delete": "Show confirmation before deleting files",
        "system_settings": "System Settings",
        "start_with_windows": "Start with Windows",
        "debug_mode": "Debug Mode (verbose logging)",
        "save": "Save",
        "cancel_settings": "Cancel",
        "settings_saved": "Settings saved.",
        "settings_success": "Success",
        "settings_error": "Failed to save settings: %s",
        "settings_error_title": "Error",

        # ---- Tray Menu ----
        "tray_status_active": "Status: Active",
        "tray_status_paused": "Status: Paused",
        "tray_open": "Open FastFileOp...",
        "tray_view_log": "View Log",
        "tray_pause": "Pause Interception",
        "tray_resume": "Resume Interception",
        "tray_settings": "Settings...",
        "tray_dll_registered": "DLL: Registered",
        "tray_register_dll": "Register Shell Extension...",
        "tray_exit": "Exit",
        "tray_unstable": "Status: UNSTABLE",
        "tray_unstable_msg": "Interception paused due to errors",
        "tray_resume_interception": "Resume Interception",

        # ---- Operation Log ----
        "log_title": "FastFileOp - Operation Log",
        "log_close": "Close",

        # ---- Progress Window ----
        "progress_title": "FastFileOp - %s",
        "progress_preparing": "Preparing...",
        "progress_files": "%d / %d files (%.1f%%)",
        "progress_speed": "Speed: %s/s",
        "progress_eta": "Time remaining: %s",
        "progress_done_success": "Operation completed successfully!",
        "progress_done_fail": "Operation failed",
        "progress_completed": "%d files processed",
        "progress_close": "Close",

        # ---- Delete Confirmation ----
        "confirm_delete_title": "FastFileOp - Confirm Delete",
        "confirm_delete_msg": "Delete %d item(s)?\n\n%s\n\nMode: %s",
        "delete_mode_recycle": "Recycle Bin",
        "delete_mode_permanent": "Permanent",
        "delete_cancelled": "Delete cancelled",

        # ---- Notifications ----
        "notify_copy": "Copying",
        "notify_move": "Moving",
        "notify_delete": "Deleting",
        "notify_deleting": "Deleting %d items (%s)",
        "notify_done": "Done — %d files (%s)",
        "notify_warning": "Completed with %d failures",
        "notify_error": "Operation failed: %s",
        "notify_first_run": "FastFileOp has been set to start with Windows. You can change this in Settings.",
        "notify_dll_missing": "Shell extension not registered. Run as administrator to register.",
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
