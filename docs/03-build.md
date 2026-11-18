# 构建与维护（任务 2）

本仓库不修改系统里的 zellij。所有上游源码、构建产物和运行时数据都放在
`.work/`（已 gitignore）。`tools/zhcn.py` 只用 Python 标准库
（需要 Python ≥ 3.11 的 `tomllib`）。

## 前置条件

- rustup（`rust-toolchain.toml` 会自动安装固定的 Rust 版本与
  `wasm32-wasip1`、`x86_64-unknown-linux-musl` target）。
- `protoc`（zellij 的 protobuf codegen 需要）。
- 无需 sudo，不触碰 `/usr/bin/zellij` 与 `~/.config/zellij`。

## 可选：crates 镜像覆盖

如果默认 crates.io 源不可用，把覆盖写进 `.work/cargo-local.toml`
（该文件已 gitignore，不会提交）。`zhcn.py` 检测到它存在时，会把它通过
`--config` 传给所有外层及嵌套 cargo 调用。示例：

```toml
[source.crates-io]
replace-with = "ustc"
[source.ustc]
registry = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"
```

**不要**改 `.work/zellij/.cargo/config.toml`——它是上游文件，
`check`/`apply` 会把工作区重置回基线，手改会被丢弃。

## 命令

```bash
# 1. 克隆/拉取上游到 .work/zellij，核对 HEAD == 钉住的提交
python3 tools/zhcn.py fetch            # 可加 --tag/--commit/--workdir 覆盖

# 2. 校验：基线提交、补丁队列能在干净副本上依次应用、译文目录合法
python3 tools/zhcn.py check
#    失败时输出中文原因并拒绝构建；上游不兼容时不会产出半成品

# 3. 构建：check + apply（git am 补丁 + 生成目录/资源）+ cargo xtask ci build-release
python3 tools/zhcn.py build
#    产物：.work/zellij/target/release/zellij
#
#    apply/build 会重置 .work/zellij 到基线再 git am。工作区有未提交的
#    已跟踪改动，或 zh-cn 分支与已导出补丁不一致（有未导出提交）时，
#    会以中文报错并拒绝执行；确认可丢弃后用 --force 强制重建。

# 4. 报告：列出已用键、缺译键（回退英文）、未使用的目录条目、占位符不匹配
python3 tools/zhcn.py report           # 加 --json 输出机器可读结果
#    占位符不匹配返回非零；缺译仅为警告；加 --strict 时缺译/冗余条目也返回非零（CI 使用）
#    注意：report 需要已应用补丁的工作区（先 apply 或 build），否则会拒绝

# 4b. 漏译审计：列出没有包 tr() 的英文界面字面量（启发式）；--sites 更严格，
#     --strict 在有疑似漏译时返回非零。有意不译的写入 i18n/audit-allow.txt
python3 tools/zhcn.py audit
#     高亮检查：按内容高亮的译文必须仍包含被高亮的词/按键
python3 tools/check_emphasis.py

# 5. 补丁开发流程：在 .work/zellij 的 zh-cn 分支上修改/提交，然后重新导出
python3 tools/zhcn.py export-patches   # git format-patch <基线>..zh-cn

# 单独生成（apply/build 内部已调用，仅供调试）
python3 tools/zhcn.py gen-rust --out <路径>
python3 tools/zhcn.py gen-web  --out <路径>
```

## 测试

```bash
# 本仓库的查找库（零依赖）。测试用内置测试表，不需要先生成目录；
# 仓库里提交的 catalog_generated.rs 是空占位表（全部回退英文），正式构建时
# apply/build 会自动调用 gen-rust 生成真实目录
cargo test --manifest-path crates/zellij-i18n/Cargo.toml

# 上游受影响 crate（在 .work/zellij 内；bars 测试含英文断言，需英文环境）
cd .work/zellij
env -u ZELLIJ_LANG LC_ALL=C cargo test -p bars
cargo test -p xtask                                          # assets/integrity
cargo test -p zellij-client web_client_tests -- --exact      # index.html 完整性
```

注意：bars 的部分既有测试断言英文界面文案，运行这些测试时应保证语言为英文
（`env -u ZELLIJ_LANG LC_ALL=C`）。`zellij-i18n` 自身的测试通过
`lang_from` 注入语言，不受环境影响。

## 语言选择

- 插件/程序文本：`ZELLIJ_LANG` → `LC_ALL` → `LC_MESSAGES` → `LANG`，
  取第一个非空变量；值以 `zh` 开头（不区分大小写）→ 简体中文，否则英文。
- 网页：URL `?lang=zh-CN|en`（写入 `localStorage` 的 `zellij-lang`）
  → localStorage → 浏览器语言。
- 任何缺失的键都回退英文原文；`{name}` 占位符在键与译文中必须一致
  （`check`/`report` 会校验）。

## 运行时隔离约定

手工验证构建产物时，用独立 HOME/XDG/`ZELLIJ_SOCKET_DIR` 与非默认端口，
结束后停掉启动的所有进程。长路径下 `ZELLIJ_SOCKET_DIR` 可能超过
Unix socket 107 字节限制，可用短路径（如 `/tmp/<短名>`）。

## 当前覆盖范围（v0.46.0）

- **网页**：登录/令牌弹窗、错误弹窗、断线重连弹窗、auth/connection 错误信息。
- **终端**：bars 状态栏模式标签（锁/窗格/标签页/调整大小/移动/搜索/会话/退出
  及其短形式）、搜索状态文案；相关宽度计算已改用显示宽度。
- 尚未覆盖：bars 第二行动作提示文案（New/Close 等 keymap 表）、
  tab-bar 插件、其他插件与程序本体文本——按同样模式（`tr`/`trf` + 目录）
  逐个补丁增量扩展。
