"""
蒙版引擎 — 圆形/矩形/线性/自定义 PNG 蒙版
"""

import tempfile
import os
from typing import Optional


class MaskEngine:
    """
    蒙版引擎

    支持:
        - 圆形蒙版 (circle)
        - 矩形蒙版 (rectangle)
        - 线性蒙版 (linear) — 渐变过渡
        - 自定义 PNG 蒙版 (custom)
        - 文字蒙版 (text)
    """

    @staticmethod
    def build_circle_mask(
        width: int, height: int,
        cx: Optional[int] = None, cy: Optional[int] = None,
        radius: Optional[int] = None,
        feather: int = 20,
    ) -> str:
        """
        生成圆形蒙版的 FFmpeg 滤镜

        返回: FFmpeg filter string
        """
        cx = cx or width // 2
        cy = cy or height // 2
        radius = radius or min(width, height) // 3

        # 用 geq 滤镜生成圆形的 alpha 通道
        # 使用欧几里得距离：圆内 alpha=255，圆外 alpha=0，羽化边缘
        return (
            f"geq=a='if(lte(sqrt((X-{cx})^2+(Y-{cy})^2),{radius}),255,"
            f"if(lte(sqrt((X-{cx})^2+(Y-{cy})^2),{radius+feather}),"
            f"255-(sqrt((X-{cx})^2+(Y-{cy})^2)-{radius})*255/{feather},0))'"
        )

    @staticmethod
    def build_rectangle_mask(
        width: int, height: int,
        x: int = 0, y: int = 0,
        w: Optional[int] = None, h: Optional[int] = None,
        feather: int = 10,
    ) -> str:
        """
        生成矩形蒙版的 FFmpeg 滤镜

        返回: FFmpeg filter string
        """
        w = w or width // 2
        h = h or height
        return (
            f"geq=a='if(lte(X,{x+w})*lte(Y,{y+h})*gte(X,{x})*gte(Y,{y}),255,0)'"
        )

    @staticmethod
    def build_linear_mask(
        width: int, height: int,
        direction: str = "left-to-right",
        feather: int = 50,
    ) -> str:
        """
        生成线性渐变蒙版

        参数:
            direction: left-to-right, right-to-left, top-to-bottom, bottom-to-top
            feather: 渐变过渡宽度（像素）

        返回: FFmpeg filter string
        """
        if direction == "left-to-right":
            return (
                f"geq=a='if(lte(X,{width//2-feather//2}),255,"
                f"if(gte(X,{width//2+feather//2}),0,"
                f"(1-(X-{width//2-feather//2})/{feather})*255))'"
            )
        elif direction == "right-to-left":
            return (
                f"geq=a='if(gte(X,{width//2+feather//2}),255,"
                f"if(lte(X,{width//2-feather//2}),0,"
                f"(X-{width//2-feather//2})*255/{feather}))'"
            )
        elif direction == "top-to-bottom":
            return (
                f"geq=a='if(lte(Y,{height//2-feather//2}),255,"
                f"if(gte(Y,{height//2+feather//2}),0,"
                f"(1-(Y-{height//2-feather//2})/{feather})*255))'"
            )
        elif direction == "bottom-to-top":
            return (
                f"geq=a='if(gte(Y,{height//2+feather//2}),255,"
                f"if(lte(Y,{height//2-feather//2}),0,"
                f"(Y-{height//2-feather//2})*255/{feather}))'"
            )
        else:
            raise ValueError(f"不支持的方向: {direction}")

    @staticmethod
    def build_split_screen_mask(
        width: int, height: int,
        sections: int = 2,
        gap: int = 2,
    ) -> list[str]:
        """
        生成分屏蒙版（多个矩形蒙版）

        参数:
            sections: 分几屏
            gap: 屏间间距（像素）

        返回: FFmpeg filter strings 列表
        """
        masks = []
        section_w = width // sections
        for i in range(sections):
            x = i * section_w + (gap // 2 if i > 0 else 0)
            act_w = section_w - gap
            masks.append(
                f"geq=a='if(lte(X,{x+act_w})*gte(X,{x}),255,0)'"
            )
        return masks

    @staticmethod
    def build_custom_mask(mask_image: str) -> str:
        """
        使用外部 PNG 图片作蒙版

        FFmpeg 用法: 用 alphaextract + alphamerge
        返回给调用者的是 overlay 命令的一部分
        """
        # 这个需要调用方配合使用 overlay 滤镜
        return f"custom:{mask_image}"

    @staticmethod
    def apply_mask(
        video_path: str,
        mask_filter: str,
        output_path: str,
    ) -> list[str]:
        """
        对视频应用蒙版并输出

        返回: ffmpeg 命令列表
        """
        if mask_filter.startswith("custom:"):
            mask_img = mask_filter[7:]
            return [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", mask_img,
                "-filter_complex",
                f"[0:v][1:v]alphamerge",
                "-c:v", "libx264", "-preset", "medium",
                "-pix_fmt", "yuva420p",
                output_path,
            ]
        else:
            return [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", f"format=rgba,{mask_filter}",
                "-c:v", "libx264", "-preset", "medium",
                "-pix_fmt", "yuva420p",
                output_path,
            ]
