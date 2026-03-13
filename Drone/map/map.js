// 创建地图
var map = L.map(
    "map",
    {
        center: [30.5928, 104.3055],
        crs: L.CRS.EPSG3857,
        ...{
            "zoom": 13,
            "zoomControl": true,
            "preferCanvas": false,
        }
    }
);

var tile_layer = L.tileLayer(
    // "https://webst02.is.autonavi.com/appmaptile?style=6\u0026x={x}\u0026y={y}\u0026z={z}",
    "https://mt1.google.com/vt/lyrs=s\u0026x={x}\u0026y={y}\u0026z={z}",
    {
        "minZoom": 0,
        "maxZoom": 18,
        "maxNativeZoom": 18,
        "noWrap": false,
        "attribution": "\u9ad8\u5fb7\u536b\u661f\u5730\u56fe",
        "subdomains": "abc",
        "detectRetina": false,
        "tms": false,
        "opacity": 1,
    }
);

tile_layer.addTo(map)

// 存储标点的数组
var markers = [];
var polyline = null;
var markerIndex = 1;

// QWebChannel 连接变量
var pyqt_bridge = null;

// 初始化QWebChannel通信
function initializeWebChannel() {
    if (typeof QWebChannel !== 'undefined') {
        new QWebChannel(qt.webChannelTransport, function (channel) {
            // 连接到Python对象
            pyqt_bridge = channel.objects.bridge;
        });
    }
}

initializeWebChannel()

// 修改向PyQt发送坐标数据函数，确保按序号排序
function sendCoordinatesToPyQt(action, data) {
    if (pyqt_bridge) {
        try {
            if (action === 'add') {
                pyqt_bridge.addCoordinate(data.index, data.lat, data.lng);
            } else if (action === 'remove') {
                pyqt_bridge.removeCoordinate(data.index);
            } else if (action === 'clear') {
                pyqt_bridge.clearAllCoordinates();
            } else if (action === 'update') {
                // 发送完整的坐标列表（按序号排序）
                var coordinateList = markers.slice().sort(function(a, b) {
                    return a.index - b.index;
                }).map(function(m) {
                    return {
                        index: m.index,
                        lat: m.lat,
                        lng: m.lng
                    };
                });
                pyqt_bridge.updateCoordinateList(JSON.stringify(coordinateList));
            }
        } catch (error) {

        }
    }
}

// 创建方框标点图标
function createSquareMarker(number) {
    var iconHtml = '<div style="' +
        'width: 15px; ' +
        'height: 15px; ' +
        'background-color: #FF0000; ' +
        'border: 3px solid white; ' +
        'border-radius: 4px; ' +
        'display: flex; ' +
        'align-items: center; ' +
        'justify-content: center; ' +
        'font-size: 10px; ' +
        'font-weight: bold; ' +
        'color: white; ' +
        'font-family: Arial, sans-serif; ' +
        'text-shadow: 1px 1px 2px black; ' +
        'box-shadow: 0 3px 8px rgba(0,0,0,0.6); ' +
        'cursor: pointer; ' +
        'z-index: 1000;' +
        '">' + number + '</div>';

    return L.divIcon({
        className: '', // 不使用CSS类，直接用内联样式
        html: iconHtml,
        iconSize: [10, 10],
        iconAnchor: [10, 10],
        popupAnchor: [0, -15]
    });
}

// 地图点击事件处理
function onMapClick(e) {
    var lat = e.latlng.lat;
    var lng = e.latlng.lng;

    // 使用当前的markerIndex（应该是最后一个标点序号+1）
    var currentIndex = markerIndex;

    // 创建带序号的标记
    var marker = L.marker([lat, lng], {
        icon: createSquareMarker(currentIndex),
        zIndexOffset: 1000
    }).addTo(map);

    // 添加弹窗显示坐标和序号
    marker.bindPopup(
        '<div style="text-align: center; padding: 10px;">' +
        '<h3 style="margin: 5px 0; color: #FF0000;">📍 标点 ' + currentIndex + '</h3>' +
        '<p style="margin: 3px 0;"><strong>纬度:</strong> ' + lat.toFixed(6) + '</p>' +
        '<p style="margin: 3px 0;"><strong>经度:</strong> ' + lng.toFixed(6) + '</p>' +
        '<button onclick="removeMarkerByIndex(' + currentIndex + ')" ' +
        'style="margin-top: 8px; padding: 4px 8px; background: #E74C3C; color: white; ' +
        'border: none; border-radius: 3px; cursor: pointer;">🗑️ 删除此标点</button>' +
        '</div>'
    );

    // 存储标记信息
    var markerData = {
        marker: marker,
        lat: lat,
        lng: lng,
        index: currentIndex
    };

    // 存储标记信息
    markers.push(markerData);
    // 发送新坐标到PyQt
    sendCoordinatesToPyQt('add', {
        index: currentIndex,
        lat: lat,
        lng: lng
    });

    // 更新markerIndex为下一个序号
    markerIndex = markers.length + 1;

    // 连接标点
    updatePolyline();
}

// 根据索引删除特定标点
function removeMarkerByIndex(index) {
    // 找到对应的标点
    var markerToRemove = null;
    var removeIndex = -1;

    for (var i = 0; i < markers.length; i++) {
        if (markers[i].index === index) {
            markerToRemove = markers[i];
            removeIndex = i;
            break;
        }
    }

    if (markerToRemove) {
        // 从地图上移除标记
        map.removeLayer(markerToRemove.marker);

        // 从数组中移除
        markers.splice(removeIndex, 1);

        // 通知PyQt删除对应坐标
        sendCoordinatesToPyQt('remove', {index: index});

        // 重新排序所有标点
        reorderMarkers();

        // 更新连接线
        updatePolyline();
    }
}

// 重新排序标点函数
function reorderMarkers() {
    // 临时移除所有标点从地图
    markers.forEach(function(m) {
        map.removeLayer(m.marker);
    });

    // 重新分配序号并更新标点
    for (var i = 0; i < markers.length; i++) {
        var newIndex = i + 1;
        var oldIndex = markers[i].index;

        // 更新索引
        markers[i].index = newIndex;

        // 创建新的标记图标
        var newMarker = L.marker([markers[i].lat, markers[i].lng], {
            icon: createSquareMarker(newIndex),
            zIndexOffset: 1000
        }).addTo(map);

        // 更新弹窗内容
        newMarker.bindPopup(
            '<div style="text-align: center; padding: 10px;">' +
            '<h3 style="margin: 5px 0; color: #FF0000;">📍 标点 ' + newIndex + '</h3>' +
            '<p style="margin: 3px 0;"><strong>纬度:</strong> ' + markers[i].lat.toFixed(6) + '</p>' +
            '<p style="margin: 3px 0;"><strong>经度:</strong> ' + markers[i].lng.toFixed(6) + '</p>' +
            '<button onclick="removeMarkerByIndex(' + newIndex + ')" ' +
            'style="margin-top: 8px; padding: 4px 8px; background: #E74C3C; color: white; ' +
            'border: none; border-radius: 3px; cursor: pointer;">🗑️ 删除此标点</button>' +
            '</div>'
        );

        // 更新标记引用
        markers[i].marker = newMarker;
    }

    // 更新全局标点索引为下一个可用序号
    markerIndex = markers.length + 1;

    // 同步更新到PyQt
    sendCoordinatesToPyQt('update', {});

    console.log('✅ 标点重新排序完成，下一个标点序号: ' + markerIndex);
}

// 更新连接线
function updatePolyline() {
    // 移除旧的连接线
    if (polyline) {
        map.removeLayer(polyline);
    }

    // 如果有两个或更多标点，创建连接线
    if (markers.length >= 2) {
        // 按序号排序后创建连接线
        var sortedMarkers = markers.slice().sort(function(a, b) {
            return a.index - b.index;
        });

        var latlngs = sortedMarkers.map(function(m) {
            return [m.lat, m.lng];
        });

        polyline = L.polyline(latlngs, {
            color: '#FF0000',   // 红色线条
            weight: 2,
            opacity: 0.7,
        }).addTo(map);
    }
}

// 清除所有标点的函数
function clearAllMarkers() {
    markers.forEach(function(m) {
        map.removeLayer(m.marker);
    });

    if (polyline) {
        map.removeLayer(polyline);
        polyline = null;
    }

    markers = [];
    markerIndex = 1; // 重置为1

    // 通知PyQt清除所有坐标
    sendCoordinatesToPyQt('clear', {});
}

// 撤销最后一个标点
function undoLastMarker() {
    if (markers.length > 0) {
        // 找到序号最大的标点（最后添加的）
        var maxIndex = Math.max.apply(Math, markers.map(function(m) { return m.index; }));
        var lastMarkerIndex = -1;

        for (var i = 0; i < markers.length; i++) {
            if (markers[i].index === maxIndex) {
                lastMarkerIndex = i;
                break;
            }
        }

        if (lastMarkerIndex !== -1) {
            var lastMarker = markers[lastMarkerIndex];
            var lastIndex = lastMarker.index;

            // 从地图移除
            map.removeLayer(lastMarker.marker);
            markers.splice(lastMarkerIndex, 1);

            // 通知PyQt删除对应坐标
            sendCoordinatesToPyQt('remove', {index: lastIndex});

            // 重新排序（确保序号连续）
            reorderMarkers();

            // 更新连接线
            updatePolyline();

            console.log('↶ 撤销标点 ' + lastIndex + '，剩余:', markers.length);
        }
    } else {
        console.log('⚠️ 没有可撤销的标点');
    }
}

// 获取所有坐标数据（供PyQt调用）
function getAllCoordinates() {
    var coordinateList = markers.map(function(m) {
        return {
            index: m.index,
            lat: m.lat,
            lng: m.lng
        };
    });
    return JSON.stringify(coordinateList);
}

// 添加控制按钮
var customControl = L.Control.extend({
    onAdd: function(map) {
        var container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');

        // 直接定义按钮样式
        var buttonStyle = 'padding: 8px 12px; margin: 2px; border: none; border-radius: 4px; ' +
            'cursor: pointer; font-weight: bold; font-size: 12px; ' +
            'transition: all 0.2s ease; display: block; width: 120px;';

        container.innerHTML =
            '<button onclick="clearAllMarkers()" title="清除所有标点" ' +
            'style="' + buttonStyle + 'background: #E74C3C; color: white;"' +
            'onmouseover="this.style.background=\'#C0392B\'" ' +
            'onmouseout="this.style.background=\'#E74C3C\'">' +
            '🗑️ 清除全部</button>' +
            '<button onclick="undoLastMarker()" title="撤销最后一个标点" ' +
            'style="' + buttonStyle + 'background: #F39C12; color: white;"' +
            'onmouseover="this.style.background=\'#E67E22\'" ' +
            'onmouseout="this.style.background=\'#F39C12\'">' +
            '↶ 撤销上一个</button>' +
            '<button onclick="sendCoordinatesToPyQt(\'update\', {})" title="同步数据到PyQt" ' +
            'style="' + buttonStyle + 'background: #27AE60; color: white;"' +
            'onmouseover="this.style.background=\'#229954\'" ' +
            'onmouseout="this.style.background=\'#27AE60\'">' +
            '🔄 同步数据</button>';


        container.style.backgroundColor = 'white';
        container.style.padding = '8px';
        container.style.borderRadius = '6px';
        container.style.boxShadow = '0 2px 8px rgba(0,0,0,0.3)';

        // 阻止点击事件冒泡到地图
        L.DomEvent.disableClickPropagation(container);

        return container;
    }
});

map.addControl(new customControl({position: 'topleft'}));

// 绑定地图点击事件
map.whenReady(function() {
    console.log('🗺️ 地图准备就绪！点击地图任意位置添加方框标点');
    console.log('📝 标点将显示为红色方框，内含序号');
    map.on('click', onMapClick);
});

// 鼠标划过显示经纬度
var mouse_position = new L.Control.MousePosition({
    "position": "topright",
    "separator": " | ",
    "emptyString": "\u9f20\u6807\u5212\u52a8\u663e\u793a\u7ecf\u7eac\u5ea6",
    "lngFirst": false,
    "numDigits": 20,
    "prefix": "\u7ecf\u7eac\u5ea6\uff1a",
})
mouse_position["latFormatter"] = function(num) {return L.Util.formatNum(num, 4) + ' A° '};
mouse_position["lngFormatter"] = function(num) {return L.Util.formatNum(num, 4) + ' A° '};
map.addControl(mouse_position);
tile_layer.addTo(map);
