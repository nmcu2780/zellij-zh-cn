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

## 其余（未开始）

| 区域 | 状态 |
|---|---|
| about | 已翻译 | onboarding、pages、tips、keybindings 页；版本号/URL 不译（0012） |
| plugin-manager | 已翻译 | 加载界面、URL 输入、配置提示、搜索导航（0013）|
| layout-manager | 已翻译 | 导入/保存/重命名屏、解析与保存错误、布局表/详情视图（0013）|
| configuration | 部分翻译 | 屏标题、设置名/描述、帮助行、按钮、确认、错误、向导（0014）。有意不译：KDL 写回串（keybinds preset=、{}={} 等）、动作名（写入 config）、下拉选项标签（option_value 反向映射）、类别名仅在显示点译、help.rs 配置注释帮助文本（源自 default.kdl 注释）、mode_name 值、主题名/预设名 |
| 服务端/客户端核心（zellij-server、zellij-client、zellij-utils 等程序输出与 CLI） | 未翻译 |
| 首次运行向导（about 插件欢迎屏 "Hi there, welcome to Zellij!" 等） | 未翻译 |

## 有意不译的类别

键名与修饰键（Ctrl/Alt/Shift/ENTER/ESC/SPACE/TAB/PgUp/PgDn/HJKL/方向键）、"Zellij"、"TMUX"、文件名、环境变量名、日志输出（log::/eprintln!）、协议/配置键名、IPC 字符串、用户数据（会话/标签页/窗格名）、由服务端生成的默认标签页名（"Tab #N"）。
