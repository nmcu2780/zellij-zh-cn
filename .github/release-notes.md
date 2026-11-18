Zellij 简体中文（非官方）预编译版本，对应上游 **Zellij v0.46.0**（提交 `aedee21`），含 20 个汉化补丁、2067 条译文。

## 下载

| 平台 | 文件 | 验证程度 |
| --- | --- | --- |
| Linux x86_64（静态 musl） | `zellij-zh-x86_64-unknown-linux-musl.tar.gz` | **已实测**：校验和、静态链接、`--version`、中英文界面 |
| Linux aarch64（静态 musl） | `zellij-zh-aarch64-unknown-linux-musl.tar.gz` | 仅验证能构建，**未在 ARM 设备上运行过** |
| macOS Intel | `zellij-zh-x86_64-apple-darwin.tar.gz` | 仅验证能构建，**未在 macOS 上运行过** |
| macOS Apple 芯片 | `zellij-zh-aarch64-apple-darwin.tar.gz` | 仅验证能构建，**未在 macOS 上运行过** |
| Windows x86_64 | 暂未提供 | 构建尚未成功，计划下一版；可按项目 README 自行构建 |

每个压缩包都有同名 `.sha256sum` 校验文件。macOS 下载后如被系统拦截，需要在“系统设置 → 隐私与安全性”里允许，二进制没有做 Apple 签名。

## 使用

解压后直接运行 `zellij`，它与系统里已有的 zellij 互不影响，不需要安装，不会修改你的配置。

- 中文界面：`ZELLIJ_LANG`、`LC_ALL`、`LC_MESSAGES`、`LANG` 之一以 `zh` 开头（例如 `LANG=zh_CN.UTF-8`）。`ZELLIJ_LANG=en` 可切回英文。
- 网页端：在地址后加 `?lang=zh-CN`。
- 回滚：删除解压出来的文件即可。

## 注意

- 只对应上游 v0.46.0；之后的上游版本不会自动变成中文，需要先适配。
- layout-manager 插件的紧凑控制行未翻译；终端输入法（IBus/fcitx）未实测。完整范围见 [覆盖清单](https://github.com/nmcu2780/zellij-zh-cn/blob/main/docs/coverage.md) 与 [测试记录](https://github.com/nmcu2780/zellij-zh-cn/blob/main/docs/05-test-record.md)。
- 本项目与 Zellij 官方无关。
