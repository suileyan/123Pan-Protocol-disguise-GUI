# 123Pan GUI（PySide6）

![App 图标](favicon.png)

一个基于 PySide6 的 123 云盘非官方桌面工具。  
支持 **Web/Android** 两种协议、目录浏览、上传/删除、分享/直链、批量下载（带下载管理器：暂停/继续/取消/并发）。

> ⚠️ 免责声明：本项目仅做学习与个人备份用途，请遵循 123 云盘的服务条款与当地法律法规。不要用于任何商业或侵权场景。

---

## ✨ 功能特性

- Web / Android 协议切换
- 登录 / 自动登录
- 目录浏览、返回上级/回到根目录、创建文件夹、上传、删除
- 分享链接、批量获取直链（支持多选）
- 下载管理器：并行下载、进度/速度、暂停/继续/取消、删除记录
- UI 语言：中文 / English
- 鼠标侧键导航：前进 / 后退（后退=上级目录）

---

## 🗂 项目结构

```
project-root/
├─ app.py                 # 主程序（PySide6 GUI）
├─ favicon.ico            # 程序图标（Windows 优先）
├─ favicon.svg            # SVG 图标（备用/渲染多尺寸）
├─ tools/                 # 适配层所需的工具脚本
│  ├─ web.py              # 来自上游仓库：Web 协议客户端
│  ├─ android.py          # 来自上游仓库：Android 协议客户端
│  └─ sign_py.py          # 可能被 web.py 引用（若存在）
├─ config/                # 运行后生成（凭证/设置），打包时无需包含
│  ├─ 123pan.txt          # 登录凭证（JSON）
│  └─ app_settings.json   # 应用设置（JSON）
└─ requirements.txt       # 依赖（可选）
```

- `tools/` 目录取自上游仓库：<https://github.com/tosasitill/123pan>  
  请把 `web.py / android.py`（以及若存在 `sign_py.py`）放到 `tools/` 目录下。

---

## 🧰 环境要求

- Python 3.10 – 3.12（推荐）
- Windows / macOS / Linux（开发与打包以 Windows 为主）
- 依赖库：
  - `PySide6`（含 `PySide6.QtSvg`）
  - `requests`
  - （打包）`pyinstaller`

**示例 `requirements.txt`：**
```
PySide6>=6.5
requests>=2.28
pyinstaller>=6.0
```

安装依赖：
```bash
pip install -r requirements.txt
# 或
pip install PySide6 requests pyinstaller
```

---

## 🚀 运行（源码）

```bash
python app.py
```

首次运行会在程序同级目录创建 `config/`：
- `config/123pan.txt`：保存账号（JSON）
- `config/app_settings.json`：应用设置（自动登录、协议、语言、下载目录、并发数等）

> Linux/macOS 会将配置保存在「当前脚本所在目录」；打包后为可执行文件同级目录。

---

## 📦 打包（Windows / PyInstaller）

打包指令（推荐）：

```bash
pyinstaller --noconfirm --clean --name 123pan --icon favicon.ico --noconsole --onefile   --add-data "favicon.ico;." --add-data "favicon.svg;."   --add-data "tools;tools"   --hidden-import PySide6.QtSvg   app.py
```

### 参数说明（关键点）
- `--add-data "tools;tools"`：把 `tools/` 目录打进可执行文件（**必须**）
- `--hidden-import PySide6.QtSvg`：显式包含 QtSvg 模块（图标渲染）
- `--onefile`：单文件分发；`--noconsole`：无控制台窗口
- 图标：Windows 优先 `.ico`，同时带上 `.svg` 以便渲染多尺寸

> 调试期可去掉 `--noconsole` 方便查看日志输出。

### 打包产物位置
- `dist/123pan.exe`（Windows）

> 若遇到杀软误报，请手动放行或将 `dist/` 目录加入白名单（见 FAQ）。

---

## 🧭 使用说明

### 登录与协议
- 顶部选择 **Protocol**（Android / Web），点击 **登录**
- 勾选 **自动登录** 则下次启动读取 `config/123pan.txt` 自动登录
- 切换协议会自动尝试用已保存账号静默登录

### 目录操作
- **Refresh** 刷新；**Up** 上级；**Root** 根目录
- 双击文件夹进入
- 鼠标侧键：后退=上级 / 前进=历史下一个

### 文件操作
- **New Folder** 创建文件夹
- **Upload** 上传本地文件（当前目录）
- **Delete** 删除所选
- **Share** 创建分享链接（可选提取码）
- **Get Link** 获取直链（支持多选；复制到剪贴板）

### 下载管理
- **Download**：为所选项生成直链并入队；会切换到下载页
- 支持并行：默认 2（设置里可改 1–10）
- 支持暂停/继续、取消、删除记录
- 悬浮圆形按钮（右下角）：文件页/下载页快速切换  
- Android 协议下，**文件夹** 可能会以 **zip** 打包下载（UI 会自动把目标文件名后缀设为 `.zip`）

### 设置
- **Settings**：下载目录 / 并行数
- 更改语言与协议的控件在顶部工具条

---

## ⚙️ 配置文件格式

`config/app_settings.json`（示例）：
```json
{
  "autoLogin": true,
  "protocol": "android",
  "language": "zh",
  "downloadDir": "D:/Downloads/123pan",
  "concurrentDownloads": 3
}
```

`config/123pan.txt`（示例）：
```json
{
  "userName": "your_account",
  "passWord": "your_password"
}
```

> Windows 之外的平台会尝试把配置文件权限收紧为 `0600`（若支持）。

---

## 🔌 tools 目录来源与说明

- 上游仓库：<https://github.com/tosasitill/123pan>
- 将仓库中的 `web.py`、`android.py`（以及若存在的 `sign_py.py`）复制到本项目的 `tools/` 目录
- 程序按 **如下顺序** 动态加载模块：
  1. `import tools.<mod>`
  2. 从 `_MEIPASS/tools/`（打包临时目录）或运行目录的 `tools/` 加载
  3. 顶层模块名（作为兜底）

> 若 `web.py` 内 `from sign_py import ...`，程序已注册别名，兼容 `tools/sign_py.py` 的位置。

---

## ❓ 常见问题（FAQ）

**Q1: 打包后运行报缺少 `tools.web` / `tools.android`？**  
A: 确认命令中包含 `--add-data "tools;tools"`，并且 `tools/` 目录里有 `web.py` / `android.py`（必要）及 `sign_py.py`（若上游使用到）。  

**Q2: 图标不显示或报 `QtSvg` 相关错误？**  
A: 确认依赖已装 `PySide6`，并在打包命令里加了 `--hidden-import PySide6.QtSvg`。  

**Q3: 下载报错 / 速度为 0？**  
A: 可能是网络/证书问题。公司代理环境下可尝试配置 `HTTPS_PROXY` / `REQUESTS_CA_BUNDLE`。也可升级 `certifi`：
```bash
pip install -U certifi
```

**Q4: 杀软误报怎么办？**  
A: PyInstaller 的单文件可执行容易被误报。**建议加入白名单**或改用 `--onedir` 打包分发。

**Q5: 控制台日志怎么看？**  
A: 开发/排错时移除 `--noconsole`，或直接 `python app.py` 运行查看终端输出。

**Q6: 提示 `AttributeError: 'MainWindow' object has no attribute 'do_download'`？**  
A: 请使用当前提供的 `app.py`（已包含 `do_download` 实现），或对旧版进行合并更新。

**Q7: macOS 打包图标？**  
A: 需准备 `.icns` 图标并使用 `--icon your.icns`；其余 `--add-data "tools:tools"`（冒号分隔）语法按平台调整。

---

## 🧪 快速自检

- 依赖检查：
```bash
python -c "import PySide6, requests; print('deps ok')"
```

- 工具脚本可见性：
```bash
python -c "import importlib; import sys; sys.path.append('tools'); import tools.web, tools.android; print('tools ok')"
```

- 运行检查：
```bash
python app.py
```

---

## 🤝 贡献

欢迎提交 PR / Issue（文档、Bug 修复、兼容性、UI 体验等）。  
在提交前请尽量复现并附上环境信息（OS、Python、PyInstaller 版本等）。

---

## 📝 许可证

- 本仓库遵循以学习/研究为目的的MIT开源许可  
- `tools/` 目录来源于上游仓库，**请遵循其原始许可证**：<https://github.com/tosasitill/123pan>

---
