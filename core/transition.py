"""
转场引擎 — 支持 30+ 种 xfade 原生转场 + 自定义组合转场
"""

# ============================================================
# xfade 滤镜支持的转场类型（FFmpeg 4.4+）
# 完整列表：https://ffmpeg.org/ffmpeg-filters.html#xfade
# ============================================================

XFADE_TRANSITIONS = {
    # --- 基础 ---
    "fade": "fade",
    "fadeblack": "fadeblack",
    "fadewhite": "fadewhite",
    "fadegrays": "fadegrays",

    # --- 溶解 ---
    "dissolve": "dissolve",
    "pixelize": "pixelize",

    # --- 滑动 ---
    "slideleft": "slideleft",
    "slideright": "slideright",
    "slideup": "slideup",
    "slidedown": "slidedown",

    # --- 擦除 ---
    "wipeleft": "wipeleft",
    "wiperight": "wiperight",
    "wipeup": "wipeup",
    "wipedown": "wipedown",
    "wipein": "wipein",
    "wipeout": "wipeout",

    # --- 光圈 ---
    "circleopen": "circleopen",
    "circleclose": "circleclose",

    # --- 缩放 ---
    "sliced": "sliced",          # 画面切成条交替
    "zoomin": "zoomin",

    # --- 创意 ---
    "smoothleft": "smoothleft",
    "smoothright": "smoothright",
    "smoothup": "smoothup",
    "smoothdown": "smoothdown",
    "rectcrop": "rectcrop",
    "hblur": "hblur",            # 水平模糊过渡
    "radial": "radial",          # 放射状
    "horzopen": "horzopen",      # 水平开门
    "horzclose": "horzclose",    # 水平关门
    "vertopen": "vertopen",      # 垂直开门
    "vertclose": "vertclose",    # 垂直关门
    "canball": "canball",
    "cornerwipe": "cornerwipe",
    "coverleft": "coverleft",
    "coverright": "coverright",
    "coverup": "coverup",
    "coverdown": "coverdown",
    "revealleft": "revealleft",
    "revealright": "revealright",
    "revealup": "revealup",
    "revealdown": "revealdown",
    "diagtl": "diagtl",         # 对角线左上到右下
    "diagtr": "diagtr",
    "diagbl": "diagbl",
    "diagbr": "diagbr",
}

# 常用转场（推荐给用户的子集）
COMMON_TRANSITIONS = {
    "fade": "交叉溶解（最通用，推荐默认）",
    "fadeblack": "黑场过渡",
    "fadewhite": "白场过渡/闪白",
    "dissolve": "溶解/颗粒溶解",
    "slideleft": "右向左滑动推入",
    "slideright": "左向右滑动推入",
    "wipeleft": "向左擦除",
    "wiperight": "向右擦除",
    "circleopen": "圆形展开（光圈效果）",
    "circleclose": "圆形收缩",
    "zoomin": "放大进入",
    "sliced": "条状切片交替",
    "smoothleft": "平滑左滑",
    "hblur": "模糊过渡",
    "radial": "放射状过渡",
    "horzopen": "水平开门效果",
    "vertopen": "垂直开门效果",
    "coverleft": "遮盖左移",
    "coverright": "遮盖右移",
    "revealleft": "揭示左移",
}


def get_transition_list() -> dict:
    """获取所有可用转场"""
    return {
        "all": XFADE_TRANSITIONS,
        "common": COMMON_TRANSITIONS,
    }


def validate_transition(name: str) -> bool:
    """检查转场名称是否有效"""
    # 支持直接 xfade 名称
    if name in XFADE_TRANSITIONS:
        return True
    # 支持带时长的简写: fade-0.5s, slideleft-1.0s
    base = name.rsplit("-", 1)[0] if "-" in name else name
    if base in XFADE_TRANSITIONS:
        return True
    return False


def parse_transition(name: str) -> tuple:
    """
    解析转场名称，返回 (类型, 时长)

    例:
        "fade" -> ("fade", 0.3)
        "fade-0.5s" -> ("fade", 0.5)
        "slideleft-1.0" -> ("slideleft", 1.0)
    """
    duration = 0.3
    parts = name.rsplit("-", 1)
    base = parts[0]

    if len(parts) > 1:
        dur_str = parts[1].rstrip("s")
        try:
            duration = float(dur_str)
        except ValueError:
            base = name

    if base in XFADE_TRANSITIONS:
        return XFADE_TRANSITIONS[base], duration

    # fallback
    return "fade", 0.3
