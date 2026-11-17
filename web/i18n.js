// zellij-zh-cn: runtime string lookup for the web client.
// Classic (non-module) script loaded before modals.js/app.js.
// The catalog below is injected by tools/zhcn.py at the marker and only
// contains translations for keys actually used by the web sources.
(function () {
    "use strict";

    var CATALOG = /*__ZELLIJ_I18N_CATALOG__*/;

    function normalize(value) {
        if (typeof value !== "string") {
            return null;
        }
        value = value.toLowerCase();
        if (value.indexOf("zh") === 0) {
            return "zh-CN";
        }
        if (value.indexOf("en") === 0) {
            return "en";
        }
        return null;
    }

    function detectLang() {
        // 1. ?lang= URL parameter (persisted for later visits)
        try {
            var param = new URLSearchParams(window.location.search).get("lang");
            var fromUrl = normalize(param);
            if (fromUrl) {
                try {
                    window.localStorage.setItem("zellij-lang", fromUrl);
                } catch (e) {}
                return fromUrl;
            }
        } catch (e) {}
        // 2. localStorage
        try {
            var stored = normalize(window.localStorage.getItem("zellij-lang"));
            if (stored) {
                return stored;
            }
        } catch (e) {}
        // 3. navigator.languages
        var langs = window.navigator.languages || [window.navigator.language];
        for (var i = 0; i < langs.length; i++) {
            var detected = normalize(langs[i]);
            if (detected) {
                return detected;
            }
        }
        return "en";
    }

    var lang = detectLang();
    document.documentElement.lang = lang;

    // t(en, params): look up the translation of the English original `en`,
    // then replace each `{name}` placeholder with params[name]. Falls back to
    // the English text when the language is English or the key is unknown.
    function t(en, params) {
        var s = en;
        if (lang === "zh-CN" && Object.prototype.hasOwnProperty.call(CATALOG, en)) {
            s = CATALOG[en];
        }
        if (params) {
            for (var name in params) {
                if (Object.prototype.hasOwnProperty.call(params, name)) {
                    s = s.split("{" + name + "}").join(String(params[name]));
                }
            }
        }
        return s;
    }

    window.zellijI18n = { lang: lang, t: t };
})();
