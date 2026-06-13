"""
滤镜/LUT 模块 — LUT加载、内置滤镜效果
"""

from typing import Optional
from pathlib import Path
from utils.ffmpeg import run_ffmpeg


def apply_lut(
    video_path: str,
    lut_path: str,
    output_path: str,
    strength: float = 1.0,
) -> dict:
    """
    应用 LUT 调色文件（.cube 格式）

    参数:
        video_path: 输入视频
        lut_path: .cube 文件路径
        output_path: 输出路径
        strength: 滤镜强度（0~1）

    网上可免费下载大量 LUT 文件：
        - 胶片风 (Kodak Portra, Fuji Pro 400H)
        - 电影感 (Teal-Orange, Cinematic)
        - 日系清新
        - 黑白胶片
    """
    if not Path(lut_path).exists():
        return {"success": False, "error": f"LUT 文件不存在: {lut_path}"}

    if strength < 1.0:
        # 强度混合: 原画面 + LUT画面 按比例混合
        filter_str = (
            f"split[original][luted];"
            f"[luted]lut3d=file={lut_path}[luted];"
            f"[original][luted]blend=all_mode=addition:all_opacity={strength}"
        )
    else:
        filter_str = f"lut3d=file={lut_path}"

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", filter_str,
        "-c:a", "copy",
        output_path,
    ]

    r = run_ffmpeg(cmd)
    if not r["success"]:
        return {"success": False, "error": r.get("stderr", "应用LUT失败")[:1000]}

    return {"success": True, "output": output_path}


# ============================================================
# 内置滤镜预设（不依赖外部 LUT 文件）
# ============================================================

BUILTIN_FILTERS = {
    "vintage": {
        "name": "复古胶片",
        "description": "温暖的复古色调，带轻微颗粒感",
        "filter": "curves=vintage,noise=alls=5:allf=t",
    },
    "blackwhite": {
        "name": "黑白",
        "description": "经典黑白效果",
        "filter": "hue=s=0,curves=blackwhite,contrast=1.2",
    },
    "warm": {
        "name": "暖色调",
        "description": "温暖的橙色/金色调",
        "filter": "colorbalance=rs=0.2:gs=-0.1:bs=-0.15",
    },
    "cool": {
        "name": "冷色调",
        "description": "清冷的蓝调",
        "filter": "colorbalance=rs=-0.15:gs=0:bs=0.2",
    },
    "dramatic": {
        "name": "电影感",
        "description": "高对比度，暗部偏青，亮部偏橙",
        "filter": "curves=dramatic,contrast=1.3,saturation=1.1",
    },
    "soft": {
        "name": "柔光",
        "description": "柔和朦胧效果",
        "filter": "curves=medium_contrast,hue=s=0.8,gblur=sigma=0.5",
    },
    "vivid": {
        "name": "鲜艳",
        "description": "高饱和度，鲜艳明亮",
        "filter": "eq=saturation=1.5:contrast=1.1:brightness=0.05",
    },
    "sepia": {
        "name": "深褐色",
        "description": "老照片棕色调",
        "filter": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
    },
    "neon": {
        "name": "霓虹",
        "description": "赛博朋克风格，蓝紫调+高对比",
        "filter": "colorbalance=rs=-0.2:gs=0:bs=0.3,hue=s=1.3,contrast=1.2",
    },
    "dreamy": {
        "name": "梦幻",
        "description": "低对比度，轻微发光效果",
        "filter": "gblur=sigma=0.3,eq=brightness=0.05:saturation=0.8:contrast=0.9",
    },
}


def list_builtin_filters() -> dict:
    """列出所有内置滤镜"""
    return BUILTIN_FILTERS


def apply_builtin_filter(
    video_path: str,
    filter_name: str,
    output_path: str,
) -> dict:
    """
    应用内置滤镜

    参数:
        video_path: 输入视频
        filter_name: 滤镜名称（vintage, blackwhite, warm, cool, dramatic, soft, vivid, sepia, neon, dreamy）
        output_path: 输出路径
    """
    if filter_name not in BUILTIN_FILTERS:
        return {"success": False, "error": f"未知滤镜: {filter_name}，可用滤镜: {', '.join(BUILTIN_FILTERS.keys())}"}

    filter_str = BUILTIN_FILTERS[filter_name]["filter"]

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", filter_str,
        "-c:a", "copy",
        output_path,
    ]

    r = run_ffmpeg(cmd)
    if not r["success"]:
        return {"success": False, "error": r.get("stderr", f"应用滤镜 {filter_name} 失败")[:1000]}

    return {"success": True, "output": output_path, "filter": filter_name}
