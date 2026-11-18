"""tools/zhcn.py 的单元测试（仅标准库）。运行：python3 -m unittest discover -s tools/tests -v"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
REPO = TOOLS.parent
spec = importlib.util.spec_from_file_location("zhcn", TOOLS / "zhcn.py")
zhcn = importlib.util.module_from_spec(spec)
sys.modules["zhcn"] = zhcn
spec.loader.exec_module(zhcn)


def write_catalog(text: str) -> Path:
    d = tempfile.mkdtemp()
    p = Path(d) / "c.toml"
    p.write_text(text, encoding="utf-8")
    return p


class CatalogValidation(unittest.TestCase):
    def test_valid_entry(self):
        entries, errors = zhcn.load_catalog(write_catalog('"Hello {a0}" = "你好 {a0}"\n'))
        self.assertEqual(entries, {"Hello {a0}": "你好 {a0}"})
        self.assertEqual(errors, [])

    def test_placeholder_mismatch_is_rejected(self):
        entries, errors = zhcn.load_catalog(write_catalog('"Hello {a0}" = "你好"\n'))
        self.assertEqual(entries, {})
        self.assertEqual(len(errors), 1)
        self.assertIn("占位符", errors[0])

    def test_extra_placeholder_in_translation_is_rejected(self):
        _, errors = zhcn.load_catalog(write_catalog('"Hello" = "你好 {a0}"\n'))
        self.assertEqual(len(errors), 1)

    def test_empty_translation_is_rejected(self):
        _, errors = zhcn.load_catalog(write_catalog('"Hello" = "  "\n'))
        self.assertEqual(len(errors), 1)

    def test_invalid_toml_is_reported(self):
        entries, errors = zhcn.load_catalog(write_catalog('"Hello" = \n'))
        self.assertIsNone(entries)
        self.assertTrue(errors)

    def test_missing_file_is_reported(self):
        entries, errors = zhcn.load_catalog(Path("/nonexistent/zh.toml"))
        self.assertIsNone(entries)
        self.assertTrue(errors)

    def test_shipped_catalog_is_valid(self):
        entries, errors = zhcn.load_catalog()
        self.assertEqual(errors, [])
        self.assertGreater(len(entries), 1000)


class RustKeyExtraction(unittest.TestCase):
    def extract(self, source: str) -> dict:
        d = Path(tempfile.mkdtemp())
        src = d / "default-plugins" / "demo" / "src"
        src.mkdir(parents=True)
        (src / "main.rs").write_text(source, encoding="utf-8")
        return zhcn.extract_rust_keys(d)

    def test_tr_trf_and_tr_ctx_are_found(self):
        keys = self.extract('fn f(){ tr("A"); trf("B {a0}", &[]); tr_ctx("C (short)"); }')
        self.assertEqual(set(keys), {"A", "B {a0}", "C (short)"})

    def test_escaped_quote_is_kept_in_key(self):
        keys = self.extract(r'fn f(){ tr("say \"hi\""); }')
        self.assertEqual([zhcn.unescape_rust(k) for k in keys], ['say "hi"'])

    def test_test_modules_are_skipped(self):
        keys = self.extract(
            'fn f(){ tr("Real"); }\n#[cfg(test)]\nmod tests { fn t(){ tr("OnlyInTest"); } }\n'
        )
        self.assertEqual(set(keys), {"Real"})

    def test_other_functions_with_tr_suffix_are_ignored(self):
        keys = self.extract('fn f(){ entry("X"); str("Y"); }')
        self.assertEqual(keys, {})


class Unescape(unittest.TestCase):
    def test_common_escapes(self):
        self.assertEqual(zhcn.unescape_rust(r"a\nb\tc\\d"), "a\nb\tc\\d")

    def test_line_continuation_swallows_leading_whitespace(self):
        self.assertEqual(zhcn.unescape_rust("one \\\n      two"), "one two")


class Generators(unittest.TestCase):
    def test_rust_catalog_is_sorted_and_escaped(self):
        out = Path(tempfile.mkdtemp()) / "c.rs"
        zhcn.gen_rust_catalog({"b": "乙", 'a"x': "甲\n"}, out)
        text = out.read_text(encoding="utf-8")
        self.assertLess(text.index('("a\\"x"'), text.index('("b"'))
        self.assertIn('"甲\\n"', text)


class ShippedPatches(unittest.TestCase):
    def test_patch_queue_is_numbered_without_gaps(self):
        up = zhcn.load_upstream()
        names = sorted(p.name for p in zhcn.patches_dir(up).glob("*.patch"))
        self.assertTrue(names)
        self.assertEqual([int(n[:4]) for n in names], list(range(1, len(names) + 1)))

    def test_no_build_artifacts_in_patches(self):
        up = zhcn.load_upstream()
        for p in zhcn.patches_dir(up).glob("*.patch"):
            self.assertNotIn("GIT binary patch", p.read_text(encoding="utf-8"), p.name)
            self.assertLess(p.stat().st_size, 1_000_000, p.name)

    def test_upstream_baseline_is_pinned_to_a_full_commit(self):
        up = zhcn.load_upstream()
        self.assertRegex(up["commit"], r"^[0-9a-f]{40}$")


class Audit(unittest.TestCase):
    def test_ui_like_text(self):
        self.assertTrue(zhcn.audit_looks_like_ui_text("Approve and Continue"))
        self.assertTrue(zhcn.audit_looks_like_ui_text("Dismiss"))
        self.assertTrue(zhcn.audit_looks_like_ui_text("Search: {}_"))

    def test_not_ui_text(self):
        for text in ["session_panel_size", "zellij-app-quit", "<Ctrl c>", "Alt + i",
                     "/usr/bin/zellij", "https://zellij.dev", "x", "ok", "default.kdl"]:
            self.assertFalse(zhcn.audit_looks_like_ui_text(text), text)

    def scan(self, source: str, entries=None, allow=None, sites=False):
        d = Path(tempfile.mkdtemp())
        f = d / "default-plugins" / "demo" / "src" / "main.rs"
        f.parent.mkdir(parents=True)
        f.write_text(source, encoding="utf-8")
        return [t for _, t in zhcn.audit_scan_file(d, f, entries or {}, allow or set(), sites)]

    def test_wrapped_literals_are_not_reported(self):
        self.assertEqual(self.scan('fn f(){ tr("Save changes"); trf("Hello {a0}", &[]); }'), [])

    def test_bare_literal_is_reported(self):
        self.assertEqual(self.scan('fn f(){ let t = "Save changes"; }'), ["Save changes"])

    def test_logs_and_asserts_are_not_reported(self):
        self.assertEqual(self.scan('fn f(){ eprintln!("Something bad happened"); assert!(x, "Must hold true"); }'), [])

    def test_match_patterns_and_comparisons_are_not_reported(self):
        self.assertEqual(self.scan('fn f(){ match a { "Save changes" => 1, _ => 2 }; if b == "Save changes" {} }'), [])

    def test_test_module_is_skipped(self):
        self.assertEqual(self.scan('fn f(){}\n#[cfg(test)]\nmod tests { fn t(){ let t = "Only in tests"; } }'), [])

    def test_catalog_hit_is_skipped_unless_sites_mode(self):
        entries = {"Save changes": "保存更改"}
        self.assertEqual(self.scan('fn f(){ let t = "Save changes"; }', entries), [])
        self.assertEqual(self.scan('fn f(){ let t = "Save changes"; }', entries, sites=True), ["Save changes"])

    def test_allowlist_literal_and_regex(self):
        self.assertEqual(self.scan('fn f(){ let t = "Save changes"; }', allow={"Save changes"}), [])
        self.assertEqual(self.scan('fn f(){ let t = "failed to open it"; }', allow={"re: ^failed"}), [])


class EmphasisChecker(unittest.TestCase):
    def test_shipped_translations_keep_highlighted_words(self):
        spec = importlib.util.spec_from_file_location("check_emphasis", TOOLS / "check_emphasis.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        wd = REPO / ".work" / "zellij"
        if not (wd / "zellij-i18n").is_dir():
            self.skipTest("需要已应用补丁的 .work/zellij（先运行 tools/zhcn.py apply）")
        sys.argv = ["check_emphasis.py", "--workdir", str(wd)]
        self.assertEqual(mod.main(), 0)


if __name__ == "__main__":
    unittest.main()
