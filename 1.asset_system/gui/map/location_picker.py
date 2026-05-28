"""
资产添加/编辑对话框中的地图定位功能
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView


def show_location_picker(self, initial_location=""):
    """
    显示位置选择器对话框
    :param initial_location: 初始位置
    :return: (地址, 经度, 纬度)
    """
    from .map_launcher import MapLocationPicker
    picker = MapLocationPicker(self.db, initial_location)
    return picker.get_result()


class MapLocationPicker(QDialog):
    """位置选择器对话框"""

    def __init__(self, db, initial_location="", parent=None):
        super().__init__(parent)
        self.db = db
        self.geocoding_service = None
        self.current_location = initial_location
        self.result_location = initial_location
        self.result_lng = None
        self.result_lat = None

        self.setWindowTitle("位置选择")
        self.resize(800, 600)
        self.init_ui()
        self.load_map()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 顶部搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入地址搜索...")
        self.search_input.returnPressed.connect(self.search_location)
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.search_location)
        search_layout.addWidget(search_btn)

        layout.addLayout(search_layout)

        # 地图
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        confirm_btn = QPushButton("确认")
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def load_map(self):
        """加载地图"""
        html = self.generate_map_html()
        self.web_view.setHtml(html)

    def generate_map_html(self):
        """生成地图HTML"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>位置选择</title>
    <style>
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; }
        #container { width: 100%; height: 100%; }
    </style>
    <script type="text/javascript" src="https://webapi.amap.com/maps?v=2.0&key=YOUR_AMAP_KEY"></script>
</head>
<body>
    <div id="container"></div>
    <script type="text/javascript">
        var map = new AMap.Map('container', {
            zoom: 12,
            center: [120.293, 30.243]
        });

        var marker = null;

        map.on('click', function(e) {
            if (marker) {
                marker.setPosition(e.lnglat);
            } else {
                marker = new AMap.Marker({
                    position: e.lnglat,
                    draggable: true
                });
                marker.setMap(map);
            }
            document.selectedLng = e.lnglat.getLng();
            document.selectedLat = e.lnglat.getLat();
        });

        function setMarker(lng, lat) {
            if (marker) {
                marker.setPosition([lng, lat]);
            } else {
                marker = new AMap.Marker({
                    position: [lng, lat],
                    draggable: true
                });
                marker.setMap(map);
            }
            map.setCenter([lng, lat]);
            map.setZoom(16);
        }
    </script>
</body>
</html>
"""
        return html

    def search_location(self):
        """搜索位置"""
        address = self.search_input.text().strip()
        if not address:
            return

        if not self.geocoding_service:
            from services.geocoding import GeocodingService
            self.geocoding_service = GeocodingService(self.db)

        lng, lat = self.geocoding_service.geocode(address)

        if lng and lat:
            self.result_location = address
            self.result_lng = lng
            self.result_lat = lat
            js_code = f"setMarker({lng}, {lat});"
            self.web_view.page().runJavaScript(js_code)

    def get_result(self):
        """获取结果"""
        if self.exec_() == QDialog.Accepted:
            return self.result_location, self.result_lng, self.result_lat
        return None, None, None
