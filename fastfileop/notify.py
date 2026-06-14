"""FastFileOp - Windows Toast Notification Module

Shows Windows 10/11 toast notifications for file operations.
Uses PowerShell to call Windows Runtime Toast API (no extra dependencies).
"""

import logging
import subprocess
import threading

logger = logging.getLogger(__name__)


def show_toast(title: str, message: str, tag: str = ""):
    """Show a Windows toast notification

    Args:
        title: Notification title
        message: Notification body text
        tag: Optional tag to replace previous notification with same tag
    """
    def _show():
        try:
            ps_script = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null

$template = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>{_escape_xml(title)}</text>
            <text>{_escape_xml(message)}</text>
        </binding>
    </visual>
    <audio src="ms-winsoundevent:Notification.Default"/>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("FastFileOp")
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
{f'$toast.Tag = "{tag}"' if tag else ''}
$notifier.Show($toast)
'''
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
                 "-Command", ps_script],
                capture_output=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0x08000000,
            )
        except Exception as e:
            logger.debug(f"Toast notification error: {e}")

    # Run in background thread to avoid blocking
    t = threading.Thread(target=_show, daemon=True)
    t.start()


def _escape_xml(text: str) -> str:
    """Escape special XML characters"""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))
