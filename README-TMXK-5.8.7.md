# TMXK FongMi 5.8.7

此分支使用官方 FongMi 5.8.7 arm64 手机版、电视版作为二进制基底，保留原版播放核心与界面，再注入本地资源和首次启动配置注册器。

## 内置内容

- 饭太硬点播入口：`http://www.饭太硬.cc/tv`
- 央视频、央视官网、广东广电：`assets://tmxk/config.json`
- 游戏直播 Spider：`assets://tmxk/game-live-vod.json`
- 所有 Python/JSON 脚本均放在 APK 的 `assets/tmxk/` 下，脚本相对路径保持原目录结构。

首次启动会在原版 Config 数据库中幂等注册上述来源；若用户已经有同地址来源，不重复添加。若 VOD/直播类别原本为空，则自动选择对应内置源，不覆盖已有选择。

## Python 与运行模块

在 App 的「设置 → 模块」中安装官方对应架构模块。5.8.7 官方模块仓库包含 Python 1.1.3、QuickJS 1.1.0、MPV 1.1.0。个别 Spider 还依赖 pycryptodome、lxml、pywasm 等 Python 包；这些依赖是否能由设备端 Python 模块直接满足，仍需在实际设备上验证。

## 安装注意事项

- 产物与官方 APK 使用相同包名，但使用本分支生成的签名。Android 不允许不同签名直接覆盖安装官方版。
- 安装前先备份 FongMi 应用数据，再卸载官方签名版，随后安装对应的 TMXK APK。
- Actions 每次构建会生成新的临时签名密钥。后续重新构建的签名可能不同，因此不要删除已安装版本的数据前忘记备份。
- 本流程只做 APK 重打包与资源注入，并未声称已在真实电视/手机上完成播放验收。
