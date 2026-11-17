use std::{env, fs, path::PathBuf};

fn main() {
    let manifest = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let src = manifest.join("src/catalog_generated.rs");
    let out = PathBuf::from(env::var("OUT_DIR").unwrap()).join("catalog_generated.rs");
    if src.exists() {
        fs::copy(&src, &out).unwrap();
    } else {
        // The generated catalog lives outside version control; without it the
        // crate still compiles with an empty table (all English fallback).
        fs::write(&out, "static CATALOG: &[(&str, &str)] = &[];\n").unwrap();
        println!("cargo:warning=zellij-i18n: catalog_generated.rs missing, using empty catalog");
    }
    println!("cargo:rerun-if-changed={}", src.display());
}
