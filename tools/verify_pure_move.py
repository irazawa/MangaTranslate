"""Buktikan sebuah refactor benar-benar PEMINDAHAN MURNI, bukan perubahan perilaku.

Dipakai selama Fase 1 pemecahan main_window.py: method berpindah file, tapi
isinya tidak boleh berubah satu token pun.

Cara kerja: bangun peta {kunci: hash struktur AST} untuk semua method, lalu
bandingkan snapshot sebelum vs sesudah. Perbandingan memakai ast.dump tanpa
atribut posisi, jadi pindah baris/indentasi tidak dianggap perubahan --
sedangkan perubahan token sekecil apa pun langsung ketahuan.

Method milik MangaOCRABC dan seluruh mixin-nya dianggap satu namespace ('app'),
karena justru itu invariannya: kumpulan method yang tersedia pada objek
MangaOCRApp harus tetap sama persis, di file mana pun ia sekarang tinggal.

Pemakaian:
    python tools/verify_pure_move.py snapshot            # rekam baseline
    python tools/verify_pure_move.py check               # bandingkan dgn baseline
    python tools/verify_pure_move.py selftest            # skrip ini menguji dirinya
"""

import argparse
import ast
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pure_move_baseline.json")

# Class yang method-nya berakhir di objek MangaOCRApp yang sama.
APP_CLASS = "MangaOCRApp"


def _is_app_class(name):
    return name == APP_CLASS or name.endswith("Mixin")


def _hash(node):
    # include_attributes=False -> abaikan lineno/col_offset. Yang dibandingkan
    # struktur kode, bukan posisinya di file.
    return hashlib.sha256(
        ast.dump(node, include_attributes=False).encode("utf-8")
    ).hexdigest()[:16]


def collect(paths):
    """-> (peta {kunci: hash}, daftar duplikat dalam namespace 'app')."""
    out = {}
    app_seen = {}
    dupes = []
    for path in sorted(paths):
        try:
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
        except ValueError:
            # Windows: relpath melempar bila beda drive (mis. temp dir saat selftest).
            rel = os.path.basename(path)
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                scope = "app" if _is_app_class(node.name) else node.name
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        key = f"{scope}::{item.name}"
                        if scope == "app":
                            if item.name in app_seen:
                                dupes.append((item.name, app_seen[item.name], rel))
                            app_seen[item.name] = rel
                        # Nama ganda sudah ada di kode sekarang (mis. import_font
                        # terdefinisi 2x). Beri kunci berbeda supaya SEMUA salinan
                        # terlacak -- kalau tidak, yang mati bisa hilang diam-diam
                        # saat dipindah dan tak ada yang tahu.
                        n = 2
                        while key in out:
                            key = f"{scope}::{item.name}#{n}"
                            n += 1
                        out[key] = _hash(item)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[f"module::{node.name}"] = _hash(node)
    return out, dupes


def default_paths():
    paths = [os.path.join(ROOT, "src", "ui", "main_window.py")]
    mixin_dir = os.path.join(ROOT, "src", "ui", "main_window_mixins")
    if os.path.isdir(mixin_dir):
        paths += [
            os.path.join(mixin_dir, f)
            for f in os.listdir(mixin_dir)
            if f.endswith(".py")
        ]
    return paths


def cmd_snapshot(paths, out_path):
    data, dupes = collect(paths)
    if dupes:
        _report_dupes(dupes)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    print(f"snapshot: {len(data)} method -> {os.path.relpath(out_path, ROOT)}")
    return 0


def _report_dupes(dupes):
    names = sorted({d[0] for d in dupes})
    print(f"PERINGATAN: {len(names)} nama method ganda -- hanya definisi TERAKHIR yang hidup:")
    for name in names:
        n = sum(1 for d in dupes if d[0] == name) + 1
        print(f"  {name} ({n}x)")
    print("  (sudah ada sebelum refactor; jangan pindahkan nama-nama ini di Fase 1)")


def cmd_check(paths, baseline_path):
    if not os.path.exists(baseline_path):
        print(f"GAGAL: baseline tidak ada ({baseline_path}). Jalankan 'snapshot' dulu.")
        return 1
    with open(baseline_path, encoding="utf-8") as f:
        before = json.load(f)
    after, dupes = collect(paths)

    if dupes:
        # Bukan kegagalan: duplikat ini sudah ada di baseline. Kunci '#2' di bawah
        # yang menjaga -- kalau salah satu salinan hilang/berubah, ketahuan di sana.
        _report_dupes(dupes)

    missing = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])

    if not (missing or added or changed):
        print(f"OK: {len(after)} method identik. Pemindahan terbukti murni.")
        return 0

    print("GAGAL: ini bukan pemindahan murni.")
    for k in missing:
        print(f"  HILANG  {k}")
    for k in added:
        print(f"  BARU    {k}")
    for k in changed:
        print(f"  BERUBAH {k}")
    return 1


def selftest():
    """Buktikan skrip ini benar-benar menangkap perubahan sekecil satu karakter."""
    import tempfile

    before_src = (
        "class MangaOCRApp:\n"
        "    def halo(self):\n"
        "        return 1 + 1\n"
        "    def lain(self):\n"
        "        return 'x'\n"
    )
    # Method 'halo' pindah ke mixin, isi PERSIS sama -> harus dianggap identik.
    moved_a = "class HaloMixin:\n    def halo(self):\n        return 1 + 1\n"
    moved_b = "class MangaOCRApp(HaloMixin):\n    def lain(self):\n        return 'x'\n"
    # Sama, tapi 1+1 jadi 1+2 -> harus GAGAL.
    tampered = "class HaloMixin:\n    def halo(self):\n        return 1 + 2\n"

    with tempfile.TemporaryDirectory() as d:
        w = lambda name, src: (
            open(os.path.join(d, name), "w", encoding="utf-8").write(src),
            os.path.join(d, name),
        )[1]

        base = collect([w("before.py", before_src)])[0]
        pure = collect([w("a.py", moved_a), w("b.py", moved_b)])[0]
        bad = collect([w("a.py", tampered), w("b.py", moved_b)])[0]

        assert base == pure, "pemindahan murni salah dilaporkan sebagai berubah"
        assert base != bad, "perubahan 1+1 -> 1+2 TIDAK terdeteksi"

        # Nama ganda harus tertangkap.
        dupes = collect([w("a.py", moved_a), w("c.py", moved_a.replace("HaloMixin", "LainMixin"))])[1]
        assert dupes, "method ganda tidak terdeteksi"

    print("selftest OK: pemindahan murni lolos, perubahan token tertangkap, duplikat tertangkap.")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["snapshot", "check", "selftest"])
    p.add_argument("--baseline", default=BASELINE)
    p.add_argument("files", nargs="*")
    args = p.parse_args()

    if args.mode == "selftest":
        return selftest()

    paths = [os.path.abspath(f) for f in args.files] or default_paths()
    if args.mode == "snapshot":
        return cmd_snapshot(paths, args.baseline)
    return cmd_check(paths, args.baseline)


if __name__ == "__main__":
    sys.exit(main())
