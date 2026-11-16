"""สร้าง + แพ็กแบบ A-TH และ A1–A5 (EN/TH) -> template/<V>/ — ไม่แตะแบบ A ต้นฉบับและไม่แก้ pack.py / dc2html.py
ใช้: python tools/report_templates/ax/build.py ATH A1 ...   (ไม่ใส่ = ทุกแบบที่มีโมดูล) · เพิ่ม --nopack เพื่อเขียน source อย่างเดียว
ชื่อไฟล์: ATH-… · A1-… (อังกฤษ) · A1TH-… (ไทย) → PDF แยก A1.pdf / A1TH.pdf ในโฟลเดอร์ template/A1/
"""
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import dc2html  # noqa: E402
import pack as packer  # noqa: E402

VARIANTS = ["ATH", "A1", "A2", "A3", "A4", "A5"]
ROW_Z = 36800 + 2300 * 9            # แถว Z
FOLDER = {"ATH": "A-TH"}


def load(v):
    try:
        return importlib.import_module(v.lower())
    except ModuleNotFoundError:
        return None


def place(canvas, v, mod):
    """ATH ต่อท้ายแถว A · A1–A5 เป็นแถวใหม่ต่อจาก Z (EN ซ้าย, TH ขวา)"""
    if v == "ATH":
        x, y = 3496, 0
    else:
        y = ROW_Z + 2300 * int(v[1])
        x = 0
    prev_lang = None
    for b in mod.boards():
        lang = "th" if b["name"].startswith(v + "TH-") else "en"
        if prev_lang == "en" and lang == "th":
            x += 160                # เว้นช่องระหว่างชุด EN กับ TH
        prev_lang = lang
        entry = {"x": x, "y": y, "w": b["w"], "h": b["h"], "title": b["title"]}
        if (b["w"], b["h"]) == (794, 1123):
            entry["paper"] = "a4"
        canvas["boards"][b["name"]] = entry
        if b["name"] not in canvas["order"]:
            canvas["order"].append(b["name"])
        x += b["w"] + 80
    key = "headingATH" if v == "ATH" else f"heading{v}"
    if v != "ATH":
        canvas["notes"][key] = {"x": 0, "y": y - 300, "text": mod.HEADING, "kind": "title1", "maxW": 7000}
    else:
        canvas["notes"]["qATH"] = {"x": 3496, "y": 1243, "w": 640, "size": 24, "fill": "blue", "text": mod.HEADING}


def main(args):
    nopack = "--nopack" in args
    versions = [a.upper() for a in args if not a.startswith("--")] or [v for v in VARIANTS if load(v)]
    mods = {v: m for v in VARIANTS if (m := load(v))}
    canvas = json.loads((ROOT / "template" / "Z" / "source" / "canvas.json").read_text(encoding="utf-8"))
    for v, m in mods.items():
        place(canvas, v, m)
    text = json.dumps(canvas, ensure_ascii=False, indent=1)
    # เลือกบอร์ดตามคำนำหน้าเท่านั้น (เฉพาะตอนสคริปต์นี้รัน — dc2html.py ไม่ถูกแก้)
    dc2html.wanted = lambda version, name: name.startswith(version + "-")
    for v in versions:
        out = ROOT / "template" / FOLDER.get(v, v)
        src = out / "source"
        src.mkdir(parents=True, exist_ok=True)
        for b in mods[v].boards():
            (src / b["name"]).write_text(b["html"], encoding="utf-8")
        (src / "canvas.json").write_text(text, encoding="utf-8")
        if nopack:
            continue
        for pv in ([v] if v == "ATH" else [v, v + "TH"]):
            names = packer.pack(pv, src, out)
            print(pv, len(names), "boards ->", out.name)


if __name__ == "__main__":
    main(sys.argv[1:])
