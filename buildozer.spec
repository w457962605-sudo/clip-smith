[app]

# 应用名称
title = JY

# 包名（唯一标识）
package.name = jyclips

# 域名（反向）
package.domain = com.justyou

# 源码目录
source.dir = .

# 入口文件
source.main = clip.py

# 版本号
version = 0.1.0

# 需求
requirements = python3,kivy

# 权限
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# 支持的架构
android.archs = armeabi-v7a,arm64-v8a

# 最低 SDK 版本
android.minapi = 21

# 目标 SDK 版本
android.api = 33

# 应用图标（默认使用 Kivy 默认图标）
# icon = icon.png

# 是否为数字签名调试版本
android.debug = 1

[buildozer]

# 日志级别
log_level = 2

# 是否清理构建
clean_after_build = 0
