import os
import sys
import json
import shutil
import threading
import time
from datetime import datetime

# NOTE(pyinstaller): 预导入常见模块，减少打包后缺失概率
try:
    import uuid as _pyi_uuid
    import hashlib as _pyi_hashlib
    import hmac as _pyi_hmac
    import base64 as _pyi_base64
    import random as _pyi_random
    import urllib.parse as _pyi_urllib_parse
    import zlib as _pyi_zlib
    import gzip as _pyi_gzip
except Exception:
    pass

from PySide6.QtCore import Qt, QThread, Signal, QObject, QEvent, QTimer, QSize, QRectF, QPoint
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QFileDialog, QLineEdit, QDialog, QDialogButtonBox,
    QMessageBox, QProgressBar, QInputDialog, QCheckBox, QHeaderView, QSpinBox,
    QFormLayout, QStackedWidget
)
from PySide6.QtGui import QPalette, QColor, QIcon, QPixmap, QPainter, QBrush, QLinearGradient

# NOTE(runtime paths): _MEIPASS 为 PyInstaller 解包目录；RUN_DIR 为可写目录
FROZEN = getattr(sys, "frozen", False)
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
RUN_DIR = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.abspath(__file__))

APP_ICON_SVG = os.path.join(BASE_DIR, "favicon.svg")
APP_ICON_ICO = os.path.join(BASE_DIR, "favicon.ico")

CONFIG_DIR = os.path.join(RUN_DIR, "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "123pan.txt")
ROOT_123_FILE = os.path.join(RUN_DIR, "123pan.txt")
CONFIG_SETTINGS = os.path.join(CONFIG_DIR, "app_settings.json")

# NOTE(QtSvg is optional): 没有 QtSvg 也能跑，用占位图标兜底
try:
    from PySide6.QtSvg import QSvgRenderer
    _HAS_QTSVG = True
except Exception:
    _HAS_QTSVG = False

STYLE_QSS = """
* { font-family: "Microsoft YaHei UI","PingFang SC","Segoe UI","Helvetica Neue",Arial; font-size: 13px; }
QMainWindow { background: #101114; }
QStatusBar { background: #0f1115; color: #d0d3d7; border-top: 1px solid #23252b; }
QToolTip { color: #e6e9ef; background: #2b2f36; border: 1px solid #3b4048; border-radius: 6px; padding: 4px 8px; }
QLabel, QCheckBox { color: #dfe4ea; }
QPushButton { color: #e6e9ef; background: #2a2f37; border: 1px solid #3a3f47; border-radius: 8px; padding: 6px 12px; }
QPushButton:hover { background: #333842; border-color: #4a505a; }
QPushButton:pressed { background: #1f2329; }
QPushButton:disabled { color: #8b9098; background: #20242b; border-color: #2c3139; }
#FabButton { background: #3b82f6; border: none; border-radius: 28px; color: #ffffff; padding: 0; }
#FabButton:hover { background: #2563eb; }
#FabButton:pressed { background: #1d4ed8; }
QComboBox { color: #e6e9ef; background: #23262e; border: 1px solid #3a3f47; border-radius: 6px; padding: 4px 8px; }
QComboBox:hover { background: #2a2e36; border-color: #4a505a; }
QComboBox QAbstractItemView { background: #1c1f25; color: #e6e9ef; selection-background-color: #3b82f6; selection-color: #ffffff; border: 1px solid #3a3f47; outline: 0; }
QLineEdit { color: #e6e9ef; background:#1c1f25; border:1px solid #3a3f47; border-radius:6px; padding:6px 8px; }
QLineEdit:focus { border-color: #3b82f6; }
QTableWidget { background: #15171c; alternate-background-color: #191c22; gridline-color: #2b3038; selection-background-color: #3b82f6; selection-color: #ffffff; }
QHeaderView::section { background: #111318; color: #bfc6d4; padding: 8px; border: 0; border-bottom: 1px solid #2b3038; }
QTableCornerButton::section { background: #111318; border: 0; border-bottom: 1px solid #2b3038; }
QProgressBar { background: #1b1e24; border:1px solid #31343c; border-radius: 6px; text-align: center; color:#dfe4ea; min-height: 10px; }
QProgressBar::chunk { background-color: #22c55e; border-radius: 6px; }
QMessageBox { background: #15171c; }
"""

def apply_app_theme(app: QApplication):
    app.setStyle("Fusion")
    palette = QPalette()
    bg, base, alt = QColor(20, 22, 27), QColor(28, 31, 37), QColor(25, 28, 34)
    text, btn, hi = QColor(223, 228, 234), QColor(42, 47, 55), QColor(59, 130, 246)
    palette.setColor(QPalette.Window, bg)
    palette.setColor(QPalette.WindowText, text)
    palette.setColor(QPalette.Base, base)
    palette.setColor(QPalette.AlternateBase, alt)
    palette.setColor(QPalette.Text, text)
    palette.setColor(QPalette.Button, btn)
    palette.setColor(QPalette.ButtonText, text)
    palette.setColor(QPalette.Highlight, hi)
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ToolTipBase, QColor(43, 47, 54))
    palette.setColor(QPalette.ToolTipText, text)
    palette.setColor(QPalette.Link, hi)
    app.setPalette(palette)
    app.setStyleSheet(STYLE_QSS)

# --- dynamic import (supports both source & bundled) ---
import importlib
import importlib.util

def _import_tools_module(mod_name: str, required: bool = True):
    # 1) import tools.<mod_name>
    try:
        return importlib.import_module(f"tools.{mod_name}")
    except Exception:
        pass
    # 2) try loading from file candidates
    candidates = [
        os.path.join(BASE_DIR, "tools", f"{mod_name}.py"),
        os.path.join(RUN_DIR,  "tools", f"{mod_name}.py"),
        os.path.join(BASE_DIR, "tools", f"{mod_name}.pyc"),
        os.path.join(RUN_DIR,  "tools", f"{mod_name}.pyc"),
    ]
    for py_path in candidates:
        if os.path.isfile(py_path):
            spec = importlib.util.spec_from_file_location(f"tools.{mod_name}", py_path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[f"tools.{mod_name}"] = mod
            assert spec.loader is not None
            spec.loader.exec_module(mod)
            return mod
    # 3) bare module name
    try:
        return importlib.import_module(mod_name)
    except Exception:
        pass
    if required:
        raise ImportError(
            "Cannot locate tools.{0}. 请在打包命令中加入 --add-data \"tools;tools\"".format(mod_name)
        )
    return None

# NOTE(compat): tools/web.py 可能直接 import sign_py，这里注册别名
try:
    _sign_py_pkg = _import_tools_module("sign_py", required=False)
    if _sign_py_pkg:
        sys.modules.setdefault("sign_py", _sign_py_pkg)
except Exception:
    pass

web_client = _import_tools_module("web")
android_client = _import_tools_module("android")

import requests

def human_size(num_bytes: int) -> str:
    try:
        size = int(num_bytes)
    except Exception:
        return str(num_bytes)
    return f"{round(size / (1024 * 1024), 2)}M" if size >= 1024 * 1024 else f"{round(size / 1024, 2)}K"

def _harden_config_file_permissions(path: str):
    try:
        if os.name == 'posix' and os.path.isfile(path):
            os.chmod(path, 0o600)
    except Exception:
        pass

def migrate_123pan_to_config() -> bool:
    # NOTE(migration): 将根目录旧版 123pan.txt 迁移到 config/ 下
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.isfile(ROOT_123_FILE):
            if os.path.exists(CONFIG_FILE):
                try: os.remove(CONFIG_FILE)
                except Exception: pass
            shutil.move(ROOT_123_FILE, CONFIG_FILE)
            _harden_config_file_permissions(CONFIG_FILE)
            return True
    except Exception:
        pass
    return False

def read_saved_creds() -> dict:
    try:
        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.loads(f.read() or "{}")
    except Exception:
        pass
    return {}

def load_settings() -> dict:
    try:
        if os.path.isfile(CONFIG_SETTINGS):
            with open(CONFIG_SETTINGS, "r", encoding="utf-8") as f:
                return json.loads(f.read() or "{}")
    except Exception:
        pass
    return {}

def ensure_settings_defaults(s: dict) -> dict:
    defaults = {
        "autoLogin": False,
        "protocol": "android",
        "language": "zh",
        "downloadDir": os.path.join(RUN_DIR, "download"),
        "concurrentDownloads": 2,
    }
    out = dict(defaults)
    for k, v in (s or {}).items():
        if k in defaults:
            out[k] = v
    return out

def write_settings(s: dict):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_SETTINGS, "w", encoding="utf-8") as f:
            f.write(json.dumps(s, ensure_ascii=False, indent=2))
        _harden_config_file_permissions(CONFIG_SETTINGS)
    except Exception:
        pass

# TODO(i18n): 后续考虑外置 JSON 资源、热切换
TRANSLATIONS = {
    'zh': {
        'title': '123云盘 工具', 'protocol': '协议', 'android': '安卓', 'web': '网页', 'login': '登录',
        'switch_account': '切换账号', 'refresh': '刷新', 'up': '上级', 'root': '根目录', 'mkdir': '新建文件夹',
        'upload': '上传', 'delete': '删除', 'share': '分享', 'link': '获取直链', 'download': '下载',
        'language': '语言', 'chinese': '中文', 'english': 'English', 'auto_login': '自动登录',
        'col_index': '编号', 'col_name': '名称', 'col_size': '大小', 'col_type': '类型', 'col_id': 'ID',
        'type_file': '文件', 'type_folder': '文件夹', 'login_title': '登录', 'username': '用户名', 'password': '密码',
        'ok': '确定', 'cancel': '取消', 'select_row_first': '请先选择一行', 'select_rows_first': '请至少选择一行',
        'enter_folder_name': '输入文件夹名称', 'mkdir_success': '创建成功', 'mkdir_failed': '创建失败',
        'choose_download_dir': '选择下载目录', 'download_start': '开始下载', 'download_done': '下载完成',
        'download_failed': '下载失败', 'share_pwd': '输入提取码（可留空）', 'share_ok': '分享成功',
        'share_failed': '分享失败', 'delete_confirm': '确认删除所选项？', 'yes': '是', 'no': '否',
        'not_logged_in': '请先登录', 'copied': '已复制', 'settings': '设置', 'download_dir': '下载位置',
        'browse': '浏览', 'concurrent_downloads': '并行下载数', 'downloads': '下载管理', 'back': '返回',
        'col_d_name': '名称', 'col_d_size': '大小', 'col_d_progress': '进度', 'col_d_speed': '速度',
        'col_d_status': '状态', 'col_d_actions': '操作', 'status_queued': '排队中', 'status_downloading': '下载中',
        'status_paused': '已暂停', 'status_done': '已完成', 'status_failed': '失败', 'status_canceled': '已取消',
        'pause': '暂停', 'resume': '继续', 'remove': '取消', 'delete_record': '删除记录',
        'show_downloads': '查看下载', 'back_to_files': '返回目录',
    },
    'en': {
        'title': '123Pan Tool', 'protocol': 'Protocol', 'android': 'Android', 'web': 'Web', 'login': 'Login',
        'switch_account': 'Switch account', 'refresh': 'Refresh', 'up': 'Up', 'root': 'Root', 'mkdir': 'New Folder',
        'upload': 'Upload', 'delete': 'Delete', 'share': 'Share', 'link': 'Get Link', 'download': 'Download',
        'language': 'Language', 'chinese': '中文', 'english': 'English', 'auto_login': 'Auto login',
        'col_index': 'Index', 'col_name': 'Name', 'col_size': 'Size', 'col_type': 'Type', 'col_id': 'ID',
        'type_file': 'File', 'type_folder': 'Folder', 'login_title': 'Login', 'username': 'Username', 'password': 'Password',
        'ok': 'OK', 'cancel': 'Cancel', 'select_row_first': 'Select a row first', 'select_rows_first': 'Select at least one row',
        'enter_folder_name': 'Enter folder name', 'mkdir_success': 'Folder created', 'mkdir_failed': 'Create folder failed',
        'choose_download_dir': 'Choose download directory', 'download_start': 'Start downloading', 'download_done': 'Download finished',
        'download_failed': 'Download failed', 'share_pwd': 'Enter share password (optional)', 'share_ok': 'Share created',
        'share_failed': 'Share failed', 'delete_confirm': 'Confirm delete selected items?', 'yes': 'Yes', 'no': 'No',
        'not_logged_in': 'Please login first', 'copied': 'Copied', 'settings': 'Settings', 'download_dir': 'Download directory',
        'browse': 'Browse', 'concurrent_downloads': 'Concurrent downloads', 'downloads': 'Downloads', 'back': 'Back',
        'col_d_name': 'Name', 'col_d_size': 'Size', 'col_d_progress': 'Progress', 'col_d_speed': 'Speed',
        'col_d_status': 'Status', 'col_d_actions': 'Actions', 'status_queued': 'Queued', 'status_downloading': 'Downloading',
        'status_paused': 'Paused', 'status_done': 'Completed', 'status_failed': 'Failed', 'status_canceled': 'Canceled',
        'pause': 'Pause', 'resume': 'Resume', 'remove': 'Cancel', 'delete_record': 'Delete Record',
        'show_downloads': 'Show downloads', 'back_to_files': 'Back to files',
    }
}

def load_app_icon() -> QIcon:
    # 优先 .ico（Windows 任务栏更稳）
    if sys.platform.startswith("win") and os.path.isfile(APP_ICON_ICO):
        ico = QIcon(APP_ICON_ICO)
        if not ico.isNull():
            return ico
    # 其次 svg（有 QtSvg 则渲染多尺寸）
    if os.path.isfile(APP_ICON_SVG):
        if _HAS_QTSVG:
            try:
                renderer = QSvgRenderer(APP_ICON_SVG)
                if renderer.isValid():
                    icon = QIcon()
                    for s in [16, 24, 32, 48, 64, 128, 256]:
                        pm = QPixmap(s, s); pm.fill(Qt.transparent)
                        p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
                        renderer.render(p, QRectF(0, 0, s, s)); p.end()
                        icon.addPixmap(pm)
                    return icon
            except Exception:
                pass
        ico = QIcon(APP_ICON_SVG)
        if not ico.isNull():
            return ico
    # 占位图标
    pm = QPixmap(256, 256); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, 256, 256)
    grad.setColorAt(0.0, QColor("#3b82f6")); grad.setColorAt(1.0, QColor("#1d4ed8"))
    p.setBrush(QBrush(grad)); p.setPen(Qt.NoPen)
    p.drawRoundedRect(16, 16, 224, 224, 48, 48)
    p.setPen(QColor(255, 255, 255, 230)); p.setBrush(Qt.NoBrush)
    p.drawLine(128, 70, 128, 162)
    p.drawPolyline([QPoint(128, 162), QPoint(168, 122), QPoint(88, 122), QPoint(128, 162)])
    p.end()
    return QIcon(pm)

class LoginDialog(QDialog):
    def __init__(self, lang='zh', parent=None, default_user='', default_pwd=''):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(TRANSLATIONS[self.lang]['login_title'])
        v = QVBoxLayout(self); v.setContentsMargins(18, 18, 18, 18); v.setSpacing(10)
        self.user_edit = QLineEdit()
        self.pwd_edit = QLineEdit(); self.pwd_edit.setEchoMode(QLineEdit.Password)
        self.user_edit.setText(default_user or ''); self.pwd_edit.setText(default_pwd or '')
        v.addWidget(QLabel(TRANSLATIONS[self.lang]['username'])); v.addWidget(self.user_edit)
        v.addWidget(QLabel(TRANSLATIONS[self.lang]['password'])); v.addWidget(self.pwd_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

    def set_lang(self, lang):  # TODO(i18n): 连带控件文本也动态刷新
        self.lang = lang
        self.setWindowTitle(TRANSLATIONS[self.lang]['login_title'])

    def get_values(self):
        return self.user_edit.text().strip(), self.pwd_edit.text()

class SettingsDialog(QDialog):
    def __init__(self, lang='zh', parent=None, download_dir='', concurrent=2):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(TRANSLATIONS[self.lang]['settings'])
        v = QVBoxLayout(self); v.setContentsMargins(18, 18, 18, 18); v.setSpacing(12)
        form = QFormLayout(); form.setContentsMargins(0, 0, 0, 0); form.setSpacing(8)
        self.dir_edit = QLineEdit(download_dir or '')
        self.dir_btn = QPushButton(TRANSLATIONS[self.lang]['browse'])
        h = QHBoxLayout(); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(8)
        h.addWidget(self.dir_edit, 1); h.addWidget(self.dir_btn, 0)
        w_dir = QWidget(); w_dir.setLayout(h)
        form.addRow(QLabel(TRANSLATIONS[self.lang]['download_dir']), w_dir)
        self.concurrent_spin = QSpinBox(); self.concurrent_spin.setRange(1, 10)
        self.concurrent_spin.setValue(max(1, int(concurrent or 2)))
        form.addRow(QLabel(TRANSLATIONS[self.lang]['concurrent_downloads']), self.concurrent_spin)
        v.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        v.addWidget(buttons)
        self.dir_btn.clicked.connect(self._choose_dir)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)

    def _choose_dir(self):
        cur = self.dir_edit.text().strip() or os.path.join(RUN_DIR, 'download')
        d = QFileDialog.getExistingDirectory(self, TRANSLATIONS[self.lang]['choose_download_dir'], cur)
        if d: self.dir_edit.setText(d)

    def get_values(self):
        return {"downloadDir": self.dir_edit.text().strip(), "concurrentDownloads": self.concurrent_spin.value()}

class DownloadThread(QThread):
    # NOTE: 简单 HTTP 下行器，支持暂停/继续/取消
    progress = Signal(int)
    stat = Signal(int, int, float)
    finished_ok = Signal(str)
    failed = Signal(str)
    canceled = Signal()

    def __init__(self, url: str, dest_path: str, chunk_size: int = 1024 * 128):
        super().__init__()
        self.url = url
        self.dest_path = dest_path
        self.chunk_size = chunk_size
        self._pause_flag = threading.Event()
        self._cancel_flag = threading.Event()

    def pause(self): self._pause_flag.set()
    def resume(self): self._pause_flag.clear()
    def cancel(self): self._cancel_flag.set()

    def run(self):
        tmp_path = self.dest_path + ".part"
        try:
            with requests.get(self.url, stream=True, timeout=15) as r:
                r.raise_for_status()
                total = int(r.headers.get('Content-Length', '0'))
                os.makedirs(os.path.dirname(self.dest_path), exist_ok=True)
                downloaded = 0
                last_t = time.time(); last_b = 0
                with open(tmp_path, 'wb') as f:
                    for chunk in r.iter_content(self.chunk_size):
                        if self._cancel_flag.is_set():
                            try:
                                f.close()
                                if os.path.exists(tmp_path): os.remove(tmp_path)
                            except Exception:
                                pass
                            self.canceled.emit(); return
                        while self._pause_flag.is_set() and not self._cancel_flag.is_set():
                            time.sleep(0.1)
                        if not chunk: continue
                        f.write(chunk); downloaded += len(chunk)
                        now = time.time(); dt = now - last_t
                        if dt >= 0.5:
                            db = downloaded - last_b
                            speed = db / dt if dt > 0 else 0.0
                            last_t = now; last_b = downloaded
                            self.progress.emit(int(downloaded * 100 / total) if total > 0 else 0)
                            self.stat.emit(downloaded, total, speed)
            os.replace(tmp_path, self.dest_path)
            if total == 0: self.progress.emit(100)
            self.stat.emit(downloaded, total, 0.0)
            self.finished_ok.emit(self.dest_path)
        except Exception as e:
            try:
                if os.path.exists(tmp_path): os.remove(tmp_path)
            except Exception:
                pass
            self.failed.emit(str(e))

class PanClientAdapter:
    """统一封装 web/android 客户端"""
    def __init__(self, protocol: str):
        self.protocol = protocol
        self._client = None

    def login(self, username: str, password: str):
        if self.protocol == 'web':
            self._client = web_client.Pan123(readfile=False, user_name=username, pass_word=password, input_pwd=False)
        else:
            self._client = android_client.Pan123(readfile=False, user_name=username, pass_word=password, input_pwd=False)
        return self.get_dir()

    def ensure(self):
        if self._client is None:
            raise RuntimeError('Not logged in')

    def get_dir(self):
        self.ensure()
        return self._client.get_dir()

    def current_list(self):
        self.ensure()
        return list(self._client.list or [])

    def cd_root(self):
        self.ensure()
        self._client.parent_file_id = 0
        self._client.parent_file_list = [0]
        return self._client.get_dir()

    def cd_up(self):
        self.ensure()
        if len(self._client.parent_file_list) > 1:
            self._client.parent_file_list.pop()
            self._client.parent_file_id = self._client.parent_file_list[-1]
        return self._client.get_dir()

    def cd_by_id(self, file_id: int):
        self.ensure()
        self._client.cdById(file_id)
        return self._client.get_dir()

    def link(self, index_zero_based: int) -> str:
        self.ensure()
        return self._client.link(index_zero_based, showlink=False)

    def mkdir(self, name: str):
        self.ensure()
        return self._client.mkdir(name)

    def delete_index(self, index_zero_based: int):
        self.ensure()
        return self._client.delete_file(index_zero_based)

    def upload(self, file_path: str):
        self.ensure()
        return self._client.up_load(file_path)

    def header_logined(self):
        self.ensure()
        return self._client.header_logined

    def get_path_list(self) -> list[int]:
        self.ensure()
        lst = list(self._client.parent_file_list or [])
        return lst if lst else [0]

    def nav_to_path(self, path_list: list[int]) -> int:
        self.ensure()
        if not path_list: path_list = [0]
        if path_list[0] != 0: path_list = [0] + list(path_list)
        self._client.parent_file_id = 0
        self._client.parent_file_list = [0]
        code = self._client.get_dir()
        if code != 0: return code
        for fid in path_list[1:]:
            self._client.cdById(fid)
            code = self._client.get_dir()
            if code != 0: return code
        return code

    def share(self, file_ids: list[int], pwd: str) -> dict:
        # NOTE(api): 直接调用 123pan 分享接口；请求头沿用已登录 header
        self.ensure()
        base_headers = self._client.header_logined or {}
        headers = {**base_headers, "Content-Type": "application/json;charset=utf-8"}
        url = "https://www.123pan.com/a/api/share/create"
        file_id_str = ",".join(str(fid) for fid in file_ids)
        payload = {
            "driveId": 0,
            "expiration": "2099-12-12T08:00:00+08:00",
            "fileIdList": file_id_str,
            "shareName": "我的分享",
            "sharePwd": pwd or "",
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=15)
            js = r.json()
            if js.get('code') == 0:
                key = js['data'].get('ShareKey', '')
                return {"ok": True, "url": f"https://www.123pan.com/s/{key}", "message": js.get('message', 'ok')}
            return {"ok": False, "url": "", "message": js.get('message', 'error')}
        except Exception as e:
            return {"ok": False, "url": "", "message": str(e)}

class _Invoker(QObject):
    invoke = Signal(object)

class DownloadRecord:
    def __init__(self, rec_id: int, url: str, name: str, dest: str, size_total: int | None = None):
        self.id = rec_id
        self.url = url
        self.name = name
        self.dest = dest
        self.size_total = size_total or 0
        self.received = 0
        self.speed = 0.0
        self.status = "queued"   # queued/downloading/paused/done/failed/canceled
        self.thread: DownloadThread | None = None
        self.row = -1
        self._pending_delete = False

class MainWindow(QMainWindow):
    def __init__(self):
        migrate_123pan_to_config()
        self._saved_creds = read_saved_creds()
        self._settings = ensure_settings_defaults(load_settings())

        super().__init__()
        self.lang = self._settings.get('language', 'zh')
        self.protocol = self._settings.get('protocol', 'android')

        self.setWindowTitle(TRANSLATIONS[self.lang]['title'])
        self.setWindowIcon(load_app_icon())
        self.resize(1100, 680)

        self.client: PanClientAdapter | None = None
        self.download_dir = self._settings.get('downloadDir') or os.path.join(RUN_DIR, 'download')

        self._back_stack: list[list[int]] = []
        self._forward_stack: list[list[int]] = []

        self._download_queue: list[DownloadRecord] = []
        self._active_downloads: set[DownloadThread] = set()
        self._all_recs: list[DownloadRecord] = []
        self._dl_lock = threading.Lock()
        self._dl_counter = 0

        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(14, 14, 14, 14); root.setSpacing(12)

        controls = QHBoxLayout(); controls.setContentsMargins(0,0,0,0); controls.setSpacing(8)
        self.protocol_label = QLabel(TRANSLATIONS[self.lang]['protocol'])
        self.protocol_cb = QComboBox(); self.protocol_cb.addItem(TRANSLATIONS[self.lang]['android'], 'android')
        self.protocol_cb.addItem(TRANSLATIONS[self.lang]['web'], 'web')
        self.protocol_cb.currentIndexChanged.connect(self.on_protocol_changed)

        self.btn_login = QPushButton(TRANSLATIONS[self.lang]['login'])
        self.btn_refresh = QPushButton(TRANSLATIONS[self.lang]['refresh'])
        self.btn_up = QPushButton(TRANSLATIONS[self.lang]['up'])
        self.btn_root = QPushButton(TRANSLATIONS[self.lang]['root'])
        self.btn_mkdir = QPushButton(TRANSLATIONS[self.lang]['mkdir'])
        self.btn_upload = QPushButton(TRANSLATIONS[self.lang]['upload'])
        self.btn_delete = QPushButton(TRANSLATIONS[self.lang]['delete'])
        self.btn_share = QPushButton(TRANSLATIONS[self.lang]['share'])
        self.btn_link = QPushButton(TRANSLATIONS[self.lang]['link'])
        self.btn_download = QPushButton(TRANSLATIONS[self.lang]['download'])
        self.btn_settings = QPushButton(TRANSLATIONS[self.lang]['settings'])
        for b in [self.btn_login, self.btn_refresh, self.btn_up, self.btn_root, self.btn_mkdir,
                  self.btn_upload, self.btn_delete, self.btn_share, self.btn_link,
                  self.btn_download, self.btn_settings]:
            b.setMinimumHeight(34)

        self.lang_label = QLabel(TRANSLATIONS[self.lang]['language'])
        self.lang_cb = QComboBox()
        self.lang_cb.addItem(TRANSLATIONS[self.lang]['chinese'], 'zh')
        self.lang_cb.addItem(TRANSLATIONS[self.lang]['english'], 'en')
        self.lang_cb.currentIndexChanged.connect(self.on_lang_changed)

        self.auto_login_cb = QCheckBox(TRANSLATIONS[self.lang]['auto_login'])
        self.auto_login_cb.setChecked(bool(self._settings.get('autoLogin', False)))
        self.auto_login_cb.toggled.connect(self.on_auto_login_toggled)

        for w in [self.protocol_label, self.protocol_cb, self.btn_login, self.btn_refresh, self.btn_up, self.btn_root,
                  self.btn_mkdir, self.btn_upload, self.btn_delete, self.btn_share, self.btn_link,
                  self.btn_download, self.btn_settings, self.lang_label, self.lang_cb, self.auto_login_cb]:
            controls.addWidget(w)
        controls.addStretch(1)
        root.addLayout(controls)

        self.pages = QStackedWidget(); root.addWidget(self.pages, 1)

        page_files = QWidget()
        vf = QVBoxLayout(page_files); vf.setContentsMargins(0, 0, 0, 0); vf.setSpacing(0)
        self.table = QTableWidget(0, 5)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        header = self.table.horizontalHeader()
        header.setHighlightSections(False)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(60)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 64)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 220)
        self.table.doubleClicked.connect(self.on_table_double_clicked)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        vf.addWidget(self.table)
        self.pages.addWidget(page_files)

        page_dl = QWidget()
        vd = QVBoxLayout(page_dl); vd.setContentsMargins(0, 0, 0, 0); vd.setSpacing(8)
        top_dl = QHBoxLayout()
        self.btn_back_files = QPushButton(TRANSLATIONS[self.lang]['back'])
        self.btn_back_files.setMinimumHeight(30)
        top_dl.addWidget(QLabel(TRANSLATIONS[self.lang]['downloads']))
        top_dl.addStretch(1)
        top_dl.addWidget(self.btn_back_files)
        vd.addLayout(top_dl)

        self.table_dl = QTableWidget(0, 6)
        self.table_dl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_dl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_dl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_dl.setAlternatingRowColors(True)
        self.table_dl.setShowGrid(False)
        self.table_dl.verticalHeader().setVisible(False)
        self.table_dl.verticalHeader().setDefaultSectionSize(30)
        h2 = self.table_dl.horizontalHeader()
        h2.setHighlightSections(False)
        h2.setStretchLastSection(False)
        h2.setMinimumSectionSize(60)
        self.table_dl.setHorizontalHeaderLabels([
            TRANSLATIONS[self.lang]['col_d_name'],
            TRANSLATIONS[self.lang]['col_d_size'],
            TRANSLATIONS[self.lang]['col_d_progress'],
            TRANSLATIONS[self.lang]['col_d_speed'],
            TRANSLATIONS[self.lang]['col_d_status'],
            TRANSLATIONS[self.lang]['col_d_actions'],
        ])
        h2.setSectionResizeMode(0, QHeaderView.Stretch)
        h2.setSectionResizeMode(1, QHeaderView.Fixed)
        h2.setSectionResizeMode(2, QHeaderView.Fixed)
        h2.setSectionResizeMode(3, QHeaderView.Fixed)
        h2.setSectionResizeMode(4, QHeaderView.Fixed)
        h2.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table_dl.setColumnWidth(1, 120)
        self.table_dl.setColumnWidth(2, 220)
        self.table_dl.setColumnWidth(3, 120)
        self.table_dl.setColumnWidth(4, 120)
        self.table_dl.setColumnWidth(5, 220)
        vd.addWidget(self.table_dl)
        self.pages.addWidget(page_dl)

        self.progress = QProgressBar()
        self.progress.setMinimum(0); self.progress.setMaximum(100); self.progress.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress)

        self.fab = QPushButton()
        self.fab.setObjectName("FabButton")
        self.fab.setFixedSize(56, 56)
        self._icon_download = self._create_download_icon()
        self._icon_back = self._create_back_icon()
        self.fab.setIcon(self._icon_download)
        self.fab.setIconSize(QSize(28, 28))
        self.fab.setToolTip(TRANSLATIONS[self.lang]['show_downloads'])
        self.fab.setParent(self); self.fab.raise_()
        self.fab.clicked.connect(self._on_fab_clicked)
        self.fab.setVisible(False)
        self.pages.currentChanged.connect(self._on_page_changed)

        self.btn_login.clicked.connect(self.do_login)
        self.btn_refresh.clicked.connect(self.do_refresh)
        self.btn_up.clicked.connect(self.do_up)
        self.btn_root.clicked.connect(self.do_root)
        self.btn_mkdir.clicked.connect(self.do_mkdir)
        self.btn_upload.clicked.connect(self.do_upload)
        self.btn_delete.clicked.connect(self.do_delete)
        self.btn_share.clicked.connect(self.do_share)
        self.btn_link.clicked.connect(self.do_link)
        self.btn_download.clicked.connect(self.do_download)
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_back_files.clicked.connect(lambda: self.pages.setCurrentIndex(0))

        self.retranslate()

        idx = self.protocol_cb.findData(self.protocol)
        if idx >= 0: self.protocol_cb.setCurrentIndex(idx)
        idx = self.lang_cb.findData(self.lang)
        if idx >= 0: self.lang_cb.setCurrentIndex(idx)

        self._invoker = _Invoker()
        self._invoker.invoke.connect(self._on_invoke)

        self.installEventFilter(self)
        central.installEventFilter(self)
        self.table.viewport().installEventFilter(self)

        QTimer.singleShot(0, self._initial_login_flow)
        self._apply_tooltips()

    # --- icons ---
    def _create_download_icon(self) -> QIcon:
        svg_data = b"""
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 3v10m0 0l4-4m-4 4L8 9" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M4 17a2 2 0 002 2h12a2 2 0 002-2" stroke="white" stroke-width="2" stroke-linecap="round"/>
        </svg>
        """
        if _HAS_QTSVG:
            renderer = QSvgRenderer(svg_data)
            pix = QPixmap(56,56); pix.fill(Qt.transparent)
            p = QPainter(pix); renderer.render(p, QRectF(0,0,56,56)); p.end()
            return QIcon(pix)
        pix = QPixmap(56,56); pix.fill(Qt.transparent)
        p = QPainter(pix); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.white); p.setBrush(Qt.white)
        p.drawRect(14, 36, 28, 6)
        p.drawLine(28, 10, 28, 30)
        p.drawPolygon([QPoint(28,30), QPoint(36,22), QPoint(20,22)])
        p.end()
        return QIcon(pix)

    def _create_back_icon(self) -> QIcon:
        svg_data = b"""
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M15 19l-7-7 7-7" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        """
        if _HAS_QTSVG:
            renderer = QSvgRenderer(svg_data)
            pix = QPixmap(56,56); pix.fill(Qt.transparent)
            p = QPainter(pix); renderer.render(p, QRectF(0,0,56,56)); p.end()
            return QIcon(pix)
        pix = QPixmap(56,56); pix.fill(Qt.transparent)
        p = QPainter(pix); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QColor("white")); p.setBrush(Qt.NoBrush)
        p.drawLine(36, 14, 20, 28); p.drawLine(36, 42, 20, 28); p.end()
        return QIcon(pix)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not hasattr(self, 'fab') or self.fab is None: return
        margin = 18
        x = self.width() - self.fab.width() - margin
        y = self.height() - self.fab.height() - margin - self.statusBar().height()
        self.fab.move(max(0, x), max(0, y))

    def _on_fab_clicked(self):
        self.pages.setCurrentIndex(1 if self.pages.currentIndex() == 0 else 0)

    def _on_page_changed(self, idx: int):
        if not hasattr(self, 'fab') or self.fab is None: return
        if idx == 0:
            self.fab.setIcon(self._icon_download)
            self.fab.setToolTip(self.t('show_downloads'))
        else:
            self.fab.setIcon(self._icon_back)
            self.fab.setToolTip(self.t('back_to_files'))

    def _update_fab_visibility(self):
        self.fab.setVisible(len(self._active_downloads) > 0)

    def _apply_tooltips(self):
        self.btn_login.setToolTip("登录 / 切换账号")
        self.btn_refresh.setToolTip("刷新当前目录")
        self.btn_up.setToolTip("返回上级目录（支持鼠标侧键后退）")
        self.btn_root.setToolTip("回到根目录")
        self.btn_mkdir.setToolTip("新建文件夹")
        self.btn_upload.setToolTip("上传文件")
        self.btn_delete.setToolTip("删除所选项")
        self.btn_share.setToolTip("创建分享链接")
        self.btn_link.setToolTip("复制直链（支持多选）")
        self.btn_download.setToolTip("下载所选项（支持多选与并行）")
        self.btn_settings.setToolTip("下载位置、并行下载数等设置")
        self.protocol_cb.setToolTip("切换 Web / 安卓协议（自动重登）")
        self.lang_cb.setToolTip("切换界面语言")
        self.auto_login_cb.setToolTip("开启后，下次启动自动使用保存的账号登录")

    def _update_login_button_label(self):
        self.btn_login.setText(self.t('login') if self.client is None else self.t('switch_account'))

    def t(self, key):  # NOTE: 简易 i18n 访问器
        return TRANSLATIONS[self.lang].get(key, key)

    def retranslate(self):
        self.setWindowTitle(self.t('title'))
        self.protocol_label.setText(self.t('protocol'))
        self.protocol_cb.setItemText(0, self.t('android'))
        self.protocol_cb.setItemText(1, self.t('web'))
        self._update_login_button_label()
        self.btn_refresh.setText(self.t('refresh'))
        self.btn_up.setText(self.t('up'))
        self.btn_root.setText(self.t('root'))
        self.btn_mkdir.setText(self.t('mkdir'))
        self.btn_upload.setText(self.t('upload'))
        self.btn_delete.setText(self.t('delete'))
        self.btn_share.setText(self.t('share'))
        self.btn_link.setText(self.t('link'))
        self.btn_download.setText(self.t('download'))
        self.btn_settings.setText(self.t('settings'))
        self.lang_label.setText(self.t('language'))
        self.lang_cb.setItemText(0, self.t('chinese'))
        self.lang_cb.setItemText(1, self.t('english'))
        if hasattr(self, 'auto_login_cb'):
            self.auto_login_cb.setText(self.t('auto_login'))
        headers = [self.t('col_index'), self.t('col_name'), self.t('col_size'), self.t('col_type'), self.t('col_id')]
        self.table.setHorizontalHeaderLabels(headers)

    def _initial_login_flow(self):
        if self._settings.get('autoLogin') and self._saved_creds.get('userName') and self._saved_creds.get('passWord'):
            self._auto_login_with_saved(on_done=self._on_initial_auto_login_done)
        else:
            self.do_login()

    def _on_initial_auto_login_done(self, ok: bool):
        if not ok: self.do_login()

    def _push_history_before_nav(self):
        try:
            if self.client is None: return
            self._back_stack.append(self.client.get_path_list())
            self._forward_stack.clear()
        except Exception:
            pass

    def _clear_history_on_login_or_protocol_change(self):
        self._back_stack.clear(); self._forward_stack.clear()

    def on_auto_login_toggled(self, checked: bool):
        self._settings['autoLogin'] = bool(checked)
        write_settings(self._settings)

    def open_settings(self):
        dlg = SettingsDialog(
            lang=self.lang,
            parent=self,
            download_dir=self._settings.get('downloadDir', self.download_dir),
            concurrent=self._settings.get('concurrentDownloads', 2),
        )
        if dlg.exec() == QDialog.Accepted:
            vals = dlg.get_values()
            d = vals.get("downloadDir") or self.download_dir
            c = int(vals.get("concurrentDownloads") or 2)
            self._settings['downloadDir'] = d
            self._settings['concurrentDownloads'] = max(1, min(10, c))
            write_settings(self._settings)
            self.download_dir = self._settings['downloadDir']
            self.statusBar().showMessage(self.t('settings'))

    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.MouseButton.XButton1:
                    self.nav_back(); return True
                elif event.button() == Qt.MouseButton.XButton2:
                    self.nav_forward(); return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def nav_back(self):
        if not self.ensure_logged(): return
        if not self._back_stack: return
        target_path = self._back_stack.pop()
        current_path = self.client.get_path_list()
        self.statusBar().showMessage(self.t('up'))
        self.progress.setVisible(True); self.progress.setRange(0, 0)

        def task():
            try: return (self.client.nav_to_path(target_path) == 0), 0
            except Exception as e: return False, str(e)

        def after(res):
            self.progress.setVisible(False); self.progress.setRange(0, 100)
            ok, code = res
            if ok:
                self._forward_stack.append(current_path); self.refresh_table()
            else:
                self._back_stack.append(target_path); QMessageBox.warning(self, self.t('up'), str(code))

        threading.Thread(target=lambda: self._run_and_invoke(task, after), daemon=True).start()

    def nav_forward(self):
        if not self.ensure_logged(): return
        if not self._forward_stack: return
        target_path = self._forward_stack.pop()
        current_path = self.client.get_path_list()
        self.statusBar().showMessage(self.t('refresh'))
        self.progress.setVisible(True); self.progress.setRange(0, 0)

        def task():
            try: return (self.client.nav_to_path(target_path) == 0), 0
            except Exception as e: return False, str(e)

        def after(res):
            self.progress.setVisible(False); self.progress.setRange(0, 100)
            ok, code = res
            if ok:
                self._back_stack.append(current_path); self.refresh_table()
            else:
                self._forward_stack.append(target_path); QMessageBox.warning(self, self.t('refresh'), str(code))

        threading.Thread(target=lambda: self._run_and_invoke(task, after), daemon=True).start()

    def on_protocol_changed(self):
        self.protocol = self.protocol_cb.currentData() or 'android'
        self._settings['protocol'] = self.protocol
        write_settings(self._settings)
        self.client = None
        self.table.setRowCount(0)
        self.statusBar().showMessage(self.t('login'))
        self._clear_history_on_login_or_protocol_change()
        self._update_login_button_label()
        if self._saved_creds.get('userName') and self._saved_creds.get('passWord'):
            self._auto_login_with_saved()
        else:
            self.statusBar().showMessage('')

    def on_lang_changed(self):
        self.lang = self.lang_cb.currentData() or 'zh'
        self._settings['language'] = self.lang
        write_settings(self._settings)
        self.retranslate()

    def ensure_logged(self) -> bool:
        if self.client is None:
            QMessageBox.warning(self, self.t('title'), self.t('not_logged_in'))
            return False
        return True

    def _auto_login_with_saved(self, on_done=None):
        user = self._saved_creds.get("userName", "")
        pwd = self._saved_creds.get("passWord", "")
        if not user or not pwd:
            if callable(on_done): on_done(False)
            return
        self.statusBar().showMessage(self.t('login'))
        self.progress.setVisible(True); self.progress.setRange(0, 0)

        def login_task():
            try:
                self.client = PanClientAdapter(self.protocol)
                code = self.client.login(user, pwd)
                return (code == 0), code
            except Exception as e:
                return False, str(e)

        def after(result):
            self.progress.setVisible(False); self.progress.setRange(0, 100)
            ok, code = result
            if ok:
                self.statusBar().showMessage(self.t('login'))
                self._clear_history_on_login_or_protocol_change()
                self.refresh_table()
                self._update_login_button_label()
                if migrate_123pan_to_config():
                    self._saved_creds = read_saved_creds()
            else:
                self.statusBar().showMessage('')
            if callable(on_done): on_done(bool(ok))

        threading.Thread(target=lambda: self._run_and_invoke(login_task, after), daemon=True).start()

    def do_login(self):
        default_user = self._saved_creds.get("userName", "")
        default_pwd = self._saved_creds.get("passWord", "")
        dlg = LoginDialog(lang=self.lang, parent=self, default_user=default_user, default_pwd=default_pwd)
        if dlg.exec() == QDialog.Accepted:
            user, pwd = dlg.get_values()
            if not user or not pwd: return
            self.statusBar().showMessage(self.t('login'))
            self.progress.setVisible(True); self.progress.setRange(0, 0)

            def login_task():
                try:
                    self.client = PanClientAdapter(self.protocol)
                    code = self.client.login(user, pwd)
                    return (code == 0), code
                except Exception as e:
                    return False, str(e)

            def after(result):
                ok, code = result
                self.progress.setVisible(False); self.progress.setRange(0, 100)
                if ok:
                    self.statusBar().showMessage(self.t('login'))
                    self._clear_history_on_login_or_protocol_change()
                    self.refresh_table()
                    self._update_login_button_label()
                    if migrate_123pan_to_config():
                        self._saved_creds = read_saved_creds()
                else:
                    QMessageBox.critical(self, self.t('login_title'), str(code))

            threading.Thread(target=lambda: self._run_and_invoke(login_task, after), daemon=True).start()

    def _run_and_invoke(self, func, callback):
        res = func()
        self._invoker.invoke.emit((callback, res))

    def _on_invoke(self, payload):
        try:
            cb, res = payload
            cb(res)
        except Exception:
            pass

    def do_refresh(self):
        if not self.ensure_logged(): return
        self.statusBar().showMessage(self.t('refresh'))
        self.progress.setVisible(True); self.progress.setRange(0, 0)

        def task():
            try:
                code = self.client.get_dir()
                return (code == 0), code
            except Exception as e:
                return False, str(e)

        def after(res):
            ok, code = res
            self.progress.setVisible(False); self.progress.setRange(0, 100)
            if ok: self.refresh_table()
            else: QMessageBox.warning(self, self.t('refresh'), str(code))

        threading.Thread(target=lambda: self._run_and_invoke(task, after), daemon=True).start()

    def do_up(self):
        if not self.ensure_logged(): return
        self._push_history_before_nav()
        self.statusBar().showMessage(self.t('up'))
        self.progress.setVisible(True); self.progress.setRange(0, 0)

        def task():
            try: return (self.client.cd_up() == 0), 0
            except Exception as e: return False, str(e)

        def after(res):
            self.progress.setVisible(False); self.progress.setRange(0, 100)
            ok, code = res
            if ok: self.refresh_table()
            else:
                if self._back_stack: self._back_stack.pop()
                QMessageBox.warning(self, self.t('up'), str(code))

        threading.Thread(target=lambda: self._run_and_invoke(task, after), daemon=True).start()

    def do_root(self):
        if not self.ensure_logged(): return
        self._push_history_before_nav()
        self.statusBar().showMessage(self.t('root'))
        self.progress.setVisible(True); self.progress.setRange(0, 0)

        def task():
            try: return (self.client.cd_root() == 0), 0
            except Exception as e: return False, str(e)

        def after(res):
            self.progress.setVisible(False); self.progress.setRange(0, 100)
            ok, code = res
            if ok: self.refresh_table()
            else:
                if self._back_stack: self._back_stack.pop()
                QMessageBox.warning(self, self.t('root'), str(code))

        threading.Thread(target=lambda: self._run_and_invoke(task, after), daemon=True).start()

    def do_mkdir(self):
        if not self.ensure_logged(): return
        name, ok = QInputDialog.getText(self, self.t('mkdir'), self.t('enter_folder_name'))
        if not ok or not name.strip(): return

        def task():
            try: return True if self.client.mkdir(name.strip()) else False
            except Exception: return False

        def after(ok):
            if ok:
                QMessageBox.information(self, self.t('mkdir'), self.t('mkdir_success'))
                self.do_refresh()
            else:
                QMessageBox.warning(self, self.t('mkdir'), self.t('mkdir_failed'))

        threading.Thread(target=lambda: self._run_and_invoke(task, after), daemon=True).start()

    def do_upload(self):
        if not self.ensure_logged(): return
        file_path, _ = QFileDialog.getOpenFileName(self, self.t('upload'))
        if not file_path: return
        self.statusBar().showMessage(self.t('upload'))
        self.progress.setVisible(True); self.progress.setRange(0, 0)

        def task():
            try: self.client.upload(file_path); return True
            except Exception as e: return str(e)

        def after(res):
            self.progress.setVisible(False); self.progress.setRange(0, 100)
            if res is True: self.do_refresh()
            else: QMessageBox.warning(self, self.t('upload'), str(res))

        threading.Thread(target=lambda: self._run_and_invoke(task, after), daemon=True).start()

    def _selected_rows(self):
        return sorted({i.row() for i in self.table.selectedIndexes()})

    def do_delete(self):
        if not self.ensure_logged(): return
        rows = self._selected_rows()
        if not rows:
            QMessageBox.information(self, self.t('delete'), self.t('select_rows_first'))
            return
        reply = QMessageBox.question(self, self.t('delete'), self.t('delete_confirm'),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes: return
        rows = sorted(rows, reverse=True)

        def task():
            try:
                for r in rows: self.client.delete_index(r)
                return True
            except Exception as e:
                return str(e)

        def after(res):
            if res is True: self.do_refresh()
            else: QMessageBox.warning(self, self.t('delete'), str(res))

        threading.Thread(target=lambda: self._run_and_invoke(task, after), daemon=True).start()

    def do_share(self):
        if not self.ensure_logged(): return
        rows = self._selected_rows()
        if not rows:
            QMessageBox.information(self, self.t('share'), self.t('select_rows_first'))
            return
        items = self.client.current_list()
        file_ids = [items[r]['FileId'] for r in rows]
        pwd, ok = QInputDialog.getText(self, self.t('share'), self.t('share_pwd'))
        if not ok: return

        def task(): return self.client.share(file_ids, pwd)

        def after(res: dict):
            if res.get('ok'):
                url = res.get('url') or ''
                QApplication.clipboard().setText(url)
                QMessageBox.information(self, self.t('share'), f"{self.t('share_ok')}:\n{url}\n{self.t('copied')} {url}")
            else:
                QMessageBox.warning(self, self.t('share'), f"{self.t('share_failed')}: {res.get('message')}")

        threading.Thread(target=lambda: self._run_and_invoke(task, after), daemon=True).start()

    def do_link(self):
        if not self.ensure_logged(): return
        rows = self._selected_rows()
        if not rows:
            QMessageBox.information(self, self.t('link'), self.t('select_row_first'))
            return
        self.statusBar().showMessage(self.t('link'))
        self.progress.setVisible(True); self.progress.setRange(0, 0)

        def task():
            try:
                urls = []
                for r in rows:
                    url = self.client.link(r)
                    if isinstance(url, str) and url.startswith('http'):
                        urls.append(url)
                return urls
            except Exception as e:
                return e

        def after(res):
            self.progress.setVisible(False); self.progress.setRange(0, 100)
            if isinstance(res, Exception):
                QMessageBox.warning(self, self.t('link'), str(res)); return
            if not res:
                QMessageBox.warning(self, self.t('link'), "No link generated"); return
            text = "\n".join(res)
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, self.t('link'), f"{self.t('copied')}:\n{text}")

        threading.Thread(target=lambda: self._run_and_invoke(task, after), daemon=True).start()

    # --- downloads ---
    def do_download(self):
        if not self.ensure_logged(): return
        rows = self._selected_rows()
        if not rows:
            QMessageBox.information(self, self.t('download'), self.t('select_rows_first'))
            return
        target_dir = QFileDialog.getExistingDirectory(self, self.t('choose_download_dir'), self.download_dir)
        if not target_dir: return
        self.download_dir = target_dir
        self._settings['downloadDir'] = target_dir
        write_settings(self._settings)

        items = self.client.current_list()
        tasks_meta = []
        for r in rows:
            item = items[r]
            name = item['FileName']
            if item.get('Type') == 1 and self.protocol == 'android':
                name = f"{name}.zip"  # NOTE(android): 目录可能以 zip 打包下载
            dest_path = os.path.join(target_dir, name)
            sz = int(item.get('Size', 0) or 0)
            tasks_meta.append((r, dest_path, name, sz))

        self.statusBar().showMessage(self.t('download_start'))
        self.progress.setVisible(True); self.progress.setRange(0, 0)

        def link_task():
            ok_list, errs = [], []
            try:
                for idx, dest, name, sz in tasks_meta:
                    try:
                        url = self.client.link(idx)
                        if isinstance(url, str) and url.startswith('http'):
                            ok_list.append((url, dest, name, sz))
                        else:
                            errs.append((idx, f"Link invalid: {url}"))
                    except Exception as e:
                        errs.append((idx, str(e)))
                return ok_list, errs
            except Exception as e:
                return [], [(None, str(e))]

        def after(res):
            ok_list, errs = res
            for url, dest, name, sz in ok_list:
                self.enqueue_download(url, dest, name, sz)
            if errs:
                msg = "\n".join([f"Row {i}: {e}" for i, e in errs if i is not None]) or "\n".join([e for _, e in errs])
                QMessageBox.warning(self, self.t('download'), f"{self.t('download_failed')}:\n{msg}")
            if not ok_list and not self._active_downloads:
                self.progress.setVisible(False)
                self.statusBar().showMessage('')
            self.pages.setCurrentIndex(1)

        threading.Thread(target=lambda: self._run_and_invoke(link_task, after), daemon=True).start()

    def enqueue_download(self, url: str, dest_path: str, name: str, size_total: int):
        with self._dl_lock:
            self._dl_counter += 1
            rec = DownloadRecord(self._dl_counter, url, name, dest_path, size_total)
            self._all_recs.append(rec)
            self._download_queue.append(rec)
        self._add_download_row(rec)
        self._pump_download_queue()

    def _add_download_row(self, rec: DownloadRecord):
        row = self.table_dl.rowCount()
        self.table_dl.insertRow(row)
        rec.row = row
        self.table_dl.setItem(row, 0, QTableWidgetItem(rec.name))
        self.table_dl.setItem(row, 1, QTableWidgetItem(human_size(rec.size_total)))
        pb = QProgressBar(); pb.setRange(0, 100); pb.setValue(0)
        self.table_dl.setCellWidget(row, 2, pb)
        self.table_dl.setItem(row, 3, QTableWidgetItem("0 KB/s"))
        self.table_dl.setItem(row, 4, QTableWidgetItem(self.t('status_queued')))
        w = QWidget(); hl = QHBoxLayout(w); hl.setContentsMargins(0,0,0,0); hl.setSpacing(6)
        btn_pause = QPushButton(self.t('pause'))
        btn_remove = QPushButton(self.t('remove'))
        btn_delete = QPushButton(self.t('delete_record'))
        for b in (btn_pause, btn_remove, btn_delete): b.setMinimumHeight(24)
        btn_pause.clicked.connect(lambda _, rid=rec.id: self.toggle_pause_resume(rid))
        btn_remove.clicked.connect(lambda _, rid=rec.id: self.cancel_download(rid))
        btn_delete.clicked.connect(lambda _, rid=rec.id: self.delete_record(rid))
        hl.addWidget(btn_pause); hl.addWidget(btn_remove); hl.addWidget(btn_delete)
        self.table_dl.setCellWidget(row, 5, w)

    def _update_download_row(self, rec: DownloadRecord):
        if rec.row < 0 or rec.row >= self.table_dl.rowCount(): return
        pb: QProgressBar = self.table_dl.cellWidget(rec.row, 2)
        if pb:
            pct = 0
            if rec.size_total > 0:
                pct = int(rec.received * 100 / rec.size_total)
            elif rec.status in ("done", "failed", "canceled"):
                pct = 100 if rec.status == "done" else 0
            pb.setValue(max(0, min(100, pct)))
        self.table_dl.item(rec.row, 3).setText(self._fmt_speed(rec.speed))
        status_map = {
            "queued": self.t('status_queued'),
            "downloading": self.t('status_downloading'),
            "paused": self.t('status_paused'),
            "done": self.t('status_done'),
            "failed": self.t('status_failed'),
            "canceled": self.t('status_canceled'),
        }
        self.table_dl.item(rec.row, 4).setText(status_map.get(rec.status, rec.status))
        cell = self.table_dl.cellWidget(rec.row, 5)
        if isinstance(cell, QWidget):
            btn_pause: QPushButton = cell.layout().itemAt(0).widget()
            btn_pause.setText(self.t('resume') if rec.status == "paused" else self.t('pause'))

    def _fmt_speed(self, bps: float) -> str:
        if bps < 1024: return f"{int(bps)} B/s"
        if bps < 1024*1024: return f"{round(bps/1024,1)} KB/s"
        return f"{round(bps/1024/1024,2)} MB/s"

    def _pump_download_queue(self):
        max_conc = max(1, int(self._settings.get('concurrentDownloads', 2)))
        launched = []
        with self._dl_lock:
            while len(self._active_downloads) < max_conc and self._download_queue:
                rec = self._download_queue.pop(0)
                th = DownloadThread(rec.url, rec.dest)
                rec.thread = th; rec.status = "downloading"
                self._active_downloads.add(th)
                th.progress.connect(lambda pct, r=rec: self._on_dl_progress(r, pct))
                th.stat.connect(lambda recv, total, spd, r=rec: self._on_dl_stat(r, recv, total, spd))
                th.finished_ok.connect(lambda path, r=rec, th=th: self._on_dl_finished(r, th, path))
                th.failed.connect(lambda err, r=rec, th=th: self._on_dl_failed(r, th, err))
                th.canceled.connect(lambda r=rec, th=th: self._on_dl_canceled(r, th))
                launched.append(rec); th.start()
        if launched:
            self.progress.setVisible(True); self.progress.setRange(0, 0)
            self.statusBar().showMessage(f"{self.t('download_start')} ({len(self._active_downloads)} active)")
            for r in launched: self._update_download_row(r)
        self._update_fab_visibility()

    def _on_dl_progress(self, rec: DownloadRecord, pct: int):
        pass  # NOTE: 细粒度进度已由 stat 计算并更新 UI

    def _on_dl_stat(self, rec: DownloadRecord, received: int, total: int, speed: float):
        rec.received = received
        if total > 0 and rec.size_total == 0:
            rec.size_total = total
            if 0 <= rec.row < self.table_dl.rowCount():
                self.table_dl.item(rec.row, 1).setText(human_size(total))
        rec.speed = speed
        if rec.status == "downloading":
            self._update_download_row(rec)

    def _on_dl_finished(self, rec: DownloadRecord, th: DownloadThread, path: str):
        with self._dl_lock:
            if th in self._active_downloads: self._active_downloads.remove(th)
        rec.status = "done"; rec.speed = 0.0
        rec.received = rec.size_total or rec.received
        self._update_download_row(rec)
        QMessageBox.information(self, self.t('download'), f"{self.t('download_done')}:\n{path}")
        self._maybe_collapse_progress(); self._pump_download_queue()

    def _on_dl_failed(self, rec: DownloadRecord, th: DownloadThread, err: str):
        with self._dl_lock:
            if th in self._active_downloads: self._active_downloads.remove(th)
        rec.status = "failed"; rec.speed = 0.0
        self._update_download_row(rec)
        QMessageBox.warning(self, self.t('download'), f"{self.t('download_failed')}: {err}")
        self._maybe_collapse_progress(); self._pump_download_queue()

    def _on_dl_canceled(self, rec: DownloadRecord, th: DownloadThread):
        with self._dl_lock:
            if th in self._active_downloads: self._active_downloads.remove(th)
        rec.status = "canceled"; rec.speed = 0.0
        self._update_download_row(rec)
        if rec._pending_delete: self._remove_row_for_record(rec)
        self._maybe_collapse_progress(); self._pump_download_queue()

    def _maybe_collapse_progress(self):
        with self._dl_lock:
            if not self._active_downloads and not self._download_queue:
                self.progress.setVisible(False)
                self.statusBar().showMessage(self.t('download_done'))
        self._update_fab_visibility()

    def _find_record(self, rid: int) -> DownloadRecord | None:
        for r in self._all_recs:
            if r.id == rid: return r
        return None

    def toggle_pause_resume(self, rid: int):
        rec = self._find_record(rid)
        if rec is None or rec.thread is None: return
        if rec.status == "downloading":
            rec.thread.pause(); rec.status = "paused"
        elif rec.status == "paused":
            rec.thread.resume(); rec.status = "downloading"
        self._update_download_row(rec)

    def cancel_download(self, rid: int):
        with self._dl_lock:
            for r in list(self._download_queue):
                if r.id == rid:
                    self._download_queue.remove(r)
                    r.status = "canceled"; r.speed = 0.0
                    self._update_download_row(r)
                    self._maybe_collapse_progress()
                    return
        rec = self._find_record(rid)
        if rec and rec.thread: rec.thread.cancel()

    def delete_record(self, rid: int):
        rec = self._find_record(rid)
        if not rec: return
        with self._dl_lock:
            if rec in self._download_queue:
                self._download_queue.remove(rec)
                self._remove_row_for_record(rec)
                self._maybe_collapse_progress()
                return
        if rec.thread and rec.status in ("downloading", "paused"):
            rec._pending_delete = True
            rec.thread.cancel(); return
        self._remove_row_for_record(rec)
        self._maybe_collapse_progress()

    def _remove_row_for_record(self, rec: DownloadRecord):
        row = rec.row
        if 0 <= row < self.table_dl.rowCount():
            self.table_dl.removeRow(row)
            for r in self._all_recs:
                if r.row > row: r.row -= 1
        if rec in self._all_recs: self._all_recs.remove(rec)

    def _enter_row(self, row: int):
        if not self.ensure_logged(): return
        items = self.client.current_list()
        if row < 0 or row >= len(items): return
        item = items[row]
        if item.get('Type') != 1: return
        self._push_history_before_nav()
        file_id = item['FileId']
        self.statusBar().showMessage(self.t('refresh'))
        self.progress.setVisible(True); self.progress.setRange(0, 0)

        def task():
            try: return (self.client.cd_by_id(file_id) == 0), 0
            except Exception as e: return False, str(e)

        def after(res):
            self.progress.setVisible(False); self.progress.setRange(0, 100)
            ok, code = res
            if ok: self.refresh_table()
            else:
                if self._back_stack: self._back_stack.pop()
                QMessageBox.warning(self, self.t('refresh'), str(code))

        threading.Thread(target=lambda: self._run_and_invoke(task, after), daemon=True).start()

    def on_table_double_clicked(self, index):
        try: self._enter_row(index.row())
        except Exception: pass

    def on_item_double_clicked(self, item):
        try: self._enter_row(item.row())
        except Exception: pass

    def refresh_table(self):
        items = self.client.current_list() if self.client else []
        self.table.setRowCount(len(items))
        for i, it in enumerate(items):
            idx = QTableWidgetItem(str(i + 1))
            name = QTableWidgetItem(str(it.get('FileName', '')))
            size = QTableWidgetItem(human_size(it.get('Size', 0)))
            typ = QTableWidgetItem(self.t('type_folder') if it.get('Type') == 1 else self.t('type_file'))
            fid = QTableWidgetItem(str(it.get('FileId', '')))
            for w in (idx, name, size, typ, fid):
                w.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if w is name else Qt.AlignCenter))
            self.table.setItem(i, 0, idx)
            self.table.setItem(i, 1, name)
            self.table.setItem(i, 2, size)
            self.table.setItem(i, 3, typ)
            self.table.setItem(i, 4, fid)

class _InvokeEvent:
    def __init__(self, fn): self.fn = fn

def main():
    # NOTE(windows): 提前设置 AppUserModelID，避免任务栏分组异常
    if sys.platform.startswith("win"):
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("suileyan.123pan.tool")
        except Exception:
            pass

    app = QApplication(sys.argv)
    apply_app_theme(app)
    app.setWindowIcon(load_app_icon())

    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
