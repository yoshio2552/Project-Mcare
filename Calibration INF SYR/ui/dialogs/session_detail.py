"""ข้อความสอบย้อนของผล (ค่าแก้ g→ml, งบความไม่แน่นอน, ลายนิ้วมือไฟล์) + ทางเข้าเดิม SessionDetailDialog

หน้าดูผลย้อนหลังตัวจริง = ui/dialogs/result_workspace.py (2026-11-20 แบบแท็บ + เล่นซ้ำ + เอกสาร)
"""
from __future__ import annotations

from config.i18n import tr
from services.session_store import raw_result, volume_factor
from ui.widgets.common import fmt

# ชุดสายเทียบกับมาตรฐานของโรงพยาบาล (JobInfo.accessory_usage)
USAGE_TEXT = {"standard": "hospital standard", "temporary": "temporary",
              "new_standard": "new hospital standard", "first": "first time — set as standard"}

MAX_PLOT_POINTS = 6000


def _text(value) -> str:
    return "—" if value in (None, "") else str(value)


_SOURCES = {"form": "entered", "settings": "Settings", "liquid": "= liquid temperature", "temperature": "from temperature"}


def _source(key: str) -> str:
    return tr(_SOURCES.get(key, key)) if key else ""


def integrity_text(checks: list[tuple[str, str]]) -> str:
    """ผลตรวจลายนิ้วมือ SHA-256 ของไฟล์ผล"""
    if not checks:
        return tr("Not recorded (result from an earlier version)")
    changed = [name for name, status in checks if status == "changed"]
    missing = [name for name, status in checks if status == "missing"]
    if not changed and not missing:
        return tr("✓ {n} files unchanged since saved (SHA-256)", n=len(checks))
    parts = ([tr("✗ changed: {files}", files=", ".join(changed))] if changed else []) +             ([tr("✗ missing: {files}", files=", ".join(missing))] if missing else [])
    return "  ".join(parts)


def correction_rows(summary: dict) -> list[tuple[str, str]]:
    """แถวสอบย้อนหลังของค่าแก้ g -> ml: ค่าที่ใช้ + ที่มา + ตรวจสูตร (ดิบ − B) × Z = สุทธิ"""
    c = summary.get("correction") or {}
    z = volume_factor(summary)
    baseline = float(summary.get("baseline_g_per_h") or 0.0)
    raw_flow, raw_error, derived = raw_result(summary)
    rows = []
    if c:
        rows += [
            (tr("Liquid temperature"), fmt(c.get("liquid_temp_c"), 1, " °C")),
            (tr("Water density ρw"), f'{fmt(c.get("water_density_g_per_ml"), 5, " g/ml")}  ·  '
                                     f'{_source(c.get("water_density_source", ""))}'),
        ]
        if c.get("air_buoyancy"):
            rows += [
                (tr("Air temperature"), f'{fmt(c.get("air_temp_c"), 1, " °C")}  ·  {_source(c.get("air_temp_source", ""))}'),
                (tr("Humidity"), f'{fmt(c.get("humidity_pct"), 1, " %RH")}  ·  {_source(c.get("humidity_source", ""))}'),
                (tr("Air pressure"), f'{fmt(c.get("pressure_hpa"), 2, " hPa")}  ·  {_source(c.get("pressure_source", ""))}'),
                (tr("Air density ρa"), fmt(c.get("air_density_g_per_ml", 0.0) * 1000.0, 4, " kg/m³")),
                (tr("Weight density ρb"), fmt(c.get("reference_density_g_per_ml"), 2, " g/ml")),
            ]
        else:
            rows.append((tr("Air buoyancy"), tr("Off")))
    else:       # ผลรุ่นก่อนมีค่าแก้แรงลอยตัว
        rows += [
            (tr("Water density ρw"), f'{fmt(summary.get("density_g_per_ml"), 5, " g/ml")}  ·  '
                                     f'{_source(summary.get("density_source", ""))}'),
            (tr("Air buoyancy"), tr("Not applied (result from an earlier version)")),
        ]
    rows += [
        (tr("Factor Z"), fmt(z, 6, " ml/g")),
        (tr("Self-check B"), fmt(baseline * 1000.0, 1, " mg/h", signed=True) if baseline else tr("Not applied")),
        (tr("Uncorrected flow Q₀"), fmt(raw_flow, 4, " ml/h") + ("  " + tr("(derived)") if derived else "")),
        (tr("Uncorrected error"), fmt(raw_error, 2, " %", signed=True)),
    ]
    net = summary.get("mean_flow")
    if raw_flow is not None and net is not None:
        recomputed = (raw_flow - baseline) * z
        ok = abs(recomputed - net) <= max(1e-4, abs(net) * 1e-5)
        rows.append((tr("Check (Q₀ − B) × Z"), f"{recomputed:.4f} ml/h  " + ("✓" if ok else f"≠ {net:.4f}")))
    if c.get("standard"):
        rows.append((tr("Standard"), c["standard"]))
    rows += [(tr("Note"), tr(w)) for w in c.get("warnings", [])]
    return rows


def uncertainty_rows(summary: dict) -> list[tuple[str, str]]:
    """แถวงบความไม่แน่นอน: องค์ประกอบ · u สัมพัทธ์ (%) — และ U รวม"""
    budget = summary.get("uncertainty") or {}
    rows = [(tr(c.get("name", "")), f'{c.get("u_rel_pct", 0):.4f} %') for c in budget.get("components", [])]
    if budget:
        rows.append((tr("Combined u_c"), f'{budget.get("u_c_pct", 0):.4f} %'))
        rows.append((tr("Expanded U (k = {k:.2f})", k=budget.get("k", 2.0)),
                     f'{budget.get("U_pct", 0):.3f} %  ·  ± {budget.get("U_ml_h", 0):.4f} ml/h'))
    return rows


class SessionDetailDialog:
    """เข้ากันได้กับโค้ด/เทสต์เดิม: หน้ารายละเอียดผลคือ ResultWorkspace (ui/dialogs/result_workspace.py — 2026-11-20)
    SessionDetailDialog(parent, detail, on_report) -> ResultWorkspace ของผลนี้ผลเดียว"""

    def __new__(cls, parent, detail, on_report=None):
        from ui.dialogs.result_workspace import ResultWorkspace
        return ResultWorkspace(parent, [detail.summary], on_report=on_report, detail=detail)
