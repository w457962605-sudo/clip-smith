"""
FFmpeg 工具模块 — 命令构造器 + 视频信息探测
"""

import json
import subprocess
import re
from pathlib import Path
from typing import Optional


def probe(path: str) -> dict:
    """获取视频文件的完整信息"""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return json.loads(result.stdout)


def get_video_info(path: str) -> dict:
    """提取视频的关键信息（分辨率、时长、帧率、编码等）"""
    info = probe(path)
    stream = None
    for s in info.get("streams", []):
        if s["codec_type"] == "video":
            stream = s
            break
    if not stream:
        raise ValueError(f"未找到视频流: {path}")

    # 计算帧率
    avg_frame_rate = stream.get("avg_frame_rate", "0/0")
    parts = avg_frame_rate.split("/")
    fps = round(float(parts[0]) / float(parts[1]), 2) if parts[1] != "0" else 0.0

    # 时长（秒）
    duration = float(stream.get("duration", info.get("format", {}).get("duration", 0)))

    return {
        "width": stream.get("width", 0),
        "height": stream.get("height", 0),
        "fps": fps,
        "duration": duration,
        "codec": stream.get("codec_name", "h264"),
        "pix_fmt": stream.get("pix_fmt", "yuv420p"),
        "bitrate": int(stream.get("bit_rate", 0)),
        "path": path,
    }


def get_audio_info(path: str) -> Optional[dict]:
    """提取音频流信息"""
    info = probe(path)
    for s in info.get("streams", []):
        if s["codec_type"] == "audio":
            return {
                "codec": s.get("codec_name", "aac"),
                "sample_rate": int(s.get("sample_rate", 0)),
                "channels": s.get("channels", 2),
            }
    return None


def detect_hardware_accel() -> Optional[str]:
    """检查可用的硬件加速器（仅限于这台机器的 Intel 集显）"""
    try:
        r = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=10
        )
        output = r.stdout + r.stderr
        if "h264_qsv" in output:
            return "qsv"   # Intel QuickSync
        if "h264_vaapi" in output:
            return "vaapi"
    except Exception:
        pass
    return None


def build_filter_complex(filters: list[str]) -> str:
    """将滤镜列表拼接成一个 filter_complex 字符串"""
    return ";".join(filters)


def run_ffmpeg(cmd: list[str], timeout: int = 600) -> dict:
    """执行 FFmpeg 命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"FFmpeg 超时 ({timeout}s)"}
    except FileNotFoundError:
        return {"success": False, "error": "FFmpeg 未安装，请先安装 ffmpeg"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def concat_demuxer(clip_paths: list[str], output_path: str) -> list[str]:
    """使用 concat demuxer 拼接同参数视频（不重新编码）"""
    # 生成文件列表
    lines = []
    for p in clip_paths:
        lines.append(f"file '{Path(p).absolute()}'\n")
    list_content = "".join(lines)

    # 写入临时文件
    import tempfile
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    tmp.write(list_content)
    tmp.close()

    return [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", tmp.name,
        "-c", "copy",
        output_path
    ], tmp.name


def build_reencode_cmd(
    input_path: str,
    output_path: str,
    video_filter: Optional[str] = None,
    audio_filter: Optional[str] = None,
    width: int = 1920,
    height: int = 1080,
    fps: float = 30.0,
    bitrate: str = "4M",
    remove_tmp: Optional[str] = None,
) -> list[str]:
    """构建统一的重新编码 FFmpeg 命令"""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-i", input_path]

    # 滤镜
    filters = []
    scale = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    filters.append(scale)
    if video_filter:
        filters.append(video_filter)
    if audio_filter:
        pass  # 音频滤镜另外处理

    if filters:
        cmd += ["-vf", ",".join(filters)]

    # 视频编码
    cmd += [
        "-c:v", "libx264",
        "-preset", "medium",
        "-b:v", bitrate,
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
    ]

    # 音频
    cmd += ["-c:a", "aac", "-b:a", "128k"]

    # 输出
    cmd.append(output_path)

    if remove_tmp:
        Path(remove_tmp).unlink(missing_ok=True)

    return cmd


def build_concat_with_transitions(
    clip_paths: list[str],
    output_path: str,
    transition: str = "fade",
    transition_duration: float = 0.5,
    width: int = 1920,
    height: int = 1080,
    fps: float = 30.0,
) -> list[str]:
    """
    使用 xfade 滤镜拼接多段视频带转场

    返回: [ffmpeg命令, 临时文件列表]
    """
    # 先统一编码所有片段到中间文件
    import tempfile
    import os

    unified = []
    for i, clip in enumerate(clip_paths):
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.close()
        cmd = build_reencode_cmd(
            clip, tmp.name,
            width=width, height=height, fps=fps
        )
        r = run_ffmpeg(cmd)
        if not r["success"]:
            raise RuntimeError(f"统一编码失败: {clip}\n{r.get('stderr','')}")
        unified.append(tmp.name)

    if len(unified) == 1:
        # 只有一个片段，直接复制
        import shutil
        shutil.copy2(unified[0], output_path)
        for f in unified:
            os.unlink(f)
        return []

    # 构建 xfade filter 链
    # xfade 用法: [0][1]xfade=transition=fade:duration=0.5:offset=10
    filter_parts = []
    prev_label = "0"
    total_duration = 0.0

    # 先获取第一个片段的时长
    info = get_video_info(unified[0])
    total_duration = info["duration"]

    for i in range(1, len(unified)):
        info_i = get_video_info(unified[i])
        offset = total_duration - transition_duration
        label = f"v{i}"
        filter_parts.append(
            f"[{prev_label}][{i}]xfade=transition={transition}:duration={transition_duration}:offset={offset}[{label}]"
        )
        prev_label = label
        total_duration += info_i["duration"] - transition_duration

    # 构建完整命令
    inputs = []
    for f in unified:
        inputs += ["-i", f]

    cmd = (
        ["ffmpeg", "-y", "-hide_banner"] + inputs +
        ["-filter_complex", ";".join(filter_parts)] +
        ["-map", f"[{prev_label}]"] +
        ["-c:v", "libx264", "-preset", "medium", "-b:v", "4M"] +
        ["-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p", output_path]
    )

    return cmd + ["__cleanup__"] + unified
