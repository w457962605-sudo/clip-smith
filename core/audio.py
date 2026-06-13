"""
音频模块 — BGM混音、人声优先（Ducking）、淡入淡出、音量统一
"""

import os
import tempfile
from typing import Optional
from pathlib import Path
from utils.ffmpeg import run_ffmpeg, get_video_info


def add_bgm(
    video_path: str,
    bgm_path: Optional[str],
    output_path: str,
    bgm_volume: float = 0.3,
    original_volume: float = 1.0,
    fade_in: float = 0.5,
    fade_out: float = 1.0,
    ducking: bool = False,
    ducking_threshold: float = 0.1,
    ducking_reduction: float = 0.5,
    loop_bgm: bool = True,
) -> dict:
    """
    给视频添加背景音乐

    参数:
        video_path: 视频文件路径
        bgm_path: BGM 文件路径（None = 不加BGM，只做音频调整）
        output_path: 输出路径
        bgm_volume: BGM 音量（0~1）
        original_volume: 原视频音量（0~1）
        fade_in/fade_out: BGM 淡入淡出时长（秒）
        ducking: 是否开启人声优先（自动压低BGM）
        ducking_threshold: 人声检测阈值
        ducking_reduction: 人声出现时BGM降低幅度（0=静音，1=不变）
        loop_bgm: BGM是否循环（如果BGM比视频短）

    返回: {"success": bool, "output": str, "error": str}
    """
    if not Path(video_path).exists():
        return {"success": False, "error": f"视频不存在: {video_path}"}

    video_info = get_video_info(video_path)
    video_duration = video_info["duration"]

    # 构建滤镜
    filters = []

    if bgm_path and Path(bgm_path).exists():
        bgm_info = get_video_info(bgm_path) if bgm_path else None
        bgm_duration = bgm_info["duration"] if bgm_info else 0

        # BGM 滤镜链
        bgm_filters = []

        if loop_bgm and bgm_duration > 0 and bgm_duration < video_duration:
            # 需要循环
            loop_count = int(video_duration / bgm_duration) + 1
            bgm_filters.append(f"aloop=loop={loop_count}:size={int(bgm_duration * 44100)}")
            # 裁剪到视频长度
            bgm_filters.append(f"atrim=duration={video_duration}")

        if bgm_filters:
            filters.append(f"[1:a]{','.join(bgm_filters)}[bgm]")

        if ducking:
            # 人声优先（声控压低BGM）
            # 使用 sidechaincompress 滤镜
            duck_str = (
                f"[0:a]volume={original_volume}[orig];"
                f"[bgm]volume={bgm_volume}[bgm_vol];"
                f"[orig][bgm_vol]sidechaincompress="
                f"threshold={ducking_threshold}:ratio={1/ducking_reduction if ducking_reduction > 0 else 20}:"
                f"attack=5:release=50[mixed]"
            )
            filters.append(duck_str)
        else:
            # 简单混音
            filters.append(
                f"[0:a]volume={original_volume}[orig];"
                f"[bgm]volume={bgm_volume}[bgm_vol];"
                f"[orig][bgm_vol]amix=inputs=2:duration=first[outa]"
            )
    else:
        # 无BGM，只调整原音频
        filters.append(f"[0:a]volume={original_volume}[outa]")

    # 拼接完整滤镜
    filter_complex = ";".join(filters) if filters else ""
    output_label = "[outa]"

    cmd = ["ffmpeg", "-y", "-i", video_path]

    if bgm_path and Path(bgm_path).exists():
        cmd += ["-i", bgm_path]

    if filter_complex:
        cmd += ["-filter_complex", filter_complex]
        cmd += ["-map", "0:v"]

        # 判断输出标签
        if "[outa]" in filter_complex:
            cmd += ["-map", "[outa]"]
        else:
            # fallback: 用第一个音频流
            cmd += ["-map", "0:a"] if not bgm_path else []
    else:
        cmd += ["-map", "0:v", "-map", "0:a"]

    # 视频编码（复制，不重新编码视频）
    cmd += ["-c:v", "copy", "-c:a", "aac", "-b:a", "128k", output_path]

    r = run_ffmpeg(cmd)
    if not r["success"]:
        return {"success": False, "error": r.get("stderr", "添加BGM失败")[:2000]}

    return {"success": True, "output": output_path}


def normalize_volume(video_path: str, output_path: str, target_level: float = -14.0) -> dict:
    """
    统一音量（响度标准化到指定 LUFS）

    参数:
        video_path: 输入视频
        output_path: 输出路径
        target_level: 目标响度（dB，抖音标准 -14 LUFS）
    """
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-af", f"loudnorm=I={target_level}:LRA=7:TP=-1.5:print_format=json",
        "-c:v", "copy",
        output_path,
    ]
    r = run_ffmpeg(cmd)
    if not r["success"]:
        return {"success": False, "error": r.get("stderr", "音量标准化失败")[:1000]}

    return {"success": True, "output": output_path}


def extract_audio(
    video_path: str,
    output_path: str,
    format: str = "mp3",
) -> dict:
    """
    提取视频中的音频
    """
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn",
        "-acodec", "libmp3lame" if format == "mp3" else "aac",
        output_path,
    ]
    r = run_ffmpeg(cmd)
    if not r["success"]:
        return {"success": False, "error": r.get("stderr", "提取音频失败")[:1000]}
    return {"success": True, "output": output_path}


def remove_silence(video_path: str, output_path: str) -> dict:
    """
    去除视频中的静音片段
    """
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-af", "silenceremove=start_periods=1:start_duration=0.5:start_threshold=-50dB:"
               "detection=peak",
        "-c:v", "copy",
        output_path,
    ]
    r = run_ffmpeg(cmd)
    if not r["success"]:
        # 有些编码格式不能 copy，fallback 到重新编码
        cmd[cmd.index("-c:v") + 1] = "libx264"
        r = run_ffmpeg(cmd)
    return {"success": r["success"], "output": output_path, "error": r.get("stderr", "")[:500]}
