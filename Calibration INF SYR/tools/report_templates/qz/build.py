"""สร้างไฟล์ต้นฉบับของแบบ Q–Z -> template/<V>/source/ (ไฟล์ .dc.html + canvas.json ทั้งผืน)
ใช้: python tools/report_templates/qz/build.py Q R ...   (ไม่ใส่ = ทุกแบบที่มีโมดูล)
canvas.json ตั้งต้นจาก template/P/source/canvas.json (= สำเนาของ canvas บนเว็บ) แล้วเติมแถว Q–Z
"""
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]          # D:\Claude\Calibration INF SYR
sys.path.insert(0, str(HERE))
ALL = "QRSTUVWXYZ"
ROW0, ROW_STEP = 36800, 2300    # แถว Q ต่อจาก P (34500) ระยะเท่าแถวเดิม


def load(v):
    try:
        return importlib.import_module(v.lower())
    except ModuleNotFoundError:
        return None


def canvas_with(mods, base):
    canvas = json.loads(base.read_text(encoding="utf-8"))
    for k, mod in mods.items():
        y = ROW0 + ROW_STEP * ALL.index(k)
        x = 0
        for b in mod.boards():
            entry = {"x": x, "y": y, "w": b["w"], "h": b["h"], "title": b["title"]}
            if (b["w"], b["h"]) == (794, 1123):
                entry["paper"] = "a4"
            canvas["boards"][b["name"]] = entry
            if b["name"] not in canvas["order"]:
                canvas["order"].append(b["name"])
            x += b["w"] + 80
        canvas["notes"][f"heading{k}"] = {"x": 0, "y": y - 300, "text": mod.HEADING, "kind": "title1",
                                          "maxW": 3416}
        if getattr(mod, "NOTE", None):
            canvas["notes"][f"q{k}"] = {"x": x, "y": y, "w": 560, "size": 24, "fill": mod.NOTE_FILL,
                                        "text": mod.NOTE}
    return canvas


def main(versions):
    base = ROOT / "template" / "P" / "source" / "canvas.json"
    mods = {v: m for v in ALL if (m := load(v))}
    canvas = canvas_with(mods, base)
    text = json.dumps(canvas, ensure_ascii=False, indent=1)
    for v in versions:
        mod = mods[v]
        src = ROOT / "template" / v / "source"
        src.mkdir(parents=True, exist_ok=True)
        for b in mod.boards():
            (src / b["name"]).write_text(b["html"], encoding="utf-8")
        (src / "canvas.json").write_text(text, encoding="utf-8")
        print(v, [b["name"] for b in mod.boards()])


if __name__ == "__main__":
    main([a.upper() for a in sys.argv[1:]] or [v for v in ALL if load(v)])
