#!/usr/bin/env python3
"""检查“按子串上色”的译文是否仍包含被上色的词（否则高亮会在中文下静默丢失）。

扫描补丁树里 `Text::from(tr("英文")).color_substring(级别, "词" | tr("词"))` 与
`combo_text(tr("英文"), 级别, "组合键")`，要求中文译文包含对应的词（按键与命令原样保留，
普通词取其译文）。用法：python3 tools/check_emphasis.py [--workdir .work/zellij]
"""
import argparse
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STR = r'"((?:[^"\\]|\\.)*)"'
CHAIN = re.compile(r'Text::from\(\s*tr\(\s*' + STR + r'\s*\)\s*\)((?:\s*\.color_substring\(\s*\d+\s*,\s*(?:tr\(\s*' + STR + r'\s*\)|' + STR + r')\s*\))+)')
SUBS = re.compile(r'\.color_substring\(\s*\d+\s*,\s*(?:tr\(\s*' + STR + r'\s*\)|' + STR + r')\s*\)')
COMBO = re.compile(r'combo_text\(\s*tr\(\s*' + STR + r'\s*\)\s*,\s*\d+\s*,\s*' + STR + r'\s*\)')


def unesc(s: str) -> str:
    return s.replace('\\"', '"').replace("\\\\", "\\")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=str(ROOT / ".work" / "zellij"))
    args = ap.parse_args()
    wd = Path(args.workdir)
    cat = tomllib.load(open(ROOT / "i18n" / "zh-CN.toml", "rb"))
    problems = []
    checked = 0
    for path in sorted((wd / "default-plugins").rglob("*.rs")):
        text = path.read_text(encoding="utf-8")
        marker = re.search(r"#\[cfg\(test\)\]\s*\n\s*mod\s+test", text)
        if marker:
            text = text[: marker.start()]
        for m in CHAIN.finditer(text):
            en = unesc(m.group(1))
            zh = cat.get(en)
            if zh is None:
                continue
            for sm in SUBS.finditer(m.group(2)):
                translated, literal = sm.group(1), sm.group(2)
                if translated is not None:
                    want = cat.get(unesc(translated))
                    if want is None:
                        problems.append((path.name, en, f"tr({translated!r}) 没有译文"))
                        continue
                else:
                    want = unesc(literal)
                checked += 1
                if want not in zh:
                    problems.append((path.name, en, f"译文 {zh!r} 不含 {want!r}"))
        for m in COMBO.finditer(text):
            en, combo = unesc(m.group(1)), unesc(m.group(2))
            zh = cat.get(en)
            checked += 1
            if zh is not None and combo not in zh:
                problems.append((path.name, en, f"译文 {zh!r} 不含组合键 {combo!r}"))
    for name, en, why in problems:
        print(f"{name}: {en[:60]!r}: {why}")
    print(f"检查 {checked} 处高亮，问题 {len(problems)} 处。")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
