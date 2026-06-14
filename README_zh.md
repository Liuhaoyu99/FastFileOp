# FastFileOp

**替换 Windows 默认的复制、移动、删除操作，使用高速多线程引擎。速度提升 2.5-4 倍。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](https://www.microsoft.com/windows)

## 功能特性

- 🚀 **高速文件操作** - 多线程引擎配合 64MB 缓冲区，SSD 上可达 318 MB/s
- ⌨️ **键盘钩子集成** - 无缝拦截资源管理器中的 Ctrl+C/X/V 和 Delete 键
- 🔄 **Shell 扩展 DLL** - C++ COM 组件，用于拦截拖放操作
- 📊 **系统托盘界面** - 实时状态、暂停/恢复、设置 GUI
- 🔁 **开机自启支持** - 自动随 Windows 启动
- 🛡️ **看门狗机制** - 管道断开后自动恢复
- 🗑️ **安全删除** - 3 次覆写永久删除
- ⏯️ **操作控制** - 暂停、恢复、取消正在进行的操作

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Windows 资源管理器                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Ctrl+C/V   │  │   Delete    │  │      拖放操作           │  │
│  │   快捷键    │  │    键       │  │                         │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastFileOp 组件                                │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │  键盘钩子    │    │ Shell 扩展   │    │   剪贴板监控     │   │
│  │  (Python)    │    │  DLL (C++)   │    │                  │   │
│  └──────┬───────┘    └──────┬───────┘    └────────┬─────────┘   │
│         │                   │                     │             │
│         │                   ▼                     │             │
│         │         ┌──────────────────┐            │             │
│         │         │    命名管道      │            │             │
│         │         │ \\.\pipe\FFOPipe │            │             │
│         │         └────────┬─────────┘            │             │
│         │                  │                      │             │
│         ▼                  ▼                      ▼             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    文件操作引擎                          │   │
│  │            (多线程, 64MB 缓冲区)                         │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │   │
│  │  │  复制   │  │  移动   │  │  删除   │  │  安全删除   │  │   │
│  │  │         │  │         │  │(回收站) │  │  (3次覆写)  │  │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│  ┌───────────────────────────┴───────────────────────────┐     │
│  │                     系统托盘                           │     │
│  │    状态 │ 暂停/恢复 │ 设置 │ 退出                      │     │
│  └───────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## 性能对比

| 指标 | FastFileOp | Windows 默认 | 提升 |
|------|------------|-------------|------|
| 100MB 复制速度 | **318 MB/s** | ~80-120 MB/s | **2.5-4 倍** |
| 缓冲区大小 | 64 MB | 8-64 KB | 减少系统调用 |
| 工作线程数 | 4 (可配置) | 1 | 并行 I/O |
| 大文件复制 | 优化 | 标准 | 显著提升 |

### 基准测试结果

```
测试: NVMe SSD 上复制 100MB 文件
FastFileOp: 0.31s (318.4 MB/s)
Windows 默认: ~1.0-1.2s (~80-100 MB/s)
```

## 安装

### 前置要求

- Windows 10/11 (64位)
- Python 3.11+ (从源码运行需要)
- MinGW-w64 (从源码编译 DLL 需要)

### 快速安装

1. 下载最新版本
2. 以管理员身份运行 `install.bat`
3. 重启 Windows 资源管理器 (或注销/登录)

```batch
# 以管理员身份运行
install.bat
```

### 手动安装

```batch
# 1. 编译可执行文件
build.bat

# 2. 安装到 Program Files
install.bat

# 3. 注册 Shell 扩展
regsvr32 "C:\Program Files\FastFileOp\FastFileOpShim.dll"
```

## 卸载

```batch
# 以管理员身份运行
uninstall.bat
```

这将：
- 注销 Shell 扩展 DLL
- 从 Program Files 删除文件
- 清理注册表项
- 移除开机自启项

## 杀毒软件白名单设置

部分杀毒软件（如 360、Windows Defender）可能会将键盘钩子或 Shell 扩展标记为可疑。解决方法：

### 360 杀毒

1. 打开 360 安全中心
2. 进入 **病毒查杀** → **信任区**
3. 添加以下文件到白名单：
   - `C:\Program Files\FastFileOp\FastFileOp.exe`
   - `C:\Program Files\FastFileOp\FastFileOpShim.dll`

### Windows Defender

1. 打开 Windows 安全中心
2. 进入 **病毒和威胁防护** → **排除项**
3. 添加 FastFileOp 文件夹

## 已知限制

1. **拖放操作** 需要注册 C++ Shell 扩展 DLL
2. **安装** 需要管理员权限
3. **杀毒软件** 可能将键盘钩子检测为键盘记录器（误报）
4. **安装时** 可能出现 UAC 提示
5. **部分应用** 使用自定义拖放处理器，可能无法被拦截

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端引擎 | Python 3.11+ |
| Shell 扩展 | C++ (Win32 API, COM) |
| 进程间通信 | 命名管道 |
| 键盘钩子 | WH_KEYBOARD_LL |
| 剪贴板 | CF_HDROP 格式 |
| 图形界面 | tkinter + pystray |
| 构建 | PyInstaller + MinGW-w64 |

## 项目结构

```
FastFileOp/
├── fastfileop/              # Python 包
│   ├── __main__.py          # 入口点
│   ├── engine.py            # 文件操作引擎
│   ├── pipe_server.py       # 命名管道服务器
│   ├── hook.py              # 键盘钩子
│   ├── clipboard.py         # 剪贴板监控
│   ├── tray.py              # 系统托盘
│   ├── config.py            # 配置管理
│   └── settings.py          # 设置界面
├── FastFileOpShim/          # C++ Shell 扩展
│   ├── CopyHook.cpp         # ICopyHook 实现
│   ├── PipeClient.cpp       # 命名管道客户端
│   └── dllmain.cpp          # DLL 入口
├── tests/                   # 测试套件
│   ├── test_engine.py       # 引擎单元测试
│   ├── test_pipe.py         # 管道通信测试
│   └── test_manual_guide.md # 手动测试指南
├── build.bat                # 构建脚本
├── install.bat              # 安装脚本
├── uninstall.bat            # 卸载脚本
├── requirements.txt         # Python 依赖
└── README.md                # 本文件
```

## 开发

### 从源码构建

```batch
# 编译 Python 可执行文件
python -m PyInstaller --onefile --windowed --name FastFileOp main.py

# 编译 C++ DLL (需要 MinGW-w64)
g++ -shared -o FastFileOpShim.dll -static-libgcc -static-libstdc++ ^
    FastFileOpShim/*.cpp -lole32 -lshell32 -luuid -luser32
```

### 运行测试

```batch
# 引擎测试
python tests/test_engine.py

# 管道测试 (需要先启动服务器)
python -m fastfileop
python tests/test_pipe.py
```

## 贡献

欢迎贡献代码！请随时提交 Pull Request。

## 许可证

本项目采用 MIT 许可证 - 详情见 [LICENSE](LICENSE) 文件。

## 作者

**刘浩宇 (BakerLiu)**

---

⭐ 如果这个项目对你有帮助，请给个 Star！
