[app]

# 应用名称
title = JY剪辑

# 包名（唯一标识）
package.name = jyclips

# 域名（反向）
package.domain = com.justyou

# 源码目录
source.dir = .

# 入口文件
source.main = main.py

# 版本号
version = 0.1.0

# 需求 - ffmpeg 通过 kivy 的 android 依赖自动包含
requirements = python3,kivy

# 权限
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# 支持的架构
android.archs = armeabi-v7a,arm64-v8a

# 最低 SDK 版本
android.minapi = 21

# 目标 SDK 版本
android.api = 33

# 应用图标
# icon = icon.png

# 是否为数字签名调试版本
android.debug = 1

# 添加 ffmpeg 二进制
android.add_libs_armeabi_v7a = /usr/lib/arm-linux-gnueabihf/lib*.so
android.add_libs_arm64_v8a = /usr/lib/aarch64-linux-gnu/lib*.so

[buildozer]

# 日志级别
log_level = 2

# 是否清理构建
clean_after_build = 0
