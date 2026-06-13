# ClipSmith

命令行短视频剪辑工具 — 多段视频拼接 + 模板套用 + 转场/滤镜/BGM/字幕

## 快速开始

```bash
cd ~/clip-smith
chmod +x clip
./clip stitch clip1.mp4 clip2.mp4 clip3.mp4 -o output/result.mp4
```

## 主要命令

| 命令 | 用途 |
|------|------|
| `clip stitch` | 拼接视频（核心功能） |
| `clip template list` | 查看可用模板 |
| `clip template apply` | 套用模板出片 |
| `clip info` | 查看视频信息 |
| `clip text` | 添加文字 |
| `clip bgm` | 添加BGM |
| `clip filter` | 应用滤镜 |
| `clip transitions` | 查看所有转场 |
| `clip batch` | 批量处理 |

## 使用示例

```bash
# 拼接多个视频，默认交叉溶解转场
./clip stitch clip1.mp4 clip2.mp4 clip3.mp4 -o output.mp4

# 拼接+滑动转场
./clip stitch clip1.mp4 clip2.mp4 -t slideleft -d 0.5 -o output.mp4

# 套用模板
./clip template apply product-show clip1.mp4 clip2.mp4 -o output.mp4

# 查看视频信息
./clip info video.mp4

# 添加文字+背景音乐
./clip text video.mp4 "标题" -o output.mp4
./clip bgm video.mp4 -b bgm.mp3 -o output.mp4
```

## 预设模板 (10个)

- product-show — 产品展示快节奏
- talking-head — 口播知识类
- vlog-daily — Vlog日常
- beat-sync — 卡点节奏
- promo-ads — 带货促销
- cinematic-mix — 电影感混剪
- unboxing-review — 开箱评测
- tutorial-steps — 教程步骤
- comparison-review — 对比评测
- carousel-showcase — 轮播展示

## 系统要求

- Python 3.8+
- FFmpeg 4.2+ (sudo apt install ffmpeg)
- 操作系统: Linux/macOS/Windows (WSL)
