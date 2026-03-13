import logging
import folium
import folium.plugins
import os
from PyQt5.QtCore import QUrl, Qt, QObject
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from folium.plugins import MousePosition


class MapBridge(QObject):
    """用于JavaScript和Python通信的桥接类"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def mapClicked(self, lat, lng):
        """处理地图点击事件"""
        print(f"地图点击 - 纬度: {lat:.6f}, 经度: {lng:.6f}")

class MapWidget(QWidget):
    """
    使用folium和QWebEngineView显示地图和无人机位置的控件
    """
    def __init__(self, default_location=(30.5928, 104.3055), zoom_start=13, map_file_path='map.html', drone=None):
        """初始化地图控件

        Args:
            default_location: 默认地图中心位置(纬度,经度)
            zoom_start: 默认缩放级别
            map_file_path: 预先创建的地图HTML文件路径
        """
        super().__init__()
        self.default_location = default_location
        self.zoom_start = zoom_start
        self.map_file_path = map_file_path

        self.logger = logging.getLogger(__name__)
        self.drone = drone
        self.m = None
        # 创建folium地图对象
        self.m = folium.Map(
            location=self.default_location,
            zoom_start=self.zoom_start,
            tiles="https://webst02.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}",
            attr='高德卫星地图'
        )

        self.create_map()
        # 初始化界面
        self.init_ui()

    def init_ui(self):
        """初始化UI布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建Web引擎视图以显示folium地图
        self.web_view = QWebEngineView()
        self.web_view.setContextMenuPolicy(Qt.NoContextMenu)  # 禁用右键菜单
        
        # 设置WebChannel
        self.channel = QWebChannel()
        self.bridge = MapBridge(self)
        self.channel.registerObject("map_widget", self.bridge)
        self.web_view.page().setWebChannel(self.channel)
        
        layout.addWidget(self.web_view)

        # 初始化地图
        self.load_map()

    def load_map(self):
        """加载预先创建的地图文件或创建新地图"""
        map_file_path = 'map/new_map.html'

        if os.path.exists(map_file_path):
            # 如果地图文件已存在，直接加载
            self.web_view.load(QUrl.fromLocalFile(os.path.abspath(map_file_path)))

        else:

            html = self.m.get_root().render()
            self.web_view.setHtml(html, QUrl(''))

            # 保存地图文件
            self.m.save(map_file_path)

    def create_map(self):
        """添加插件"""
        # 搜索栏
        plugin_geocoder = folium.plugins.Geocoder()
        plugin_geocoder.add_to(self.m)

        # 测量工具
        plugin_measure = folium.plugins.MeasureControl()
        plugin_measure.add_to(self.m)

        # 绘图工具
        plugin_draw = folium.plugins.Draw()
        plugin_draw.add_to(self.m)

        # 获取用户当前位置
        # plugin_loc = folium.plugins.LocateControl(auto_start=True)
        # plugin_loc.add_to(self.m)

        # 点击鼠标，显示经纬度
        plugin_click_LatLon = folium.LatLngPopup()
        self.m.add_child(plugin_click_LatLon)

        # 移动鼠标显示经纬度
        formatter = 'function(num) {return L.Util.formatNum(num, 4) + \' A° \'}'
        plugin_hover = MousePosition(
            position='topright',
            separator = ' | ',
            empty_string='鼠标划动显示经纬度',
            lng_first=False,
            num_digits=20,
            prefix='经纬度：',
            lat_formatter=formatter,
            lng_formatter=formatter,
        )
        self.m.add_child(plugin_hover)

    def map_clicked(self, lat, lng):
        """处理地图点击事件"""
        print(f"地图点击 - 纬度: {lat:.6f}, 经度: {lng:.6f}")

    def setup_webchannel(self, bridge):
        """设置WebChannel桥接"""
        from PyQt5.QtWebChannel import QWebChannel

        self.bridge = bridge
        self.channel = QWebChannel()
        self.channel.registerObject('bridge', self.bridge)
        self.web_view.page().setWebChannel(self.channel)
        self.logger.info("🔗 WebChannel连接已设置")
