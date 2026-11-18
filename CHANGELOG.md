# 更新记录

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。版本号为 `<上游版本>-zh.<修订>`。

## [未发布]

### 新增
- 针对 Zellij v0.46.0（提交 `aedee21`）的简体中文支持：19 个补丁、1764 条译文。
  - 网页：令牌登录、断线重连、错误提示、移动端界面。
  - 终端内：状态栏、紧凑栏、标签栏、快捷键提示、会话管理、设置、关于、插件/布局管理、右键菜单、窗格边框与常见提示。
- `tools/zhcn.py`：fetch / check / apply / build / report / export-patches / upstream-status / probe。
- 构建时校验上游提交与补丁可应用性，不兼容版本拒绝构建；构建产物旁生成 `zellij.zh-buildinfo.json`。
- CI 工作流（检查、构建、每周探测上游新版本，只报告不发布）。
- `tools/tests`：工具单元测试。
- Arch `PKGBUILD` 草案（未经完整验证）。

### 已知限制
- 只适配并验证了 v0.46.0；终端输入法（IBus/fcitx）未验证。
- 设置页少量哨兵文案（`(not set)` 等）与配置枚举值保持英文。
