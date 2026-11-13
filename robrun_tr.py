#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rob Run - Türkçe Yama (açık kaynak kurulum aracı)

Ne yapar:
  1. Steam kütüphanelerinde Rob Run kurulumunu bulur.
  2. Oyunun güncel Addressables katalog adını ve hash değerini settings.json'dan okur.
  3. Oyunun KENDİ İngilizce dil paketini ve font paketini okuyup, bu bilgisayarda
     Türkçe dil paketi ve Türkçe karakterli font paketi üretir.
  4. Oyunun güncel kataloğunun bir kopyasında yalnızca bu iki paketin adresini değiştirip
     Unity'nin resmi önbellek klasörüne yazar:
        %USERPROFILE%\\AppData\\LocalLow\\Kefir\\ROB RUN\\com.unity.addressables
  5. İsteğe bağlı olarak oyunu Steam üzerinden başlatır.

Yapmadıkları:
  - İnternete bağlanmaz, veri göndermez.
  - Driver/servis kurmaz, yönetici izni istemez.
  - Oyun işlemine (RAM) müdahale etmez, DLL enjekte etmez.
  - Oyun klasörüne yeni dosya eklemez.

Kullanım:
  python robrun_tr.py              -> kur / güncelle ve oyunu başlat
  python robrun_tr.py --no-launch  -> sadece kur / güncelle
  python robrun_tr.py --uninstall  -> yamayı kaldır (İngilizceye dön)
  python robrun_tr.py --game-dir "D:\\SteamLibrary\\steamapps\\common\\Rob Run"
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys

try:
    import winreg  # yalnızca Windows
except ImportError:  # pragma: no cover
    winreg = None

PATCH_VERSION = "5.1.0"
STEAM_APPID = "4262460"

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
MASTER_TR_PATH = os.path.join(DATA_DIR, "master_tr.json")
SHARED_KEYS_PATH = os.path.join(DATA_DIR, "shared_keys.json")

DEFAULT_CACHE_DIR = os.path.join(
    os.path.expandvars("%USERPROFILE%"), "AppData", "LocalLow", "Kefir", "ROB RUN", "com.unity.addressables"
)

EN_BUNDLE_NAME = "localization-string-tables-english(unitedstates)(en-us)_assets_all.bundle"
INBUILD_BUNDLE_NAME = "inbuild_assets_all.bundle"
TR_LOC_BUNDLE_NAME = "localization-string-tables-turkish(turkey-republic)(tr)_assets_all_turkish_.bundle"
TR_INBUILD_BUNDLE_NAME = "inbuild_assets_all_turkish_.bundle"
STATE_FILE_NAME = "robrun_tr_state.json"

# Eski sürümlerin oyun klasörüne bırakmış olabileceği dosyalar (temizlenir)
LEGACY_GAME_FOLDER_FILES = [
    "localization-string-tables-turkish(turkey-republic)(tr)_assets_all.bundle",
    TR_LOC_BUNDLE_NAME,
    TR_INBUILD_BUNDLE_NAME,
    "localization-tr.bundle",
]

# Katalogdaki adresler. Uzunluklar birebir aynı olmalı (ikili katalogda yerinde değişim).
LOC_ID_ORIG = (
    b"{UnityEngine.AddressableAssets.Addressables.RuntimePath}\\StandaloneWindows64\\"
    b"localization-string-tables-english(unitedstates)(en-us)_assets_all.bundle"
)
LOC_ID_NEW = (
    b"{UnityEngine.Application.persistentDataPath}/com.unity.addressables/"
    b"localization-string-tables-turkish(turkey-republic)(tr)_assets_all_turkish_.bundle"
)
INBUILD_ID_ORIG = (
    b"{UnityEngine.AddressableAssets.Addressables.RuntimePath}\\StandaloneWindows64\\"
    b"inbuild_assets_all.bundle"
)
INBUILD_ID_NEW = (
    b"{UnityEngine.Application.persistentDataPath}/com.unity.addressables/"
    b"inbuild_assets_all_turkish_.bundle"
)
assert len(LOC_ID_ORIG) == len(LOC_ID_NEW)
assert len(INBUILD_ID_ORIG) == len(INBUILD_ID_NEW)

TR_FALLBACK_PAIRS = [
    ("ğ", "g"), ("Ğ", "G"), ("ş", "s"), ("Ş", "S"),
    ("ı", "i"), ("İ", "I"), ("ç", "c"), ("Ç", "C"),
    ("ö", "o"), ("Ö", "O"), ("ü", "u"), ("Ü", "U"),
]

# ---------------------------------------------------------------------------
# SDF font glif birleştirme tarifleri.
# Mevcut harflerin SDF parçaları (ör. Ç'nin çengeli + S) atlasın boş alanına
# kopyalanarak yeni Türkçe harfler oluşturulur. Atlas düzeni beklenenden farklıysa
# (oyun fontları güncellenmişse) bu adım atlanır ve basit eşleme kullanılır.
# blit: (kaynak_x, kaynak_y, genişlik, yükseklik, hedef_x, hedef_y, dikey_çevir)
# ---------------------------------------------------------------------------
FONT_RECIPES = {
    "TT_Bluescreens SDF": {
        "expect": {
            "S": (155, 455), "s": (785, 800), "Ç": (47, 441), "ç": (595, 437),
            "G": (333, 493), "g": (671, 703), "Â": (849, 454), "â": (222, 877),
            "I": (531, 388), "i": (872, 173),
        },
        "glyphs": {
            "Ş": {"blits": [(47, 441, 29, 19, 460, 818, False), (155, 455, 29, 74, 460, 835, False)],
                  "rect": (460, 818, 29, 91), "metrics": (28.40625, 89.609375, 2.0, 71.203125, 32.40625)},
            "ş": {"blits": [(595, 437, 27, 19, 493, 818, False), (785, 800, 27, 58, 493, 835, False)],
                  "rect": (493, 818, 27, 75), "metrics": (25.703125, 73.609375, 1.703125, 55.203125, 29.40625)},
            "Ğ": {"blits": [(333, 493, 30, 74, 524, 818, False), (851, 525, 30, 17, 524, 889, True)],
                  "rect": (524, 818, 30, 88), "metrics": (29.09375, 87.90625, 3.5, 87.90625, 35.59375)},
            "ğ": {"blits": [(671, 703, 27, 72, 558, 818, False), (222, 936, 27, 15, 558, 889, True)],
                  "rect": (558, 818, 27, 86), "metrics": (26.5, 85.203125, 3.5, 69.203125, 33.5)},
            "İ": {"blits": [(531, 388, 11, 70, 590, 818, False), (872, 228, 13, 16, 589, 888, False)],
                  "rect": (589, 818, 13, 86), "metrics": (12.0, 86.0, 3.5, 86.0, 18.90625)},
            "ı": {"blits": [],
                  "rect": (872, 173, 13, 56), "metrics": (12.0, 55.203125, 2.703125, 55.203125, 17.296875)},
        },
    },
    "RobotoBoldCondensed": {
        "expect": {
            "S": (986, 394), "s": (843, 700), "Ç": (76, 888), "ç": (809, 214),
            "G": (467, 874), "g": (839, 85), "Â": (17, 744), "â": (356, 765),
            "I": (491, 480), "i": (385, 430),
        },
        "glyphs": {
            "Ş": {"blits": [(76, 888, 21, 12, 626, 982, False), (986, 394, 21, 31, 626, 992, False)],
                  "rect": (626, 982, 21, 41), "metrics": (21.0, 41.0, 1.0, 31.0, 24.0)},
            "ş": {"blits": [(809, 214, 18, 12, 650, 982, False), (843, 700, 18, 23, 650, 992, False)],
                  "rect": (650, 982, 18, 33), "metrics": (18.0, 33.0, 1.0, 23.0, 20.0)},
            "Ğ": {"blits": [(467, 874, 22, 31, 672, 982, False), (19, 774, 22, 10, 672, 1012, True)],
                  "rect": (672, 982, 22, 40), "metrics": (22.0, 40.0, 2.0, 40.0, 26.0)},
            "ğ": {"blits": [(839, 85, 19, 32, 698, 982, False), (356, 789, 19, 9, 698, 1014, True)],
                  "rect": (698, 982, 19, 41), "metrics": (19.0, 41.0, 1.0, 32.0, 22.0)},
            "İ": {"blits": [(491, 480, 7, 31, 720, 982, False), (385, 453, 7, 9, 720, 1012, False)],
                  "rect": (720, 982, 7, 39), "metrics": (7.0, 39.0, 2.0, 39.0, 12.0)},
            "ı": {"blits": [],
                  "rect": (385, 430, 7, 23), "metrics": (7.0, 23.0, 2.0, 23.0, 11.0)},
        },
    },
}


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------
def log(msg=""):
    print(msg, flush=True)


def md5_of(path):
    if not os.path.exists(path):
        return ""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_state(cache_dir):
    p = os.path.join(cache_dir, STATE_FILE_NAME)
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(cache_dir, state):
    with open(os.path.join(cache_dir, STATE_FILE_NAME), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Oyun klasörünü bulma
# ---------------------------------------------------------------------------
def find_game_dir(explicit=None):
    def ok(p):
        return p and os.path.isfile(os.path.join(p, "ROB RUN.exe"))

    if explicit:
        return explicit if ok(explicit) else None

    cur = os.path.abspath(os.getcwd())
    while len(cur) > 3:
        if ok(cur):
            return cur
        cur = os.path.dirname(cur)

    roots = set()
    if winreg is not None:
        for hive, sub, val in [
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
        ]:
            try:
                with winreg.OpenKey(hive, sub) as k:
                    v, _ = winreg.QueryValueEx(k, val)
                    if v and os.path.isdir(v):
                        roots.add(os.path.normpath(v))
            except OSError:
                pass

    for drv in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        base = f"{drv}:\\"
        if not os.path.exists(base):
            continue
        for sub in [r"Program Files (x86)\Steam", r"Program Files\Steam", "Steam", "SteamLibrary",
                    r"Games\Steam", r"Oyunlar\Steam"]:
            p = os.path.join(base, sub)
            if os.path.isdir(p):
                roots.add(os.path.normpath(p))

    libs = set(roots)
    for r in list(roots):
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            try:
                with open(vdf, "r", encoding="utf-8", errors="ignore") as f:
                    for m in re.finditer(r'"path"\s+"([^"]+)"', f.read()):
                        p = m.group(1).replace("\\\\", "\\")
                        if os.path.isdir(p):
                            libs.add(os.path.normpath(p))
            except OSError:
                pass

    for lib in libs:
        cand = os.path.join(lib, "steamapps", "common", "Rob Run")
        if ok(cand):
            return cand
    return None


# ---------------------------------------------------------------------------
# Oyun sürümünü (katalog) tespit etme
# ---------------------------------------------------------------------------
def detect_catalog(game_dir):
    aa = os.path.join(game_dir, "ROB RUN_Data", "StreamingAssets", "aa")
    sa = os.path.join(aa, "StandaloneWindows64")
    settings = os.path.join(aa, "settings.json")

    hash_name = None
    with open(settings, "r", encoding="utf-8") as f:
        sdata = json.load(f)
    for loc in sdata.get("m_CatalogLocations", []):
        if "AddressablesMainContentCatalogCacheHash" in loc.get("m_Keys", []):
            hash_name = os.path.basename(loc.get("m_InternalId", "").replace("\\", "/"))
            break
    if not hash_name:
        raise RuntimeError("settings.json içinde önbellek (CacheHash) girdisi yok. "
                           "Oyunun yükleme sistemi değişmiş olabilir; yama bu sürümle çalışmaz.")
    if not sdata.get("m_DisableCatalogUpdateOnStart", False):
        log("  [UYARI] m_DisableCatalogUpdateOnStart kapalı; önbellek yöntemi çalışmayabilir.")

    bin_name = hash_name[:-5] + ".bin"
    sa_hash = os.path.join(sa, hash_name)
    sa_bin = os.path.join(sa, bin_name)
    if not os.path.isfile(sa_hash) or not os.path.isfile(sa_bin):
        raise RuntimeError(f"Güncel katalog dosyaları bulunamadı: {bin_name}")
    with open(sa_hash, "rb") as f:
        hash_bytes = f.read().strip()
    return {"aa": aa, "sa": sa, "bin_name": bin_name, "hash_name": hash_name,
            "sa_bin": sa_bin, "hash_bytes": hash_bytes}


def tidy_game_folder(cat):
    """Eski yama sürümlerinin bıraktığı izleri temizler. Oyun dosyalarına başka dokunmaz."""
    for name in LEGACY_GAME_FOLDER_FILES:
        p = os.path.join(cat["sa"], name)
        if os.path.isfile(p):
            try:
                os.remove(p)
                log(f"  [TEMİZLENDİ] Oyun klasöründe kalan eski yama dosyası: {name}")
            except OSError as e:
                log(f"  [UYARI] Silinemedi: {name} ({e})")

    # Eski sürümler aa\catalog.bin'i değiştirmiş olabilir. Oyunun kendi aa\catalog.hash
    # değeri güncel katalogla aynıysa, aa\catalog.bin de güncel katalogla aynı olmalıdır.
    aa_bin = os.path.join(cat["aa"], "catalog.bin")
    aa_hash = os.path.join(cat["aa"], "catalog.hash")
    try:
        with open(aa_hash, "rb") as f:
            same_build = f.read().strip() == cat["hash_bytes"]
    except OSError:
        same_build = False
    if same_build and os.path.isfile(aa_bin) and md5_of(aa_bin) != md5_of(cat["sa_bin"]):
        with open(cat["sa_bin"], "rb") as f:
            sa_raw = f.read()
        if b"persistentDataPath}/com.unity.addressables/" not in sa_raw:
            shutil.copy2(cat["sa_bin"], aa_bin)
            log("  [ONARILDI] aa\\catalog.bin oyunun güncel kataloğuyla eşitlendi. "
                "(Emin olmak için Steam > Dosya bütünlüğünü doğrula da yapabilirsiniz.)")


# ---------------------------------------------------------------------------
# Türkçe dil paketi
# ---------------------------------------------------------------------------
def build_loc_bundle(src_bundle, dst_bundle):
    import UnityPy

    with open(MASTER_TR_PATH, "r", encoding="utf-8") as f:
        master_tr = json.load(f)
    with open(SHARED_KEYS_PATH, "r", encoding="utf-8") as f:
        shared_keys = json.load(f)

    env = UnityPy.load(src_bundle)
    total, hit = 0, 0
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        tree = obj.read_typetree()
        name = tree.get("m_Name", "")
        prefix = next((p for p in ("StaticStrings", "RealmNames", "TimeFormatterAbbreviations") if p in name), None)
        if not prefix:
            continue
        keys = shared_keys.get(prefix, {})
        for entry in tree.get("m_TableData", []):
            total += 1
            eid = str(entry.get("m_Id"))
            kname = keys.get(eid)
            lkey = f"{prefix}::{kname}" if kname else f"{prefix}::{eid}"
            if lkey in master_tr:
                entry["m_Localized"] = master_tr[lkey]
                hit += 1
        obj.save_typetree(tree)

    with open(dst_bundle, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    return hit, total


# ---------------------------------------------------------------------------
# Türkçe karakterli font paketi
# ---------------------------------------------------------------------------
def _add_glyph(tree, ch, rect, metrics):
    glyphs, chars = tree["m_GlyphTable"], tree["m_CharacterTable"]
    idx = max(g["m_Index"] for g in glyphs) + 1
    x, y, w, h = rect
    mw, mh, bx, by, adv = metrics
    glyphs.append({
        "m_Index": idx,
        "m_Metrics": {"m_Width": mw, "m_Height": mh, "m_HorizontalBearingX": bx,
                      "m_HorizontalBearingY": by, "m_HorizontalAdvance": adv},
        "m_GlyphRect": {"m_X": x, "m_Y": y, "m_Width": w, "m_Height": h},
        "m_Scale": 1.0, "m_AtlasIndex": 0, "m_ClassDefinitionType": 0,
    })
    chars[:] = [c for c in chars if c["m_Unicode"] != ord(ch)]
    chars.append({"m_ElementType": 1, "m_Unicode": ord(ch), "m_GlyphIndex": idx, "m_Scale": 1.0})


def _add_fallbacks(tree):
    cmap = {c["m_Unicode"]: c["m_GlyphIndex"] for c in tree["m_CharacterTable"]}
    added = 0
    for tr_ch, base in TR_FALLBACK_PAIRS:
        if ord(tr_ch) not in cmap and ord(base) in cmap:
            tree["m_CharacterTable"].append(
                {"m_ElementType": 1, "m_Unicode": ord(tr_ch), "m_GlyphIndex": cmap[ord(base)], "m_Scale": 1.0})
            added += 1
    return added


def build_font_bundle(src_bundle, dst_bundle):
    import UnityPy
    from UnityPy.streams import EndianBinaryReader

    env = UnityPy.load(src_bundle)

    # .resS (doku verisi) ve doku konumlarını bul
    ress_key = next((k for k in env.file.files if k.endswith(".resS")), None)
    tex_info = {}
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            try:
                t = obj.read_typetree()
                sd = t.get("m_StreamData", {})
                tex_info[obj.path_id] = (t.get("m_Width"), t.get("m_Height"), t.get("m_TextureFormat"),
                                         sd.get("offset"), sd.get("size"))
            except Exception:
                pass

    buf = bytearray(env.file.files[ress_key].bytes) if ress_key else None
    ress_dirty = False
    report = []

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if "m_GlyphTable" not in tree or "m_CharacterTable" not in tree:
            continue
        fname = tree.get("m_Name", "")
        if fname == "IconsFont":
            continue

        composed = False
        recipe = FONT_RECIPES.get(fname)
        if recipe and buf is not None:
            composed = _try_compose(tree, recipe, tex_info, buf)
            ress_dirty = ress_dirty or composed

        added = _add_fallbacks(tree)
        tree["m_GlyphTable"].sort(key=lambda g: g["m_Index"])
        tree["m_CharacterTable"].sort(key=lambda c: c["m_Unicode"])
        obj.save_typetree(tree)
        report.append(f"{fname}: {'gerçek Türkçe glifler' if composed else 'basit eşleme'} (+{added} eşleme)")

    if ress_dirty:
        orig = env.file.files[ress_key]
        reader = EndianBinaryReader(bytes(buf))
        reader.flags = getattr(orig, "flags", 0)
        env.file.files[ress_key] = reader

    with open(dst_bundle, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    return report


def _try_compose(tree, recipe, tex_info, buf):
    atlases = tree.get("m_AtlasTextures") or []
    if not atlases:
        return False
    info = tex_info.get(atlases[0].get("m_PathID"))
    if not info:
        return False
    w, h, fmt, off, size = info
    if (w, h, fmt) != (1024, 1024, 1) or off is None or size != 1024 * 1024:
        return False

    cmap = {c["m_Unicode"]: c["m_GlyphIndex"] for c in tree["m_CharacterTable"]}
    gmap = {g["m_Index"]: g for g in tree["m_GlyphTable"]}

    # Atlas düzeni beklenenle aynı mı?
    for ch, (ex, ey) in recipe["expect"].items():
        gi = cmap.get(ord(ch))
        if gi is None or gi not in gmap:
            return False
        r = gmap[gi]["m_GlyphRect"]
        if (r["m_X"], r["m_Y"]) != (ex, ey):
            return False
    for ch in recipe["glyphs"]:
        if ord(ch) in cmap:
            return False

    # Hedef alanlar boş mu?
    for spec in recipe["glyphs"].values():
        if not spec["blits"]:
            continue
        x, y, gw, gh = spec["rect"]
        for row in range(y, y + gh):
            start = off + row * 1024 + x
            if any(buf[start:start + gw]):
                return False

    # Glifleri çiz (SDF değerleri max ile birleştirilir)
    for spec in recipe["glyphs"].values():
        for sx, sy, bw, bh, dx, dy, flip in spec["blits"]:
            for r in range(bh):
                src_r = (sy + bh - 1 - r) if flip else (sy + r)
                s0 = off + src_r * 1024 + sx
                d0 = off + (dy + r) * 1024 + dx
                for c in range(bw):
                    v = buf[s0 + c]
                    if v > buf[d0 + c]:
                        buf[d0 + c] = v

    for ch, spec in recipe["glyphs"].items():
        _add_glyph(tree, ch, spec["rect"], spec["metrics"])
    return True


# ---------------------------------------------------------------------------
# Kurulum / kaldırma
# ---------------------------------------------------------------------------
def install(game_dir, cache_dir, force=False):
    cat = detect_catalog(game_dir)
    log(f"[2/5] Oyun sürümü: {cat['bin_name']}  (hash {cat['hash_bytes'].decode('ascii', 'ignore')})")
    tidy_game_folder(cat)

    os.makedirs(cache_dir, exist_ok=True)
    for fn in os.listdir(cache_dir):
        if fn.startswith("catalog_") and fn.endswith((".bin", ".hash")) and fn not in (cat["bin_name"], cat["hash_name"]):
            try:
                os.remove(os.path.join(cache_dir, fn))
                log(f"  [ESKİ ÖNBELLEK SİLİNDİ] {fn}")
            except OSError:
                pass

    state = {} if force else load_state(cache_dir)
    en_src = os.path.join(cat["sa"], EN_BUNDLE_NAME)
    inb_src = os.path.join(cat["sa"], INBUILD_BUNDLE_NAME)
    loc_dst = os.path.join(cache_dir, TR_LOC_BUNDLE_NAME)
    inb_dst = os.path.join(cache_dir, TR_INBUILD_BUNDLE_NAME)

    loc_sig = f"{PATCH_VERSION}|{md5_of(en_src)}|{md5_of(MASTER_TR_PATH)}"
    inb_sig = f"{PATCH_VERSION}|{md5_of(inb_src)}"

    log("[3/5] Türkçe dil paketi hazırlanıyor...")
    if state.get("loc_sig") == loc_sig and os.path.isfile(loc_dst):
        log("  Değişiklik yok, mevcut paket kullanılıyor.")
    else:
        hit, total = build_loc_bundle(en_src, loc_dst)
        log(f"  {hit}/{total} satır Türkçeleştirildi.")
        state["loc_sig"] = loc_sig

    log("[4/5] Türkçe karakterli font paketi hazırlanıyor...")
    use_font = True
    if state.get("inb_sig") == inb_sig and os.path.isfile(inb_dst):
        log("  Değişiklik yok, mevcut paket kullanılıyor.")
    else:
        try:
            for line in build_font_bundle(inb_src, inb_dst):
                log("  " + line)
            state["inb_sig"] = inb_sig
        except Exception as e:
            log(f"  [UYARI] Font paketi üretilemedi ({e}); oyunun kendi fontları kullanılacak.")
            use_font = False
            if os.path.isfile(inb_dst):
                os.remove(inb_dst)
            state.pop("inb_sig", None)

    with open(cat["sa_bin"], "rb") as f:
        raw = f.read()
    if LOC_ID_ORIG not in raw:
        raise RuntimeError("Güncel katalogda İngilizce dil paketi adresi bulunamadı; yama bu sürümle uyumsuz.")
    patched = raw.replace(LOC_ID_ORIG, LOC_ID_NEW)
    if use_font and INBUILD_ID_ORIG in patched:
        patched = patched.replace(INBUILD_ID_ORIG, INBUILD_ID_NEW)
    assert len(patched) == len(raw)

    with open(os.path.join(cache_dir, cat["bin_name"]), "wb") as f:
        f.write(patched)
    with open(os.path.join(cache_dir, cat["hash_name"]), "wb") as f:
        f.write(cat["hash_bytes"])

    state.update({"patch_version": PATCH_VERSION, "catalog": cat["bin_name"], "game_dir": game_dir})
    save_state(cache_dir, state)
    log(f"  Önbellek yazıldı: {cache_dir}")


def uninstall(game_dir, cache_dir):
    if game_dir:
        try:
            tidy_game_folder(detect_catalog(game_dir))
        except Exception:
            pass
    removed = 0
    if os.path.isdir(cache_dir):
        for fn in os.listdir(cache_dir):
            ours = (fn.startswith("catalog_") and fn.endswith((".bin", ".hash"))) or fn in (
                TR_LOC_BUNDLE_NAME, TR_INBUILD_BUNDLE_NAME, STATE_FILE_NAME, "loc_source_version.md5")
            if ours:
                try:
                    os.remove(os.path.join(cache_dir, fn))
                    removed += 1
                except OSError:
                    pass
    log(f"Yama kaldırıldı ({removed} dosya silindi). Oyun İngilizce açılacak.")


def main():
    ap = argparse.ArgumentParser(description="Rob Run Türkçe Yama")
    ap.add_argument("--game-dir", help="Rob Run kurulum klasörü (otomatik bulunamazsa)")
    ap.add_argument("--no-launch", action="store_true", help="Kurulumdan sonra oyunu başlatma")
    ap.add_argument("--uninstall", action="store_true", help="Yamayı kaldır")
    ap.add_argument("--force", action="store_true", help="Paketleri baştan üret")
    ap.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR, help=argparse.SUPPRESS)
    args = ap.parse_args()

    log("=" * 64)
    log(f" Rob Run Türkçe Yama v{PATCH_VERSION}")
    log("=" * 64)

    game_dir = find_game_dir(args.game_dir)

    if args.uninstall:
        uninstall(game_dir, args.cache_dir)
        return 0

    if not game_dir:
        log("[HATA] Rob Run kurulumu bulunamadı. --game-dir ile klasörü belirtin.")
        return 1
    log(f"[1/5] Oyun klasörü: {game_dir}")

    for p in (MASTER_TR_PATH, SHARED_KEYS_PATH):
        if not os.path.isfile(p):
            log(f"[HATA] Eksik dosya: {p}")
            return 1
    try:
        import UnityPy  # noqa: F401
    except ImportError:
        log("[HATA] UnityPy kurulu değil. Önce: pip install -r requirements.txt")
        return 1

    try:
        install(game_dir, args.cache_dir, force=args.force)
    except Exception as e:
        log(f"[HATA] {e}")
        return 1

    if args.no_launch:
        log("[5/5] Kurulum tamam. Oyunu Steam'den başlatabilirsiniz.")
    else:
        log("[5/5] Oyun Steam üzerinden başlatılıyor...")
        os.startfile(f"steam://run/{STEAM_APPID}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
