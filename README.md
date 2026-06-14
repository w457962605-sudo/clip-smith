# JY — 命令行视频剪辑工具

纯命令行 FFmpeg 封装，专注于**自动化视频剪辑**。

## 特点

- 🎯 **纯 CLI** — 无 GUI，适合服务器/AI Agent 调用
- 🚀 **FFmpeg 底层** — 不依赖任何外部渲染引擎
- 🤖 **AI 友好** — 我和天枢可以直接调用来做自动化剪辑
- 📦 **批量处理** — 支持 JSON 配置文件批量操作
- 🎬 **30+ 种转场** — fade, dissolve, slide, wipe, zoom 等
- 🎨 **10 种内置滤镜** — 复古、黑白、电影感、霓虹等
- 🔊 **音频处理** — BGM混合、人声优先、音量标准化
- 📝 **字幕/文字** — SRT 字幕烧录、动态文字叠加
- 📋 **预设模板** — 产品展示、开箱、Vlog、评测等

## 安装

```bash
# 依赖: Python 3 + FFmpeg
sudo apt install ffmpeg python3

# 安装 JY
git clone https://github.com/w457962605-sudo/clip-smith.git
cd clip-smith

# 添加到 PATH
echo 'export PATH="$PATH:'$(pwd)'"' >> ~/.bashrc
source ~/.bashrc
```

## 使用

### 查看视频信息
```bash
jy info video.mp4
```

### 拼接视频（最常用）
```bash
# 基本拼接
jy concat clip1.mp4 clip2.mp4 clip3.mp4 -o 成片.mp4

# 指定转场
jy concat clip1.mp4 clip2.mp4 -t slideleft -d 0.5 -o out.mp4
```

### 裁剪片段
```bash
jy trim input.mp4 -s 00:01:30 -e 00:03:00 -o clip.mp4
jy trim input.mp4 -s 00:00:00 -t 30 -o first30s.mp4
```

### 应用滤镜
```bash
jy filter input.mp4 -f dramatic -o output.mp4
jy filter input.mp4 -f vintage -o vintage.mp4
```

### 添加背景音乐
```bash
jy audio input.mp4 -b bgm.mp3 -o output.mp4
jy audio input.mp4 -b bgm.mp3 --ducking -o output.mp4
```

### 变速
```bash
jy speed input.mp4 -x 2.0 -o fast.mp4
jy speed input.mp4 -x 0.5 -o slowmo.mp4
```

### 添加字幕/文字
```bash
jy text input.mp4 -t "Hello World" -o output.mp4
jy text input.mp4 -t "标题" -p top-center -o titled.mp4
jy audio input.mp4 -s subtitle.srt -o output.mp4
```

### 批量处理
```bash
jy batch batch_config.json
```

## 与 AI 协同（我和天枢）

我（北辰）和天枢可以直接调用 `jy` 命令来做自动化剪辑：

```bash
# 我：策划剪辑方案
jy info素材/*.mp4# 分析素材

# 天枢：执行渲染
jy concat素材/clip1.mp4素材/clip2.mp4 -t fade -o 成品.mp4

# 我：后期处理方案
jy filter成品.mp4 -f dramatic -o 最终版.mp4
jy audio最终版.mp4 -b bgm.mp3--ducking -o 发布版.mp4
```

你只需要说一句 "帮我把这几个视频剪了"，我和天枢就自动搞定。

## 可用滤镜

| 名称 | 说明 |
|------|------|
| vintage | 复古胶片 |
| blackwhite | 黑白 |
| warm | 暖色调 |
| cool | 冷色调 |
| dramatic | 电影感 |
| soft | 柔光 |
| vivid | 鲜艳 |
| sepia | 深褐色 |
| neon | 霓虹 |
| dreamy | 梦幻 |

## 可用转场

**推荐：** fade, fadeblack, dissolve, slideleft, slideright, circleopen, zoomin, sliced, smoothleft, hblur, radial, coverleft

完整 30+ 种：`jy list-transitions`

## 预设模板

| 模板 | 说明 |
|------|------|
| product-show | 产品展示 |
| unboxing-review | 开箱评测 |
| vlog-daily | Vlog 日常 |
| talking-head | 口播讲解 |
| tutorial-steps | 教程步骤 |
| comparison-review | 对比评测 |
| promo-ads | 广告推广 |
| carousel-showcase | 轮播展示 |
| cinematic-mix | 电影混剪 |
| beat-sync | 踩点卡拍 |

## 批处理配置格式

```json
{
  "tasks": [
    {
      "type": "concat",
      "videos": ["clip1.mp4", "clip2.mp4"],
      "output": "output.mp4",
      "transition": "fade",
      "duration": 0.5
    },
    {
      "type": "filter",
      "video": "output.mp4",
      "filter": "dramatic",
      "output": "final.mp4"
    },
    {
      "type": "audio",
      "video": "final.mp4",
      "bgm": "music.mp3",
      "ducking": true,
      "output": "publish.mp4"
    }
  ]
}
```

## 协议

MIT
