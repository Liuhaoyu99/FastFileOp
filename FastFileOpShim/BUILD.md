# FastFileOpShim 编译说明

## 环境要求

- Visual Studio 2022 (v143 工具集)
- Windows 10 SDK
- ATL (Active Template Library)

## 编译步骤

### 方法一：使用 Visual Studio IDE

1. 打开 `FastFileOpShim.sln`
2. 选择配置：`Release | x64`
3. 生成 -> 生成解决方案
4. 输出文件位于 `Output\Release\FastFileOpShim.dll`

### 方法二：使用命令行

```cmd
:: 打开 Visual Studio 开发者命令提示符 (x64 Native Tools)

:: 进入项目目录
cd /d "path\to\FastFileOpShim"

:: 编译 Release 版本
msbuild FastFileOpShim.sln /p:Configuration=Release /p:Platform=x64

:: 输出文件位于 Output\Release\FastFileOpShim.dll
```

## 安装

1. 以管理员身份运行 `install.bat`
2. 或手动执行：
   ```cmd
   regsvr32 FastFileOpShim.dll
   ```

## 卸载

1. 以管理员身份运行 `uninstall.bat`
2. 或手动执行：
   ```cmd
   regsvr32 /u FastFileOpShim.dll
   ```

## 项目结构

```
FastFileOpShim/
├── FastFileOpShim.sln          # 解决方案文件
├── FastFileOpShim.vcxproj      # 项目文件
├── stdafx.h / stdafx.cpp       # 预编译头
├── dllmain.cpp                 # DLL 入口点
├── FastFileOpShim.idl          # IDL 接口定义
├── FastFileOpShim.rc           # 资源文件
├── resource.h                  # 资源 ID 定义
├── targetver.h                 # 目标版本定义
│
├── PipeClient.h / .cpp         # Named Pipe 通信模块
├── CopyHook.h / .cpp           # ICopyHook 实现
├── ContextMenu.h / .cpp        # IContextMenu 实现
├── DropTarget.h / .cpp         # IDropTarget 实现
├── ExplorerCommand.h / .cpp    # IExplorerCommand 实现
├── Utils.cpp                   # 辅助函数
│
├── CopyHook.rgs                # CopyHook 注册脚本
├── ContextMenu.rgs             # ContextMenu 注册脚本
├── DropTarget.rgs              # DropTarget 注册脚本
├── DeleteCommand.rgs           # DeleteCommand 注册脚本
│
├── install.bat                 # 安装脚本
├── uninstall.bat               # 卸载脚本
└── BUILD.md                    # 本文件
```

## IPC 协议

DLL 通过 Named Pipe `\\.\pipe\FastFileOpPipe` 与 Python 服务通信。

### 请求格式 (JSON)

```json
{"action":"copy","src":["C:\\path\\file1.txt","C:\\path\\file2.txt"],"dst":"D:\\target"}
```

支持的 action:
- `copy` - 复制操作
- `move` - 移动操作
- `delete` - 删除到回收站
- `delete_permanent` - 永久删除

### 响应格式 (JSON)

```json
{"status":"ok","failed":[]}
```

或

```json
{"status":"error","failed":["C:\\path\\failed_file.txt"]}
```

## 注意事项

1. **必须编译为 64 位 DLL**，因为现代 Windows 资源管理器是 64 位进程
2. **需要管理员权限**才能注册/注销 COM 组件
3. **Python 服务必须在线**，否则 DLL 会回退到系统默认行为
4. 注册后可能需要**重启资源管理器**或**注销/重启系统**才能生效

## 已知限制

1. ICopyHook 只能拦截文件夹操作，不能拦截文件操作
2. 拖拽操作需要目标文件夹支持 IDropTarget 接口
3. 部分第三方文件管理器可能不支持这些 Shell 扩展接口
4. 异步 IPC 操作有超时限制，避免阻塞资源管理器
