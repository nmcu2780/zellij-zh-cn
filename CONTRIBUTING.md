# 参与贡献

感谢你愿意改进 Zellij 简体中文。请保持友善、就事论事；这是一个个人维护的小项目，回复可能不及时。

先说清边界：本项目是对上游 Zellij 的**汉化补丁集**，与官方无关。Zellij 本身的缺陷和功能请提到[上游](https://github.com/zellij-org/zellij/issues)。

## 提 Issue 之前

- **译文不准确或不自然**：用“译文建议”模板，给出界面位置、当前译文和你的建议。
- **界面出现错位、截断、点击区域不对**：用“问题反馈”模板，附上终端宽度和 `zellij-zh-cn` 的构建信息（见模板）。
- **某处仍是英文**：先看 [覆盖清单](docs/coverage.md) 和 [已知遗留](docs/05-test-record.md)，有些是有意不译（配置值、命令名、协议字符串等）。

## 改译文（最常见的贡献）

译文集中在 [`i18n/zh-CN.toml`](i18n/zh-CN.toml)：键是英文原文，值是中文。

1. 先读文件头部的**术语表和风格约定**，保持用词一致（如 pane = 窗格、tab = 标签页、session = 会话）。
2. 键必须与代码里的原文逐字一致；带参数的文字用 `{a0}`、`{count}` 这类占位符，**键和译文里的占位符集合必须相同**。
3. 不要翻译：快捷键与修饰键名（Ctrl、Alt、Shift、Esc 等）、`Zellij` 和 `TMUX`、配置键、命令、协议、会话名与路径等用户数据。
4. 简洁为先：状态栏和菜单空间很小，短标签不加句号，省略号用“……”。
5. 校验：

   ```bash
   python3 tools/zhcn.py fetch && python3 tools/zhcn.py apply   # 首次
   python3 tools/zhcn.py report --strict                        # 键与目录必须完全对应
   python3 tools/zhcn.py audit --strict                         # 没有漏包 tr() 的界面字符串
   python3 tools/check_emphasis.py                              # 被高亮的词仍在译文里
   python3 -m unittest discover -s tools/tests                  # 工具测试
   ```

有些译文有**联动约束**：例如欢迎窗口里高亮的词本身也是翻译键，必须出现在对应句子的译文里（见 [测试记录](docs/05-test-record.md)）。改这类条目后请跑 `about` 插件的测试。

## 改代码（补丁）

补丁队列在 `patches/v0.46.0/`，是对上游源码的修改。**不要直接手改 `.patch` 文件**，流程是：

1. `python3 tools/zhcn.py fetch && python3 tools/zhcn.py apply`，得到应用了补丁的 `.work/zellij`（`zh-cn` 分支）。
2. 在 `.work/zellij` 里改代码并提交（只提交源码，不要提交构建产物，如 `*.wasm`、`assets/` 下的生成文件）。
3. 回到本仓库根目录：`python3 tools/zhcn.py export-patches`，再 `python3 tools/zhcn.py check`。
4. 重新构建并实测：`python3 tools/zhcn.py build`（约 7 分钟）。

新增或修改界面文案时：

- 英文字面量必须包进 `tr()` / `trf()`（带参数用 `{a0}`、`{a1}`），不要用 `format!` 拼接英文句子；
- **不要用写死的字符位置给文字上色**（`color_range(1, 6..=10)` 这类写法换成中文就会错位），改用 `color_substring`、`color_keys`（给所有 `<...>` 按键标记上色）或 `combo_text`；
- 有意不译的字符串写入 [`i18n/audit-allow.txt`](i18n/audit-allow.txt) 并注明理由。

原则（详见 [架构文档](docs/02-architecture.md)）：

- 译文只在**显示点**查找，不能进入配置写回、协议或命令；
- 宽度一律按终端单元格计算（中文占 2 格），不要用字节数或字符数；
- 新增的文案优先走 `tr()` / `trf()`，查不到译文必须回退英文；
- 快捷键提示依据实际绑定生成，不要写死按键；
- 不要引入与本功能无关的改动，补丁越小越好适配上游更新。

## 测试

回归必须在**英文环境**跑上游插件测试（这些测试断言英文文案）：

```bash
cd .work/zellij
env -u ZELLIJ_LANG LC_ALL=C cargo test --no-fail-fast -p about -p configuration -p bars
```

在中文环境下这些测试会大量“失败”，这是预期的；中文环境只用来验证中文专属行为。界面改动请附上截图或终端文本，并写明终端宽度。

## 适配新的上游版本

见 [上游维护文档](docs/04-upstream-maintenance.md)。简述：`upstream-status` 看新版本，`probe --tag <版本>` 试探补丁能否应用，然后逐个修复冲突、补译新增文案、构建并回归，最后更新兼容矩阵。**未经实测的版本不会被标记为受支持。**

## 提交 Pull Request

- 一个 PR 只做一件事，说明改了什么、为什么、怎么验证的；
- 不要提交 `.work/`、令牌、会话数据或个人路径；
- 贡献的内容将以本项目的 [MIT 许可证](LICENSE) 发布。
