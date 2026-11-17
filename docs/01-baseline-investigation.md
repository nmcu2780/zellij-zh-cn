# 任务 1：基线调查与方案选择

调查日期：2026-11-16。所有命令均只读或在 `.work/`（已加入 `.gitignore`）中执行，未改动系统安装、用户配置或运行中的会话。

## 1. 上游版本与许可证

| 项目 | 结果 | 复现命令 |
| --- | --- | --- |
| 上游仓库 | `https://github.com/zellij-org/zellij` | — |
| 基线标签 | `v0.46.0`，提交 `aedee21cb0d58d716496e7f6c66ba0b6f08045d8` | `git clone --depth 1 --branch v0.46.0 … .work/zellij && git -C .work/zellij rev-parse HEAD` |
| 近期标签 | `v0.44.0 … v0.44.3, v0.45.0, v0.45.1, v0.46.0`（截至调查日最新为 0.46.0） | `git ls-remote --tags https://github.com/zellij-org/zellij.git` |
| 许可证 | MIT（根目录 `LICENSE.md`，`Copyright (c) 2020 Zellij contributors`；各默认插件目录另有 `LICENSE.md`） | `head LICENSE.md` |
| 工具链 | `rust-toolchain.toml` 固定 `1.95.0`，目标 `wasm32-wasip1`、`x86_64-unknown-linux-musl` | `cat rust-toolchain.toml` |

## 2. 本机现状（只读核实）

- `/usr/bin/zellij`，`zellij 0.46.0`，Arch 软件包 `zellij 0.46.0-1`（MIT）。`zellij web --help` 可用，说明系统包已启用 Web 服务能力。
- 调查时没有运行中的 zellij 进程；`zellij ls` 显示一个已退出、可复活的会话（不触碰）。
- 用户配置 `~/.config/zellij/config.kdl` 存在，其中 `plugins {}` 别名全部指向内置插件 `zellij:bars`、`zellij:session-manager` 等，另有 `web_client { font … }`。本项目不修改该文件。
- 用户 shell 为 fish 4.x，提示符工具 `omp` 位于 `/usr/bin/omp`。
- 系统 Rust 为 rustup 管理；上游工具链由 `rust-toolchain.toml` 自动在用户级 `~/.rustup` 安装。

## 3. 资源加载方式

### 3.1 网页客户端

- 资源位于 `zellij-client/assets/`，通过 `include_dir!("$CARGO_MANIFEST_DIR/assets")` **编译期嵌入**二进制（`zellij-client/src/web_client/http_handlers.rs`）。`/assets/<文件>` 路由直接从嵌入目录取文件，运行时**没有**从磁盘覆盖的入口。
- `app.js` 是由 `cargo xtask assets`（`xtask/src/assets.rs`）按固定 `MODULE_ORDER` 把 `utils.js … index.js` 等模块确定性拼接得到的产物；同一步骤计算 `integrity.json` 并改写 `index.html` 中的 SRI `integrity` 属性。`modals.js` 是独立的经典脚本。上游单元测试会核对 `integrity.json` 与 `index.html` 一致。
- 结论：网页汉化**必须重新编译 zellij 主程序**，修改模块源码后需运行 `cargo xtask assets` 重新生成包与完整性哈希。

### 3.2 终端内界面（插件）

- 标签栏、状态栏、紧凑栏（同一插件 `bars`，按 `role` 区分）、会话管理器/欢迎界面、设置（`configuration`）、关于、插件管理器、右键菜单、提示框、文件选择器等均为 `default-plugins/*` 下的 Rust 插件，编译为 `wasm32-wasip1`，产物 `zellij-utils/assets/plugins/*.wasm` 通过 `include_bytes!` 嵌入主程序。
- 0.46.0 新增 **Distribution 接口**（`zellij-utils/src/distribution.rs`、`zellij::run(Distribution)`）：第三方可依赖 `zellij` crate，`without_plugin(name)` + `with_plugin(name, bytes)` 替换内置插件，并可附带分层配置。它能替换插件和默认配置，但**不能替换网页资源和主程序内文字**。
- 插件 WASI 环境调用了 `WasiCtxBuilder::inherit_env()`（`zellij-server/src/plugins/plugin_loader.rs`），插件可读取会话服务器进程的环境变量 —— 可用于运行时语言选择。
- 用户配置的 `plugins {}` 别名也可把 `zellij:bars` 改指 `file:…wasm`，因此“只替换插件、沿用系统二进制”在技术上可行。

### 3.3 程序本体

- `zellij-server`（窗格边框提示、滚动/退出码提示等）、`zellij-client`、CLI 帮助等文字直接写在 Rust 源码中，只能通过补丁+重新编译修改。

### 3.4 已有语言机制

- 全仓库检索 `i18n|locale|gettext|fluent|translat` 只命中无关代码；**上游没有任何本地化机制**。`index.html` 固定 `lang="en"`。

## 4. 用户可见文案初步盘点

以下数字是基于正则的“候选字符串”估计（包含配置键、动作名、测试数据等不应翻译的内容），只用于评估规模，**不是覆盖率**。精确清单由 `tools/` 中的提取与盘点工具维护（任务 2 起）。

| 区域 | 位置 | 规模 | 说明 |
| --- | --- | --- | --- |
| 网页登录/错误/重连 | `modals.js`, `auth.js`, `connection.js`, `index.js`, `links.js` | 约 20 条 | 令牌输入、认证错误、断线/重连倒计时、连接中 |
| 网页移动端 UI | `mobile-ui.js` | 约 25 条 | 菜单、新建会话对话框、切换窗格/会话、切换桌面版；按键名 ESC/TAB/CTRL/ALT 保持原样 |
| 网页会话列表 | 由终端内 `session-manager` 插件（欢迎界面）渲染 | 见下 | 网页本身不渲染会话列表 |
| 标签栏/状态栏/紧凑栏 | `default-plugins/bars` | 候选约 200 | 模式名、快捷键提示（按实际绑定生成）、提示信息 |
| 会话管理 | `default-plugins/session-manager` | 候选约 120 | 会话列表、新建、复活、欢迎界面 |
| 设置 | `default-plugins/configuration` | 候选约 1100 | 大量为动作名/配置键，需人工甄别 |
| 关于/提示 | `default-plugins/about` | 候选约 130 | 版本说明、提示（tips）文本 |
| 其他插件 | `context-menu`、`prompt`、`share`、`layout-manager`、`plugin-manager`、`strider`、`multiple-select` | 合计候选约 150 | — |
| 程序本体 | `zellij-server/src/{panes,tab,screen.rs}` 等 | 候选约 250 | 窗格边框/退出提示等 |

右键菜单的条目定义在默认配置（`zellij-utils/assets/config/default.kdl`）中，属于配置数据。

## 5. 方案对比

| 方案 | 能覆盖 | 不能覆盖 | 维护成本 | 风险 / 回退 |
| --- | --- | --- | --- | --- |
| A. 仅替换插件：构建汉化 wasm，用户配置 `plugins {}` 指向 `file:` | 终端内插件界面 | 网页（资源嵌入二进制）、程序本体文字 | 中：每个上游版本重建插件 | 系统包升级后旧 wasm 与新宿主协议可能不兼容，插件直接加载失败而不是回退英文；需改用户配置 |
| B. Distribution 包装二进制：`zellij::run(Distribution)` 替换内置插件 | 终端内插件界面 | 网页、程序本体（仍需补丁） | 中 | 仍然需要补丁才能做网页，包装层不带来额外能力；会改变发行名所决定的配置/套接字目录（除非取名 `zellij`） |
| C. **固定上游提交 + 补丁队列 + 集中译文目录，独立构建完整二进制**（选用） | 网页、全部插件、可选的程序本体文字 | 无硬性限制 | 中：补丁随上游变化需要变基；译文目录集中 | 补丁无法应用即构建失败（不产出半汉化二进制）；独立安装不影响系统包，回滚 = 不使用/删除独立二进制 |
| D. 维护完整分叉仓库 | 全部 | — | 高，难以同步 | 违背“避免维护难以同步的源码副本” |
| E. 二进制内字符串替换/偏移补丁 | 有限 | 宽度/格式无法处理 | 极高，脆弱 | 明确禁止 |

### 选择：方案 C

理由：

1. 用户主要使用网页，网页资源只能编译期嵌入，因此重新编译不可避免；既然要编译，插件与网页在同一构建中处理最简单、最一致。
2. 本仓库只保存：上游基线描述（版本+提交）、按版本分目录的补丁队列、集中译文目录、小型查找库与工具脚本；上游源码在 `.work/` 中按需获取，不提交副本。
3. 插件中的快捷键提示由上游代码按实际绑定生成，汉化只替换说明文字，保持按键正确性。
4. 补丁以“用 `tr("English")` 包装原文”为主，英文原文就是译文键；查不到译文时原样返回英文，新文字天然回退英文。
5. 版本检测发生在**构建阶段**：工具校验 `.work/zellij` 的提交与 `upstream.toml` 一致，且补丁必须 `git apply --check` 通过，否则拒绝构建并提示。独立构建的二进制自带匹配的插件与网页资源，运行期不存在“汉化资源与宿主版本不匹配”的组合；本方案**不会也不能修改系统 `/usr/bin/zellij` 的行为**。

未采用 Distribution 包装（方案 B）的原因：它不能替换网页资源和主程序文字，而这两者仍需补丁；在补丁已重建内置插件的前提下，包装层只增加一层间接性。若将来上游为网页资源提供运行时覆盖接口，可重新评估。

### 已知限制

- 终端界面语言由**启动该会话服务器的二进制及其环境**决定：用系统 `zellij` 创建的会话即使用汉化客户端连接，插件仍为英文。网页界面语言由浏览器端决定（详见任务 2 设计）。
- 汉化二进制与系统 0.46.0 使用相同的配置与套接字目录（均名为 `zellij`），可以互相看到会话；不同版本之间的混用不受支持（上游本身也如此）。

### 回滚

- 汉化构建产物独立存放，不覆盖 `/usr/bin/zellij`；停止使用汉化二进制（或删除其安装目录）即可回到系统英文版。设置环境变量 `ZELLIJ_LANG=en`（任务 2 实现）可在汉化二进制内切回英文。

## 6. 参考项目

- `bayunai/Zellij_zh_CN`：独立的中文标签栏/状态栏插件，基于 `zellij-tile 0.44.3`，快捷键提示为固定值。本项目**不复制其代码**，仅在术语选择上参考常见中文译法；因此无需引入其许可证。若后续需要引用其代码，须先核实其仓库中的实际许可证文件。
