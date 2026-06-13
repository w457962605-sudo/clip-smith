"""
核心拼接引擎 — 多段视频拼接 + 转场 + 统一参数
"""

import os
import tempfile
from pathlib import Path
from typing import Optional
from utils.ffmpeg import (
    get_video_info, get_audio_info, run_ffmpeg,
    build_reencode_cmd, build_concat_with_transitions
)


def get_optimal_params(clip_paths: list[str]) -> dict:
    """分析所有素材，决定最佳输出参数"""
    infos = []
    for p in clip_paths:
        try:
            infos.append(get_video_info(p))
        except Exception as e:
            raise ValueError(f"读取视频信息失败: {p} — {e}")

    # 取最高分辨率
    max_w = max(i["width"] for i in infos)
    max_h = max(i["height"] for i in infos)

    # 取最常见帧率
    from collections import Counter
    fps_counter = Counter(i["fps"] for i in infos)
    common_fps = fps_counter.most_common(1)[0][0]

    # 判断横竖屏（取多数）
    orientations = []
    for i in infos:
        if i["width"] < i["height"]:
            orientations.append("portrait")
        else:
            orientations.append("landscape")
    orientation = Counter(orientations).most_common(1)[0][0]

    # 目标分辨率
    if orientation == "portrait":
        target_w, target_h = 1080, 1920  # 抖音竖屏
    else:
        target_w, target_h = 1920, 1080  # 横屏

    # 如果素材本身不超过 1080p，保持原始尺寸
    if max_w <= 1080 and max_h <= 1920:
        target_w, target_h = max_w, max_h

    # 码率按分辨率估算
    pixels = target_w * target_h
    if pixels >= 1920 * 1080:
        bitrate = "6M"
    elif pixels >= 1280 * 720:
        bitrate = "4M"
    else:
        bitrate = "2M"

    return {
        "width": target_w,
        "height": target_h,
        "fps": common_fps,
        "bitrate": bitrate,
        "orientation": orientation,
        "total_duration": sum(i["duration"] for i in infos),
        "clip_count": len(infos),
        "clip_infos": infos,
    }


def stitch(
    clip_paths: list[str],
    output_path: str,
    transition: str = "fade",
    transition_duration: float = 0.3,
    width: Optional[int] = None,
    height: Optional[int] = None,
    fps: Optional[float] = None,
    bitrate: Optional[str] = None,
    keep_temps: bool = False,
) -> dict:
    """
    拼接多段视频，带转场

    参数:
        clip_paths: 视频文件路径列表
        output_path: 输出路径
        transition: 转场类型（fade, fadeblack, fadewhite, slideleft, slideright 等 xfade 支持的所有类型）
        transition_duration: 转场时长（秒）
        width/height/fps/bitrate: 输出参数，不传则自动检测

    返回:
        {"success": bool, "output": str, "error": str, "info": dict}
    """
    if not clip_paths:
        return {"success": False, "error": "没有提供视频文件"}

    for p in clip_paths:
        if not Path(p).exists():
            return {"success": False, "error": f"文件不存在: {p}"}

    # 分析素材
    params = get_optimal_params(clip_paths)

    # 合并转场时长中的重叠部分
    total_duration = params["total_duration"]
    overlap = transition_duration * (len(clip_paths) - 1)
    final_duration = total_duration - overlap

    # 覆盖用户指定参数
    if width: params["width"] = width
    if height: params["height"] = height
    if fps: params["fps"] = fps
    if bitrate: params["bitrate"] = bitrate

    try:
        result = build_concat_with_transitions(
            clip_paths, output_path,
            transition=transition,
            transition_duration=transition_duration,
            width=params["width"],
            height=params["height"],
            fps=params["fps"],
        )
    except Exception as e:
        return {"success": False, "error": str(e)}

    if not result:
        # 只有一个片段，已经复制完了
        return {
            "success": True,
            "output": output_path,
            "info": {
                "clips": len(clip_paths),
                "duration": final_duration,
                "resolution": f"{params['width']}x{params['height']}",
                "fps": params["fps"],
            }
        }

    cmd = result

    # 分离 FFmpeg 命令和清理列表
    clean_files = []
    if "__cleanup__" in cmd:
        idx = cmd.index("__cleanup__")
        actual_cmd = cmd[:idx]
        clean_files = cmd[idx + 1:]
    else:
        actual_cmd = cmd

    # 执行
    r = run_ffmpeg(actual_cmd)
    if not r["success"]:
        # 清理临时文件
        for tmp in clean_files:
            try: os.unlink(tmp)
            except: pass
        return {"success": False, "error": r.get("stderr", "FFmpeg 失败")[:2000]}

    # 清理临时文件
    for tmp in clean_files:
            try:
                os.unlink(tmp)
            except Exception:
                pass

    return {
        "success": True,
        "output": output_path,
        "info": {
            "clips": len(clip_paths),
            "duration": round(final_duration, 2),
            "resolution": f"{params['width']}x{params['height']}",
            "fps": params["fps"],
            "bitrate": params["bitrate"],
            "orientation": params["orientation"],
        },
        "details": r,
    }


def quick_concat(
    clip_paths: list[str],
    output_path: str,
) -> dict:
    """
    快速拼接（同参数视频，不重新编码）

    适用于所有素材分辨率/编码一致的情况
    """
    from utils.ffmpeg import concat_demuxer
    cmd, list_path = concat_demuxer(clip_paths, output_path)
    r = run_ffmpeg(cmd)
    Path(list_path).unlink(missing_ok=True)

    if not r["success"]:
        return {"success": False, "error": r.get("stderr", "快速拼接失败")[:1000]}

    return {
        "success": True,
        "output": output_path,
        "info": {
            "clips": len(clip_paths),
            "method": "concat_demuxer (no re-encode)",
        },
    }
