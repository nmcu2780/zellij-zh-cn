# Zellij 简体中文项目

为 [Zellij](https://github.com/zellij-org/zellij) 提供简体中文界面（网页 + 终端内插件 + 程序本体常见提示）。以"钉住上游版本 + 补丁队列 + 集中译文目录 + 独立构建"的方式维护，不修改系统安装。

## 基线与状态

- 上游：<https://github.com/zellij-org/zellij>（MIT）
- 适配版本：`v0.46.0`，提交 `aedee21cb0d58d716496e7f6c66ba0b6f08045d8`
- 现状：**已实现并构建验证**（19 个补丁、1764 条译文）。详见下方文档。
- 兼容矩阵与未适配版本：见 `docs/04-upstream-maintenance.md`。

## 快速开始

```bash
python3 tools/zhcn.py fetch   # 获取上游基线到 .work/zellij
python3 tools/zhcn.py check   # 校验
python3 tools/zhcn.py build   # 构建 → .work/zellij/target/release/zellij
python3 tools/zhcn.py report  # 译文核对
```

使用、语言切换、回滚：见 `docs/06-install-and-rollback.md`。

## 文档

| 文档 | 内容 |
| --- | --- |
| `docs/01-baseline-investigation.md` | 上游/许可/加载方式调查、方案对比 |
| `docs/02-architecture.md` | 架构：仓库布局、语言选择与回退、补丁原则 |
| `docs/03-build.md` | 工具命令、镜像覆盖、补丁开发流程 |
| `docs/04-upstream-maintenance.md` | 版本检测、兼容矩阵、升级演练、CI |
| `docs/05-test-record.md` | 测试记录与已知遗留 |
| `docs/06-install-and-rollback.md` | 构建、安装、验证、回滚 |
| `docs/coverage.md` | 按区域列出的覆盖清单（已译/未译/不译） |

## 注意

- 本仓库**不包含上游源码副本**；上游源码只在 `.work/`（不提交）中按需获取。
- 补丁无法干净应用的上游版本直接拒绝构建，不会产出半成品；新文字自动回退英文。
- 不替换系统 `/usr/bin/zellij`、不修改用户配置、不遥测、不发数据。
