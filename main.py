import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget, QVBoxLayout
from loguru import logger
from qfluentwidgets import isDarkTheme

from .ClassWidgets.base import PluginBase

# 常量定义
WIDGET_CODE = 'widget_test.ui'
WIDGET_NAME = 'LyricsIsland'
WIDGET_WIDTH = 300

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 50063
DEFAULT_LYRIC = '等待音乐软件侧传输歌词...'


class UpdateSignal(QObject):
    """用于处理歌词更新的信号类"""
    update_signal = pyqtSignal(str, str, str)  # 修改信号以传递额外的歌词


class LyricsData:
    """存储歌词数据的类"""

    def __init__(self):
        self.lyric_lyric = ""
        self.extra_lyric = ""


# 创建全局实例
lyrics_data = LyricsData()
update_signal = UpdateSignal()


class LyricsHandler(BaseHTTPRequestHandler):
    """处理歌词HTTP请求的处理器"""

    def __init__(self, *args, **kwargs):
        self.update_signal = update_signal
        super().__init__(*args, **kwargs)

    def do_POST(self):
        """处理POST请求"""
        if self.path != '/component/lyrics/lyrics/':
            self._send_error(404, "Not Found")
            return

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                raise ValueError("Empty request body")

            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            lyric_lyric = data.get("lyric")
            extra_lyric = data.get("extra")

            if lyric_lyric is None:
                raise ValueError("Missing 'lyric' field in request")

            # 更新全局歌词数据
            lyrics_data.lyric_lyric = lyric_lyric
            lyrics_data.extra_lyric = extra_lyric or ""

            # 发送更新信号，包含两种歌词
            self.update_signal.update_signal.emit(
                lyric_lyric,
                extra_lyric or "",  # 如果extra为None，使用空字符串
                WIDGET_NAME
            )

            # logger.info(f"收到新歌词 - 基础: {lyric_lyric}, 附加: {extra_lyric}")

            self._send_response(200, "OK")

        except json.JSONDecodeError:
            logger.error("Invalid JSON format")
            self._send_error(400, "Invalid JSON format")
        except ValueError as e:
            logger.error(f"Invalid request: {str(e)}")
            self._send_error(400, str(e))
        except Exception as e:
            logger.error(f"Server error: {str(e)}")
            self._send_error(500, "Internal Server Error")

    def _send_response(self, code: int, message: str):
        """发送成功响应"""
        self.send_response(code)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(message.encode())

    def _send_error(self, code: int, message: str):
        """发送错误响应"""
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        error_response = json.dumps({"error": message})
        self.wfile.write(error_response.encode())

    def log_message(self, format, *args):
        """禁用默认日志"""
        return


class HTTPServerWithStop(HTTPServer):
    """可停止的HTTP服务器"""

    def serve_forever(self):
        self.running = True
        while self.running:
            self.handle_request()

    def stop(self):
        """停止服务器"""
        self.running = False


class Plugin(PluginBase):
    """LyricsIsland 插件主类"""

    def __init__(self, cw_contexts, method):
        super().__init__(cw_contexts, method)
        self.method.register_widget(WIDGET_CODE, WIDGET_NAME, WIDGET_WIDTH)
        self.server: Optional[HTTPServerWithStop] = None
        update_signal.update_signal.connect(self.update_content)
        self.lyrics_widget = None
        self.lyric_label = None
        self.extra_label = None

    def execute(self):
        """插件执行入口"""
        try:
            self._setup_widget()
            self._start_server()
            if self.lyrics_widget:
                title = self.lyrics_widget.findChild(QLabel, 'title')  # 获取标题
                title.hide()  # 隐藏标题
            logger.success('LyricsIsland plugin started successfully!')
        except Exception as e:
            logger.error(f"Failed to start plugin: {str(e)}")
            raise

    def _setup_widget(self):
        """设置小组件"""
        self.lyrics_widget = self.method.get_widget(WIDGET_CODE)
        if self.lyrics_widget:
            content_layout = self.lyrics_widget.findChild(QHBoxLayout, 'contentLayout')
            if content_layout:
                content_layout.setSpacing(1)

                # 创建新的窗口和布局
                widget = QWidget()
                layout = QVBoxLayout()
                widget.setLayout(layout)

                # 创建标签
                self.lyric_label = QLabel(DEFAULT_LYRIC)
                self.extra_label = QLabel("")

                # 设置标签样式
                self._update_label_styles()

                # 添加标签到布局
                layout.addWidget(self.lyric_label)
                layout.addWidget(self.extra_label)

                # 添加新窗口到contentLayout
                content_layout.addWidget(widget)
            else:
                logger.warning("Content layout not found in widget")
        else:
            logger.warning("Widget not found")

    def _update_label_styles(self):
        """更新标签样式"""
        if not self.lyric_label or not self.extra_label:
            return

        self.method.change_widget_content(WIDGET_CODE, "WIDGET_NAME", "")

        # 获取主题
        is_dark = isDarkTheme()

        # 基础文本颜色
        text_color = "#FFFFFF" if is_dark else "#000000"
        # 附加歌词颜色（稍微淡一点）
        extra_text_color = "#CCCCCC" if is_dark else "#666666"

        # 主歌词样式
        self.lyric_label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-family: "Microsoft YaHei", "微软雅黑";
                font-size: 16px;
                font-weight: bold;
                qproperty-alignment: AlignCenter;
                padding: 1px;
            }}
        """)

        # 附加歌词样式
        self.extra_label.setStyleSheet(f"""
            QLabel {{
                color: {extra_text_color};
                font-family: "Microsoft YaHei", "微软雅黑";
                font-size: 14px;
                font-weight: bold;
                qproperty-alignment: AlignCenter;
                padding: 1px;
            }}
        """)

    def theme_changed(self):
        """处理主题变化"""
        self._update_label_styles()

    def _start_server(self):
        """启动HTTP服务器"""

        def server_worker():
            try:
                self.server = HTTPServerWithStop((SERVER_HOST, SERVER_PORT), LyricsHandler)
                logger.info(f"Server started at http://{SERVER_HOST}:{SERVER_PORT}")
                self.server.serve_forever()
            except Exception as e:
                logger.error(f"Server error: {str(e)}")

        server_thread = threading.Thread(target=server_worker, daemon=True)
        server_thread.start()

    def update_content(self, lyric_lyric: str, extra_lyric: str, title: str):
        """更新歌词内容"""
        if self.lyric_label and self.extra_label:
            try:
                self.lyric_label.setText(lyric_lyric)
                self.extra_label.setText(extra_lyric)
            except Exception as e:
                logger.error(f"Failed to update content: {str(e)}")

    def cleanup(self):
        """清理资源"""
        if self.server:
            try:
                self.server.stop()
                logger.info("Server stopped")
            except Exception as e:
                logger.error(f"Failed to stop server: {str(e)}")
