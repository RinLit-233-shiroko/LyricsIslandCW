"""
    这是一个示例插件
"""
import threading
from time import sleep

from PyQt5 import uic
from loguru import logger
from datetime import datetime
from .ClassWidgets.base import PluginBase, SettingsBase, PluginConfig  # 导入CW的基类
from flask import Flask, request, jsonify
from PyQt5.QtWidgets import QHBoxLayout
from qfluentwidgets import ImageLabel, LineEdit

current_lyric = ""  # 定义全局变量来存储歌词

app = Flask(__name__)

# Flask 路由处理，接收 POST 请求并返回歌词
@app.route('/component/lyrics/lyrics/', methods=['POST'])
def listen_lyrics():
    global current_lyric  # 使用全局变量
    try:
        # 从请求体中获取 JSON 数据
        data = request.get_json()
        # 提取并更新全局变量 'current_lyric' 字段
        current_lyric = data.get("lyric", "歌词无法解析...")
        # 提取并返回 'lyric' 字段
        lyric = data.get("lyric", "歌词无法解析...")

        # 写日志
        logger.info(f"收到新歌词：{lyric}")
        # 返回 JSON 格式响应
        with app.app_context():  # 确保在应用上下文中执行 jsonify
            return "OK, 200"




    except Exception as e:
        logger.error(f"Error processing request: {e}")
        with app.app_context():  # 确保在应用上下文中执行 jsonify
            return jsonify({"error": str(e)}), 400


# 启动 Flask 服务的函数
def start_flask():
    app.run(host="127.0.0.1", port=50063, threaded=True)


# 自定义小组件
WIDGET_CODE = 'widget_test.ui'
WIDGET_NAME = 'LyricsIsland'
WIDGET_WIDTH = 300

# 启动线程以运行 Flask 服务
def start_flask_thread():
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()


class Plugin(PluginBase):  # 插件类
    def __init__(self, cw_contexts, method):  # 初始化
        super().__init__(cw_contexts, method)  # 调用父类初始化方法

        self.method.register_widget(WIDGET_CODE, WIDGET_NAME, WIDGET_WIDTH)  # 注册小组件到CW
        self.cfg = PluginConfig(self.PATH, 'config.json')  # 实例化配置类



    def execute(self):  # 自启动执行部分
        # 小组件自定义（照PyQt的方法正常写）
        self.lyrics_widget = self.method.get_widget(WIDGET_CODE)  # 获取小组件对象

        if self.lyrics_widget:  # 判断小组件是否存在
            contentLayout = self.lyrics_widget.findChild(QHBoxLayout, 'contentLayout')  # 标题布局
            contentLayout.setSpacing(1)  # 设置间距
        start_flask_thread()
        # 初始化（好像是？）
        self.method.change_widget_content(WIDGET_CODE, 'LyricsIsland', '等待音乐软件侧传输歌词...')


        logger.success('Plugin1 executed!')
        logger.info(f'Config path: {self.PATH}')

    def update(self, cw_contexts, widget_title="LyricsIsland"):  # 自动更新部分
        super().update(cw_contexts)  # 调用父类更新方法
        self.cfg.update_config()  # 更新配置

        if hasattr(self, 'lyrics_widget'):  # 判断小组件是否存在
            self.method.change_widget_content(WIDGET_CODE, widget_title, current_lyric)

        if self.method.is_get_notification():
            logger.warning('warning', f'Plugin1 got notification! Title: {self.cw_contexts["Notification"]["title"]}')

            if self.cw_contexts['Notification']['state'] == 0:  # 如果下课
                self.method.subprocess_exec(self.cfg['name'], self.cfg['action'])  # 调用CW方法构建自动化
        self.method.adjust_widget_width(WIDGET_CODE, self.widget.width())


# 设置页
class Settings(SettingsBase):
    def __init__(self, plugin_path, parent=None):
        super().__init__(plugin_path, parent)
        uic.loadUi(f'{self.PATH}/settings.ui', self)  # 加载设置界面

        default_config = {
            "name": "打开记事本",
            "action": "notepad"
        }

        self.cfg = PluginConfig(self.PATH, 'config.json')  # 实例化配置类
        self.cfg.load_config(default_config)  # 加载配置

        # 名称和动作输入框
        self.nameEdit = self.findChild(LineEdit, 'nameEdit')
        self.nameEdit.setText(self.cfg['name'])
        self.actionEdit = self.findChild(LineEdit, 'actionEdit')
        self.actionEdit.setText(self.cfg['action'])

        self.nameEdit.textChanged.connect(lambda: self.cfg.upload_config('name', self.nameEdit.text()))
        self.actionEdit.textChanged.connect(lambda: self.cfg.upload_config('action', self.actionEdit.text()))


