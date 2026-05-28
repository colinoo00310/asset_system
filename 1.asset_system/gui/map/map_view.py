"""
地图展示模块
使用 PyQt5 + QWebEngineView 嵌入地图
支持：OpenStreetMap、高德地图
"""

import sys
import os

# 添加项目根目录到路径（兼容开发和打包环境）
def setup_project_path():
    """设置项目路径"""
    if getattr(sys, 'frozen', False):
        # 打包环境
        # PyInstaller 打包后，资源文件在 _internal 目录中
        # sys._MEIPASS 指向 _internal 目录（PyInstaller 的临时解压目录）
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            # fallback: 使用 exe 所在目录
            base_path = os.path.dirname(sys.executable)
    else:
        # 开发环境
        current = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(os.path.dirname(current))  # gui/map → gui → 项目根目录

    if base_path not in sys.path:
        sys.path.insert(0, base_path)

setup_project_path()

import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QComboBox, QMessageBox, QWidget,
    QScrollArea, QSplitter, QTabWidget, QTextBrowser,
    QListWidget, QListWidgetItem, QInputDialog, QFormLayout,
    QGroupBox, QGridLayout, QTextEdit
)
from PyQt5.QtCore import Qt, QUrl, pyqtSlot, QObject, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QDesktopServices

try:
    from config.map_config import get_baidu_ak, get_amap_key, set_keys as save_map_keys
except ImportError:
    def get_baidu_ak(): return ""
    def get_amap_key(): return ""
    def save_map_keys(baidu_ak=None, amap_key=None): pass


import math

# 坐标系转换函数
# WGS84: 国际标准，GPS使用
# GCJ02: 国测局/火星坐标，高德地图使用
# BD09: 百度坐标

def bd09_to_wgs84(bd_lon, bd_lat):
    """百度坐标(BD09)转WGS84"""
    x_pi = 3.14159265358979324 * 3000.0 / 180.0
    x = bd_lon - 0.0065
    y = bd_lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * x_pi)
    lon = z * math.cos(theta)
    lat = z * math.sin(theta)
    return lon, lat

def gcj02_to_bd09(lon, lat):
    """火星坐标(GCJ02)转百度坐标(BD09)"""
    import json
    try:
        # 使用百度坐标转换API（需要AK，但也有不需要AK的简单算法）
        # 这里使用简单算法
        x_pi = 3.14159265358979324 * 3000.0 / 180.0
        x = lon
        y = lat
        z = math.sqrt(x * x + y * y) + 0.00002 * math.sin(y * x_pi)
        theta = math.atan2(y, x) + 0.000003 * math.cos(x * x_pi)
        bd_lon = z * math.cos(theta) + 0.0065
        bd_lat = z * math.sin(theta) + 0.006
        return bd_lon, bd_lat
    except:
        return lon, lat

def gcj02_to_wgs84(lon, lat):
    """火星坐标(GCJ02)转WGS84"""
    a = 6378245.0
    ee = 0.00669342162296594323
    if out_of_china(lon, lat):
        return lon, lat
    dlat = transform_lat(lon - 105.0, lat - 35.0)
    dlon = transform_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlon = (dlon * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    mglat = lat + dlat
    mglon = lon + dlon
    return lon * 2 - mglon, lat * 2 - mglat

def transform_lat(lon, lat):
    ret = -100.0 + 2.0 * lon + 3.0 * lat + 0.2 * lat * lat + 0.1 * lon * lat + 0.2 * math.sqrt(math.fabs(lon))
    ret += (20.0 * math.sin(6.0 * lon * math.pi) + 20.0 * math.sin(2.0 * lon * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * math.pi) + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * math.pi) + 320 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
    return ret

def transform_lon(lon, lat):
    ret = 300.0 + lon + 2.0 * lat + 0.1 * lon * lon + 0.1 * lon * lat + 0.1 * math.sqrt(math.fabs(lon))
    ret += (20.0 * math.sin(6.0 * lon * math.pi) + 20.0 * math.sin(2.0 * lon * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lon * math.pi) + 40.0 * math.sin(lon / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lon / 12.0 * math.pi) + 300.0 * math.sin(lon / 30.0 * math.pi)) * 2.0 / 3.0
    return ret

def out_of_china(lon, lat):
    """判断是否在中国范围外"""
    return not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271)


class AssetBridge(QObject):
    """JavaScript与Python通信的桥接类"""
    showDetailRequested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

    def requestShowDetail(self, asset_id):
        """由JavaScript调用，发射信号请求显示资产详情"""
        print(f"[AssetBridge] requestShowDetail called with asset_id={asset_id}")
        self.showDetailRequested.emit(int(asset_id))


class ExternalOpenPage(QWebEnginePage):
    """用于 window.open：收到第一个导航请求时用系统浏览器打开，不创建窗口"""
    def __init__(self, parent, map_dialog=None):
        super().__init__(parent)
        self.map_dialog = map_dialog
        self._first_navigation = True

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        scheme = url.scheme()

        # 处理 asset:// 协议（资产详情）
        if scheme == "asset":
            try:
                query = url.query()
                if query:
                    params = {}
                    for item in query.split('&'):
                        if '=' in item:
                            key, value = item.split('=', 1)
                            params[key] = value

                    if params.get('action') == 'view_detail' and params.get('asset_id'):
                        asset_id = int(params.get('asset_id'))
                        if self.map_dialog:
                            self.map_dialog.show_asset_detail(asset_id)
            except Exception as e:
                print(f"处理资产详情请求失败: {e}")
            return False

        # 处理 http/https 链接
        if scheme in ("http", "https"):
            query = url.query() if url.query() else ""
            if 'action=view_detail' in query:
                try:
                    for item in query.split('&'):
                        if 'asset_id=' in item:
                            asset_id = int(item.split('=')[1])
                            if self.map_dialog:
                                self.map_dialog.show_asset_detail(asset_id)
                except Exception as e:
                    print(f"处理资产详情请求失败: {e}")
                return False

            QDesktopServices.openUrl(url)

        return False


class MapWebPage(QWebEnginePage):
    """主地图页面：弹窗/新窗口用系统浏览器打开"""
    def __init__(self, parent, map_dialog=None):
        super().__init__(parent)
        self.map_dialog = map_dialog

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        """处理主页面导航请求"""
        scheme = url.scheme()

        # 处理 asset:// 协议（资产详情）
        if scheme == "asset":
            print("[DEBUG] MapWebPage handling asset:// protocol")
            try:
                query = url.query()
                if query:
                    params = {}
                    for item in query.split('&'):
                        if '=' in item:
                            key, value = item.split('=', 1)
                            params[key] = value

                    if params.get('action') == 'view_detail' and params.get('asset_id'):
                        asset_id = int(params.get('asset_id'))
                        if self.map_dialog:
                            # 直接调用方法
                            self.map_dialog.show_asset_detail(asset_id)
            except Exception as e:
                print(f"处理资产详情请求失败: {e}")
            return False

        return super().acceptNavigationRequest(url, _type, isMainFrame)

    def createWindow(self, _type):
        page = ExternalOpenPage(self.view(), self.map_dialog)
        return page


class MapViewDialog(QDialog):
    """地图展示对话框"""

    close_signal = pyqtSignal()

    def __init__(self, db, auth, parent=None):
        import tempfile
        import os as _os

        # 初始化日志
        def _log(msg):
            try:
                log_dir = _os.path.join(tempfile.gettempdir(), 'asset_system_logs')
                _os.makedirs(log_dir, exist_ok=True)
                log_file = _os.path.join(log_dir, 'map_dialog.log')
                with open(log_file, 'a', encoding='utf-8') as f:
                    from datetime import datetime
                    f.write(f"[{datetime.now()}] [MapViewDialog] {msg}\n")
            except:
                pass

        self._log = _log
        self._log("=== MapViewDialog.__init__ START ===")

        super().__init__(parent)
        self.db = db
        self.auth = auth
        self.geocoding_service = None
        self.current_map_type = "osm"  # 默认 OpenStreetMap（免费无需密钥）
        self.assets_data = {}
        self.asset_bridge = None  # JavaScript通信桥接

        self.setWindowTitle("资产地图展示")
        self.resize(1400, 900)
        self.setStyleSheet("QDialog { font-size: 18px; }")
        self.setWindowFlags(self.windowFlags() | Qt.Window)

        # 初始化UI和加载数据
        self._log("开始初始化 UI")
        try:
            self.init_ui()
            self._log("UI 初始化完成")
        except Exception as e:
            self._log(f"[ERROR] init_ui 失败: {e}")
            import traceback
            self._log(traceback.format_exc())
            raise

        self._log("开始加载资产")
        try:
            self.load_assets()
            self._log("资产加载完成")
        except Exception as e:
            self._log(f"[ERROR] load_assets 失败: {e}")
            import traceback
            self._log(traceback.format_exc())

        self._log("=== MapViewDialog.__init__ END ===")

    def closeEvent(self, event):
        """窗口关闭时发射信号"""
        self.close_signal.emit()
        super().closeEvent(event)

    def convert_coord(self, lng, lat, coord_type):
        """将任意坐标系转换为 WGS84（OSM/高德使用的坐标系）"""
        if coord_type is None or coord_type == "" or coord_type == "wgs84":
            return lng, lat
        elif coord_type == "bd09":
            # 百度坐标转WGS84
            return bd09_to_wgs84(lng, lat)
        elif coord_type == "gcj02":
            # 火星坐标转WGS84
            return gcj02_to_wgs84(lng, lat)
        else:
            return lng, lat

    def get_zoom_level_from_combo(self):
        """从下拉框获取缩放级别"""
        text = self.zoom_combo.currentText()
        if text == "自动":
            return None
        elif text == "市级(10)":
            return 10
        elif text == "区级(13)":
            return 13
        elif text == "街道级(15)":
            return 15
        elif text == "细节(17)":
            return 17
        return None

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)

        # 顶部工具栏（单行紧凑，不占多余高度）
        toolbar = self.create_toolbar()
        toolbar.setMaximumHeight(62)
        layout.addWidget(toolbar)

        # 主体布局：左侧资产列表（窄条），右侧地图（尽量大）
        splitter = QSplitter(Qt.Horizontal)

        # 左侧资产列表，固定最大宽度，让地图占绝大部分
        left_panel = self.create_asset_list_panel()
        left_panel.setMaximumWidth(280)
        splitter.addWidget(left_panel)

        self.map_view = self.create_map_view()
        splitter.addWidget(self.map_view)

        # 左侧不拉伸、右侧拉伸，初始宽度 260 给列表，其余全给地图
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 2000])

        layout.addWidget(splitter)

        # 底部状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("padding: 10px 14px; background: #f0f0f0; font-size: 18px;")
        self.status_label.setMaximumHeight(44)
        layout.addWidget(self.status_label)

    def create_toolbar(self):
        """创建工具栏（浅色背景、字号与按钮加大，便于阅读）"""
        toolbar = QWidget()
        toolbar.setStyleSheet("""
            QWidget { background: #e2e8ed; color: #2c3e50; padding: 8px 12px; }
            QLabel { background: transparent; color: #2c3e50; font-size: 19px; }
            QComboBox { background: white; color: #2c3e50; min-width: 180px; padding: 10px 12px; border: 1px solid #bdc3c7; border-radius: 4px; font-size: 18px; min-height: 28px; }
            QLineEdit { background: white; color: #2c3e50; padding: 10px 12px; border: 1px solid #bdc3c7; border-radius: 4px; font-size: 18px; min-height: 28px; }
            QPushButton { background: #3498db; color: white; padding: 12px 28px; border: none; border-radius: 4px; font-size: 18px; min-height: 32px; }
            QPushButton:hover { background: #2980b9; }
            QPushButton:pressed { background: #21618c; }
        """)
        layout = QHBoxLayout(toolbar)
        layout.setSpacing(12)

        # 地图类型选择（默认 OpenStreetMap，免费无需密钥）
        layout.addWidget(QLabel("地图类型:"))
        self.map_type_combo = QComboBox()
        self.map_type_combo.addItems(["OpenStreetMap（免费）", "高德地图"])
        self.map_type_combo.setCurrentText("OpenStreetMap（免费）")
        self.map_type_combo.currentTextChanged.connect(self.on_map_type_changed)
        layout.addWidget(self.map_type_combo)

        layout.addSpacing(20)

        # 搜索框
        layout.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入资产名称搜索...")
        self.search_input.setFixedWidth(240)
        self.search_input.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_input)

        layout.addSpacing(20)

        # 默认缩放级别选择
        layout.addWidget(QLabel("缩放级别:"))
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["自动", "市级(10)", "区级(13)", "街道级(15)", "细节(17)"])
        self.zoom_combo.setCurrentText("自动")
        self.zoom_combo.currentTextChanged.connect(self.on_zoom_level_changed)
        layout.addWidget(self.zoom_combo)

        layout.addStretch()

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_assets)
        layout.addWidget(refresh_btn)

        # 定位按钮
        location_btn = QPushButton("批量定位")
        location_btn.clicked.connect(self.batch_geocode_assets)
        layout.addWidget(location_btn)

        # 设置 API 密钥
        key_btn = QPushButton("设置 API 密钥")
        key_btn.clicked.connect(self.show_api_key_dialog)
        layout.addWidget(key_btn)

        return toolbar

    def show_api_key_dialog(self):
        """设置高德 API 密钥"""
        try:
            amap = get_amap_key()
        except Exception:
            amap = ""
        dlg = QDialog(self)
        dlg.setWindowTitle("地图 API 密钥")
        form = QFormLayout(dlg)
        amap_edit = QLineEdit()
        amap_edit.setPlaceholderText("在 https://console.amap.com/ 申请")
        amap_edit.setText(amap)
        form.addRow("高德地图 Key:", amap_edit)
        btn_ok = QPushButton("保存")
        btn_ok.clicked.connect(dlg.accept)
        form.addRow(btn_ok)
        if dlg.exec_() == QDialog.Accepted:
            save_map_keys(amap_key=amap_edit.text().strip())
            QMessageBox.information(self, "提示", "已保存，正在重新加载地图...")
            # 重新加载地图以应用新的密钥
            self.update_map_markers()
        return

    def create_asset_list_panel(self):
        """创建资产列表面板（字号加大便于阅读）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        title = QLabel("资产列表 (点击查看位置)")
        title.setStyleSheet("font-size: 19px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        self.asset_list = QListWidget()
        self.asset_list.setStyleSheet("font-size: 18px; padding: 8px;")
        self.asset_list.itemClicked.connect(self.on_asset_clicked)
        layout.addWidget(self.asset_list)

        return widget

    def create_map_view(self):
        """创建地图视图"""
        self._log("create_map_view: 开始创建 QWebEngineView")
        try:
            self.web_view = QWebEngineView()
            self._log("QWebEngineView 创建成功")
        except Exception as e:
            self._log(f"[ERROR] QWebEngineView 创建失败: {e}")
            import traceback
            self._log(traceback.format_exc())
            raise

        # 启用 JavaScript 和必要的功能
        settings = self.web_view.settings()
        settings.setAttribute(settings.JavascriptEnabled, True)
        settings.setAttribute(settings.JavascriptCanOpenWindows, True)
        settings.setAttribute(settings.JavascriptCanAccessClipboard, True)
        settings.setAttribute(settings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(settings.WebGLEnabled, True)
        self._log("WebEngine 设置完成")

        # 添加JavaScript console消息处理，便于调试
        # 注意：必须在 setPage 之后设置，否则会被覆盖
        self.web_view.setPage(MapWebPage(self.web_view, self))
        self.web_view.page().javaScriptConsoleMessage = self._js_console_message
        self._log("MapWebPage 设置完成")

        # 设置 WebChannel 用于 JavaScript 与 Python 通信
        self.asset_bridge = AssetBridge(self)
        self.asset_bridge.showDetailRequested.connect(self.on_show_detail_requested)
        self.channel = QWebChannel(self.web_view.page())
        self.channel.registerObject("pybridge", self.asset_bridge)
        self.web_view.page().setWebChannel(self.channel)
        self._log("WebChannel 设置完成")

        self.web_view.setUrl(QUrl("about:blank"))
        self._log("设置空白URL完成")

        # 初始化地图
        self._log("开始初始化地图...")
        self.init_map("")
        self._log("init_map 调用完成")

        return self.web_view

    def _js_console_message(self, level, message, sourceID, lineNumber):
        """捕获JavaScript console.log输出"""
        print(f"[JS Console] {message}")
        # 处理来自JavaScript的资产详情请求
        # 格式: "ASSET_DETAIL:id" 例如 "ASSET_DETAIL:123"
        if message.startswith("ASSET_DETAIL:"):
            try:
                asset_id = int(message.split(":")[1])
                print(f"[DEBUG] JS requested asset detail: id={asset_id}")
                self.show_asset_detail(asset_id)
            except (ValueError, IndexError) as e:
                print(f"[DEBUG] Failed to parse ASSET_DETAIL message: {e}")

    def init_map(self, markers_json):
        """初始化地图"""
        if self.current_map_type == "osm":
            self.load_osm(markers_json)
        elif self.current_map_type == "amap":
            self.load_amap(markers_json)

    def load_osm(self, markers_json="", custom_zoom=None):
        """加载 OpenStreetMap（免费无需密钥）"""
        html = self.generate_osm_html(markers_json, custom_zoom)
        # 断开之前的连接避免重复
        try:
            self.web_view.loadFinished.disconnect()
        except TypeError:
            pass
        # 使用 loadFinished 信号确保 HTML 加载完成后再设置
        self.web_view.loadFinished.connect(lambda ok: self._on_page_loaded(ok, 'osm'))
        self.web_view.setHtml(html)

    def load_amap(self, markers_json="", custom_zoom=None):
        """加载高德地图"""
        print(f"[DEBUG] load_amap called, markers count: {len(markers_json) if markers_json else 0}")
        try:
            key = get_amap_key()
            print(f"[DEBUG] load_amap: amap key = {key[:10] + '...' if key else 'None'}")

            if not key:
                print("[DEBUG] load_amap: no API key, showing placeholder")
                self.web_view.setHtml(self._placeholder_html("高德地图", "https://console.amap.com/", "Key"))
                return

            html = self.generate_amap_html(markers_json, custom_zoom)
            print(f"[DEBUG] HTML generated, length: {len(html)}")
            # 断开之前的连接避免重复
            try:
                self.web_view.loadFinished.disconnect()
            except TypeError:
                pass
            # 使用 loadFinished 信号确保 HTML 加载完成后再设置
            self.web_view.loadFinished.connect(lambda ok: self._on_page_loaded(ok, 'amap'))
            self.web_view.setHtml(html)
            print("[DEBUG] setHtml completed")
        except Exception as e:
            print(f"[ERROR] load_amap failed: {e}")
            import traceback
            traceback.print_exc()

    def _on_page_loaded(self, ok, map_type):
        """页面加载完成后重新设置必要属性"""
        if not ok:
            print(f"[DEBUG] Page load failed for {map_type}")
            return

        print(f"[DEBUG] Page loaded for {map_type}, re-setting properties")

        # 重新设置 console 消息处理
        self.web_view.page().javaScriptConsoleMessage = self._js_console_message

        # 重新设置 WebChannel
        self.asset_bridge = AssetBridge(self)
        self.asset_bridge.showDetailRequested.connect(self.on_show_detail_requested)
        self.channel = QWebChannel(self.web_view.page())
        self.channel.registerObject("pybridge", self.asset_bridge)
        self.web_view.page().setWebChannel(self.channel)

        print(f"[DEBUG] Properties re-set complete for {map_type}")

    def _placeholder_html(self, map_name, key_url, key_name):
        """未配置密钥时显示的说明页，不加载任何外部 API，避免未授权报错"""
        return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>配置说明</title></head>
<body style="margin:0;padding:40px;font-family:Microsoft YaHei,sans-serif;background:#f5f5f5;">
    <div style="max-width:500px;margin:80px auto;background:#fff;padding:30px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.1);">
        <h3 style="color:#2c3e50;">请先配置{map_name} API 密钥</h3>
        <p style="color:#7f8c8d;">使用地图前需在官网申请密钥并对本应用授权。</p>
        <p><a href="{key_url}" target="_blank" style="color:#3498db;">{key_url}</a></p>
        <p style="color:#95a5a6;font-size:13px;">在「地图展示」窗口工具栏点击「设置 API 密钥」，填写并保存后刷新即可。</p>
    </div>
</body>
</html>
"""

    def generate_osm_html(self, markers_json, custom_zoom=None):
        """生成高德地图 + Leaflet HTML（免费无需密钥，国内访问快）"""
        if not markers_json:
            markers_json = "[]"

        # 传递缩放级别到 JavaScript
        zoom_js = f"window.customZoom = {custom_zoom};" if custom_zoom else "window.customZoom = null;"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>资产分布地图</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script type="text/javascript" src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; }}
        #container {{ width: 100%; height: 100%; }}
        .info-window {{
            padding: 16px;
            font-size: 18px;
            max-width: 380px;
        }}
        .info-window h4 {{ margin: 0 0 14px 0; color: #333; font-size: 20px; }}
        .info-window p {{ margin: 10px 0; color: #666; font-size: 17px; }}
        .info-window button {{
            margin-top: 16px;
            padding: 14px 30px;
            background: #3498db;
            color: white;
            border: none;
            cursor: pointer;
            border-radius: 4px;
            font-size: 18px;
        }}
        .info-window button:hover {{ background: #2980b9; }}
    </style>
    <script type="text/javascript">
        window.mapData = {markers_json};
        {zoom_js}
        var pybridge = null;
    </script>
</head>
<body>
    <div id="container"></div>
    <script type="text/javascript">
        // 初始化 QWebChannel
        new QWebChannel(qt.webChannelTransport, function(channel) {{
            pybridge = channel.objects.pybridge;
            console.log('[OSM] QWebChannel connected, pybridge available');
        }});

        // 默认视图：中国/杭州
        var defaultCenter = [30.243, 120.293];
        var defaultZoom = 10;
        var map = L.map('container', {{
            center: defaultCenter,
            zoom: defaultZoom,
            minZoom: 3,
            maxZoom: 18,
            zoomControl: true,
            doubleClickZoom: true,
            scrollWheelZoom: true,
            dragging: true
        }});

        // 高德瓦片（国内快、中文标注）+ Google 瓦片（支持更高缩放）
        // 高德只到 18 级，18 级以上自动切换 Google 瓦片
        var gaodeTile = L.tileLayer('https://webrd0{{s}}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={{x}}&y={{y}}&z={{z}}', {{
            attribution: '&copy; 高德地图',
            subdomains: '1234',
            minZoom: 3,
            maxZoom: 18
        }}).addTo(map);

        var googleTile = L.tileLayer('https://mt{{s}}.google.cn/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{
            attribution: '&copy; Google',
            subdomains: '0123',
            minZoom: 15,
            maxZoom: 20,
            reuseTiles: true
        }});

        map.on('zoomend', function() {{
            var zoom = map.getZoom();
            if (zoom > 18 && map.hasLayer(gaodeTile)) {{
                map.removeLayer(gaodeTile);
                map.addLayer(googleTile);
            }} else if (zoom <= 18 && map.hasLayer(googleTile)) {{
                map.removeLayer(googleTile);
                map.addLayer(gaodeTile);
            }}
        }});

        var markersMap = new Map(); // 存储标记以便后续查找

        if (window.mapData && window.mapData.length > 0) {{
            var bounds = [];
            for (var i = 0; i < window.mapData.length; i++) {{
                var item = window.mapData[i];
                // 兼容 lat/lng 和 latitude/longitude 两种字段名
                var lat = item.lat || item.latitude;
                var lng = item.lng || item.longitude;
                if (lat && lng) {{
                    var latNum = parseFloat(lat);
                    var lngNum = parseFloat(lng);
                    if (!isNaN(latNum) && !isNaN(lngNum)) {{
                        var marker = L.marker([latNum, lngNum]).addTo(map);
                        var popupContent = `
                            <div class="info-window">
                                <h4>📍 ` + item.name + `</h4>
                                <p><b>位置:</b> ` + item.location + `</p>
                                <p><b>类别:</b> ` + item.category + `</p>
                                <p><b>状态:</b> ` + item.status + `</p>
                                <p><b>责任人:</b> ` + item.responsible + `</p>
                                <button onclick="showStreetView(` + latNum + `, ` + lngNum + `)">🖼️ 查看实景</button>
                                <button onclick="showAssetDetail(` + item.id + `)">📋 查看详细信息</button>
                            </div>
                        `;
                        marker.bindPopup(popupContent);
                        markersMap.set(item.id, marker); // 存储标记
                        bounds.push([latNum, lngNum]);
                    }}
                }}
            }}
            // 自动调整视图范围，显示所有标记（除非用户指定了缩放级别）
            if (bounds.length > 0) {{
                if (window.customZoom) {{
                    // 用户指定了缩放级别，计算中心点并使用固定缩放
                    var boundsObj = L.latLngBounds(bounds);
                    var center = boundsObj.getCenter();
                    map.setView([center.lat, center.lng], window.customZoom);
                }} else {{
                    // 自动调整视图范围
                    var boundsObj = L.latLngBounds(bounds);
                    map.fitBounds(boundsObj, {{ padding: [50, 50] }});
                }}
            }}
        }}

        // WGS84转BD09的简化算法（用于百度街景）
        function wgs84_to_bd09(lng, lat) {{
            var x_pi = 3.14159265358979324 * 3000.0 / 180.0;
            var x = lng, y = lat;
            var z = Math.sqrt(x * x + y * y) + 0.00002 * Math.sin(y * x_pi);
            var theta = Math.atan2(y, x) + 0.000003 * Math.cos(x * x_pi);
            var bd_lng = z * Math.cos(theta) + 0.0065;
            var bd_lat = z * Math.sin(theta) + 0.006;
            return [bd_lng, bd_lat];
        }}

        function showStreetView(lat, lng) {{
            // 坐标已经是WGS84，需要转换为BD09（百度坐标）才能正确显示
            var bdCoords = wgs84_to_bd09(lng, lat);
            var streetViewUrl = 'https://map.baidu.com/?latlng=' + bdCoords[1] + ',' + bdCoords[0] + '&panotype=street';
            window.open(streetViewUrl, '_blank');
        }}

        function showAssetDetail(assetId) {{
            // 使用 console.log 发送消息给 Python
            console.log("ASSET_DETAIL:" + assetId);
        }}

        function focusAsset(lat, lng, assetId) {{
            console.log('focusAsset called with:', lat, lng, assetId);
            console.log('typeof map:', typeof map);
            console.log('typeof markersMap:', typeof markersMap);
            if (typeof markersMap !== 'undefined') {{
                console.log('markersMap size:', markersMap.size, 'keys:', Array.from(markersMap.keys()));
            }}
            if (typeof lat === 'string') {{ lat = parseFloat(lat); }}
            if (typeof lng === 'string') {{ lng = parseFloat(lng); }}
            console.log('After parse:', lat, lng, 'map:', typeof map);
            if (typeof map !== 'undefined' && map) {{
                try {{
                    map.setView([lat, lng], 17);
                    console.log('Map view set successfully');

                    // 尝试打开对应标记的弹窗
                    if (assetId && typeof markersMap !== 'undefined' && markersMap && markersMap.has(assetId)) {{
                        var marker = markersMap.get(assetId);
                        marker.openPopup();
                        console.log('Popup opened for assetId:', assetId);
                    }} else {{
                        console.log('Marker not found for assetId:', assetId, 'markersMap:', typeof markersMap);
                        // 如果标记不存在，从 window.mapData 重新查找并创建
                        if (window.mapData && window.mapData.length > 0) {{
                            for (var i = 0; i < window.mapData.length; i++) {{
                                if (window.mapData[i].id == assetId) {{
                                    var item = window.mapData[i];
                                    var mlat = item.lat || item.latitude;
                                    var mlng = item.lng || item.longitude;
                                    if (mlat && mlng) {{
                                        var marker = L.marker([parseFloat(mlat), parseFloat(mlng)]).addTo(map);
                                        var popupContent = '<div class="info-window"><h4>📍 ' + item.name + '</h4>' +
                                            '<p><b>位置:</b> ' + item.location + '</p>' +
                                            '<p><b>类别:</b> ' + item.category + '</p>' +
                                            '<p><b>状态:</b> ' + item.status + '</p>' +
                                            '<p><b>责任人:</b> ' + item.responsible + '</p></div>';
                                        marker.bindPopup(popupContent).openPopup();
                                        console.log('Created new marker for assetId:', assetId);
                                    }}
                                }}
                            }}
                        }}
                    }}
                }} catch(e) {{
                    console.log('Error in focusAsset:', e.message || e);
                }}
            }} else {{
                console.log('Map is not defined!');
            }}
            return 'done';
        }}
    </script>
</body>
</html>
"""
        return html

    def generate_amap_html(self, markers_json, custom_zoom=None):
        """生成高德地图HTML"""
        key = get_amap_key()
        if not key:
            return self._placeholder_html("高德地图", "https://console.amap.com/", "Key")
        if not markers_json:
            markers_json = "[]"

        print(f"[DEBUG] generate_amap_html: markers_json length = {len(markers_json)}")
        print(f"[DEBUG] generate_amap_html: key = {key[:10] if key else 'None'}...")

        # 传递缩放级别到 JavaScript
        zoom_js = f"window.customZoom = {custom_zoom};" if custom_zoom else "window.customZoom = null;"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>资产分布地图</title>
    <script type="text/javascript" src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }}
        #container {{ width: 100%; height: 100%; }}
        .info-window {{
            padding: 16px;
            font-size: 18px;
            max-width: 380px;
        }}
        .info-window h4 {{ margin: 0 0 14px 0; color: #333; font-size: 20px; }}
        .info-window p {{ margin: 10px 0; color: #666; font-size: 17px; }}
        .info-window .label {{ color: #999; font-weight: bold; font-size: 16px; }}
        .info-window button {{
            margin-top: 16px;
            padding: 14px 30px;
            background: #3498db;
            color: white;
            border: none;
            cursor: pointer;
            border-radius: 4px;
            font-size: 18px;
        }}
        .info-window button:hover {{ background: #2980b9; }}
        .status-tag {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 3px;
            font-size: 13px;
            color: white;
        }}
        .status-normal {{ background: #27ae60; }}
        .status-rent {{ background: #e67e22; }}
        .status-other {{ background: #95a5a6; }}
    </style>
    <script type="text/javascript">
        window.mapData = {markers_json};
        {zoom_js}
        var pybridge = null;
    </script>
    <script type="text/javascript" src="https://webapi.amap.com/maps?v=2.0&key={key}"></script>
</head>
<body>
    <div id="container"></div>
    <script type="text/javascript">
        // 初始化 QWebChannel
        new QWebChannel(qt.webChannelTransport, function(channel) {{
            pybridge = channel.objects.pybridge;
            console.log('[AMap] QWebChannel connected, pybridge available');
        }});

        var map = new AMap.Map('container', {{
            zoom: 12,
            center: [120.293, 30.243],
            viewMode: '3D'
        }});

        AMap.plugin(['AMap.ToolBar', 'AMap.Scale', 'AMap.Geolocation'], function() {{
            map.addControl(new AMap.ToolBar({{ position: 'RT' }}));
            map.addControl(new AMap.Scale());
        }});

        // 创建自定义蓝色图标
        var blueIcon = new AMap.Icon({
            size: new AMap.Pixel(32, 32),
            image: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png',
            imageSize: new AMap.Pixel(32, 32)
        });

        if (window.mapData && window.mapData.length > 0) {{
            var bounds = new AMap.Bounds();
            var hasValidData = false;
            var amapMarkersMap = new Map(); // 存储标记和信息窗体
            var amapInfoWindowsMap = new Map();

            for (var i = 0; i < window.mapData.length; i++) {{
                var item = window.mapData[i];
                if (item.lng && item.lat) {{
                    var marker = new AMap.Marker({{
                        position: [item.lng, item.lat],
                        title: item.name,
                        icon: blueIcon,
                        offset: new AMap.Pixel(-16, -32)
                    }});

                    var statusClass = 'status-normal';
                    if (item.status === '租赁中') statusClass = 'status-rent';

                    var content = '<div class="info-window">' +
                        '<h4>📍 ' + item.name + '</h4>' +
                        '<p><span class="label">位置:</span> ' + item.location + '</p>' +
                        '<p><span class="label">类别:</span> ' + item.category + '</p>' +
                        '<p><span class="label">状态:</span> <span class="status-tag ' + statusClass + '">' + item.status + '</span></p>' +
                        '<p><span class="label">责任人:</span> ' + item.responsible + '</p>' +
                        '<button onclick="showStreetView(' + item.lat + ', ' + item.lng + ')">🖼️ 查看实景</button> ' +
                        '<button onclick="showAssetDetail(' + item.id + ')">📋 查看详细信息</button>' +
                        '</div>';

                    var infoWindow = new AMap.InfoWindow({{
                        content: content,
                        offset: new AMap.Pixel(0, -30)
                    }});

                    // 存储标记和信息窗体
                    amapMarkersMap.set(item.id, marker);
                    amapInfoWindowsMap.set(item.id, infoWindow);

                    marker.on('click', function() {{
                        infoWindow.open(map, marker.getPosition());
                    }});

                    marker.setMap(map);
                    bounds.extend([item.lng, item.lat]);
                    hasValidData = true;
                }}
            }}

            // 保存到全局变量
            window.amapMarkersMap = amapMarkersMap;
            window.amapInfoWindowsMap = amapInfoWindowsMap;

            if (hasValidData) {{
                if (window.customZoom) {{
                    // 用户指定了缩放级别，计算中心点并使用固定缩放
                    map.setCenter(bounds.getCenter());
                    map.setZoom(window.customZoom);
                }} else {{
                    // 自动调整视图范围
                    map.setFitView(bounds);
                }}
            }}
        }}

        // WGS84转BD09的简化算法（用于百度街景）
        function wgs84_to_bd09(lng, lat) {{
            var x_pi = 3.14159265358979324 * 3000.0 / 180.0;
            var x = lng, y = lat;
            var z = Math.sqrt(x * x + y * y) + 0.00002 * Math.sin(y * x_pi);
            var theta = Math.atan2(y, x) + 0.000003 * Math.cos(x * x_pi);
            var bd_lng = z * Math.cos(theta) + 0.0065;
            var bd_lat = z * Math.sin(theta) + 0.006;
            return [bd_lng, bd_lat];
        }}

        function showStreetView(lat, lng) {{
            // 坐标已经是WGS84，需要转换为BD09（百度坐标）才能正确显示
            var bdCoords = wgs84_to_bd09(lng, lat);
            var streetViewUrl = 'https://map.baidu.com/?latlng=' + bdCoords[1] + ',' + bdCoords[0] + '&panotype=street';
            window.open(streetViewUrl, '_blank');
        }}

        function showAssetDetail(assetId) {{
            // 使用 console.log 发送消息给 Python
            console.log("ASSET_DETAIL:" + assetId);
        }}

        function showSatellite() {{
            map.setMapStyle('amap://styles/satellite');
        }}

        function showNormal() {{
            map.setMapStyle('amap://styles/normal');
        }}

        function focusAsset(lng, lat, assetId) {{
            console.log('高德 focusAsset called with:', lng, lat);
            if (typeof lng === 'string') {{ lng = parseFloat(lng); }}
            if (typeof lat === 'string') {{ lat = parseFloat(lat); }}
            map.setCenter([lng, lat]);
            map.setZoom(16);
            console.log('高德 Map view set');

            // 尝试打开信息窗体
            if (assetId && window.amapInfoWindowsMap && window.amapInfoWindowsMap.has(assetId)) {{
                var infoWindow = window.amapInfoWindowsMap.get(assetId);
                infoWindow.open(map, [lng, lat]);
                console.log('高德 InfoWindow opened');
            }}
            return 'done';
        }}
    </script>
</body>
</html>
"""
        return html

    def generate_baidu_html(self, markers_json):
        """生成百度地图HTML"""
        ak = get_baidu_ak()
        if not ak:
            return self._placeholder_html("百度地图", "https://lbs.baidu.com/apiconsole/key", "AK")
        if not markers_json:
            markers_json = "[]"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>资产分布地图</title>
    <style>
        body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }}
        #container {{ width: 100%; height: 100%; }}
    </style>
    <script type="text/javascript" src="https://api.map.baidu.com/api?v=1.0&type=webgl&ak={ak}"></script>
    <script type="text/javascript">
        window.mapData = {markers_json};
    </script>
</head>
<body>
    <div id="container"></div>
    <script type="text/javascript">
        var map = new BMapGL.Map('container');
        var point = new BMapGL.Point(120.293, 30.243);
        map.centerAndZoom(point, 12);
        map.enableScrollWheelZoom(true);

        if (window.mapData && window.mapData.length > 0) {{
            for (var i = 0; i < window.mapData.length; i++) {{
                var item = window.mapData[i];
                if (item.lng && item.lat) {{
                    var marker = new BMapGL.Marker(new BMapGL.Point(item.lng, item.lat));
                    marker.setTitle(item.name);
                    map.addOverlay(marker);

                    var content = `
                        <div style="padding:10px;max-width:300px;">
                            <h4 style="margin:0 0 10px 0;">📍 ${{item.name}}</h4>
                            <p><b>位置:</b> ${{item.location}}</p>
                            <p><b>类别:</b> ${{item.category}}</p>
                            <p><b>状态:</b> ${{item.status}}</p>
                            <p><b>责任人:</b> ${{item.responsible}}</p>
                            <button onclick="showStreetView(${{item.lat}}, ${{item.lng}})" style="margin-top:14px;padding:12px 26px;background:#3498db;color:white;border:none;cursor:pointer;border-radius:4px;font-size:16px;">🖼️ 查看实景</button>
                        </div>
                    `;

                    var infoWindow = new BMapGL.InfoWindow({{content: content}});
                    marker.addEventListener('click', function() {{
                        map.openInfoWindow(infoWindow, marker.getPosition());
                    }});
                }}
            }}
            map.setViewport(window.mapData.map(item => new BMapGL.Point(item.lng, item.lat)));
        }}

        // WGS84转BD09的简化算法（用于百度街景）
        function wgs84_to_bd09(lng, lat) {{
            var x_pi = 3.14159265358979324 * 3000.0 / 180.0;
            var x = lng, y = lat;
            var z = Math.sqrt(x * x + y * y) + 0.00002 * Math.sin(y * x_pi);
            var theta = Math.atan2(y, x) + 0.000003 * Math.cos(x * x_pi);
            var bd_lng = z * Math.cos(theta) + 0.0065;
            var bd_lat = z * Math.sin(theta) + 0.006;
            return [bd_lng, bd_lat];
        }}

        function showStreetView(lat, lng) {{
            // 坐标已经是WGS84，需要转换为BD09（百度坐标）才能正确显示
            var bdCoords = wgs84_to_bd09(lng, lat);
            var streetViewUrl = 'https://map.baidu.com/?latlng=' + bdCoords[1] + ',' + bdCoords[0] + '&panotype=street';
            window.open(streetViewUrl, '_blank');
        }}

        function focusAsset(lng, lat, assetId) {{
            console.log('百度 focusAsset called with:', lng, lat);
            if (typeof lng === 'string') {{ lng = parseFloat(lng); }}
            if (typeof lat === 'string') {{ lat = parseFloat(lat); }}
            map.centerAndZoom(new BMapGL.Point(lng, lat), 16);
            console.log('百度 Map view set');
            return 'done';
        }}
    </script>
</body>
</html>
"""
        return html

    def load_assets(self):
        """加载资产数据：列表显示全部资产，地图只显示有坐标的；未定位的标注并提示"""
        self.asset_list.clear()

        conn = self.db.get_connection()
        c = conn.cursor()

        try:
            current_user = self.auth.get_current_user()

            # 如果没有当前用户（独立进程），默认为管理员权限查看所有资产
            if not current_user:
                print("[DEBUG] load_assets: 没有当前用户，默认为管理员权限")
                c.execute("""
                    SELECT id, name, location, category, status,
                           longitude, latitude, coord_type, responsible_person
                    FROM assets
                    ORDER BY CASE WHEN longitude IS NOT NULL AND latitude IS NOT NULL THEN 0 ELSE 1 END, name
                """)
            elif current_user['role'] == 'admin':
                c.execute("""
                    SELECT id, name, location, category, status,
                           longitude, latitude, coord_type, responsible_person
                    FROM assets
                    ORDER BY CASE WHEN longitude IS NOT NULL AND latitude IS NOT NULL THEN 0 ELSE 1 END, name
                """)
            else:
                dept_id = current_user.get('department_id')
                if dept_id:
                    c.execute("""
                        SELECT id, name, location, category, status,
                               longitude, latitude, coord_type, responsible_person
                        FROM assets
                        WHERE department_id = ?
                        ORDER BY CASE WHEN longitude IS NOT NULL AND latitude IS NOT NULL THEN 0 ELSE 1 END, name
                    """, (dept_id,))
                else:
                    c.execute("""
                        SELECT id, name, location, category, status,
                               longitude, latitude, coord_type, responsible_person
                        FROM assets
                        ORDER BY CASE WHEN longitude IS NOT NULL AND latitude IS NOT NULL THEN 0 ELSE 1 END, name
                    """)

            all_assets = c.fetchall()
            self.assets_data = {}
            has_coords_count = 0

            for asset in all_assets:
                asset_id, name, location, category, status, lng, lat, coord_type, responsible = asset
                location = location or ""
                has_coords = lng is not None and lat is not None

                if has_coords:
                    has_coords_count += 1
                    # 根据坐标类型转换到 WGS84（OSM/高德使用的坐标系）
                    lng, lat = self.convert_coord(lng, lat, coord_type)
                    self.assets_data[asset_id] = {
                        'id': asset_id,
                        'name': name,
                        'location': location,
                        'category': category,
                        'status': status or '正常',
                        'lng': lng,
                        'lat': lat,
                        'responsible': responsible
                    }
                    item_text = f"{name} - {location}"
                else:
                    item_text = f"{name} - {location} 【未定位】"

                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, asset_id)
                item.setData(Qt.UserRole + 1, has_coords)
                self.asset_list.addItem(item)

            self.update_map_markers()

            total_count = len(all_assets)
            if has_coords_count == 0:
                self.status_label.setText(
                    f"共 {total_count} 个资产，均未填写坐标。请先填写地址，再点「批量定位」输入高德 Key 自动获取经纬度。"
                )
            else:
                self.status_label.setText(
                    f"共 {total_count} 个资产，其中 {has_coords_count} 个已定位（地图显示）。未定位的请点「批量定位」。"
                )

        finally:
            conn.close()

    def update_map_markers(self):
        """更新地图标记"""
        markers = []
        for asset_id, data in self.assets_data.items():
            markers.append({
                'id': data['id'],
                'name': data['name'],
                'location': data['location'],
                'category': data['category'],
                'status': data['status'],
                'lng': data['lng'],
                'lat': data['lat'],
                'responsible': data['responsible']
            })

        markers_json = json.dumps(markers, ensure_ascii=False)

        # 获取用户选择的缩放级别
        custom_zoom = self.get_zoom_level_from_combo()

        if self.current_map_type == "osm":
            self.load_osm(markers_json, custom_zoom)
        elif self.current_map_type == "amap":
            self.load_amap(markers_json, custom_zoom)

    def on_map_type_changed(self, text):
        """地图类型切换"""
        if text == "OpenStreetMap（免费）":
            self.current_map_type = "osm"
        elif text == "高德地图":
            self.current_map_type = "amap"
            # 检查是否配置了API密钥
            key = get_amap_key()
            if not key:
                self.status_label.setText("提示：使用高德地图需要先配置API密钥，点击「设置 API 密钥」按钮进行配置")

        self.update_map_markers()

    @pyqtSlot(str)
    def on_zoom_level_changed(self, text):
        """缩放级别变化"""
        self.update_map_markers()

    @pyqtSlot(str)
    def on_search_changed(self, text):
        """搜索框内容变化"""
        self.asset_list.clear()

        for asset_id, data in self.assets_data.items():
            if text.lower() in data['name'].lower():
                has_coords = data.get('lng') is not None and data.get('lat') is not None
                if has_coords:
                    item_text = f"{data['name']} - {data['location']}"
                else:
                    item_text = f"{data['name']} - {data['location']} 【未定位】"

                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, asset_id)
                item.setData(Qt.UserRole + 1, has_coords)
                self.asset_list.addItem(item)

    @pyqtSlot("QListWidgetItem*")
    def on_asset_clicked(self, item):
        """资产列表项点击"""
        asset_id = item.data(Qt.UserRole)
        has_coords = item.data(Qt.UserRole + 1)

        print(f"[DEBUG] on_asset_clicked: asset_id={asset_id}, has_coords={has_coords}, type={type(has_coords)}")
        print(f"[DEBUG] assets_data keys: {list(self.assets_data.keys())[:10]}")

        if not has_coords:
            QMessageBox.information(
                self,
                "未定位",
                "该资产暂无坐标，无法在地图上显示。\n\n请先确保在「资产管理」中填写了地址，再点击「批量定位」并输入高德 Key 自动获取经纬度。"
            )
            return
        if asset_id in self.assets_data:
            data = self.assets_data[asset_id]
            print(f"[DEBUG] focusing on asset: {data}")
            self.focus_on_asset(data)
        else:
            print(f"[DEBUG] asset_id {asset_id} not found in assets_data")

    def focus_on_asset(self, data):
        """在地图上定位到指定资产"""
        lat, lng = data['lat'], data['lng']
        asset_id = data['id']
        print(f"[DEBUG] focus_on_asset: id={asset_id}, lat={lat}, lng={lng}, map_type={self.current_map_type}")

        if self.current_map_type == "osm":
            js_code = f"focusAsset({lat}, {lng}, {asset_id});"
        else:
            js_code = f"focusAsset({lng}, {lat}, {asset_id});"

        print(f"[DEBUG] executing JS: {js_code}")

        def js_result(result):
            print(f"[DEBUG] JS result: {result}")

        self.web_view.page().runJavaScript(js_code, js_result)

    def batch_geocode_assets(self):
        """批量地理编码"""
        from services.geocoding import GeocodingService

        api_key, ok = QInputDialog.getText(
            self, "批量定位",
            "请输入高德地图API Key:\n(申请地址: https://lbs.amap.com/)"
        )

        if not ok or not api_key:
            return

        self.geocoding_service = GeocodingService(self.db)
        self.geocoding_service.set_amap_key(api_key)

        self.status_label.setText("正在批量定位资产，请稍候...")

        import threading

        def geocode_thread():
            success_count = self.geocoding_service.auto_geocode_all("amap")

            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self, "on_geocode_complete",
                Qt.QueuedConnection,
                Q_ARG(int, success_count)
            )

        thread = threading.Thread(target=geocode_thread)
        thread.daemon = True
        thread.start()

    @pyqtSlot(int)
    def on_geocode_complete(self, success_count):
        """地理编码完成回调"""
        self.status_label.setText(f"批量定位完成，成功 {success_count} 个")
        QMessageBox.information(
            self, "完成",
            f"批量定位完成！\n成功处理 {success_count} 个资产"
        )
        self.load_assets()

    @pyqtSlot(int)
    def on_show_detail_requested(self, asset_id):
        """处理来自JavaScript的显示详情请求"""
        print(f"[DEBUG] on_show_detail_requested called with asset_id={asset_id}")
        self.show_asset_detail(asset_id)

    @pyqtSlot(int)
    def show_asset_detail(self, asset_id):
        """显示资产详细信息对话框"""
        print(f"[DEBUG] show_asset_detail called with asset_id={asset_id}")

        conn = self.db.get_connection()
        try:
            c = conn.cursor()

            # 使用与资产管理界面一致的查询
            c.execute('''
                SELECT 
                    a.id, a.name, a.category, a.management_type, a.asset_number, a.quantity,
                    a.model, a.purchase_date, a.market_value, a.responsible_person,
                    a.location, a.status, a.lease_start_date, a.lease_end_date,
                    a.lease_reminder_days, a.tenant_name, a.tenant_contact,
                    a.tenant_nature, a.tenant_purpose, a.rent_payment_method, a.bidding_situation,
                    a.certificate_status, a.property_unit, a.building_area,
                    a.rent_amount,
                    a.trusteeship_contract_type,
                    a.trusteeship_contract_amount, a.trusteeship_counterparty,
                    a.trusteeship_contract_number, a.trusteeship_start_date,
                    a.trusteeship_end_date, a.trusteeship_sign_date,
                    a.trusteeship_is_archived, 
                    a.image_path1, a.image_path2, a.image_path3, a.notes,
                    a.created_by,
                    a.created_at, a.department_id, d.name as department_name,
                    a.longitude, a.latitude, a.coord_type
                FROM assets a
                LEFT JOIN departments d ON a.department_id = d.id
                WHERE a.id=?
            ''', (asset_id,))
            row = c.fetchone()

            # 字段映射（与查询顺序一致）
            columns = [
                'id', 'name', 'category', 'management_type', 'asset_number', 'quantity',
                'model', 'purchase_date', 'market_value', 'responsible_person',
                'location', 'status', 'lease_start_date', 'lease_end_date',
                'lease_reminder_days', 'tenant_name', 'tenant_contact',
                'tenant_nature', 'tenant_purpose', 'rent_payment_method', 'bidding_situation',
                'certificate_status', 'property_unit', 'building_area',
                'rent_amount',
                'trusteeship_contract_type',
                'trusteeship_contract_amount', 'trusteeship_counterparty',
                'trusteeship_contract_number', 'trusteeship_start_date',
                'trusteeship_end_date', 'trusteeship_sign_date',
                'trusteeship_is_archived',
                'image_path1', 'image_path2', 'image_path3', 'notes',
                'created_by',
                'created_at', 'department_id', 'department_name',
                'longitude', 'latitude', 'coord_type'
            ]

            if row:
                asset = dict(zip(columns, row))
            else:
                asset = None
        finally:
            conn.close()

        if not asset:
            QMessageBox.warning(self, "错误", "未找到该资产信息")
            return

        # 创建详情对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(f"资产详情 - {asset.get('name', '')}")
        dialog.resize(700, 600)

        layout = QVBoxLayout(dialog)

        # 创建标签页
        tabs = QTabWidget()
        tabs.setDocumentMode(True)  # 文档模式
        tabs.setStyleSheet("""
            QTabWidget::pane { 
                border: 1px solid #ddd;
                background: white;
            }
            QTabBar::tab { 
                padding: 12px 20px; 
                font-size: 20px;
                min-width: 98px;
                min-height: 55px;
            }
            QTabBar::tab:selected { 
                background: #3498db;
                color: white;
            }
            QTabBar::tab:!selected { 
                background: #f0f0f0;
                color: #333;
            }
            QTabBar {
                min-height: 60px;
            }
            QLabel { font-size: 20px; }
            QTextEdit { font-size: 20px; }
        """)

        # 让标签栏可以滚动
        tabs.tabBar().setExpanding(False)
        tabs.tabBar().setUsesScrollButtons(True)  # 标签过多时显示滚动按钮

        # 基本信息标签页
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)

        def add_field(layout, label, value, bold=False):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(5, 5, 5, 5)
            lbl_title = QLabel(f"<b>{label}:</b>")
            lbl_title.setStyleSheet("font-size: 20px;")
            lbl_title.setMinimumWidth(140)
            lbl_value = QLabel(str(value) if value else "-")
            if bold:
                lbl_value.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
            else:
                lbl_value.setStyleSheet("font-size: 20px;")
            lbl_value.setWordWrap(True)
            row_layout.addWidget(lbl_title)
            row_layout.addWidget(lbl_value, 1)
            layout.addWidget(row)

        # 处理市场价值显示
        market_value = asset.get('market_value')
        if market_value is None or market_value == "" or market_value == 0:
            market_value_display = "-"
        else:
            try:
                market_value_num = float(market_value)
                if market_value_num >= 10000:
                    market_value_display = f"¥{market_value_num / 10000:,.2f} 万元"
                else:
                    market_value_display = f"¥{market_value_num:,.2f} 元"
            except (ValueError, TypeError):
                market_value_display = str(market_value) if market_value else "-"

        # 获取部门名称
        dept_name = asset.get('department_name')
        if not dept_name:
            dept_name = "未分配部门"

        # 创建信息卡片
        add_field(scroll_layout, "资产名称", asset.get('name', ''))
        add_field(scroll_layout, "资产分类", asset.get('category', ''))
        add_field(scroll_layout, "管理方式", asset.get('management_type', ''))
        add_field(scroll_layout, "资产编号", asset.get('asset_number', ''))
        add_field(scroll_layout, "数量", str(asset.get('quantity', '')))
        add_field(scroll_layout, "型号", asset.get('model', ''))
        add_field(scroll_layout, "购置日期", asset.get('purchase_date') or "-")
        add_field(scroll_layout, "市场价值", market_value_display)
        add_field(scroll_layout, "责任人", asset.get('responsible_person', ''), bold=True)
        add_field(scroll_layout, "位置", asset.get('location', ''))
        add_field(scroll_layout, "状态", asset.get('status', '') or "未设置")
        add_field(scroll_layout, "所属部门", dept_name)
        add_field(scroll_layout, "录入人", asset.get('created_by', '') or "未知")
        add_field(scroll_layout, "录入时间", asset.get('created_at', '') or "未知")

        scroll.setWidget(scroll_widget)
        basic_layout.addWidget(scroll)
        tabs.addTab(basic_tab, "基本信息")

        # 租赁信息标签页
        if asset.get('management_type') == "租赁管理":
            lease_tab = QWidget()
            lease_layout = QVBoxLayout(lease_tab)
            scroll2 = QScrollArea()
            scroll2.setWidgetResizable(True)
            scroll_widget2 = QWidget()
            scroll_layout2 = QVBoxLayout(scroll_widget2)
            scroll_layout2.setSpacing(10)

            add_field(scroll_layout2, "租赁开始日期", asset.get('lease_start_date') or "-", bold=True)
            add_field(scroll_layout2, "租赁结束日期", asset.get('lease_end_date') or "-", bold=True)
            add_field(scroll_layout2, "提醒天数", str(asset.get('lease_reminder_days')) if asset.get('lease_reminder_days') else "-")
            add_field(scroll_layout2, "承租方名称", asset.get('tenant_name') or "-")
            add_field(scroll_layout2, "承租方联系方式", asset.get('tenant_contact') or "-")
            add_field(scroll_layout2, "承租方性质", asset.get('tenant_nature') or "-")
            add_field(scroll_layout2, "承租方用途", asset.get('tenant_purpose') or "-")

            rent_amount = asset.get('rent_amount')
            if rent_amount:
                try:
                    rent_display = f"¥{float(rent_amount):,.2f} 元"
                except:
                    rent_display = str(rent_amount)
            else:
                rent_display = "-"
            add_field(scroll_layout2, "租金金额", rent_display, bold=True)

            add_field(scroll_layout2, "租金交付方式", asset.get('rent_payment_method') or "-")
            add_field(scroll_layout2, "公开招拍租情况", asset.get('bidding_situation') or "-")

            scroll2.setWidget(scroll_widget2)
            lease_layout.addWidget(scroll2)
            tabs.addTab(lease_tab, "租赁信息")

        # 托管信息标签页
        if asset.get('management_type') == "托管管理":
            trust_tab = QWidget()
            trust_layout = QVBoxLayout(trust_tab)
            scroll3 = QScrollArea()
            scroll3.setWidgetResizable(True)
            scroll_widget3 = QWidget()
            scroll_layout3 = QVBoxLayout(scroll_widget3)
            scroll_layout3.setSpacing(10)

            add_field(scroll_layout3, "合同类型", asset.get('trusteeship_contract_type') or "-")

            trust_amount = asset.get('trusteeship_contract_amount')
            if trust_amount:
                try:
                    trust_display = f"¥{float(trust_amount):,.2f} 元"
                except:
                    trust_display = str(trust_amount)
            else:
                trust_display = "-"
            add_field(scroll_layout3, "合同金额", trust_display)

            add_field(scroll_layout3, "合同相对方", asset.get('trusteeship_counterparty') or "-")
            add_field(scroll_layout3, "合同编号", asset.get('trusteeship_contract_number') or "-")
            add_field(scroll_layout3, "合同开始日期", asset.get('trusteeship_start_date') or "-")
            add_field(scroll_layout3, "合同结束日期", asset.get('trusteeship_end_date') or "-")
            add_field(scroll_layout3, "签署日期", asset.get('trusteeship_sign_date') or "-")
            add_field(scroll_layout3, "是否归档", asset.get('trusteeship_is_archived') or "-")

            scroll3.setWidget(scroll_widget3)
            trust_layout.addWidget(scroll3)
            tabs.addTab(trust_tab, "托管信息")

        # 房屋信息标签页
        if asset.get('category') == "房屋资产":
            house_tab = QWidget()
            house_layout = QVBoxLayout(house_tab)
            scroll4 = QScrollArea()
            scroll4.setWidgetResizable(True)
            scroll_widget4 = QWidget()
            scroll_layout4 = QVBoxLayout(scroll_widget4)
            scroll_layout4.setSpacing(10)

            add_field(scroll_layout4, "产证情况", asset.get('certificate_status') or "-")
            add_field(scroll_layout4, "产权单位", asset.get('property_unit') or "-")
            add_field(scroll_layout4, "建筑面积", asset.get('building_area') or "-")

            scroll4.setWidget(scroll_widget4)
            house_layout.addWidget(scroll4)
            tabs.addTab(house_tab, "房屋信息")

        # 资产图片标签页
        image_paths = []
        if asset.get('image_path1'):
            image_paths.append(asset.get('image_path1'))
        if asset.get('image_path2'):
            image_paths.append(asset.get('image_path2'))
        if asset.get('image_path3'):
            image_paths.append(asset.get('image_path3'))

        if any(image_paths):
            from PyQt5.QtGui import QPixmap
            from PyQt5.QtWidgets import QSizePolicy

            image_tab = QWidget()
            image_layout = QVBoxLayout(image_tab)

            scroll_img = QScrollArea()
            scroll_img.setWidgetResizable(True)
            scroll_img_widget = QWidget()
            scroll_img_layout = QVBoxLayout(scroll_img_widget)
            scroll_img_layout.setSpacing(15)

            for idx, img_path in enumerate(image_paths, 1):
                img_label = QLabel(f"<b>图片 {idx}</b>")
                img_label.setStyleSheet("font-size: 20px; color: #2c3e50;")
                scroll_img_layout.addWidget(img_label)

                if os.path.exists(img_path):
                    pixmap = QPixmap(img_path)
                    if not pixmap.isNull():
                        # 按比例缩放图片，最大宽度600
                        scaled_pixmap = pixmap.scaled(600, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        img_display = QLabel()
                        img_display.setPixmap(scaled_pixmap)
                        img_display.setAlignment(Qt.AlignCenter)
                        scroll_img_layout.addWidget(img_display)
                    else:
                        img_error = QLabel("无法加载图片")
                        img_error.setStyleSheet("font-size: 20px; color: #e74c3c;")
                        scroll_img_layout.addWidget(img_error)
                else:
                    img_not_found = QLabel(f"图片文件不存在: {img_path}")
                    img_not_found.setStyleSheet("font-size: 20px; color: #e74c3c;")
                    scroll_img_layout.addWidget(img_not_found)

                scroll_img_layout.addSpacing(10)

            scroll_img.setWidget(scroll_img_widget)
            image_layout.addWidget(scroll_img)
            tabs.addTab(image_tab, "资产图片")

        # 备注标签页
        if asset.get('notes'):
            notes_tab = QWidget()
            notes_layout = QVBoxLayout(notes_tab)
            notes_text = QTextEdit()
            notes_text.setText(asset.get('notes', ''))
            notes_text.setReadOnly(True)
            notes_text.setStyleSheet("font-size: 20px;")
            notes_layout.addWidget(notes_text)
            tabs.addTab(notes_tab, "备注")

        layout.addWidget(tabs)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton:hover { background: #2980b9; }
        """)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.exec_()
