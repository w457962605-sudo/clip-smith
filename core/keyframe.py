"""
关键帧引擎 — 插值计算 + FFmpeg 表达式转换
"""

from typing import Any


class KeyframeEngine:
    """
    关键帧动画引擎

    用法:
        kf = KeyframeEngine([
            {"t": 0.0, "x": -500, "y": 100, "scale": 0.5, "opacity": 0},
            {"t": 1.0, "x": 100,  "y": 100, "scale": 1.0, "opacity": 1},
            {"t": 3.0, "x": 200,  "y": 50,  "scale": 0.8, "opacity": 0.8},
        ])
        expr = kf.to_ffmpeg_expr("x")  # 生成 x 位置的表达式
    """

    def __init__(self, keyframes: list[dict]):
        """
        参数:
            keyframes: 关键帧列表，每帧格式:
                {"t": 时间(秒), "x": x位置, "y": y位置,
                 "scale": 缩放, "opacity": 透明度, "rotate": 旋转角度}
                所有属性可选，不传则不参与动画
        """
        if not keyframes:
            raise ValueError("至少需要一个关键帧")

        self.keyframes = sorted(keyframes, key=lambda k: k["t"])
        self.duration = self.keyframes[-1]["t"]

        # 提取所有关键帧中涉及的属性
        self.properties = set()
        for kf in self.keyframes:
            for key in kf:
                if key != "t":
                    self.properties.add(key)

    def get_value_at(self, prop: str, time: float) -> float:
        """在指定时间点插值计算属性值"""
        values = [kf.get(prop) for kf in self.keyframes if prop in kf]
        if not values:
            return 0.0

        times = [kf["t"] for kf in self.keyframes if prop in kf]
        values = [kf[prop] for kf in self.keyframes if prop in kf]

        # 边界
        if time <= times[0]:
            return values[0]
        if time >= times[-1]:
            return values[-1]

        # 找到所在区间并线性插值
        for i in range(len(times) - 1):
            if times[i] <= time <= times[i + 1]:
                t_ratio = (time - times[i]) / (times[i + 1] - times[i])
                return values[i] + (values[i + 1] - values[i]) * t_ratio

        return values[-1]

    def to_ffmpeg_expr(self, prop: str, variable: str = "t") -> str:
        """
        将关键帧动画转为 FFmpeg 表达式字符串

        FFmpeg 不支持直接写时间点和值的映射，
        我们用 if/between 构造分段函数

        参数:
            prop: 属性名（x, y, scale, opacity, rotate）
            variable: 时间变量名（默认 t）

        返回: FFmpeg 滤镜可用的表达式字符串
        """
        frames = [(kf["t"], kf[prop]) for kf in self.keyframes if prop in kf]
        if not frames:
            return "0"

        # 如果只有一个关键帧，返回常数值
        if len(frames) == 1:
            return str(frames[0][1])

        # 构造分段线性插值表达式
        # FFmpeg 表达式格式: 'if(between(t,0,1), A + (t-0)*(B-A)/(1-0), if(...))'
        parts = []

        for i in range(len(frames) - 1):
            t0, v0 = frames[i]
            t1, v1 = frames[i + 1]
            slope = (v1 - v0) / (t1 - t0) if t1 != t0 else 0

            if slope == 0:
                expr = str(v0)
            else:
                expr = f"{v0} + ({variable} - {t0}) * {slope}"

            if i == 0:
                # 第一个区间：如果 t < t0 用 v0
                parts.append(f"if(lt({variable},{t0}),{v0},if(between({variable},{t0},{t1}),{expr},")
            elif i == len(frames) - 2:
                # 最后一个区间
                parts.append(f"if(between({variable},{t0},{t1}),{expr},{v1})")
                # 补上闭合括号
                parts.append(")" * (len(frames) - 2))
            else:
                parts.append(f"if(between({variable},{t0},{t1}),{expr},")

        return "".join(parts)

    def to_dict(self) -> dict:
        """导出为字典（用于保存到模板）"""
        return {
            "duration": self.duration,
            "properties": list(self.properties),
            "keyframes": self.keyframes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KeyframeEngine":
        """从字典加载"""
        return cls(data["keyframes"])
