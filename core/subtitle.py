"""
字幕/文字模块 — SRT字幕烧录、文字叠加、动态文字动画
"""

import os
import tempfile
from typing import Optional
from pathlib import Path
from utils.ffmpeg import run_ffmpeg


def burn_subtitle(
    video_path: str,
    subtitle_path: str,
    output_path: str,
) -> dict:
    """
    将 SRT/ASS 字幕烧录到视频中（硬字幕）

    参数:
        video_path: 输入视频
        subtitle_path: .srt 或 .ass 字幕文件路径
        output_path: 输出路径
    """
    if not Path(subtitle_path).exists():
        return {"success": False, "error": f"字幕文件不存在: {subtitle_path}"}

    ext = Path(subtitle_path).suffix.lower()

    if ext == ".ass":
        subtitle_filter = f"ass={subtitle_path}"
    else:
        # SRT 需要转义路径中的特殊字符
        safe_path = subtitle_path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        subtitle_filter = f"subtitles={safe_path}"

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", subtitle_filter,
        "-c:a", "copy",
        output_path,
    ]
    r = run_ffmpeg(cmd)

    if not r["success"]:
        return {"success": False, "error": r.get("stderr", "烧录字幕失败")[:1000]}

    return {"success": True, "output": output_path}


def create_srt_from_segments(
    segments: list[dict],
    output_path: str,
) -> str:
    """
    从分段列表生成 SRT 字幕文件

    参数:
        segments: [
            {"start": 0.0, "end": 3.0, "text": "第一句话"},
            {"start": 3.0, "end": 6.0, "text": "第二句话"},
        ]
        output_path: .srt 文件输出路径

    返回: 输出路径
    """
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_srt_time(seg["start"])
        end = _format_srt_time(seg["end"])
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")

    content = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path


def _format_srt_time(seconds: float) -> str:
    """将秒数转为 SRT 时间格式: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def add_text_overlay(
    video_path: str,
    text: str,
    output_path: str,
    position: str = "bottom-center",
    font_size: int = 36,
    font_color: str = "white",
    bg_color: Optional[str] = "black@0.5",
    start_time: float = 0.0,
    duration: Optional[float] = None,
    animation: Optional[str] = None,
) -> dict:
    """
    在视频上叠加文字

    参数:
        video_path: 输入视频
        text: 文字内容
        output_path: 输出路径
        position: 位置 (top-left, top-center, top-right, center, bottom-left, bottom-center, bottom-right)
        font_size: 字号
        font_color: 颜色 (white, yellow, red 等)
        bg_color: 背景色 (None=无背景，格式如 "black@0.5" 表示半透黑)
        start_time: 文字出现时间
        duration: 文字持续时间（None=直到视频结束）
        animation: 动画效果 (fade-in, fade-in-up, slide-up, typewriter, None=静态)
    """
    if not Path(video_path).exists():
        return {"success": False, "error": f"视频不存在: {video_path}"}

    # 计算位置
    positions = {
        "top-left": "x=20:y=20",
        "top-center": "x=(w-text_w)/2:y=20",
        "top-right": "x=w-tw-20:y=20",
        "center": "x=(w-text_w)/2:y=(h-text_h)/2",
        "bottom-left": "x=20:y=h-th-20",
        "bottom-center": "x=(w-text_w)/2:y=h-th-40",
        "bottom-right": "x=w-tw-20:y=h-th-20",
    }
    pos_str = positions.get(position, positions["bottom-center"])

    # 文字样式
    drawtext_params = [
        f"text='{text}'",
        f"fontsize={font_size}",
        f"fontcolor={font_color}",
        f"x={pos_str.split(':')[0].split('=')[1]}",
        f"y={pos_str.split(':')[1].split('=')[1]}",
        "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    # 背景
    if bg_color:
        drawtext_params.append(f"box=1:boxcolor={bg_color}:boxborderw=10")

    # 动画（使用关键帧表达式）
    if animation == "fade-in":
        # 0.5秒淡入
        enable = f"between(t,{start_time},{start_time + duration})" if duration else f"gte(t,{start_time})"
        drawtext_params.append(f"enable='{enable}'")
        drawtext_params.append(f"alpha='if(between(t,{start_time},{start_time+0.5}),(t-{start_time})*2,1)'")
    elif animation == "fade-in-up":
        enable = f"between(t,{start_time},{start_time + duration})" if duration else f"gte(t,{start_time})"
        drawtext_params.append(f"enable='{enable}'")
        drawtext_params.append(f"y='{pos_str.split(':')[1].split('=')[1]}+if(between(t,{start_time},{start_time+0.5}),(1-(t-{start_time})*2)*30,0)'")
        drawtext_params.append(f"alpha='if(between(t,{start_time},{start_time+0.5}),(t-{start_time})*2,1)'")
    elif animation == "slide-up":
        enable = f"between(t,{start_time},{start_time + duration})" if duration else f"gte(t,{start_time})"
        drawtext_params.append(f"enable='{enable}'")
        target_y = pos_str.split(':')[1].split('=')[1]
        drawtext_params.append(f"y='{target_y}+if(between(t,{start_time},{start_time+0.3}),(1-(t-{start_time})/0.3)*50,0)'")
    else:
        # 静态文字
        if duration:
            drawtext_params.append(f"enable='between(t,{start_time},{start_time + duration})'")
        elif start_time > 0:
            drawtext_params.append(f"enable='gte(t,{start_time})'")

    drawtext_str = ":".join(drawtext_params)

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"drawtext={drawtext_str}",
        "-c:a", "copy",
        output_path,
    ]

    r = run_ffmpeg(cmd)
    if not r["success"]:
        return {"success": False, "error": r.get("stderr", "添加文字失败")[:1000]}

    return {"success": True, "output": output_path}
