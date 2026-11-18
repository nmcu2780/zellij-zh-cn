# 翻译覆盖清单（v0.46.0）

状态：已翻译 / 部分 / 未翻译 / 不翻译（注明原因）。以 `tools/zhcn.py report` 为准。

## Web 客户端（zellij-client/assets）

| 文件 | 状态 | 说明 |
|---|---|---|
| modals.js | 已翻译 | 令牌/错误/重连弹窗全部文案（0002） |
| auth.js / connection.js / app.js 中错误 | 已翻译 | 登录与连接错误信息（0002） |
| mobile-ui.js | 已翻译 | 菜单、切换浮层、新建会话对话框、修改键栏文案、卡片元信息、相对时间（0004）。按键标签 ESC/TAB/CTRL/ALT/方向键为键名，不译 |
| links.js | 已翻译 | "Shift-Click: "（0004） |
| document.title | 不翻译 | 会话名（用户数据）/ "Zellij"（产品名） |
| xterm.js、addon-*.js | 不翻译 | vendored xterm 与插件，不修改 |

## bars 插件（default-plugins/bars）

| 文件 | 状态 | 说明 |
|---|---|---|
| status_bar/first_line.rs | 已翻译 | 模式标签全称与短形式（tr_ctx）（0003） |
| status_bar/one_line_ui.rs | 已翻译 | 搜索/重命名状态文案 + 全部 keymap 提示文案（0003/0005） |
| status_bar/second_line.rs | 已翻译 | 全部 keymap 提示文案（0005） |
| status_bar/session_hints.rs | 已翻译 | "pane muted"、"Switched from…" 等（0005） |
| status_bar/hover.rs | 不翻译 | 仅逻辑代码，无 UI 文案 |
| mode_hints.rs | 已翻译 | mode_label 模式名显示（0007） |
| compact_bar 模式名 | 已翻译 | line.rs 经 mode_label 显示（0007） |
| status_bar 宽屏 Alt 提示 | 已翻译 | hint_line 文案（0007）；内联快捷键标签 "Resize"/"Floating"（0011） |
| status_bar/tip | 已翻译 | 小贴士文案与 "Tip:" 前缀（0012）|
| context-menu | 已翻译 | 渲染点 tr_dyn；标签标识符不译（0007） |
| compact_bar/* | 已翻译 | 动作描述、提示、剪贴板消息、"Enter name…"、嵌套会话标记、tooltip 带（0006）。" Zellij " 前缀为产品名不译 |
| tab_bar/mod.rs | 已翻译 | "Enter name…"（0006）。溢出标记仅含符号与数字，无词可译 |
| session_indicator.rs | 已翻译 | need you / watch alert(s) / failed / done / working / running（0006） |
| link/mod.rs | 已翻译 | "Browse: {path}"、"Open" 提示（0006） |
| main.rs | 已翻译 | "Enter name…"（0006） |

## session-manager 插件（default-plugins/session-manager）

| 文件 | 状态 | 说明 |
|---|---|---|
| main.rs | 已翻译 | 欢迎文案、会话/文件夹提示、接入/断开/窗口提示、面板标题、"Sessions"/"Inbox"、删除/重命名确认、错误信息（0008/0010） |
| panel.rs | 已翻译 | 会话列表行、预览面板、Folder/Branch 列标题、pane(s) 计数、"{count} Exited"、时间文案（0008/0010） |
| ui/components.rs | 已翻译 | 搜索框 "Session:"/"Folder:" 提示、tabs/panes/clients 明细（trf + 位置扫描着色）（0010） |
| session_list/session_tree/resurrectable_sessions/app_panel/help/inbox/single_screen/ui | 已翻译 | 会话列表、收件箱徽标、帮助行、按键提示（0008） |

会话名、布局名、路径、命令、git 分支为用户数据不译；keybinding 提示仍由真实绑定生成。

## 其余插件（批次 B）

| 文件 | 状态 | 说明 |
|---|---|---|
| share/* | 已翻译 | Web 共享主屏、令牌管理屏、令牌屏、UI 组件（0009） |
| prompt/* | 已翻译 | form、main、outcome、ui（0009） |
| multiple-select | 已翻译 | 组动作、选中计数、按键替换（0009） |
| strider/* | 已翻译 | 文件列表、搜索视图、状态、共享组件（0009） |

## about、plugin-manager、layout-manager、configuration 与核心

| 区域 | 状态 | 说明 |
|---|---|---|
| about | 已翻译 | 欢迎页、小技巧（含按键高亮）、按键绑定页、首次运行向导；版本号/URL 不译（0012、0019、0020）。**例外**：小技巧里的 `Ctrl p + u` 等按键由上游按默认键位写死，自定义键位下可能与实际不符（英文同样如此，属上游行为） |
| plugin-manager | 已翻译 | 加载界面、URL 输入、配置提示、搜索导航；按键行高亮改为按内容计算（0013、0020） |
| layout-manager | **部分翻译** | 屏标题、布局解析/保存错误等（0013）。**未覆盖**：布局表底部的紧凑控制行、`[All Tabs]`/`[Current Tab]` 等同时用于匹配和着色的标记、`Nm ago` 时间简写、KDL 语法诊断。原因：这些是手工对齐的英文表格，翻译需要重新设计布局；已在 `i18n/audit-allow.txt` 中按目录列为暂不覆盖 |
| configuration | 已翻译（有意例外见下） | 设置、主题、按键/鼠标绑定、设置向导及桌面集成结果（0014、0016、0018、0020）。有意不译：KDL 写回串、动作名（写入配置）、下拉里的枚举值（`on`/`off`/`Detach` 等，与配置文件一致）、哨兵文案 `(not set)`/`(bundled font)`/`(same as Font)`、help.rs 里源自 default.kdl 注释的帮助文本、主题名与预设名 |
| 服务端（zellij-server 的窗格边框、提示与弹窗） | 部分翻译 | 窗格边框标题与提示、嵌套会话弹窗、重命名占位符、点击提示（0017、0020）。日志、内部错误与协议字符串不译 |
| 命令行（`zellij ls`、`--help` 等）与客户端程序输出 | 未翻译 | 会被脚本解析，有意保持英文 |
| 插件窗格名（`Session Manager`、`Zellij launcher` 等） | 不译 | 是可被引用的名称，不是界面文案 |

### 覆盖情况如何核对

覆盖声明以工具为准，而不是人工印象：

- `python3 tools/zhcn.py report --strict`：代码里用到的译文键与目录必须一一对应；
- `python3 tools/zhcn.py audit --strict`：扫描插件和服务端界面代码里**没有包 `tr()`** 的英文界面字面量。有意不译的写入 [`i18n/audit-allow.txt`](../i18n/audit-allow.txt) 并注明理由；
- `python3 tools/zhcn.py audit --sites`：更严格的模式，连“目录里有这个词、但此处没用 `tr()`”的使用点也列出来（含少量误报，如配置枚举值）；
- `python3 tools/check_emphasis.py`：按内容高亮的译文必须仍含被高亮的词或按键，否则中文下高亮会静默丢失。

审计是**启发式**的：它能发现绝大多数漏译，但不能证明没有漏译（例如拼接出来的句子、以变量形式传入的文案）。最终仍要靠实际界面抽查，未抽查到的范围见 [测试记录](05-test-record.md)。

## 有意不译的类别

键名与修饰键（Ctrl/Alt/Shift/ENTER/ESC/SPACE/TAB/PgUp/PgDn/HJKL/方向键）、"Zellij"、"TMUX"、文件名、环境变量名、日志输出（log::/eprintln!）、协议/配置键名、IPC 字符串、用户数据（会话/标签页/窗格名）、由服务端生成的默认标签页名（"Tab #N"）。
