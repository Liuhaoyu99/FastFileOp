# FastFileOp Manual Test Guide

This guide covers manual testing for keyboard hooks and DLL integration.

## Prerequisites

1. FastFileOp installed and running
2. Test files/folders prepared
3. Log viewer (e.g., Notepad, tail -f)

---

## Part 1: Keyboard Hook Testing

### Test 1.1: Copy/Paste Hook (Ctrl+C, Ctrl+V)

**Steps:**
1. Start FastFileOp
2. Open Explorer, navigate to a folder with test files
3. Select a file (or multiple files)
4. Press `Ctrl+C` (copy)
5. Navigate to a different folder
6. Press `Ctrl+V` (paste)

**Expected Result:**
- Check log file: `%LOCALAPPDATA%\FastFileOp\logs\fastfileop.log`
- Should see: `Hook: Copy X items -> [destination]`
- File should appear in destination

**How to verify it's using FastFileOp engine:**

Method A - Log Check:
```
# Open log file
notepad %LOCALAPPDATA%\FastFileOp\logs\fastfileop.log

# Look for entries like:
# [INFO] Hook: Copy 3 items -> D:\Destination
# [INFO] Progress: 45.2% (1/3) - filename.txt
```

Method B - Large File Test:
1. Create a 500MB+ test file
2. Copy using Ctrl+C, Ctrl+V
3. Watch the destination folder
4. FastFileOp should show faster copy than Windows default
5. Log should show progress updates

### Test 1.2: Cut/Paste Hook (Ctrl+X, Ctrl+V)

**Steps:**
1. Select files in Explorer
2. Press `Ctrl+X` (cut)
3. Navigate to destination
4. Press `Ctrl+V` (paste)

**Expected Result:**
- Log should show: `Hook: Move X items -> [destination]`
- Original files should be removed after move

### Test 1.3: Delete Hook (Delete key)

**Steps:**
1. Select files in Explorer
2. Press `Delete`

**Expected Result:**
- Log should show: `Hook: Delete X items (recycle)`
- Files should move to Recycle Bin

### Test 1.4: Permanent Delete (Shift+Delete)

**Steps:**
1. Select files in Explorer
2. Press `Shift+Delete`
3. Confirm deletion dialog

**Expected Result:**
- Log should show: `Hook: Delete X items (permanent)`
- Files should be permanently deleted (not in Recycle Bin)

### Test 1.5: Pause/Resume Interception

**Steps:**
1. Right-click tray icon
2. Select "Pause"
3. Try copy/paste operation
4. Right-click tray icon
5. Select "Resume"
6. Try copy/paste operation again

**Expected Result:**
- When paused: operations use Windows default (no log entries)
- When resumed: operations use FastFileOp (log entries appear)

---

## Part 2: DLL Shell Extension Testing

### Prerequisites
- FastFileOpShim.dll must be registered
- Run as Administrator: `regsvr32 FastFileOpShim.dll`

### Test 2.1: Verify DLL Registration

**Steps:**
1. Open Registry Editor (regedit)
2. Navigate to: `HKEY_CLASSES_ROOT\Directory\shellex\CopyHookHandlers`
3. Look for `FastFileOp.CopyHook`

**Alternative - Command Line:**
```cmd
reg query "HKCR\Directory\shellex\CopyHookHandlers\FastFileOp.CopyHook"
```

### Test 2.2: DLL Communication Test

**Steps:**
1. Start FastFileOp
2. Check log for: `Named pipe server started`
3. Try copying a folder in Explorer
4. Check log for pipe communication entries

**Expected Log:**
```
[INFO] Named pipe server started: \\.\pipe\FastFileOpPipe
[INFO] Pipe client connected
[INFO] Received request: copy ...
```

### Test 2.3: Drag & Drop (if implemented)

**Steps:**
1. Drag a file from one folder to another
2. Check if operation is intercepted

**Note:** Drag & drop interception requires IDropTarget implementation in DLL.

---

## Part 3: Troubleshooting Guide

### Problem: Keyboard hooks not working

**Checklist:**
1. [ ] Is FastFileOp running? Check Task Manager.
2. [ ] Is the hook enabled in Settings?
3. [ ] Is interception paused? Check tray icon status.
4. [ ] Check log for errors: `Keyboard hook started`

**Solution:**
- Restart FastFileOp
- Check if another app is blocking hooks (some security software)
- Run as Administrator if needed

### Problem: DLL not registered

**Symptoms:**
- No shell extension entries in registry
- Drag & drop not intercepted

**Solution:**
```cmd
# Run as Administrator
cd "C:\Program Files\FastFileOp"
regsvr32 FastFileOpShim.dll
```

**Verify:**
```cmd
reg query "HKCR\Directory\shellex\CopyHookHandlers\FastFileOp.CopyHook"
```

### Problem: Pipe connection failed

**Symptoms:**
- DLL cannot communicate with Python
- Log shows pipe errors

**Checklist:**
1. [ ] Is FastFileOp running?
2. [ ] Check log: `Named pipe server started`
3. [ ] Is another instance running? (only one allowed)

**Solution:**
- Kill any existing FastFileOp processes
- Restart FastFileOp
- Check Windows Firewall (rarely blocks named pipes)

### Problem: Operations still use Windows default

**Diagnosis:**
1. Check if hook is enabled in Settings
2. Check if "Paused" status in tray
3. Check log for hook activation

**Log entries to look for:**
```
[INFO] Keyboard hook started
[INFO] Hook: Copy X items -> ...
```

If these entries don't appear:
- Hook may be disabled in config
- Another application may have blocked the hook
- Try restarting FastFileOp

### Problem: Permission denied errors

**Symptoms:**
- File operations fail
- Log shows "Access denied"

**Solution:**
- Run FastFileOp as Administrator
- Check file/folder permissions
- Disable antivirus temporarily to test

---

## Part 4: Performance Comparison Test

### Test Setup

1. Create a 1GB test file:
```cmd
fsutil file createnew C:\test\bigfile.bin 1073741824
```

2. Or use multiple smaller files:
```cmd
# Create 100 files of 10MB each
for /L %i in (1,1,100) do fsutil file createnew C:\test\file%i.bin 10485760
```

### Test Procedure

**Test A: Windows Default**
1. Close FastFileOp
2. Copy test files using Ctrl+C, Ctrl+V
3. Record time

**Test B: FastFileOp**
1. Start FastFileOp
2. Copy same test files using Ctrl+C, Ctrl+V
3. Record time
4. Check log for operation details

### Expected Results

FastFileOp should be faster due to:
- Larger buffer size (64MB default)
- Multi-threaded operations
- Optimized I/O patterns

**Log Analysis:**
```
[INFO] Hook: Copy 100 items -> D:\Destination
[INFO] Progress: 10.5% (10/100) - file10.bin
...
[INFO] Copy completed: 100 files, 1.0 GB, 5.2s (192 MB/s)
```

---

## Part 5: System Tray Testing

### Test 5.1: Tray Icon Visibility

**Steps:**
1. Start FastFileOp
2. Check system tray (may need to click ^ to expand)
3. Look for blue icon with "F"

**Expected:**
- Icon visible in tray
- Hover shows "FastFileOp - High-Speed File Operations"

### Test 5.2: Tray Menu

**Steps:**
1. Right-click tray icon
2. Verify menu items:
   - Status: Active/Paused
   - Pause/Resume
   - Settings...
   - Exit

### Test 5.3: Settings Window

**Steps:**
1. Right-click tray icon
2. Select "Settings..."
3. Verify all controls visible and functional

### Test 5.4: Exit via Tray

**Steps:**
1. Right-click tray icon
2. Select "Exit"
3. Verify process terminates

---

## Part 6: Auto-Start Testing

### Test 6.1: Verify Auto-Start Registration

**Registry Check:**
```cmd
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v FastFileOp
```

**Expected:**
- Value exists pointing to FastFileOp.exe

### Test 6.2: Test Auto-Start

**Steps:**
1. Enable "Start with Windows" in Settings
2. Restart Windows
3. Check if FastFileOp starts automatically

---

## Quick Reference: Log File Location

```
%LOCALAPPDATA%\FastFileOp\logs\fastfileop.log
```

**Open in Notepad:**
```cmd
notepad %LOCALAPPDATA%\FastFileOp\logs\fastfileop.log
```

**Tail (continuous view) - PowerShell:**
```powershell
Get-Content "$env:LOCALAPPDATA\FastFileOp\logs\fastfileop.log" -Wait
```

---

## Test Checklist Summary

- [ ] Keyboard hook: Copy (Ctrl+C, Ctrl+V)
- [ ] Keyboard hook: Move (Ctrl+X, Ctrl+V)
- [ ] Keyboard hook: Delete (Delete)
- [ ] Keyboard hook: Permanent Delete (Shift+Delete)
- [ ] Keyboard hook: Pause/Resume
- [ ] DLL: Registration verified
- [ ] DLL: Pipe communication
- [ ] Tray: Icon visible
- [ ] Tray: Menu functional
- [ ] Tray: Settings accessible
- [ ] Auto-start: Registry entry
- [ ] Performance: Faster than Windows default
