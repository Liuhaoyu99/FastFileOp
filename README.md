# FastFileOp - 高速文件操作工具

替代 Windows 系统默认的文件复制、移动和删除操作，改用自定义的高速多线程引擎执行。

## 功能特性

- **高速文件操作引擎**：多线程并发，大文件分块读写（默认 64MB 缓冲区）
- **Ctrl+C / Ctrl+V 接管**：在资源管理器中自动拦截粘贴，使用高速引擎复制/移动
- **Delete / Shift+Delete 接管**：拦截删除操作，支持移到回收站或永久删除（覆写后删除）
- **系统托盘图标**：右键菜单可暂停/恢复拦截、打开设置、退出
- **设置窗口**：缓冲区大小、线程数、各操作独立开关、开机自启

## 项目结构

```
fastfileop/
├── fastfileop/
│   ├── __init__.py      # 包初始化
│   ├── __main__.py      # 主入口，协调各模块
│   ├── engine.py        # 高速文件操作引擎
│   ├── clipboard.py     # 剪贴板监控（CF_HDROP）
│   ├── hook.py          # 全局键盘钩子（WH_KEYBOARD_LL）
│   ├── shell.py         # Shell COM 集成（获取选中文件）
│   ├── config.py        # 配置管理
│   ├── logger.py        # 日志模块
│   ├── tray.py          # 系统托盘
│   └── settings.py      # 设置窗口（tkinter）
├── requirements.txt
├── .gitignore
└── README.md
```

## 安装

```bash
# 克隆项目
git clone <repo-url> fastfileop
cd fastfileop

# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

## 运行

```bash
# 直接运行
python -m fastfileop

# 或
python fastfileop/__main__.py
```

## 打包

### PyInstaller

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name FastFileOp fastfileop/__main__.py
```

### Nuitka

```bash
pip install nuitka
python -m nuitka --onefile --windows-disable-console --output-filename=FastFileOp.exe fastfileop/__main__.py
```

## 使用说明

1. 启动后程序在系统托盘显示图标
2. 在资源管理器中使用 Ctrl+C / Ctrl+X 复制或剪切文件
3. 在目标目录按 Ctrl+V 粘贴，程序自动接管操作
4. 在资源管理器中选中文件后：
   - 按 Delete 移到回收站
   - 按 Shift+Delete 永久删除（覆写后删除）
5. 右键托盘图标可暂停/恢复拦截、修改设置或退出

## 配置

配置文件位于 `%APPDATA%\FastFileOp\config.json`，可通过设置窗口修改：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| buffer_size | 67108864 (64MB) | 文件读写缓冲区大小 |
| max_workers | 4 | 最大并发线程数 |
| intercept_copy | true | 是否接管复制操作 |
| intercept_move | true | 是否接管移动操作 |
| intercept_delete | true | 是否接管删除操作 |
| auto_start | false | 是否开机自启 |

## 日志

日志文件位于 `%APPDATA%\FastFileOp\logs\fastfileop.log`，自动轮转（5MB × 5 份）。

## 已知限制

1. **拖拽操作无法拦截**：Windows 拖拽操作不经过键盘钩子，无法被本工具接管
2. **第三方文件管理器不兼容**：仅支持 Windows 资源管理器（CabinetWClass / ExploreWClass 窗口类），如 Total Commander、Directory Opus 等第三方文件管理器不受支持
3. **剪贴板格式依赖**：依赖 CF_HDROP 和 Preferred DropEffect 剪贴板格式，部分应用可能不遵循此格式
4. **UAC 权限**：操作需要管理员权限的文件时会失败
5. **网络路径**：UNC 路径（如 `\\server\share`）的支持有限
6. **长路径**：超过 260 字符的路径可能需要特殊处理
7. **文件锁定**：被其他进程锁定的文件无法操作
8. **快捷方式**：.lnk 快捷方式文件的处理与资源管理器行为可能不同
9. **键盘钩子冲突**：与其他使用全局键盘钩子的软件可能存在冲突
10. **COM 初始化**：Shell COM 接口需要在 STA 线程中使用，多线程环境下需注意

## 技术栈

- Python 3.11+
- pywin32 - Windows API 调用
- pystray + Pillow - 系统托盘图标
- tkinter - 设置界面（Python 内置）
- ctypes - 底层 Windows API 调用

## 许可证

MIT License
