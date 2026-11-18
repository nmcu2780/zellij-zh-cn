# 更新记录

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。版本号为 `<上游版本>-zh.<修订>`。

## [未发布]

### 新增
- 针对 Zellij v0.46.0（提交 `aedee21`）的简体中文支持：20 个补丁、2067 条译文。
  - 网页：令牌登录、断线重连、错误提示、移动端界面。
  - 终端内：状态栏、紧凑栏、标签栏、快捷键提示、会话管理、设置、关于、插件/布局管理、右键菜单、窗格边框与常见提示。
- `tools/zhcn.py`：fetch / check / apply / build / report / export-patches / upstream-status / probe。
- 构建时校验上游提交与补丁可应用性，不兼容版本拒绝构建；构建产物旁生成 `zellij.zh-buildinfo.json`。
- CI 工作流（检查、构建、每周探测上游新版本，只报告不发布）。
- `tools/tests`：工具单元测试。
- Arch `PKGBUILD` 草案（未经完整验证）。

### 修复（完整测试中发现）
- 约 250 处界面英文字面量漏包 `tr()`（设置向导、主题页、按键/鼠标绑定、会话管理、小技巧、状态栏提示、桌面集成状态、服务端弹窗等），已补译（补丁 0020）。
- 约 100 处用写死字符位置给按键/词语上色，译成中文后高亮会落在错误的字上；改为按内容上色（`color_substring`、`color_keys`、`combo_text`）。
- 中文长句不换行（`wrap` 只按空白拆词）：新增 `zellij_i18n::wrap_by_width`，按显示宽度换行，禁止标点行首。
- 新增 `tools/zhcn.py audit`（漏译审计，含 `--sites` 严格模式与白名单 `i18n/audit-allow.txt`）、`tools/check_emphasis.py`，并接入 CI。

### 已知限制
- layout-manager 的紧凑控制行未翻译（手工对齐的英文表格），见 `docs/coverage.md`。
- 只适配并验证了 v0.46.0；终端输入法（IBus/fcitx）未验证。
- 设置页少量哨兵文案（`(not set)` 等）与配置枚举值保持英文。
