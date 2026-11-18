# Zellij 简体中文（非官方）

为 [Zellij](https://github.com/zellij-org/zellij) 提供简体中文界面，覆盖：

- **网页客户端**：令牌登录、断线重连、错误提示、移动端界面
- **终端内置界面**：状态栏、紧凑栏、标签栏、快捷键提示、会话管理、设置、关于、插件/布局管理、右键菜单、窗格边框与常见提示

快捷键提示依据实际绑定生成，自定义按键后仍然正确；配置文件、命令、会话名、路径和程序输出保持原样，不会被写入中文。

> 本项目与 Zellij 官方无关，是独立维护的汉化补丁集。

## 它是怎么工作的

不是替换系统里的 zellij，也不是改二进制。仓库里只有补丁和译文，不含上游源码：

1. 取上游 **固定版本**的源码；
2. 应用 `patches/` 里的补丁（给界面文案加上翻译查找）；
3. 用 `i18n/zh-CN.toml` 里的译文目录构建出一个独立的 `zellij`。

查不到译文的文案自动显示英文。系统的 `/usr/bin/zellij`、你的配置和正在运行的会话都不会被修改。

## 支持的版本

| 上游版本 | 状态 |
| --- | --- |
| v0.46.0 | **已适配并验证** |
| 其他版本 | 未适配。补丁无法干净应用时，构建会直接拒绝，不会产出半成品 |

Zellij 更新后，本项目**不会自动变成中文**：需要先适配并验证新版本。可用 `python3 tools/zhcn.py upstream-status` 查看上游新版本、`probe --tag <版本>` 试探兼容性。详见 [上游维护文档](docs/04-upstream-maintenance.md)。

## 构建与使用

需要：rustup（自动安装 1.95.0 与 wasm 目标）、protoc、Python ≥ 3.11、git。完整构建约 6–9 分钟。

```bash
git clone https://github.com/nmcu2780/zellij-zh-cn && cd zellij-zh-cn
python3 tools/zhcn.py fetch    # 获取固定版本的上游源码到 .work/
python3 tools/zhcn.py check    # 校验基线、补丁与译文目录
python3 tools/zhcn.py build    # 构建 → .work/zellij/target/release/zellij
```

语言选择：

- 终端内：按 `ZELLIJ_LANG` → `LC_ALL` → `LC_MESSAGES` → `LANG` 决定，`zh*` 为中文；`ZELLIJ_LANG=en` 切回英文（按会话服务器进程的环境生效，需新开会话）。
- 网页：`?lang=zh-CN` 或 `?lang=en`，其次浏览器语言。

Arch 用户可参考 [`packaging/arch/PKGBUILD`](packaging/arch/PKGBUILD)（草案，尚未经完整 `makepkg` 验证），它把结果安装为独立命令 `zellij-zh`，不覆盖系统的 `zellij`。

安装位置、验证与**回滚**步骤见 [安装与回滚](docs/06-install-and-rollback.md)。

## 已知限制

- 只测过 v0.46.0，且主要在 Linux 终端与无头浏览器中验证；**终端输入法（IBus/fcitx）未验证**。
- 设置页里少数哨兵文案（如 `(not set)`、`(bundled font)`）和配置枚举值保持英文，这是有意的。
- 命令行帮助和 `zellij ls` 等脚本会解析的命令输出不翻译。
- 完整列表见 [测试记录](docs/05-test-record.md) 与 [覆盖清单](docs/coverage.md)。

## 文档

| 文档 | 内容 |
| --- | --- |
| [01-baseline-investigation](docs/01-baseline-investigation.md) | 上游、许可与加载方式调查，方案对比 |
| [02-architecture](docs/02-architecture.md) | 仓库布局、语言选择与回退、补丁原则 |
| [03-build](docs/03-build.md) | 工具命令、镜像、补丁开发流程 |
| [04-upstream-maintenance](docs/04-upstream-maintenance.md) | 版本检测、兼容矩阵、升级演练、CI |
| [05-test-record](docs/05-test-record.md) | 测试记录与已知遗留 |
| [06-install-and-rollback](docs/06-install-and-rollback.md) | 安装、验证、回滚 |
| [coverage](docs/coverage.md) | 按区域的翻译覆盖清单 |
| [TASKS](docs/TASKS.md) | 项目最初的任务书（历史记录） |

## 许可证

[MIT](LICENSE)。补丁基于上游 Zellij（MIT，Copyright (c) 2020 Zellij contributors），其版权声明已保留。本项目不包含任何第三方汉化项目的代码。
