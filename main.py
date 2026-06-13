#!/usr/bin/env python3
"""
ClipSmith Kivy 安卓界面 — JY 视频剪辑工具
"""

import sys
import os
import json
from pathlib import Path

# 确保能加载核心模块
sys.path.insert(0, str(Path(__file__).parent))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform
from threading import Thread

from core.stitch import stitch
from core.transition import get_transition_list
from core.subtitle import add_text_overlay
from core.filter import list_builtin_filters, apply_builtin_filter
from core.audio import add_bgm
from template.engine import TemplateEngine

# 安卓上设置方向
if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])


class ClipSelector(BoxLayout):
    """视频选择界面组件"""
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.selected_files = []
        self._build_ui()

    def _build_ui(self):
        self.add_widget(Label(text='选择视频片段', size_hint_y=0.1))
        
        # 文件列表
        self.file_list = FileChooserListView(
            path='/storage/emulated/0/DCIM/Camera' if platform == 'android' else str(Path.home()),
            filters=['*.mp4', '*.mov', '*.avi', '*.3gp', '*.mkv'],
            size_hint_y=0.6
        )
        self.file_list.bind(selection=self._on_select)
        self.add_widget(self.file_list)
        
        # 已选文件区域
        self.selected_label = Label(
            text='已选: 0 个文件',
            size_hint_y=0.1,
            color=(0, 1, 0, 1)
        )
        self.add_widget(self.selected_label)
        
        # 按钮
        btn_layout = BoxLayout(size_hint_y=0.2)
        add_btn = Button(text='添加选中')
        add_btn.bind(on_press=self._add_selected)
        btn_layout.add_widget(add_btn)
        
        clear_btn = Button(text='清空')
        clear_btn.bind(on_press=self._clear_all)
        btn_layout.add_widget(clear_btn)
        
        self.add_widget(btn_layout)

    def _on_select(self, instance, selection):
        pass  # 只触发不处理

    def _add_selected(self, btn):
        for f in self.file_list.selection:
            if f not in self.selected_files:
                self.selected_files.append(f)
        self.selected_label.text = f'已选: {len(self.selected_files)} 个文件'

    def _clear_all(self, btn):
        self.selected_files.clear()
        self.selected_label.text = '已选: 0 个文件'

    def get_files(self):
        return list(self.selected_files)


class ExportDialog(BoxLayout):
    """导出参数设置"""
    def __init__(self, callback, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)
        self.callback = callback
        
        # 转场选择
        self.add_widget(Label(text='选择转场'))
        transitions = ['fade', 'slide', 'fadeblack', 'fadewhite', 'dissolve',
                       'pixelize', 'glitch', 'zoomin', 'smoothleft', 'smoothright',
                       'circleopen', 'circleclose', 'clock', 'radial', 'wipetl']
        self.transition_spinner = Spinner(text='fade', values=transitions, size_hint_y=0.15)
        self.add_widget(self.transition_spinner)
        
        # 输出文件名
        self.add_widget(Label(text='输出文件名'))
        self.filename_input = TextInput(text='output.mp4', size_hint_y=0.1, multiline=False)
        self.add_widget(self.filename_input)
        
        # 按钮
        btn_layout = BoxLayout(size_hint_y=0.2)
        export_btn = Button(text='开始导出')
        export_btn.bind(on_press=self._on_export)
        btn_layout.add_widget(export_btn)
        
        cancel_btn = Button(text='取消')
        cancel_btn.bind(on_press=self._on_cancel)
        btn_layout.add_widget(cancel_btn)
        
        self.add_widget(btn_layout)

    def _on_export(self, btn):
        self.callback(self.transition_spinner.text, self.filename_input.text)
        self.parent_window.dismiss()

    def _on_cancel(self, btn):
        self.parent_window.dismiss()


class ProgressPopup(BoxLayout):
    """进度显示"""
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=20, spacing=10, **kwargs)
        self.add_widget(Label(text='正在导出...'))
        self.progress = ProgressBar(max=100, size_hint_y=0.3)
        self.add_widget(self.progress)
        self.status_label = Label(text='准备中...', size_hint_y=0.2)
        self.add_widget(self.status_label)

    def update(self, value, text=''):
        self.progress.value = value
        if text:
            self.status_label.text = text


class TemplateSelector(BoxLayout):
    """模板选择界面"""
    def __init__(self, engine, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.engine = engine
        self._build_ui()

    def _build_ui(self):
        self.add_widget(Label(text='选择预设模板', size_hint_y=0.1))
        
        templates = self.engine.list_templates()
        names = [t['name'] for t in templates]
        names.insert(0, '（自定义拼接）')
        
        self.template_spinner = Spinner(text='（自定义拼接）', values=names, size_hint_y=0.15)
        self.add_widget(self.template_spinner)
        
        # 模板说明
        self.desc_label = Label(
            text='选择模板后点击应用',
            size_hint_y=0.6,
            halign='center',
            valign='middle'
        )
        self.add_widget(self.desc_label)
        
        # 绑定事件
        self.template_spinner.bind(text=self._on_template_change)
        
    def _on_template_change(self, spinner, text):
        if text == '（自定义拼接）':
            self.desc_label.text = '不使用模板，自定义拼接参数'
        else:
            info = self.engine.get_template_info(text)
            if info:
                self.desc_label.text = info.get('description', text)

    def get_selected_template(self):
        text = self.template_spinner.text
        return None if text == '（自定义拼接）' else text


class JYApp(App):
    """JY 视频剪辑工具主界面"""
    
    def build(self):
        Window.size = (400, 700)  # 手机竖屏比例
        
        self.template_engine = TemplateEngine()
        
        # 主布局
        self.root = BoxLayout(orientation='vertical', padding=10, spacing=5)
        
        # 标题
        title = Label(
            text='JY 剪辑',
            size_hint_y=0.08,
            font_size='24sp',
            bold=True,
            color=(0.9, 0.6, 0, 1)
        )
        self.root.add_widget(title)
        
        # 标签页切换
        tab_layout = BoxLayout(size_hint_y=0.08)
        tab1 = Button(text='选择视频')
        tab1.bind(on_press=lambda x: self._switch_tab('clips'))
        tab_layout.add_widget(tab1)
        
        tab2 = Button(text='模板')
        tab2.bind(on_press=lambda x: self._switch_tab('templates'))
        tab_layout.add_widget(tab2)
        
        tab3 = Button(text='滤镜')
        tab3.bind(on_press=lambda x: self._switch_tab('filters'))
        tab_layout.add_widget(tab3)
        
        self.root.add_widget(tab_layout)
        
        # 内容区域
        self.content_area = BoxLayout(orientation='vertical')
        self.root.add_widget(self.content_area)
        
        # 默认显示视频选择
        self._switch_tab('clips')
        
        # 底部导出按钮
        export_btn = Button(
            text='开始导出',
            size_hint_y=0.1,
            background_color=(0, 0.7, 0.3, 1),
            font_size='18sp'
        )
        export_btn.bind(on_press=self._start_export)
        self.root.add_widget(export_btn)
        
        return self.root
    
    def _switch_tab(self, tab_name):
        self.content_area.clear_widgets()
        
        if tab_name == 'clips':
            self.clip_selector = ClipSelector()
            self.content_area.add_widget(self.clip_selector)
            
        elif tab_name == 'templates':
            self.template_selector = TemplateSelector(self.template_engine)
            self.content_area.add_widget(self.template_selector)
            
        elif tab_name == 'filters':
            filters = list_builtin_filters()
            layout = GridLayout(cols=2, spacing=5, size_hint_y=None)
            layout.bind(minimum_height=layout.setter('height'))
            
            self.selected_filter = None
            for f in filters:
                btn = Button(text=f['name'], size_hint_y=None, height=50)
                btn.bind(on_press=lambda x, n=f['name']: self._select_filter(n))
                layout.add_widget(btn)
            
            scroll = ScrollView()
            scroll.add_widget(layout)
            self.content_area.add_widget(scroll)

    def _select_filter(self, name):
        self.selected_filter = name
        # 简单的反馈

    def _start_export(self, btn):
        """弹出导出设置"""
        if not hasattr(self, 'clip_selector') or len(self.clip_selector.get_files()) < 2:
            popup = Popup(title='提示', content=Label(text='请至少选择2个视频片段'), size_hint=(0.6, 0.4))
            popup.open()
            return
        
        content = ExportDialog(self._do_export)
        popup = Popup(title='导出设置', content=content, size_hint=(0.8, 0.6))
        content.parent_window = popup
        popup.open()
    
    def _do_export(self, transition, filename):
        """后台执行导出"""
        # 进度弹窗
        self.progress_popup = ProgressPopup()
        popup = Popup(
            title='导出进度',
            content=self.progress_popup,
            size_hint=(0.8, 0.5),
            auto_dismiss=False
        )
        popup.open()
        
        # 启动后台线程
        files = self.clip_selector.get_files()
        Thread(
            target=self._export_thread,
            args=(files, transition, filename, popup),
            daemon=True
        ).start()
    
    def _export_thread(self, files, transition, filename, popup):
        try:
            Clock.schedule_once(lambda dt: self.progress_popup.update(10, '正在拼接...'))
            
            output_path = os.path.join(
                '/storage/emulated/0/DCIM' if platform == 'android' else os.path.expanduser('~'),
                filename
            )
            
            # 执行拼接
            result = stitch(
                files,
                output_path,
                transition=transition,
                transition_duration=0.5
            )
            
            Clock.schedule_once(lambda dt: self.progress_popup.update(100, '导出完成！'))
            
            import time
            time.sleep(1)
            
            Clock.schedule_once(lambda dt: popup.dismiss())
            Clock.schedule_once(lambda dt: self._show_success(output_path))
            
        except Exception as e:
            Clock.schedule_once(lambda dt: self._show_error(str(e)))
            Clock.schedule_once(lambda dt: popup.dismiss())
    
    def _show_success(self, path):
        popup = Popup(
            title='成功',
            content=Label(text=f'导出完成！\n{path}'),
            size_hint=(0.7, 0.4)
        )
        popup.open()
    
    def _show_error(self, msg):
        popup = Popup(
            title='导出失败',
            content=Label(text=msg, color=(1, 0, 0, 1)),
            size_hint=(0.7, 0.4)
        )
        popup.open()


if __name__ == '__main__':
    JYApp().run()
