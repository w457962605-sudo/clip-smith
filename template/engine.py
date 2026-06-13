"""
模板引擎 — 模板加载/解析/应用 + 注册表
"""

import json
import os
import copy
from pathlib import Path
from typing import Optional


# 模板目录
TEMPLATE_DIR = Path(__file__).parent / "presets"


class TemplateEngine:
    """
    模板引擎

    模板 = JSON 配置文件，定义了：
        - 全局参数 (分辨率/帧率/码率)
        - 时间线 (每段素材的时长、动画、转场)
        - 叠加层 (水印/文字/BGM等)
        - 音频设置
    """

    def __init__(self, template_dir: Optional[str] = None):
        self.template_dir = Path(template_dir) if template_dir else TEMPLATE_DIR
        self._cache = {}

    def list_templates(self, detailed: bool = False) -> list[dict]:
        """列出所有可用模板"""
        templates = []
        if not self.template_dir.exists():
            return templates

        for f in sorted(self.template_dir.glob("*.json")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                tpl = {
                    "name": data.get("template_name", f.stem),
                    "file": f.name,
                    "description": data.get("description", ""),
                    "version": data.get("version", "1.0"),
                    "author": data.get("author", ""),
                    "category": data.get("category", "通用"),
                }
                if detailed:
                    tpl["params"] = data.get("defaults", {})
                    tpl["timeline_count"] = len(data.get("timeline", []))
                    tpl["has_bgm"] = "audio" in data
                    tpl["has_text"] = any(
                        o.get("type") == "text"
                        for o in data.get("overlays", [])
                    )
                templates.append(tpl)
            except Exception:
                templates.append({
                    "name": f.stem,
                    "file": f.name,
                    "description": "(加载失败)",
                    "error": True,
                })

        return templates

    def load_template(self, name_or_path: str) -> dict:
        """加载模板 JSON"""
        # 先查缓存
        if name_or_path in self._cache:
            return copy.deepcopy(self._cache[name_or_path])

        # 尝试作为文件路径
        path = Path(name_or_path)
        if not path.exists():
            # 在模板目录中查找
            path = self.template_dir / f"{name_or_path}.json"
            if not path.exists():
                # 按文件名查找
                path = self.template_dir / name_or_path

        if not path.exists():
            raise FileNotFoundError(f"模板不存在: {name_or_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 缓存
        self._cache[name_or_path] = copy.deepcopy(data)

        # 合并默认值
        data.setdefault("defaults", {})
        data.setdefault("timeline", [])
        data.setdefault("overlays", [])
        data.setdefault("audio", {})

        return data

    def apply_template(
        self,
        template: dict,
        clip_paths: list[str],
        variables: Optional[dict] = None,
    ) -> dict:
        """
        将模板应用到一组素材上

        参数:
            template: 模板字典
            clip_paths: 素材文件路径列表
            variables: 模板变量替换 (如 {"title": "产品名称", "brand": "品牌名"})

        返回: 解析后的配置字典，包含了所有渲染参数
        """
        variables = variables or {}
        tpl = copy.deepcopy(template)

        defaults = tpl.get("defaults", {})
        timeline = tpl.get("timeline", [])
        overlays = tpl.get("overlays", [])
        audio_conf = tpl.get("audio", {})

        # ====== 1. 解析时间线 ======
        resolved_timeline = []

        # 如果没有手动时间线，自动给每个 clip 分配一个
        if not timeline:
            for i in range(len(clip_paths)):
                resolved_timeline.append({
                    "clip_index": i,
                    "duration": defaults.get("clip_duration", 3),
                    "transition": defaults.get("transition", "fade"),
                    "transition_duration": defaults.get("transition_duration", 0.3),
                })
        else:
            # 手动时间线，自动映射 clip_index
            for i, entry in enumerate(timeline):
                resolved = dict(entry)
                if "clip_index" not in resolved:
                    resolved["clip_index"] = i if i < len(clip_paths) else None
                # 补充默认转场
                if "transition" not in resolved:
                    resolved["transition"] = defaults.get("transition", "fade")
                if "transition_duration" not in resolved:
                    resolved["transition_duration"] = defaults.get("transition_duration", 0.3)
                if "duration" not in resolved:
                    resolved["duration"] = defaults.get("clip_duration", 3)
                resolved_timeline.append(resolved)

        # 过滤掉没有对应素材的条目
        resolved_timeline = [
            e for e in resolved_timeline
            if e["clip_index"] is not None and e["clip_index"] < len(clip_paths)
        ]

        # ====== 2. 解析叠加层 ======
        resolved_overlays = []
        for overlay in overlays:
            ov = copy.deepcopy(overlay)
            # 替换变量
            for key, value in ov.items():
                if isinstance(value, str):
                    for var_name, var_val in variables.items():
                        ov[key] = ov[key].replace(f"{{{var_name}}}", str(var_val))
            resolved_overlays.append(ov)

        # ====== 3. 解析音频 ======
        resolved_audio = dict(audio_conf)
        if "bgm" in resolved_audio and isinstance(resolved_audio["bgm"], str):
            bgm_val = resolved_audio["bgm"]
            for var_name, var_val in variables.items():
                if isinstance(bgm_val, str):
                    bgm_val = bgm_val.replace(f"{{{var_name}}}", str(var_val))
            resolved_audio["bgm"] = bgm_val

        # ====== 4. 组装最终配置 ======
        config = {
            "template_name": tpl.get("template_name", "untitled"),
            "clips": [clip_paths[i] for i in range(len(clip_paths))],
            "timeline": resolved_timeline,
            "overlays": resolved_overlays,
            "audio": resolved_audio,
            "output": {
                "width": defaults.get("width", 1080),
                "height": defaults.get("height", 1920),
                "fps": defaults.get("fps", 30),
                "bitrate": defaults.get("bitrate", "4M"),
                "transition": defaults.get("transition", "fade"),
                "transition_duration": defaults.get("transition_duration", 0.3),
            },
            "variables": variables,
        }

        return config
