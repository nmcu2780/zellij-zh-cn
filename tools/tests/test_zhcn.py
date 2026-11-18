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


if __name__ == "__main__":
    unittest.main()
