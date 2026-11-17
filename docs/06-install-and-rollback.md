# 安装、使用与回滚

> 本方案是**独立构建**：产出一个自己的 `zellij` 二进制（上游 v0.46.0 + 汉化补丁），
> 与系统 `/usr/bin/zellij` 并存。不会替换系统包、不改用户配置、不影响
> 正在运行的会话。

## 构建（可复现）

```bash
git clone <本仓库> && cd zellij-zh-cn
python3 tools/zhcn.py fetch    # 拉取上游 v0.46.0（钉住提交）到 .work/zellij
python3 tools/zhcn.py check    # 校验基线、补丁可应用性、译文目录
python3 tools/zhcn.py build    # 完整构建（首次约 6–9 分钟）
# 产物：.work/zellij/target/release/zellij
# 旁边另有 zellij.zh-buildinfo.json（上游提交/补丁/目录哈希，供核对）
```

前置：rustup（自动装 1.95.0 + wasm32-wasip1）、protoc、Python ≥ 3.11。
若 crates.io 不可达，把镜像写进 `.work/cargo-local.toml`（示例见 docs/03-build.md）。

## 安装（二选一，都需先看构建产物再决定）

1. **独立目录**（推荐，最容易回滚）：

   ```bash
   mkdir -p ~/.local/zellij-zh
   cp .work/zellij/target/release/zellij ~/.local/zellij-zh/
   cp .work/zellij/target/release/zellij.zh-buildinfo.json ~/.local/zellij-zh/
   ```

   使用：把 `~/.local/zellij-zh` 放到 PATH 前面，或直接以绝对路径调用。

2. **不动 PATH，按需调用**：只用 `~/.local/zellij-zh/zellij` 启动需要中文的
   会话与 `web` 服务；系统命令行 `zellij` 继续用于其它场景。
   注意：同一 socket 目录下，**以哪个二进制创建会话服务器，就按哪个的
   插件集渲染终端界面**。混用客户端与服务器（不同二进制版本）是上游
   本身不支持的组合，不建议。

## 语言选择

- 终端界面（插件+本体）：按 `ZELLIJ_LANG` → `LC_ALL` → `LC_MESSAGES` → `LANG`
  决定，`zh*` 为中文，否则英文；按会话服务器进程的环境生效，切换需新开会话。
  `ZELLIJ_LANG=en` 可在汉化二进制内切回英文。
- 网页：`?lang=zh-CN|en`（写入 localStorage）→ localStorage → 浏览器语言。

## 验证安装

```bash
~/.local/zellij-zh/zellij --version        # 应显示 zellij 0.46.0
LANG=zh_CN.UTF-8 ~/.local/zellij-zh/zellij  # 新会话看状态栏中文
ZELLIJ_LANG=en ~/.local/zellij-zh/zellij    # 同一二进制切回英文
```

## 回滚

- 停止使用汉化二进制（把它移出 PATH 或删除 `~/.local/zellij-zh/`）即可，
  系统 `/usr/bin/zellij` 从未被改动。
- 已有会话不受安装/卸载影响；由汉化服务器创建的会话如需以英文重建，
  结束会话后用系统 zellij 新建即可。
- 网页端 `localStorage["zellij-lang"]="en"` 或 `?lang=en` 立即回到英文界面。

## 随上游更新

见 docs/04-upstream-maintenance.md：`upstream-status` 列新标签，
`probe --tag` 探测兼容性（只报告不自动适配），适配后更新 `upstream.toml`
基线 + 对应 `patches/v*`。未适配版本明确标为"未适配"，不会构建。

## 范围边界

- 覆盖：网页登录/重连/移动端 UI、状态栏、标签栏、紧凑栏、会话管理
  （含欢迎屏）、右键菜单、share/prompt/multiple-select/strider、
  configuration、about、plugin-manager、layout-manager、窗格边框与
  常见提示、插件权限弹窗。清单见 docs/coverage.md。
- 不翻译：CLI 帮助与命令输出（会被脚本解析）、配置动作名与值、按键名、
  会话/窗格/布局名等用户数据、终端程序输出。
