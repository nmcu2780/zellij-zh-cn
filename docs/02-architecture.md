# 架构设计（任务 2）

## 仓库布局

```
upstream.toml              上游基线：仓库、版本、标签、准确提交
patches/v0.46.0/*.patch    针对该基线的补丁队列（git format-patch 生成，按区域拆分）
i18n/zh-CN.toml            集中译文目录：键 = 英文原文，值 = 简体中文
crates/zellij-i18n/        零依赖查找库（Rust 插件与程序本体共用）
web/i18n.js                网页查找逻辑模板（构建时注入网页所需译文）
tools/zhcn.py              维护工具（仅用 Python 标准库）
docs/                      调查、设计、兼容矩阵、测试记录、维护文档
.work/                     （不提交）上游源码工作区、构建产物、临时测试数据
```

## 语言选择与回退

| 部分 | 选择顺序 | 能否动态切换 |
| --- | --- | --- |
| 插件与程序本体 | `ZELLIJ_LANG` → `LC_ALL` → `LC_MESSAGES` → `LANG`；值以 `zh` 开头视为 `zh-CN`，否则英文 | 按会话服务器进程的环境决定（插件经 WASI `inherit_env` 读取），切换需新建会话 |
| 网页 | URL `?lang=zh-CN|en`（写入 `localStorage`）→ `localStorage` → `navigator.languages` | 刷新页面即生效 |

- 查找键为英文原文，查不到就原样返回英文，因此上游新增或改动的文字自动回退英文，不会显示空白或错误内容。
- 带参数的文字使用命名占位符 `{name}`，如 `trf("Reconnecting in {seconds}s", …)`；占位符必须在译文中原样出现（工具检查）。
- 不翻译：按键名、命令、配置键、协议字段、用户输入、会话名、程序输出、令牌。

## 补丁原则

- 以 `tr("English")` / `t("English")` 包装原有字面量，不改动逻辑；涉及布局的地方使用显示宽度（`unicode-width`）而不是字节长度。
- 补丁按区域拆分（基础设施、网页、各插件、程序本体），减少上游变动时的冲突面。
- 补丁无法干净应用即视为“该上游版本不受支持”，工具拒绝构建并给出恢复提示。

## 构建阶段的版本检测

`tools/zhcn.py` 在应用补丁前：

1. 校验 `.work/zellij` 的 `HEAD` 等于 `upstream.toml` 中的提交；
2. 校验 `patches/v<版本>/` 存在且全部 `git apply --check` 通过；
3. 生成译文表并检查占位符一致性；

任一失败都中止，不产出二进制。独立构建的二进制自带匹配的插件和网页资源；系统安装的 `/usr/bin/zellij` 不受影响。
