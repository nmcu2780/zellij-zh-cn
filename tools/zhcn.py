#!/usr/bin/env python3
"""zellij-zh-cn 维护工具（仅使用 Python 标准库）。

子命令：
  fetch           按 upstream.toml 把上游源码取到 .work/zellij 并核对提交
  check           校验基线提交、补丁可应用性、译文目录合法性
  apply           重置工作区、git am 应用补丁、生成译文产物、刷新 assets
  build           check + apply + cargo xtask ci build-release（--target 交叉构建）
  package         把某目标平台的产物打成压缩包并生成 sha256
  export-patches  把 zh-cn 分支的提交导出为补丁队列
  report          对比代码中使用的键与译文目录
  gen-rust        生成 Rust 译文目录文件
  gen-web         生成网页 i18n.js（供 apply 调用，也可单独调试）
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = REPO_ROOT / ".work"
ZELLIJ_DIR_NAME = "zellij"
CATALOG_PATH = REPO_ROOT / "i18n" / "zh-CN.toml"
CARGO_LOCAL_CONFIG = WORK_DIR / "cargo-local.toml"
I18N_CRATE_SRC = REPO_ROOT / "crates" / "zellij-i18n"
WEB_I18N_TEMPLATE = REPO_ROOT / "web" / "i18n.js"
WEB_CATALOG_MARKER = "/*__ZELLIJ_I18N_CATALOG__*/"

# report/gen-web 的 JS 扫描排除：生成的 bundle、注入的 i18n.js、第三方文件
JS_EXCLUDE = {"app.js", "i18n.js", "integrity.json"}

RUST_KEY_RE = re.compile(r'\b(?:tr|trf|tr_ctx)\s*\(\s*"((?:[^"\\]|\\.)*)"', re.S)
# t(...) 调用（含 zellijI18n.t(...)），在调用括号内取所有字符串字面量作键
JS_CALL_RE = re.compile(r"(?<![\w$])t\s*\(")
JS_STR_RE = re.compile(r"(['\"])((?:\\.|(?!\1).)*?)\1")


def js_call_arg_text(line: str, open_paren: int) -> str:
    """从 `t(` 的左括号位置开始，引号感知地扫描到匹配的右括号。"""
    depth = 1
    i = open_paren + 1
    quote = None
    while i < len(line):
        c = line[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        else:
            if c in "'\"`":
                quote = c
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return line[open_paren + 1 : i]
        i += 1
    return line[open_paren + 1 :]
PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def eprint(*args):
    print(*args, file=sys.stderr)


def run(cmd, cwd=None, env=None, capture=False):
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=capture,
    )
    if capture:
        return result
    if result.returncode != 0:
        raise SystemExit(f"命令执行失败（退出码 {result.returncode}）：{' '.join(map(str, cmd))}")
    return result


def git(*args, cwd, env=None):
    return run(["git", *args], cwd=cwd, env=env, capture=True)


def load_upstream() -> dict:
    path = REPO_ROOT / "upstream.toml"
    if not path.is_file():
        raise SystemExit(f"缺少 {path}，无法确定上游基线。")
    with path.open("rb") as f:
        data = tomllib.load(f)
    return data["upstream"]


def workdir(args) -> Path:
    return Path(args.workdir).resolve() if getattr(args, "workdir", None) else WORK_DIR / ZELLIJ_DIR_NAME


def patches_dir(upstream: dict) -> Path:
    return REPO_ROOT / upstream["patches"]


# ── 译文目录 ──────────────────────────────────────────────────────────────


def placeholder_set(text: str) -> set:
    return set(PLACEHOLDER_RE.findall(text))


def load_catalog(path: Path = CATALOG_PATH):
    """读取并校验译文目录。返回 (entries, errors)；entries 为 dict。"""
    errors = []
    try:
        with path.open("rb") as f:
            raw = tomllib.load(f)
    except FileNotFoundError:
        return None, [f"译文目录不存在：{path}"]
    except tomllib.TOMLDecodeError as e:
        return None, [f"译文目录不是合法 TOML：{e}"]

    if not isinstance(raw, dict):
        return None, ["译文目录必须是平铺的键值表"]

    entries = {}
    for key, value in raw.items():
        if not isinstance(value, str):
            errors.append(f"目录项 {key!r} 的值不是字符串")
            continue
        if not value.strip():
            errors.append(f"目录项 {key!r} 的译文为空")
            continue
        if placeholder_set(key) != placeholder_set(value):
            errors.append(
                f"目录项 {key!r} 占位符不一致：键 {sorted(placeholder_set(key))}，"
                f"值 {sorted(placeholder_set(value))}"
            )
            continue
        entries[key] = value
    return entries, errors


def validate_catalog() -> dict:
    entries, errors = load_catalog()
    if errors:
        for e in errors:
            eprint(f"目录错误：{e}")
        raise SystemExit(
            "译文目录校验失败：上游不受支持或目录不兼容，已拒绝构建。"
            "系统安装的 zellij 不受影响。请修正 i18n/zh-CN.toml 后重试。"
        )
    return entries


# ── cargo 镜像覆盖 ────────────────────────────────────────────────────────


def cargo_env() -> dict:
    """嵌套 cargo 调用用的环境：xtask 会再 spawn `cargo`，--config 传不进去，
    而 source 替换也不能用 CARGO_SOURCE_* 环境变量表达，所以把
    .work/cargo-local.toml 软链到 .work/.cargo/config.toml —— cargo 的
    目录级配置发现会覆盖 .work/ 下的一切调用。"""
    env = dict(os.environ)
    link_dir = WORK_DIR / ".cargo"
    link = link_dir / "config.toml"
    if CARGO_LOCAL_CONFIG.is_file():
        try:
            with CARGO_LOCAL_CONFIG.open("rb") as f:
                tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            eprint(f"警告：{CARGO_LOCAL_CONFIG} 不是合法 TOML（{e}），忽略本地镜像覆盖")
            return env
        link_dir.mkdir(parents=True, exist_ok=True)
        if not (link.is_symlink() and os.readlink(link) == "../cargo-local.toml"):
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to("../cargo-local.toml")
    elif link.is_symlink():
        link.unlink()
    return env


def cargo_prefix_args() -> list:
    """cargo 顶层调用附加的 --config 参数（子命令之前的全局选项）。"""
    if CARGO_LOCAL_CONFIG.is_file():
        return ["--config", str(CARGO_LOCAL_CONFIG)]
    return []


def cargo_cmd(*args) -> list:
    return ["cargo", *cargo_prefix_args(), *args]


# ── 子命令 ────────────────────────────────────────────────────────────────


def cmd_fetch(args) -> int:
    up = load_upstream()
    tag = args.tag or up["tag"]
    commit = args.commit or up["commit"]
    wd = workdir(args)
    wd.parent.mkdir(parents=True, exist_ok=True)

    if not (wd / ".git").exists():
        eprint(f">> 克隆 {up['repo']}（{tag}）到 {wd}")
        run(["git", "clone", "--depth", "1", "--branch", tag, up["repo"], str(wd)])
    else:
        eprint(f">> 在 {wd} 中拉取 {tag}")
        res = git("fetch", "--depth", "1", "origin", "tag", tag, cwd=wd)
        if res.returncode != 0:
            # 浅克隆里可能没有 tag 引用，退化为直接取提交
            res = git("fetch", "--depth", "1", "origin", commit, cwd=wd)
            if res.returncode != 0:
                eprint(res.stderr)
                raise SystemExit(f"获取上游 {tag} 失败")

    res = git("checkout", "-f", commit, cwd=wd)
    if res.returncode != 0:
        eprint(res.stderr)
        raise SystemExit(f"无法检出基线提交 {commit}")

    head = git("rev-parse", "HEAD", cwd=wd).stdout.strip()
    if head != commit:
        raise SystemExit(f"基线校验失败：HEAD={head}，期望 {commit}")
    eprint(f">> 上游就绪：{wd} @ {head[:12]}")
    return 0


def _check_head(wd: Path, commit: str):
    if not (wd / ".git").exists():
        raise SystemExit(f"上游源码不存在：{wd}。请先运行 tools/zhcn.py fetch")
    head = git("rev-parse", "HEAD", cwd=wd).stdout.strip()
    # HEAD 必须在基线提交上，或是由其派生的 zh-cn 补丁分支
    derived = git("merge-base", "--is-ancestor", commit, "HEAD", cwd=wd)
    if head != commit and derived.returncode != 0:
        raise SystemExit(
            f"上游基线不匹配：HEAD={head}，期望 {commit}。\n"
            "该上游版本不受支持，已拒绝构建。系统安装的 zellij 不受影响。\n"
            "恢复步骤：先运行 tools/zhcn.py fetch 重新获取基线，"
            "或将 upstream.toml 更新为受支持版本后重新适配补丁。"
        )


def _check_patches_apply(wd: Path, pdir: Path, commit: str):
    """在临时索引上按顺序 git apply --check，不碰工作区。"""
    patches = sorted(pdir.glob("*.patch"))
    if not patches:
        raise SystemExit(f"补丁目录为空：{pdir}")
    with tempfile.TemporaryDirectory() as td:
        index = Path(td) / "index"
        env = dict(os.environ, GIT_INDEX_FILE=str(index))
        res = git("read-tree", commit, cwd=wd, env=env)
        if res.returncode != 0:
            raise SystemExit(f"无法建立临时索引：{res.stderr}")
        for patch in patches:
            res = git("apply", "--check", "--cached", str(patch), cwd=wd, env=env)
            if res.returncode != 0:
                raise SystemExit(
                    f"补丁无法干净应用：{patch.name}\n{res.stderr}\n"
                    "该上游版本与补丁队列不兼容，已拒绝构建。"
                    "系统安装的 zellij 不受影响。\n"
                    "恢复步骤：确认 .work/zellij 处于基线提交（tools/zhcn.py fetch），"
                    "或更新补丁队列以匹配 upstream.toml 中的基线。"
                )
            # 应用到临时索引，让后续补丁按顺序叠加校验
            res = git("apply", "--cached", str(patch), cwd=wd, env=env)
            if res.returncode != 0:
                raise SystemExit(f"补丁叠加失败：{patch.name}\n{res.stderr}")
    eprint(f">> {len(patches)} 个补丁均可干净应用")


def cmd_check(args) -> int:
    up = load_upstream()
    wd = workdir(args)
    _check_head(wd, up["commit"])
    pdir = patches_dir(up)
    if not pdir.is_dir():
        raise SystemExit(f"补丁目录不存在：{pdir}")
    _check_patches_apply(wd, pdir, up["commit"])
    validate_catalog()
    eprint(">> check 通过：基线、补丁、译文目录均有效")
    return 0


# apply/build 会重置上游工作区。这些已跟踪路径由构建重新生成，其改动
# 可以安全丢弃；其余已跟踪改动（以及 zh-cn 分支上未导出的提交）都会导致拒绝。
REGENERATED_TRACKED = [
    re.compile(r"zellij-client/assets/(app\.js|index\.html|integrity\.json)$"),
    re.compile(r"zellij-utils/assets/plugins/.*\.wasm$"),
]


def _check_worktree_clean(wd: Path):
    res = git("status", "--porcelain=v1", "--untracked-files=no", cwd=wd)
    if res.returncode != 0:
        raise SystemExit(f"无法读取工作区状态：{res.stderr}")
    dirty = []
    for line in res.stdout.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip('"')
        if not any(p.search(path) for p in REGENERATED_TRACKED):
            dirty.append(line)
    if dirty:
        raise SystemExit(
            "上游工作区存在未提交的已跟踪改动，已拒绝 apply/build：\n  "
            + "\n  ".join(dirty)
            + "\n请先提交改动并用 tools/zhcn.py export-patches 导出补丁，"
            "或确认可丢弃后加 --force。系统安装的 zellij 不受影响。"
        )


def _check_branch_matches_patches(wd: Path, commit: str, pdir: Path):
    if git("rev-parse", "--verify", "--quiet", "zh-cn", cwd=wd).returncode != 0:
        return  # 分支还不存在，首次 apply
    ahead = git("rev-list", "--count", f"{commit}..zh-cn", cwd=wd)
    if ahead.returncode == 0 and ahead.stdout.strip() == "0":
        return  # 分支停在基线上（例如上次 apply 失败后恢复的结果），没有可丢失的工作

    def norm(text: str) -> str:
        return "\n".join(
            line for line in text.splitlines() if not line.startswith("Date: ")
        ).strip()

    res = git(
        "format-patch", "--zero-commit", "--no-signature", "--stdout",
        f"{commit}..zh-cn", cwd=wd,
    )
    if res.returncode != 0:
        raise SystemExit(f"无法导出 zh-cn 分支进行比对：{res.stderr}")
    branch_side = norm(res.stdout)
    patch_side = norm("\n".join(
        p.read_text(encoding="utf-8") for p in sorted(pdir.glob("*.patch"))
    ))
    if branch_side != patch_side:
        raise SystemExit(
            "zh-cn 分支与已导出的补丁队列不一致：分支上可能有未导出的"
            "提交或过期改动，已拒绝 apply/build 以防丢失工作。\n"
            "恢复步骤：先运行 tools/zhcn.py export-patches 导出，"
            "或把 zh-cn 恢复到与补丁一致；确认可丢弃后加 --force。"
            "系统安装的 zellij 不受影响。"
        )


def cmd_apply(args) -> int:
    up = load_upstream()
    wd = workdir(args)
    commit = up["commit"]
    if not (wd / ".git").exists():
        raise SystemExit(f"上游源码不存在：{wd}。请先运行 tools/zhcn.py fetch")
    # apply 会重置工作区，只要求基线提交存在于仓库中（HEAD 可在 zh-cn 上）
    res = git("cat-file", "-e", f"{commit}^{{commit}}", cwd=wd)
    if res.returncode != 0:
        raise SystemExit(
            f"仓库中不存在基线提交 {commit}。请先运行 tools/zhcn.py fetch"
        )

    pdir = patches_dir(up)
    patches = sorted(pdir.glob("*.patch"))
    if not patches:
        raise SystemExit(f"补丁目录为空：{pdir}")

    if not getattr(args, "force", False):
        _check_worktree_clean(wd)
        _check_branch_matches_patches(wd, commit, pdir)

    eprint(">> 重置工作区到基线提交")
    res = git("checkout", "-f", "-B", "zh-cn", commit, cwd=wd)
    if res.returncode != 0:
        raise SystemExit(f"无法重置到基线：{res.stderr}")
    res = git("clean", "-fdx", "-e", "target", cwd=wd)
    if res.returncode != 0:
        raise SystemExit(f"清理工作区失败：{res.stderr}")

    eprint(f">> 应用 {len(patches)} 个补丁（git am）")
    # 提供固定的提交身份：干净环境（CI、新机器）没有全局 git 身份，
    # git am 会因“无法自动探测邮件地址”而失败。补丁自带作者信息，不受影响。
    res = git(
        "-c", "user.name=zellij-zh-cn",
        "-c", "user.email=zellij-zh-cn@localhost",
        "am", *[str(p) for p in patches], cwd=wd,
    )
    if res.returncode != 0:
        eprint(res.stderr)
        git("am", "--abort", cwd=wd)
        raise SystemExit(
            "补丁应用失败，已中止并恢复 zh-cn 分支到基线。\n"
            "原因见上方 git 输出：若提示冲突或 patch does not apply，则该上游版本与补丁队列不兼容，"
            "已拒绝构建；其他提示多为环境问题。系统安装的 zellij 不受影响。"
        )

    # 拷贝 zellij-i18n crate 并生成 Rust 译文目录
    crate_dst = wd / "zellij-i18n"
    if crate_dst.exists():
        shutil.rmtree(crate_dst)
    shutil.copytree(I18N_CRATE_SRC, crate_dst)
    entries = validate_catalog()
    gen_rust_catalog(entries, crate_dst / "src" / "catalog_generated.rs")
    eprint(">> 已拷贝 zellij-i18n 并生成 Rust 译文目录")

    # 生成网页 i18n.js（只注入网页实际用到的键）
    web_keys = extract_js_keys(wd)
    gen_web_i18n(entries, web_keys, wd / "zellij-client" / "assets" / "i18n.js")
    eprint(f">> 已生成 i18n.js（{len(web_keys)} 个网页键）")

    eprint(">> 重新打包网页资源（cargo xtask assets）")
    res = subprocess.run(
        cargo_cmd("xtask", "assets"), cwd=wd, env=cargo_env(), text=True
    )
    if res.returncode != 0:
        raise SystemExit(f"cargo xtask assets 失败（退出码 {res.returncode}）")
    eprint(">> apply 完成")
    return 0


def build_output_dir(wd: Path, target: str | None) -> Path:
    """二进制所在目录：本机构建与 Windows 原生构建在 target/release，其余交叉构建在 target/<目标>/release。"""
    if target is None or "windows" in target:
        return wd / "target" / "release"
    return wd / "target" / target / "release"


def binary_names(target: str | None) -> list[str]:
    windows = bool(target and "windows" in target) or (target is None and os.name == "nt")
    if windows:
        return ["zellij.exe", "zellij-terminal.exe"]
    return ["zellij"]


def cmd_build(args) -> int:
    cmd_check(args)
    cmd_apply(args)
    up = load_upstream()
    wd = workdir(args)
    target = getattr(args, "target", None)
    env = cargo_env()
    if target is None:
        eprint(">> 开始 release 构建（cargo xtask ci build-release）")
        command = cargo_cmd("xtask", "ci", "build-release")
    elif "windows" in target:
        # 与上游发布一致：Windows 原生构建并静态链接 CRT
        eprint(f">> 开始 Windows 原生 release 构建（{target}）")
        env = dict(env, RUSTFLAGS="-C target-feature=+crt-static")
        command = cargo_cmd("xtask", "ci", "build-release")
    else:
        # 与上游发布一致：musl（Linux）与 macOS 走 cargo xtask ci cross
        eprint(f">> 开始交叉构建（cargo xtask ci cross {target}）")
        command = cargo_cmd("xtask", "ci", "cross", target)
    res = subprocess.run(command, cwd=wd, env=env)
    if res.returncode != 0:
        raise SystemExit(f"构建失败（退出码 {res.returncode}）")
    out_dir = build_output_dir(wd, target)
    binaries = [out_dir / name for name in binary_names(target)]
    for binary in binaries:
        if not binary.is_file():
            raise SystemExit(f"构建结束但未找到二进制：{binary}")
    write_buildinfo(up, binaries[0], target)
    print(f"构建完成：{binaries[0]}")
    return 0


PACKAGE_README = """Zellij 简体中文（非官方）预编译版本

这是对上游 Zellij {version} 打上汉化补丁后的构建（{target}）。
项目主页：https://github.com/nmcu2780/zellij-zh-cn

使用
  直接运行本目录里的 zellij。它与系统里已有的 zellij 互不影响；不需要安装，
  不会修改你的配置。
  中文界面：环境变量 ZELLIJ_LANG、LC_ALL、LC_MESSAGES、LANG 之一以 zh 开头即可
  （例如 LANG=zh_CN.UTF-8）。Windows 默认没有这些变量，请设置 ZELLIJ_LANG=zh-CN。
  ZELLIJ_LANG=en 可切回英文。
  网页端：在地址后加 ?lang=zh-CN。

核对
  zellij --version 应显示 {version}。zellij.zh-buildinfo.json 记录了上游提交、补丁与
  译文目录的哈希。sha256 校验文件与压缩包一起发布。

回滚
  删除本目录即可；系统安装与你的配置从未被修改。

限制
  只对应上游 {version}；其他版本请自行构建（见项目主页）。
  不同系统的验证程度不同，见发布页的说明。
"""


def cmd_package(args) -> int:
    """把构建产物打成压缩包并生成 sha256 校验文件（仅用标准库，跨平台）。"""
    import hashlib
    import tarfile
    import zipfile

    up = load_upstream()
    wd = workdir(args)
    target = args.target
    out_dir = Path(args.source).resolve() if getattr(args, "source", None) else build_output_dir(wd, target)
    names = binary_names(target)
    for name in names:
        if not (out_dir / name).is_file():
            raise SystemExit(f"找不到 {out_dir / name}，请先运行 tools/zhcn.py build --target {target}")
    info = out_dir / (names[0] + ".zh-buildinfo.json")
    if not info.is_file():
        raise SystemExit(f"找不到 {info}")
    dest = Path(args.out).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    readme = PACKAGE_README.format(version=up["version"], target=target)
    windows = "windows" in target
    base = f"zellij-zh-{target}"
    archive = dest / (base + (".zip" if windows else ".tar.gz"))
    members = [(out_dir / n, n) for n in names] + [
        (info, "zellij.zh-buildinfo.json"),
        (REPO_ROOT / "LICENSE", "LICENSE"),
    ]
    if windows:
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for path, arc in members:
                z.write(path, arc)
            z.writestr("README.txt", readme)
    else:
        with tarfile.open(archive, "w:gz") as t:
            for path, arc in members:
                t.add(path, arcname=arc)
            data = readme.encode("utf-8")
            ti = tarfile.TarInfo("README.txt")
            ti.size = len(data)
            ti.mode = 0o644
            import io
            t.addfile(ti, io.BytesIO(data))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = dest / (base + ".sha256sum")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"已生成 {archive}（sha256 {digest[:16]}…）")
    return 0


def write_buildinfo(up: dict, binary: Path, target: str | None = None):
    """在二进制旁写 zellij.zh-buildinfo.json，记录本次构建的基线、
    补丁与译文目录的哈希，便于核对与汇报。"""
    import datetime
    import hashlib

    def sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    pdir = patches_dir(up)
    info = {
        "upstream_repo": up["repo"],
        "upstream_version": up["version"],
        "upstream_tag": up["tag"],
        "upstream_commit": up["commit"],
        "target": target or "host",
        "patch_dir": str(pdir.relative_to(REPO_ROOT)),
        "patches": {p.name: sha256(p) for p in sorted(pdir.glob("*.patch"))},
        "catalog_sha256": sha256(CATALOG_PATH),
        "tool_sha256": sha256(Path(__file__).resolve()),
        "built_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    out = binary.with_name(binary.name + ".zh-buildinfo.json")
    out.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_export_patches(args) -> int:
    up = load_upstream()
    wd = workdir(args)
    pdir = patches_dir(up)
    pdir.mkdir(parents=True, exist_ok=True)
    for old in pdir.glob("*.patch"):
        old.unlink()
    forbidden = (
        subprocess.run(
            ["git", "-C", str(wd), "diff", "--name-only",
             f"{up['commit']}..zh-cn", "--",
             "zellij-utils/assets/plugins/",
             "zellij-client/assets/app.js",
             "zellij-client/assets/integrity.json"],
            capture_output=True, text=True,
        ).stdout.split()
    )
    if forbidden:
        raise SystemExit(
            "拒绝导出：以下构建产物不应进入补丁队列（由 cargo xtask assets / 插件构建再生成）：\n  "
            + "\n  ".join(forbidden)
            + "\n请从历史中移除这些文件改动（如 git rebase -i 删除或 git checkout <上游> -- <路径> 后 amend），再重新导出。"
        )
    res = git(
        "format-patch",
        f"{up['commit']}..zh-cn",
        "--zero-commit",
        "--no-signature",
        "-o",
        str(pdir),
        cwd=wd,
    )
    if res.returncode != 0:
        raise SystemExit(f"导出补丁失败：{res.stderr}")
    exported = sorted(p.name for p in pdir.glob("*.patch"))
    for name in exported:
        print(name)
    return 0


# ── 键提取 ────────────────────────────────────────────────────────────────


def iter_rust_files(wd: Path):
    roots = [wd / "default-plugins"] + sorted(wd.glob("zellij-*/src"))
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.rs"):
            parts = set(path.parts)
            if "tests" in parts or "test" in parts:
                continue
            yield path


def extract_rust_keys(wd: Path) -> dict:
    """返回 {key: [位置]}。"""
    used = {}
    for path in iter_rust_files(wd):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        # 跳过测试模块（定位 #[cfg(test)] 后的 mod test*；个别文件中部有
        # cfg(test) 辅助函数，不能用第一个标记截断）
        marker = re.search(r"#\[cfg\(test\)\]\s*\n\s*(?:pub\s*(?:\(crate\)\s*)?)?mod\s+test", text)
        if marker:
            text = text[: marker.start()]
        for m in RUST_KEY_RE.finditer(text):
            key = m.group(1)
            lineno = text.count("\n", 0, m.start()) + 1
            used.setdefault(key, []).append(
                f"{path.relative_to(wd)}:{lineno}"
            )
    return used


def iter_js_files(wd: Path):
    assets = wd / "zellij-client" / "assets"
    if not assets.is_dir():
        return
    for path in sorted(assets.glob("*.js")):
        name = path.name
        if name in JS_EXCLUDE or name.startswith("addon-") or name.startswith("xterm"):
            continue
        yield path


def extract_js_keys(wd: Path) -> dict:
    used = {}
    for path in iter_js_files(wd):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for call in JS_CALL_RE.finditer(line):
                args = js_call_arg_text(line, call.end() - 1)
                for m in JS_STR_RE.finditer(args):
                    used.setdefault(m.group(2), []).append(
                        f"{path.relative_to(wd)}:{lineno}"
                    )
    return used


CONFIG_LABEL_RE = re.compile(r'(?:item|toggled_label)(?:\s+|=)"([^"]+)"')


def extract_config_labels(wd: Path) -> dict:
    """context-menu 等插件的用户可见标签来自内置 default.kdl。"""
    used = {}
    cfg = wd / "zellij-utils" / "assets" / "config" / "default.kdl"
    if cfg.is_file():
        for lineno, line in enumerate(cfg.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("//"):
                continue
            for m in CONFIG_LABEL_RE.finditer(line):
                used.setdefault(m.group(1), []).append(
                    f"{cfg.relative_to(wd)}:{lineno}"
                )
    return used


def unescape_rust(s: str) -> str:
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n == "\n":
                # Rust 续行：反斜杠+换行会吞掉下一行的前导空白
                i += 2
                while i < len(s) and s[i] in " \t\n\r":
                    i += 1
                continue
            mapping = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'"}
            if n in mapping:
                out.append(mapping[n])
                i += 2
                continue
        out.append(c)
        i += 1
    return "".join(out)


# ── 上游更新检测 ──────────────────────────────────────────────────────────

TAG_RE = re.compile(r"refs/tags/(v(\d+)\.(\d+)\.(\d+))\^\{\}$")


def list_remote_tags(repo: str):
    """返回 {tag: (commit, (major, minor, patch))}，按版本排序。"""
    res = run(["git", "ls-remote", "--tags", repo], capture=True)
    if res.returncode != 0:
        raise SystemExit(f"无法查询上游标签：{res.stderr}")
    tags = {}
    for line in res.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        m = TAG_RE.match(ref)
        if m:
            tags[m.group(1)] = (sha, tuple(int(g) for g in m.groups()[1:]))
    return dict(sorted(tags.items(), key=lambda kv: kv[1][1]))


def cmd_upstream_status(args) -> int:
    up = load_upstream()
    tags = list_remote_tags(up["repo"])
    base_v = up["version"].lstrip("v")
    base = tuple(int(x) for x in base_v.split("."))
    rows = []
    for tag, (sha, ver) in tags.items():
        if ver < base:
            continue
        supported = (REPO_ROOT / "patches" / tag).is_dir()
        mark = "基线" if tag == up["tag"] else ("已适配" if supported else "未适配")
        rows.append({"tag": tag, "commit": sha, "status": mark})
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            print(f"{r['tag']:<12} {r['status']}  {r['commit'][:12]}")
    return 0


def files_touched_by_patches(pdir: Path):
    """补丁队列触及的文件（diff 头中的 +++/--- 路径）。"""
    files = set()
    for patch in sorted(pdir.glob("*.patch")):
        for line in patch.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^[+-]{3} [ab]/(.*)$", line)
            if m and m.group(1) != "dev/null":
                files.add(m.group(1))
    return files


CANDIDATE_RE = re.compile(r'"([A-Za-z][^"\\]{4,90})"')
CANDIDATE_SKIP_RE = re.compile(r"[\{\}\\/:=@]|\b(http|file|wss?)\b")
CANDIDATE_WORDS = re.compile(r"[a-z]+ [a-zA-Z]|[A-Z][a-z]+ [a-zA-Z]")


def collect_candidates(wd: Path) -> dict:
    """启发式收集“可能是界面文字”的英文字符串（用于版本间差异报告，
    不是覆盖率统计，会产生误报/漏报）。"""
    found = {}

    def add(key, loc):
        if " " not in key or CANDIDATE_SKIP_RE.search(key):
            return
        if not CANDIDATE_WORDS.search(key):
            return
        found.setdefault(key, loc)

    for path in iter_rust_files(wd):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        marker = re.search(r"#\[cfg\(test\)\]\s*\n\s*(?:pub\s*(?:\(crate\)\s*)?)?mod\s+test", text)
        if marker:
            text = text[: marker.start()]
        for m in CANDIDATE_RE.finditer(text):
            add(m.group(1), str(path.relative_to(wd)))
    for path in iter_js_files(wd):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for m in CANDIDATE_RE.finditer(text):
            add(m.group(1), str(path.relative_to(wd)))
    for key, locs in extract_config_labels(wd).items():
        add(key, locs[0])
    return found


def crate_version(wd: Path, crate: str):
    toml_path = wd / crate / "Cargo.toml"
    if not toml_path.is_file():
        return None
    try:
        with toml_path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError:
        return None
    v = data.get("package", {}).get("version")
    if v in (None, "", "workspace"):
        root = wd / "Cargo.toml"
        with root.open("rb") as f:
            v = tomllib.load(f).get("workspace", {}).get("package", {}).get("version")
    return v


def cmd_probe(args) -> int:
    """探测某个上游标签与当前补丁队列/译文的兼容性（只读，不构建）。"""
    up = load_upstream()
    tag = args.tag
    base_commit = up["commit"]
    base_wd = workdir(args)
    pdir = patches_dir(up)
    if not pdir.is_dir():
        raise SystemExit(f"补丁目录不存在：{pdir}")

    probe_wd = Path(args.probe_workdir or WORK_DIR / f"probe-{tag}").resolve()
    probe_wd.parent.mkdir(parents=True, exist_ok=True)
    if not (probe_wd / ".git").exists():
        eprint(f">> 克隆 {tag} 到 {probe_wd}")
        run(["git", "clone", "--depth", "1", "--branch", tag, up["repo"], str(probe_wd)])
    else:
        run(["git", "fetch", "--depth", "1", "origin", "tag", tag], cwd=probe_wd)
    res = git("checkout", "-f", tag, cwd=probe_wd)
    if res.returncode != 0:
        raise SystemExit(f"无法检出 {tag}：{res.stderr}")
    probe_commit = git("rev-parse", "HEAD", cwd=probe_wd).stdout.strip()

    # 基线侧候选集：取基线提交到独立 worktree（不污染 zh-cn 分支）
    base_tree = WORK_DIR / "probe-baseline"
    res = git("fetch", "--depth", "1", "origin", base_commit, cwd=probe_wd)
    if res.returncode != 0:
        raise SystemExit(f"无法在探测仓库获取基线提交：{res.stderr}")
    if base_tree.exists():
        shutil.rmtree(base_tree)
    res = git("worktree", "add", "--detach", str(base_tree), base_commit, cwd=probe_wd)
    if res.returncode != 0:
        raise SystemExit(f"无法建立基线 worktree：{res.stderr}")

    try:
        # 1) 补丁应用
        ok, failed = [], []
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ, GIT_INDEX_FILE=str(Path(td) / "index"))
            git("read-tree", "HEAD", cwd=probe_wd, env=env)
            for patch in sorted(pdir.glob("*.patch")):
                r = git("apply", "--check", "--cached", str(patch), cwd=probe_wd, env=env)
                if r.returncode == 0:
                    ok.append(patch.name)
                    git("apply", "--cached", str(patch), cwd=probe_wd, env=env)
                else:
                    failed.append(patch.name)

        # 2) 补丁触及的文件在上游是否还在
        touched = files_touched_by_patches(pdir)
        created = set()
        for patch in sorted(pdir.glob("*.patch")):
            for m in re.finditer(r"^\+\+\+ b/(.*)$", patch.read_text(), re.M):
                prev = git("show", f"{base_commit}:{m.group(1)}", cwd=base_wd)
                if prev.returncode != 0:
                    created.add(m.group(1))
        missing_files = sorted(
            f for f in touched - created if not (probe_wd / f).exists()
        )

        # 3) 接口版本差异
        iface = {}
        for crate in ("zellij-tile", "zellij-tile-utils", "zellij-utils",
                      "zellij-server", "zellij-client"):
            iface[crate] = {
                "baseline": crate_version(base_tree, crate),
                "probe": crate_version(probe_wd, crate),
            }
        assets_rs = probe_wd / "xtask" / "src" / "assets.rs"
        iface["xtask-assets"] = {
            "has_module_order": "MODULE_ORDER" in assets_rs.read_text() if assets_rs.is_file() else None,
            "has_integrity": "integrity.json" in assets_rs.read_text() if assets_rs.is_file() else None,
        }

        # 4) 文案候选差异（启发式）
        cand_base = collect_candidates(base_tree)
        cand_probe = collect_candidates(probe_wd)
        added = sorted(set(cand_probe) - set(cand_base))
        removed = sorted(set(cand_base) - set(cand_probe))
    finally:
        git("worktree", "remove", "--force", str(base_tree), cwd=probe_wd)

    report = {
        "probe_tag": tag,
        "probe_commit": probe_commit,
        "baseline_commit": base_commit,
        "patches_ok": ok,
        "patches_failed": failed,
        "missing_files": missing_files,
        "interface_versions": iface,
        "strings_added": added,
        "strings_removed": removed,
    }
    out = probe_wd / "PROBE-REPORT.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"探测 {tag}（{probe_commit[:12]}）对比基线 {base_commit[:12]}")
        print(f"补丁应用：{len(ok)} 成功 / {len(failed)} 失败")
        for f in failed:
            print(f"  ✗ {f}")
        if missing_files:
            print(f"补丁触及但上游已删除的文件：{missing_files}")
        for crate, vers in iface.items():
            if isinstance(vers, dict) and "baseline" in vers and vers["baseline"] != vers["probe"]:
                print(f"接口版本变化：{crate} {vers['baseline']} → {vers['probe']}")
        print(f"文案候选差异（启发式，需人工盘点）：+{len(added)} / -{len(removed)}")
        for s in added[:50]:
            print(f"  + {s!r}（{cand_probe[s]}）")
        if len(added) > 50:
            print(f"  …其余 {len(added) - 50} 条见 {out}")
        for s in removed[:20]:
            print(f"  - {s!r}（原位于 {cand_base[s]}）")
        print(f"报告已写入 {out}")
    return 2 if failed or missing_files else 0


def cmd_report(args) -> int:
    up = load_upstream()
    wd = workdir(args)
    entries, errors = load_catalog()
    if entries is None:
        raise SystemExit("译文目录无法解析：" + "；".join(errors))

    # report 扫描的是“已应用补丁”的源码；对未打补丁的上游只会统计到几乎为零的键，
    # 并把整本目录误报为未使用，所以直接拒绝，避免给出假结论。
    if not (wd / "zellij-i18n").is_dir():
        raise SystemExit(
            f"工作区 {wd} 尚未应用补丁，无法对照译文键。请先运行 tools/zhcn.py apply（或 build）。"
        )

    rust_keys = extract_rust_keys(wd)
    js_keys = extract_js_keys(wd)
    used = {}
    for key, locs in rust_keys.items():
        used.setdefault(unescape_rust(key), []).extend(locs)
    for key, locs in js_keys.items():
        used.setdefault(key.replace("\\'", "'").replace('\\"', '"'), []).extend(locs)
    for key, locs in extract_config_labels(wd).items():
        used.setdefault(key, []).extend(locs)

    # 目录本身占位符问题（不参与退出码，validation 已单独报）
    missing = sorted(k for k in used if k not in entries)
    unused = sorted(k for k in entries if k not in used)
    mismatches = []
    for key in sorted(used):
        if key in entries and placeholder_set(key) != placeholder_set(entries[key]):
            mismatches.append(
                {
                    "key": key,
                    "key_placeholders": sorted(placeholder_set(key)),
                    "value_placeholders": sorted(placeholder_set(entries[key])),
                    "locations": used[key],
                }
            )

    if args.json:
        print(
            json.dumps(
                {
                    "missing_translations": missing,
                    "unused_catalog_entries": unused,
                    "placeholder_mismatches": mismatches,
                    "used_key_count": len(used),
                    "catalog_entry_count": len(entries),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"代码中使用键数：{len(used)}，目录条目数：{len(entries)}")
        if missing:
            print(f"\n警告：{len(missing)} 个键没有译文（运行时回退英文）：")
            for k in missing:
                locs = used[k]
                print(f"  - {k!r}（{locs[0]}{' 等' if len(locs) > 1 else ''}）")
        if unused:
            print(f"\n{len(unused)} 个目录条目未被代码使用：")
            for k in unused:
                print(f"  - {k!r}")
        if mismatches:
            print(f"\n错误：{len(mismatches)} 个键占位符不一致：")
            for m in mismatches:
                print(
                    f"  - {m['key']!r}：键 {m['key_placeholders']}，"
                    f"译文 {m['value_placeholders']}（{m['locations'][0]}）"
                )
        if not missing and not unused and not mismatches:
            print("目录与代码完全对应。")

    if mismatches or (getattr(args, "strict", False) and (missing or unused)):
        return 1
    return 0


# ── 漏译审计 ──────────────────────────────────────────────────────────────

AUDIT_ALLOW_PATH = REPO_ROOT / "i18n" / "audit-allow.txt"
# 字符串、行注释、字符字面量（先匹配注释，避免注释中的引号被当成字符串）
AUDIT_TOKEN_RE = re.compile(r'//[^\n]*|"((?:[^"\\]|\\.)*)"|\'(?:\\.|[^\'\\])\'', re.S)
# 字面量之前的上下文中出现这些调用/宏，说明它是已翻译、日志或断言，不属于界面文案
AUDIT_CONTEXT_SKIP_RE = re.compile(
    r"(?:\btr|\btrf|\btr_ctx|\btr_dyn|eprintln!|println!|print!|panic!|assert\w*!|debug_assert\w*!|"
    r"\bwrite!|\bwriteln!|log::\w+!|\b(?:debug|info|warn|error|trace)!|\.expect|unreachable!|todo!|"
    r"include_str!|env!|concat!|\.context|\.with_context|\bBail|\banyhow!|\bbail!)\s*\(\s*$"
)
# 同一条语句里出现这些宏时，其任一参数里的字面量都不是界面文案（如 assert!(cond, "消息")）
AUDIT_STATEMENT_SKIP_RE = re.compile(
    r"(?:eprintln!|println!|print!|panic!|assert\w*!|debug_assert\w*!|unreachable!|todo!|"
    r"log::\w+!|\b(?:debug|info|warn|error|trace)!|\banyhow!|\bbail!)\s*\("
)


def audit_load_allow() -> set:
    """读取白名单：每行一个字面量原文；`file: <路径前缀>` 表示整个文件/目录不审计；`#` 开头为注释。"""
    allow = set()
    if AUDIT_ALLOW_PATH.is_file():
        for line in AUDIT_ALLOW_PATH.read_text(encoding="utf-8").splitlines():
            line = line.rstrip("\n")
            if line and not line.lstrip().startswith("#"):
                allow.add(line)
    return allow


def audit_literal_allowed(literal: str, allow: set) -> bool:
    if literal in allow:
        return True
    return any(a.startswith("re: ") and re.search(a[4:].strip(), literal) for a in allow)


def audit_file_allowed(rel: str, allow: set) -> bool:
    return any(a.startswith("file: ") and rel.startswith(a[6:].strip()) for a in allow)


def audit_looks_like_ui_text(text: str) -> bool:
    """像面向用户的英文文案：含空格的多词短语，或首字母大写的单个英文单词。"""
    if not re.search(r"[A-Za-z]{3}", text):
        return False
    # 纯按键标记（<Ctrl c>、Alt + i、Ctrl g + p）不是可翻译文案
    key_words = r"(?:Ctrl|Alt|Shift|Super|Enter|Esc|Tab|Space|Left|Right|Up|Down|Del|Home|End|ENTER|ESC|TAB|[A-Za-z0-9]|[↑↓←→+/,-])"
    if re.fullmatch(rf"(?:<\s*{key_words}(?:\s*[+ ]\s*{key_words})*\s*>|{key_words}(?:\s*[+ ]\s*{key_words})*)(?:\s*[,+]\s*(?:<[^>]*>|{key_words}))*", text.strip()):
        return False
    # 路径、标识符、URL 等不是文案；多词短语里的下划线（如 "Search: {}_" 的光标）不算标识符
    if re.search(r"[\\/=@#$%^&*|~`]|::|\b(?:https?|wss?|file)\b|\.rs\b|\.kdl\b|\.wasm\b", text):
        return False
    if "_" in text and " " not in text.strip():
        return False
    stripped = text.strip()
    words = re.findall(r"[A-Za-z][A-Za-z'’-]*", stripped)
    if " " in stripped and len(words) >= 2 and any(len(w) >= 3 for w in words):
        return True
    # 单个首字母大写的单词（"Dismiss"），或“单词:”开头的标签（"Search: {}_"）
    return bool(re.fullmatch(r"[A-Z][a-z]{2,}", stripped) or re.match(r"[A-Z][a-z]{2,}:", stripped))


def audit_scan_file(wd: Path, path: Path, entries: dict, allow: set, sites: bool = False) -> list:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    marker = re.search(r"#\[cfg\(test\)\]\s*\n\s*(?:pub\s*(?:\(crate\)\s*)?)?mod\s+\w+", text)
    if marker:
        text = text[: marker.start()]
    found = []
    for m in AUDIT_TOKEN_RE.finditer(text):
        raw = m.group(1)
        if raw is None:
            continue
        literal = unescape_rust(raw)
        if audit_literal_allowed(literal, allow):
            continue
        # 默认只报“目录里也没有”的字面量；sites=True 时连目录里已有、
        # 但此处没包 tr() 的使用点也报（译文存在却不会生效）
        if not sites and (literal in entries or raw in entries):
            continue
        if not audit_looks_like_ui_text(literal):
            continue
        if AUDIT_CONTEXT_SKIP_RE.search(text[max(0, m.start() - 80): m.start()]):
            continue
        statement_start = max(text.rfind(";", 0, m.start()), text.rfind("{", 0, m.start()),
                              text.rfind("}", 0, m.start()), m.start() - 400)
        if AUDIT_STATEMENT_SKIP_RE.search(text[statement_start + 1: m.start()]):
            continue
        # match 分支的模式（"x" => ...、"x" | "y" =>）与相等比较（== "x"）只是标识，不显示
        if re.match(r"\s*(?:=>|\|\s*\")", text[m.end(): m.end() + 12]) \
                or re.search(r"(?:==|!=)\s*$", text[max(0, m.start() - 6): m.start()]):
            continue
        line_start = text.rfind("\n", 0, m.start()) + 1
        if re.match(r"\s*#\[", text[line_start: text.find("\n", m.start())]):
            continue
        lineno = text.count("\n", 0, m.start()) + 1
        found.append((f"{path.relative_to(wd)}:{lineno}", literal))
    return found


def collect_audit(wd: Path, entries: dict, allow: set, sites: bool = False) -> list:
    """返回 [(位置, 字面量)]：不在 tr()/日志/断言中、像界面文案、且既无译文也未列入白名单。

    范围：全部默认插件 + server 的 ui/ + 补丁触及过的 Rust 文件（协议、解析器、
    测试等内部代码里的英文不是界面文案，不审计）。"""
    candidates = set()
    for root in [wd / "default-plugins", wd / "zellij-server" / "src" / "ui"]:
        if root.is_dir():
            candidates.update(root.rglob("*.rs"))
    for f in files_touched_by_patches(patches_dir(load_upstream())):
        if f.endswith(".rs") and (wd / f).is_file():
            candidates.add(wd / f)
    found = []
    for path in sorted(candidates):
        parts = set(path.parts)
        if parts & {"tests", "test", "unit"} or "fixture" in str(path) \
                or path.name.endswith(("_tests.rs", "_test.rs", "tests.rs")):
            continue
        if audit_file_allowed(str(path.relative_to(wd)), allow):
            continue
        found.extend(audit_scan_file(wd, path, entries, allow, sites))
    return found


def cmd_audit(args) -> int:
    """漏译审计：列出可能漏掉 tr() 的英文界面字面量（启发式；有意不译的写入 i18n/audit-allow.txt）。"""
    wd = workdir(args)
    if not (wd / "zellij-i18n").is_dir():
        raise SystemExit(f"工作区 {wd} 尚未应用补丁，请先运行 tools/zhcn.py apply（或 build）。")
    entries, errors = load_catalog()
    if entries is None:
        raise SystemExit("译文目录无法解析：" + "；".join(errors))
    found = collect_audit(wd, entries, audit_load_allow(), getattr(args, "sites", False))
    if args.json:
        print(json.dumps([{"location": loc, "text": t} for loc, t in found], ensure_ascii=False, indent=2))
    else:
        by_file = {}
        for loc, t in found:
            by_file.setdefault(loc.rsplit(":", 1)[0], []).append((loc, t))
        for f in sorted(by_file):
            print(f"\n{f}（{len(by_file[f])}）")
            for loc, t in by_file[f]:
                print(f"  {loc.rsplit(':', 1)[1]:>5}  {t!r}")
        print(f"\n共 {len(found)} 处疑似漏译（启发式；确属有意不译的请写入 i18n/audit-allow.txt）。")
    return 1 if (found and args.strict) else 0


# ── 生成器 ────────────────────────────────────────────────────────────────


def rust_escape(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .replace("\r", "\\r")
    )


def gen_rust_catalog(entries: dict, out: Path):
    lines = [
        "// Generated by tools/zhcn.py gen-rust from i18n/zh-CN.toml. Do not edit.",
        "// Sorted by key for binary search.",
        "pub(crate) static CATALOG: &[(&str, &str)] = &[",
    ]
    for key in sorted(entries):
        lines.append(f'    ("{rust_escape(key)}", "{rust_escape(entries[key])}"),')
    lines.append("];\n")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def gen_web_i18n(entries: dict, web_keys: dict, out: Path):
    template = WEB_I18N_TEMPLATE.read_text(encoding="utf-8")
    catalog = {k: entries[k] for k in sorted(web_keys) if k in entries}
    payload = json.dumps(catalog, ensure_ascii=False, indent=None, sort_keys=True)
    if WEB_CATALOG_MARKER not in template:
        raise SystemExit(f"i18n.js 模板缺少注入标记 {WEB_CATALOG_MARKER}")
    result = template.replace(WEB_CATALOG_MARKER, payload)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result, encoding="utf-8")


def cmd_gen_rust(args) -> int:
    entries = validate_catalog()
    gen_rust_catalog(entries, Path(args.out))
    eprint(f">> 已生成 {args.out}")
    return 0


def cmd_gen_web(args) -> int:
    up = load_upstream()
    wd = workdir(args)
    entries = validate_catalog()
    gen_web_i18n(entries, extract_js_keys(wd), Path(args.out))
    eprint(f">> 已生成 {args.out}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="zhcn.py", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_workdir(p):
        p.add_argument("--workdir", help=f"上游工作区（默认 {WORK_DIR / ZELLIJ_DIR_NAME}）")

    p = sub.add_parser("fetch", help="获取上游源码并核对基线提交")
    p.add_argument("--tag", help="覆盖 upstream.toml 的 tag")
    p.add_argument("--commit", help="覆盖 upstream.toml 的 commit")
    add_workdir(p)
    p.set_defaults(fn=cmd_fetch)

    p = sub.add_parser("check", help="校验基线、补丁与译文目录")
    add_workdir(p)
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("apply", help="重置工作区并应用补丁、生成产物")
    p.add_argument("--force", action="store_true",
                   help="丢弃工作区未提交改动与 zh-cn 分支后重建")
    add_workdir(p)
    p.set_defaults(fn=cmd_apply)

    p = sub.add_parser("build", help="check + apply + release 构建")
    p.add_argument("--force", action="store_true",
                   help="丢弃工作区未提交改动与 zh-cn 分支后重建")
    p.add_argument("--target", help="目标平台三元组（如 x86_64-unknown-linux-musl）；不给则构建本机")
    add_workdir(p)
    p.set_defaults(fn=cmd_build)

    p = sub.add_parser("package", help="把某目标平台的构建产物打包并生成 sha256")
    p.add_argument("--target", required=True, help="目标平台三元组")
    p.add_argument("--out", default="dist", help="输出目录（默认 dist）")
    p.add_argument("--source", help="二进制所在目录（默认按目标平台推断）")
    add_workdir(p)
    p.set_defaults(fn=cmd_package)

    p = sub.add_parser("export-patches", help="导出 zh-cn 分支为补丁队列")
    add_workdir(p)
    p.set_defaults(fn=cmd_export_patches)

    p = sub.add_parser("report", help="对比代码键与译文目录")
    p.add_argument("--json", action="store_true", help="输出 JSON")
    p.add_argument("--strict", action="store_true",
                   help="有缺译或冗余条目时也以非零退出码结束（CI 用）")
    add_workdir(p)
    p.set_defaults(fn=cmd_report)

    p = sub.add_parser("audit", help="漏译审计：列出疑似未包 tr() 的英文界面字面量")
    p.add_argument("--json", action="store_true", help="输出 JSON")
    p.add_argument("--strict", action="store_true", help="有疑似漏译时以非零退出码结束")
    p.add_argument("--sites", action="store_true",
                   help="连译文目录里已有、但此处没包 tr() 的使用点也列出（更严格，含少量误报）")
    add_workdir(p)
    p.set_defaults(fn=cmd_audit)

    p = sub.add_parser("gen-rust", help="生成 Rust 译文目录")
    p.add_argument("--out", required=True, help="输出路径")

    p = sub.add_parser("gen-web", help="生成网页 i18n.js")
    p.add_argument("--out", required=True, help="输出路径")
    add_workdir(p)

    p = sub.add_parser("upstream-status", help="列出上游 ≥ 基线的标签及适配状态")
    p.add_argument("--json", action="store_true", help="输出 JSON")
    p.set_defaults(fn=cmd_upstream_status)

    p = sub.add_parser("probe", help="探测某上游标签与补丁队列的兼容性（不构建）")
    p.add_argument("--tag", required=True, help="上游标签，如 v0.45.1")
    p.add_argument("--probe-workdir", help="探测工作区（默认 .work/probe-<tag>）")
    p.add_argument("--json", action="store_true", help="输出 JSON")
    add_workdir(p)
    p.set_defaults(fn=cmd_probe)

    args = parser.parse_args()
    if args.cmd == "gen-rust":
        return cmd_gen_rust(args)
    if args.cmd == "gen-web":
        return cmd_gen_web(args)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
