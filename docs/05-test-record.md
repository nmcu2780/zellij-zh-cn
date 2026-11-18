# 测试记录

> 时间：2026-11-16 ~ 2026-11-17。所有测试均在隔离环境（`.work/test-home`，
> 独立 HOME/XDG/socket/端口 18082/18083）进行，未触碰系统安装与用户会话。
> 证据：`.work/evidence/`（原始抓取与截图，不入库）。

## 验证环境

- 本机：Arch Linux，zellij 0.46.0-1（pacman）；测试用独立构建
  `.work/zellij/target/release/zellij`（上游 v0.46.0 + 20 补丁）。
- 工具链：rustup 1.95.0 + wasm32-wasip1 + x86_64-unknown-linux-musl；protoc 36.1。
- 无头浏览器：Helium + playwright-core（仅 localhost 页面）。

## 构建与静态检查

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 基线+补丁+目录 | `tools/zhcn.py check` | 通过，20 补丁全部干净应用 |
| 键/目录对应 | `tools/zhcn.py report` | 2067 用键 = 2067 条目，0 缺失/0 冗余/0 占位符错误 |
| i18n 库单测 | `cargo test --manifest-path crates/zellij-i18n/Cargo.toml` | 6/6 |
| 上游插件测试 | `env -u ZELLIJ_LANG LC_ALL=C cargo test -p bars -p session-manager -p configuration -p context-menu -p share -p prompt -p multiple-select -p strider -p plugin-manager -p layout-manager -p about` | 全通过（bars 177、session-manager 182、configuration 174 等；configuration 的 KDL 回写 round-trip 测试证明译文不进入配置） |
| 网页完整性测试 | `cargo test -p zellij-client web_client`（integrity 相关） | 通过 |
| 服务端相关测试 | `cargo test -p zellij-server`（pane frame/tab 子集） | 72+820 通过 |
| 全量构建 | `tools/zhcn.py build` | ~5–7 分钟，产物 + buildinfo |

## 功能验证（中文/英文对照，pty 抓取 + headless 截图）

| 界面 | 结论 |
| --- | --- |
| 网页令牌登录弹窗 | 中/英切换正常（`?lang=`、localStorage、浏览器语言） |
| 网页断线/重连弹窗 | 中文倒计时、按钮正常 |
| 网页移动端 UI（390×844） | 菜单/新建会话/切换窗格均中文，布局正常 |
| 网页欢迎屏/会话列表 | 中文渲染、WebGL canvas 激活（hasGL:true） |
| 状态栏/紧凑栏/标签栏 | 模式名、快捷键提示（按实际绑定生成）、tips、Alt 宽提示全部中文；80/120/200 列截断行为与英文一致 |
| 会话管理（含欢迎屏） | 列表/预览/新建/复活/帮助/收件箱全中文；SGR 左键点击中文行正确选中 |
| 右键菜单 | 默认标签中文显示、菜单宽度和命中区域正确 |
| share/prompt/multiple-select/strider | 中文显示正常 |
| configuration 设置 | 屏内说明中文；配置值为英文枚举（正确）；**保存后 config.kdl 零汉字**（diff + CJK grep 验证） |
| about/plugin-manager/layout-manager | 中文显示正常 |
| 窗格边框 | 滚动指示 `回滚：x/y`、退出码、PIN、重命名占位符中文；80/120 列正确 |
| 插件权限弹窗 | fixture 插件触发，13 条权限说明全中文 |
| 中文输入/显示 | UTF-8 中文、双宽、光标位置、窗格中文标题与省略号截断均正确 |
| fish + omp + 全屏程序 | fish 提示符/中断/清屏正常；omp TUI 渲染正常退出干净；htop/less/vim 全屏进出正常 |
| 语言回退 | `ZELLIJ_LANG=en` 或英文 locale → 全英文；未知键 → 英文原文 |

## 升级演练

| 项目 | 结果 |
| --- | --- |
| `probe --tag v0.45.1`（演练时队列为 17 个补丁） | 退出码 2：15/17 补丁失败、52 个文件上游已变更——正确拒绝，不标为受支持 |
| `upstream-status` | 正确列出 ≥ 基线标签（调查期无更新标签） |

## 已知缺陷与遗留（截至本记录时）

| 项 | 状态 |
| --- | --- |
| configuration 深链 `page=<slug>` 中文环境失效 | **已修复并验证**：slug 取自英文标题；中文环境 `page=zellij_terminal` 直接打开“Zellij 终端”页；单测 `slugs_are_derived_from_the_english_titles` 在中/英环境均通过 |
| 窄宽度 `⟳ 重启` 徽标回绕污染侧栏 | **已修复并验证**：90 列各行徽标不回绕；60 列显示“窗格太小，无法显示设置（需要 50x12）” |
| 欢迎窗口中文长句不换行（`wrap` 只按空白拆词） | **已修复**（补丁 0019：按显示宽度断行，禁止标点行首）；单测 `text_without_spaces_wraps_by_display_width`、`english_wrapping_is_unchanged` |
| 欢迎窗口首句高亮丢失（高亮词是翻译键，必须出现在译文句中） | **已修复**；`every_emphasized_phrase_is_in_a_point` 在中文环境通过。维护提示：改这几条译文时必须保留高亮词 |
| 设置页残留英文 `(not set)`、`(bundled font)`、`(same as Font)` | 已知残留：它们是参与比较/保存的哨兵常量，翻译有风险，保持英文 |
| 配置枚举值（如 `Detach`、`Ask, sug…`、`on`/`off`） | 设计如此：属配置值，不翻译 |
| `import` 警告清理 | 已在补丁中修复 |
| SGR 右键直开 context-menu | 未验证（`zellij action open-context-menu` 路径已验证） |
| 终端 IME（如 IBus/fcitx）输入法 | 未验证（测试中中文输入为 UTF-8 字节注入） |
| 用户实际键位布局的非默认组合 | 覆盖由运行时绑定生成，理论上正确，未逐一验证 |

## 测试局限

- pty 捕获无法覆盖真实终端差异；未实测的渲染器（如非 WebGL 路径）依赖上游行为。
- `collect_candidates` 文案盘点为启发式，人工抽查不能替代全量覆盖声明。
- 未验证项明确列出，不视为已通过。

## 开源前完整测试（2026-11-18，20 个补丁，最终二进制）

环境：Arch Linux，隔离 HOME/socket/端口（`.work/test-home`、18083），Helium 无头浏览器；
没有触碰系统 zellij、用户配置与正在运行的会话。

### 自动化

| 项目 | 命令 | 结果 |
| --- | --- | --- |
| 英文环境回归（项目约定命令） | `env -u ZELLIJ_LANG LC_ALL=C cargo test --no-fail-fast -p about -p configuration -p bars -p session-manager -p prompt -p strider -p plugin-manager -p zellij-i18n` | about 5、bars 177、configuration 176、plugin-manager 4、prompt 83、session-manager 182、strider 13、zellij-i18n 11，**0 失败** |
| 设置往返（任意语言） | `cargo test -p configuration every_choice_label`（`ZELLIJ_LANG=en` 与 `zh-CN` 各一次） | 均通过：下拉标签总能映射回配置值 |
| 桌面集成 | `cargo test -p zellij-utils desktop_integration` | 44 通过 |
| 工具测试 | `python3 -m unittest discover -s tools/tests` | 27 个（含审计与高亮检查） |
| 键/目录对应 | `tools/zhcn.py report --strict` | 2067 = 2067，无缺译/冗余/占位符错误 |
| 漏译审计 | `tools/zhcn.py audit --strict` | 0 处（白名单见 `i18n/audit-allow.txt`） |
| 高亮检查 | `tools/check_emphasis.py` | 55 处高亮，0 问题 |
| 干净克隆复现（无全局 git 身份） | fetch → check → build → report/audit/emphasis | 见下方“可复现性” |

### 实机（pty 驱动 + 无头浏览器）

| 项目 | 结论 |
| --- | --- |
| 语言选择与回退 | 中文环境为中文；`ZELLIJ_LANG=en`、`LANG=C`、`LANG=fr_FR` 回退英文；`ZELLIJ_LANG=zh-CN` 可覆盖 `LANG=C` |
| 自定义快捷键 | 状态栏按实际绑定显示（`Ctrl b 窗格`、`Ctrl y 标签页`），中英文一致 |
| 启动小技巧（17 页） | 全部中文；按键与词语高亮按内容计算；链接紧跟标签，句子不再被截断 |
| 设置：主题/按键/鼠标/常规/Zellij 终端 | 中文；深链 `page=<slug>` 在中文环境有效；`⟳ 重启` 在 90 列不回绕，60 列显示“窗格太小，无法显示设置（需要 50x12）” |
| 设置保存 | 在中文界面修改并保存后，`config.kdl` 只新增 `show_release_notes false`，**中文字符数 0** |
| 设置向导（`Ctrl w`） | 中文；“?” 帮助浮层中文 |
| 会话管理 / 插件管理 / 分享 / 文件选择 / about | 中文；会话明细高亮已修正 |
| 网页 | `?lang=zh-CN`：登录弹窗、错误令牌提示“登录令牌无效或已被撤销。”、登录成功、会话列表、WebGL 画布（`gl:true`）；英文端同样通过 |
| fish + 中文输入 + 全屏程序 | fish 提示符与中文欢迎语正常；`echo 你好，世界`、`printf '标题｜测试'` 输出正确；vim（含插入中文）、less、htop 进出正常 |

### 本轮测试发现并修复的缺陷

1. 约 250 处界面英文字面量漏包 `tr()`（此前“1764 条与代码完全对应”只能证明已包的键有译文），已补译，并新增 `audit` 命令防止回归。
2. 约 100 处写死字符位置的高亮在中文下错位，改为按内容上色；`check_emphasis.py` 防止译文丢失被高亮的词。
3. 中文长句不换行（`wrap` 只按空白拆词）：新增 `zellij_i18n::wrap_by_width`。
4. 页面块宽度、链接位置与“放不放得下”的判断按字符数而非显示宽度计算，导致小技巧/about 句子被截断、链接盖住标签；plugin-manager、share、about 已改为显示宽度。
5. 用 `find()` 的字节偏移当字符下标（会话明细、strider “查找：”提示），中文前缀下高亮错位，已修。
6. 构建/CI 复现问题：`git am` 无提交身份会失败、`report` 在未打补丁的工作区假通过、失败后需 `--force`。

### 可复现性

- 早先的干净克隆完整构建（19 补丁，无全局 git 身份）：`BUILD_EXIT 0`，`report --strict` 通过。
- 最终提交的干净克隆构建结果见本文件末尾“发布前核对”。

### 未验证与局限

- **终端输入法（IBus/fcitx）**：中文输入只测了 UTF-8 字节注入，没有测真实输入法的预编辑与候选框。
- SGR 右键直开 context-menu；嵌套会话弹窗（服务端）的中文显示只做了编译与静态审计，没有实机渲染。
- layout-manager 的紧凑控制行未翻译（见 `docs/coverage.md`），因此该插件的中文界面不完整。
- About 小技巧里的 `Ctrl p + u` 等按键由上游按默认键位写死，自定义键位下可能与实际不符（英文同样，属上游行为）。
- 只在 Linux、一种终端模拟（pty）与一种浏览器（Chromium 系）里验证；未测 macOS/Windows、其他终端与 Firefox。
- 网页端测试用的是 16:26 的构建；之后只改了 session-manager/strider 的插件高亮代码，网页资源未变，未重跑网页测试。
- 审计是启发式的，不能证明没有漏译；最终仍靠实际界面抽查。

