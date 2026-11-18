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

## 补充验证（2026-11-17，19 补丁构建，二进制 22:06）

| 项目 | 命令/方法 | 结果 |
| --- | --- | --- |
| 英文环境回归 | `env -u ZELLIJ_LANG LC_ALL=C cargo test --no-fail-fast -p about -p configuration -p bars` | about 5、bars 177、configuration 175 全部通过 |
| 中文环境欢迎窗口 | `ZELLIJ_LANG=zh-CN cargo test -p about` | 5/5 通过 |
| 深链/窄宽度 | pty 驱动隔离会话（`LANG=zh_CN.UTF-8`，120/90/60 列） | 见上表“已修复并验证” |

> 注意：在 `ZELLIJ_LANG=zh-CN` 下跑 bars/configuration 单测会有大量“失败”，因为这些测试断言英文文案；
> 回归必须按上面的英文命令执行，中文环境只用于验证中文专属行为（如 about 的断行与高亮）。
