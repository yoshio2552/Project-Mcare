"""CSS ของใบรายงาน (แบบ Main Fable-1) + ฟอนต์ Sarabun ฝังในเอกสาร (ใช้ได้โดยไม่ต่อเน็ต)

TEMPLATE_CSS = คัดลอกตรงจาก tools/report_templates/fable (styles.BASE + styles.A + a.CSS + EXTRA_CSS main/rate_error/lab)
ด้วยสคริปต์ — อย่าแก้ในก้อนนี้ ให้แก้/เพิ่มใน EXTRA ด้านล่าง (ส่วนที่ข้อมูลจริงต้องใช้แต่แบบไม่มี: ไม่ผ่าน สีแดง, ลายเซ็น, โลโก้)
ฟอนต์: ui/assets/fonts/Sarabun-*.ttf (SIL Open Font License 1.1 — ui/assets/fonts/OFL.txt) ฝังเป็น data URI
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

FONT_DIR = Path(__file__).resolve().parents[2] / "ui" / "assets" / "fonts"
FONT_WEIGHTS = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}
PAGE_W, PAGE_H = 794, 1123          # A4 ที่ 96 dpi

TEMPLATE_CSS = r"""

* { box-sizing: border-box; margin: 0; padding: 0 }
html, body { background: #E7E9EC }
.page { width: 794px; height: 1123px; position: relative; overflow: hidden; background: #fff; color: var(--ink);
        padding: var(--mt, 40px) var(--mx) 0; font: 400 13px/1.42 var(--font); font-variant-numeric: tabular-nums lining-nums }
.page b, .page h1, .page h2, .page h3 { font-weight: 600 }
.page i, .page em { font-style: normal }
small, .note, .fine, .lead, .foot, .count, .none { font-size: 12px }
.hdr { display: grid; grid-template-columns: 1fr auto; grid-template-areas: "co ttl" "co pg"; column-gap: 20px; align-items: end }
.co { grid-area: co; align-self: start } .ttl { grid-area: ttl; text-align: right } .pg { grid-area: pg; text-align: right; font-size: 12px; color: var(--mute) }
.mark { font-size: 22px; font-weight: 700; letter-spacing: -.3px; line-height: 1.1 }
.coname { font-weight: 600 } .coaddr { font-size: 12px; color: var(--mute) }
.kind { font-size: 12px; letter-spacing: 1.6px; color: var(--mute) }
h1 { font-size: 25px; line-height: 1.2 } .sub { font-size: 14px; font-weight: 600; color: var(--acc) }
.sub .alt { font-weight: 400; color: var(--mute); margin-left: 6px }
.meta { display: grid; grid-template-columns: 1fr 1fr 2.4fr; margin-top: 12px; border-top: 1.5px solid var(--ink); border-bottom: 1px solid var(--hair) }
.meta > div { padding: 6px 0 } .meta b { display: block; font-size: 12px; font-weight: 400; color: var(--mute) }
.meta span { font-weight: 600 } .jobno { color: var(--acc) }
.opt { display: inline-flex; align-items: center; gap: 6px; margin-right: 16px; font-weight: 400 } .opt .bx { margin: 0 }
.two { display: grid; grid-template-columns: 1fr 1fr; column-gap: 30px }
.who { margin-top: 10px }
h3 { font-size: 12px; color: var(--mute); font-weight: 600; letter-spacing: .4px; margin-bottom: 2px }
.kv > div { display: grid; grid-template-columns: var(--kw, 118px) 1fr; column-gap: 8px; padding: 1.5px 0 }
.kv dt { color: var(--mute) } .kv dd { font-weight: 500 }
.kv.ident { display: grid; grid-template-columns: 1fr 1.6fr 1fr 1fr; column-gap: 14px; margin-top: 12px; padding: 6px 0;
            border-top: 1.5px solid var(--ink); border-bottom: 1px solid var(--hair) }
.kv.ident > div { display: block; padding: 0 } .kv.ident dt { font-size: 12px }
.kv.wide { --kw: 190px }
.sec { margin-top: 10px }
.sec h2 { font-size: 14px; display: flex; align-items: baseline; gap: 8px; padding-bottom: 3px; border-bottom: 1px solid var(--ink); margin-bottom: 3px }
.sec h2 .no { color: var(--acc) }
.sec h2 .en, h3 .en { display: none }
.chk { display: grid; column-gap: 30px } .chk.c2 { grid-template-columns: 1fr 1fr }
.chk .hd, .chk .it { display: grid; grid-template-columns: 1fr auto; align-items: center; column-gap: 8px }
.chk .hd { font-size: 12px; color: var(--mute); padding: 1px 0 }
.chk .it { min-height: 22px; border-top: 1px solid var(--hair); padding: 1px 0 }
.chk.nohd .it:nth-child(-n+2) { border-top: none }
.nm small { display: block; color: var(--mute); line-height: 1.3 }
.cols { display: inline-grid; grid-template-columns: repeat(3, 42px); justify-items: center; align-items: center }
.word { display: none; font-weight: 600 }
.bx { display: inline-block; width: 13px; height: 13px; border: 1.2px solid var(--ink); position: relative; flex: none }
.bx.on::after { content: ""; position: absolute; left: 3.2px; top: -.5px; width: 4px; height: 8.5px; border: solid var(--ink); border-width: 0 1.8px 1.8px 0; transform: rotate(40deg) }
.pair { display: grid; grid-template-columns: 1.55fr 1fr; column-gap: 30px }
.safe { display: flex; gap: 22px; align-items: flex-start; padding-top: 3px }
.safe b { display: block; font-size: 12px; font-weight: 400; color: var(--mute) } .safe span { font-weight: 600 }
.safe em { display: block; font-size: 12px; color: var(--mute) } .safe .sv { margin-left: auto } .safe .sv .cols { display: none } .safe .okw { font-weight: 700 }
.safe .sv .word { display: none }
.fin { display: flex; flex-direction: column; gap: 4px; padding-top: 4px } .fin .opt { margin: 0 }
.extras .rc { margin-top: 3px; padding-top: 3px; border-top: 1px solid var(--hair) }
.extras .rc b { font-size: 12px; font-weight: 600; color: var(--mute); margin-right: 10px }
.count { color: var(--mute); margin-bottom: 2px }
ol.parts { list-style: none; columns: 3; column-gap: 20px; counter-reset: p }
ol.parts li { counter-increment: p; break-inside: avoid; padding: 1px 0 }
ol.parts li::before { content: counter(p) "  "; color: var(--mute); display: inline-block; min-width: 18px }
ol.parts li i { white-space: nowrap; font-size: 12px; color: var(--acc); font-weight: 600; margin-left: 4px }
.verdict { display: grid; grid-template-columns: 1fr auto; margin-top: 12px; border: 1.5px solid var(--ink) }
.vt { padding: 8px 14px; align-self: center } .vt b { display: none }
.vr { border-left: 1.5px solid var(--ink); padding: 6px 30px; text-align: center; min-width: 170px }
.vl { display: block; font-size: 12px; color: var(--mute) } .vv { font-size: 30px; font-weight: 700; line-height: 1.15 }
.vticks { display: none }
.signs { display: grid; column-gap: 30px; margin-top: 8px } .signs.n2 { grid-template-columns: 1fr 1fr } .signs.n3 { grid-template-columns: repeat(3, 1fr) }
.sg .ln { height: 36px; border-bottom: 1px solid var(--ink); margin-bottom: 4px } .sg b { display: block }
.sg span { display: block; font-size: 12px; color: var(--mute) } .sg b { display: inline } .sg .hold { display: inline; margin-left: 8px }
.foot { position: absolute; left: var(--mx); right: var(--mx); bottom: 22px; display: flex; justify-content: space-between;
        color: var(--mute); border-top: 1px solid var(--hair); padding-top: 5px }
.figs { display: grid; grid-template-columns: repeat(5, 1fr); column-gap: 12px; padding: 6px 0 2px }
.fig b { display: block; font-size: 12px; font-weight: 400; color: var(--mute) }
.fig span { font-size: 26px; font-weight: 600; line-height: 1.2 } .fig i { font-size: 12px; color: var(--mute); margin-left: 4px }
.gg { margin-top: 6px }
.chart { display: block } .plot .body { padding-top: 4px }
.tb { width: 100%; border-collapse: collapse } .tb th, .tb td { text-align: right; padding: 4px 8px; border-bottom: 1px solid var(--hair) }
.tb th { font-size: 12px; font-weight: 400; color: var(--mute); vertical-align: bottom; line-height: 1.25; border-bottom: 1px solid var(--ink) }
.tb th i { display: block } .tb .l { text-align: left; padding-left: 0 } .tb .pass { font-weight: 700 }
.note, .lead { color: var(--mute); margin-top: 4px } .lead { margin: 0 0 2px }
.fine { color: var(--mute); margin-top: 8px }
.multi { display: flex } figure figcaption { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 2px }
figure figcaption span { color: var(--mute) }
.meas .sec, .tech .sec, .cal .sec { margin-top: 16px }

.page { --ink: #141414; --mute: #5C5F66; --hair: #C9CCD1; --acc: #1D3557; --mx: 48px; --font: 'Sarabun', 'Leelawadee UI', sans-serif; font-size: 13px; --mt: 34px }
.hdr { padding-bottom: 8px; border-bottom: 3px double var(--ink) }
.mark { font-size: 24px } h1 { font-size: 26px; font-weight: 700 }
.meta { border-top: none; margin-top: 0 } .kv.ident { border-top: none; margin-top: 0 }
.sec h2 { text-transform: uppercase; letter-spacing: .6px; border-bottom: none; border-top: 1.5px solid var(--ink); padding-top: 4px; margin-bottom: 0 }
.sec h2 .no::after { content: "." }
.chk .it:first-of-type { border-top: 1px solid var(--ink) }
.verdict { border: 3px double var(--ink) } .vr { border-left: 1px solid var(--ink) } .vv { letter-spacing: 1px }
.tb th { border-bottom: 1.5px solid var(--ink) } .tb tbody tr:last-child td { border-bottom: 1.5px solid var(--ink) }
.fig { border-left: 1px solid var(--ink); padding-left: 10px } .fig.f0 { border-left: none; padding-left: 0 }

.page.infusion { --acc: #0B6FA4; --bar: #38BDF8; --tint: #E0F2FE }
.page.syringe { --acc: #B0306A; --bar: #F472B6; --tint: #FCE7F3 }
.page.a2::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 6px; background: var(--bar) }
.page.a2 { --mt: 30px }
.a2 .sub { font-size: 15px; font-weight: 700; letter-spacing: .3px }
.a2 .jobno, .a2 .dev, .a2 .fj { color: var(--acc); font-weight: 700 }
.a2 .sec h2 .en, .a2 h3 .en { display: inline; margin-left: auto; font-size: 12px; font-weight: 600; letter-spacing: 1px; color: #5A626C }
.a2 h3 { display: flex; align-items: baseline; font-size: 13px; color: var(--ink); letter-spacing: 0; border-bottom: 1px solid var(--ink);
         padding-bottom: 2px; margin-bottom: 3px }
.a2 .who h3 span:first-child { font-weight: 700 }
.a2 .pass, .a2 .vv { color: #166534 }
.a2 .ev { color: var(--acc) }
.a2 .meta.m4 { grid-template-columns: 1fr 1fr 1.2fr 1.2fr }
.a2 .meta > div + div { padding-left: 12px; border-left: 1px solid var(--hair) }
.a2 .chk .it { min-height: 21px }
.a2 .nm small { display: inline; margin-left: 8px; font-size: 12px }
/* แถบผลอัตราการไหล (Inspection หน้า 1) */
.flow { display: grid; grid-template-columns: 1fr 250px; align-items: end; column-gap: 12px; margin-top: 5px;
        padding: 4px 0 2px 12px; border-left: 3px solid var(--acc); background: #F6F8FA }
.flow .fl { grid-column: 1 / -1; display: flex; gap: 10px; align-items: baseline }
.flow .fl b { font-size: 12px; color: var(--acc); font-weight: 700 } .flow .fl em { font-size: 12px; color: var(--mute) }
.figs4 { display: grid; grid-template-columns: repeat(4, auto); column-gap: 22px; justify-content: start; padding-bottom: 4px }
.fs b { display: block; font-size: 12px; font-weight: 400; color: var(--mute); line-height: 1.3 }
.fs span { font-size: 19px; font-weight: 700; line-height: 1.25 } .fs i { font-size: 12px; font-weight: 400; color: var(--mute); margin-left: 3px }
.fs:nth-child(3) span { color: var(--acc) }
/* ความปลอดภัยทางไฟฟ้า แถวเดียว */
.safe2 { display: grid; grid-template-columns: 1fr 1.6fr auto; align-items: baseline; padding-top: 3px; column-gap: 18px }
.safe2 b { font-size: 12px; font-weight: 400; color: var(--mute); margin-right: 8px } .safe2 span { font-weight: 700 }
.safe2 em { font-size: 12px; color: var(--mute); margin-left: 10px }
.safe2 .sv { display: flex; align-items: center; gap: 6px }
/* อะไหล่ */
ol.parts2 { list-style: none; display: grid; grid-template-columns: repeat(3, 1fr); column-gap: 22px; counter-reset: p }
ol.parts2 li { counter-increment: p; display: flex; justify-content: space-between; gap: 6px; border-bottom: 1px solid var(--hair); padding: 2px 0 }
ol.parts2 li span::before { content: counter(p) "."; color: var(--mute); display: inline-block; min-width: 20px }
ol.parts2 li i { font-size: 12px; font-weight: 600; white-space: nowrap }
ol.parts2 li i.cl { color: #166534 } ol.parts2 li i.nw { color: var(--mute) }
.pfoot { display: flex; justify-content: space-between; font-size: 12px; color: var(--mute); margin-top: 3px }
.pfoot b { font-weight: 600; margin-right: 8px } .pfoot span:first-child { color: var(--ink) } .pfoot span:first-child b { color: var(--mute) }
/* กล่องสรุปผล + ตรวจขั้นสุดท้าย */
.a2 .verdict { margin-top: 10px }
.a2 .vt b { display: block; font-size: 13px; font-weight: 700; color: var(--ink) }
.fin2 { display: flex; gap: 20px; margin-top: 4px } .fin2 .opt { margin: 0 }
/* ลายเซ็น: ลายมือชื่อ + ชื่อ-นามสกุล ไม่มีวันที่ */
.signs3 { display: grid; column-gap: 24px; margin-top: 10px } .signs3.n2 { grid-template-columns: 1fr 1fr }
.signs3.n3 { grid-template-columns: repeat(3, 1fr) }
.sbox { border: 1px solid var(--hair); border-bottom: 1.4px solid var(--ink); background: #FAFBFC }
.shd { display: flex; justify-content: space-between; align-items: baseline; padding: 3px 10px 0 }
.srole { font-size: 13px; font-weight: 700 } .sen { font-size: 12px; color: var(--mute) }
.spad { height: 34px; display: flex; align-items: center; justify-content: center }
.spad span { font-size: 12px; color: #B4BAC1; letter-spacing: .3px }
.sname { text-align: center; font-weight: 600; color: var(--mute); padding-top: 3px; line-height: 1.3 }
.spos { text-align: center; font-size: 12px; color: var(--mute); line-height: 1.3 }
.signs2 { display: grid; column-gap: 30px; margin-top: 10px } .signs2.n2 { grid-template-columns: 1fr 1fr } .signs2.n3 { grid-template-columns: repeat(3, 1fr) }
.sg2 .role { font-weight: 700 } .sg2 .role span { font-weight: 400; font-size: 12px; color: var(--mute); margin-left: 8px }
.sg2 .line { display: grid; grid-template-columns: auto 1fr; align-items: end; column-gap: 8px; height: 22px }
.sg2 .line.tall { height: 28px } .sg2 .line span { font-size: 12px; color: var(--mute); line-height: 1.2 }
.sg2 .line i { border-bottom: 1px solid var(--ink); height: 100% }
/* หน้า 2 */
.figs.six { grid-template-columns: repeat(5, 1fr) 1.1fr } .figs.six .fig:nth-child(3) span { color: var(--acc) }
.a2 .gg { margin-top: 2px }
.mtag { margin-top: 6px } .mtag b { display: block; font-size: 12px; font-weight: 400; color: var(--mute) } .mtag { font-weight: 700; color: var(--acc) }
.rows.tight .row { padding: 1px 0; font-size: 12px }
.rows .row { display: flex; justify-content: space-between; gap: 10px; border-bottom: 1px solid #E3E6EA; padding: 2px 0; font-size: 12.5px; line-height: 1.35 }
.rows .row span:first-child { color: var(--mute) } .rows .row span:last-child { font-weight: 600; text-align: right }
.env { display: grid; grid-template-columns: repeat(5, 1fr); margin-top: 4px } .env.v4 { grid-template-columns: repeat(4, 1fr) } .env.v3 { grid-template-columns: repeat(3, 1fr) }
.env > div { padding: 2px 10px } .env > div:first-child { padding-left: 0 } .env > div + div { border-left: 1px solid var(--hair) }
.env b { display: block; font-size: 12px; font-weight: 400; color: var(--mute) } .env span { font-weight: 600 }
/* Calibration */
.a2 .tb td.mt { font-size: 12px; color: var(--acc); font-weight: 600; white-space: nowrap }
.errw { display: grid; grid-template-columns: 470px 1fr; column-gap: 22px; align-items: start }
.side .rows { margin-top: 4px }
.lg { display: flex; flex-direction: column; gap: 3px; margin-top: 8px; font-size: 12px; color: var(--mute) }
.lg span { display: flex; align-items: center; gap: 8px }
.lg i { display: inline-block; flex: none } .lg .pt { width: 9px; height: 9px; border-radius: 50%; background: var(--acc) }
.lg .fit { width: 20px; border-top: 2.2px dashed #D9691A } .lg .tolb { width: 18px; height: 9px; background: var(--tint); border-top: 1px dashed var(--acc); border-bottom: 1px dashed var(--acc) }
.rb { display: grid; grid-template-columns: 220px 1fr; column-gap: 22px; padding: 6px 0 4px; border-bottom: 1px solid var(--hair) }
.rb:last-child { border-bottom: none }
.rb .rt { display: flex; justify-content: space-between; align-items: baseline } .rb .rt b { font-size: 18px; font-weight: 700 }
.rb .mt { font-size: 12px; color: var(--acc); font-weight: 600; margin-bottom: 2px }
.tech .sec, .cal .sec, .meas .sec { margin-top: 12px }

.a2 .sec h2 { text-transform: none; letter-spacing: 0; font-size: 14px }
.page.a2::before { height: 4px }
.a2 .flow { background: none; border: 1px solid var(--hair); border-left: 3px solid var(--acc) }
.a2 .spad span { visibility: hidden }
.a2 .sbox { background: #fff }
.a2 .signs3 { margin-top: 7px }

.rb .rerr { display: flex; justify-content: space-between; align-items: baseline; margin: 2px 0 4px; padding: 2px 0 2px 9px;
            border-left: 3px solid var(--acc) }
.rb .rerr em { font-size: 12px; color: var(--mute) }
.rb .rerr b { font-size: 20px; font-weight: 700; color: var(--acc); white-space: nowrap }
.rb .rerr i { font-size: 13px; font-weight: 600; color: var(--mute); margin-left: 6px; white-space: nowrap }

.gv { display: flex; justify-content: space-between; align-items: flex-start }
.rb .rerr.lab { border-left-width: 2px; padding-left: 8px; margin: 3px 0 5px }
.rb .rerr.lab b { font-size: 18px }
.rb .rerr.lab i { font-size: 15px; font-weight: 600; color: var(--ink); margin-left: 5px; font-style: normal }
.rb .rerr.lab u { text-decoration: none; font-size: 13px; color: var(--mute); margin-left: 4px }
"""

EXTRA = r"""
.a2 .fail, .a2 .vv.fail { color: #B42318 }
.a2 ol.parts2 li.none { grid-column: 1 / -1; border-bottom: none; color: var(--mute) }
.a2 ol.parts2 li.none span::before { content: none }
.sname.set { color: var(--ink) }
.spad img { max-height: 34px; max-width: 80%; object-fit: contain }
.co .logo { max-height: 40px; max-width: 220px; display: block; margin-bottom: 2px }
.a2 .tb td.na, .a2 .na { color: var(--mute) }
.a2 .rows .row span.fail, .a2 .rt .fail { color: #B42318 }
/* ย่อเมื่อข้อมูลจริงยาวจนล้นหน้า — render.FIT_JS ใส่ทีละระดับเฉพาะหน้าที่ล้น (ข้อมูลปกติไม่ถูกแตะ หน้าตาเหมือนแบบ) */
.page.fit1 { --mt: 22px }
.page.fit1 .hdr { padding-bottom: 4px }
.page.fit1 .sec { margin-top: 6px }
.page.fit1 .who { margin-top: 4px }
.page.fit1 .chk .it { min-height: 18px; padding: 0 }
.page.fit1 .verdict { margin-top: 6px }
.page.fit1 .vr { padding: 2px 30px } .page.fit1 .vv { font-size: 26px }
.page.fit1 .signs3 { margin-top: 5px }
.page.fit1 .spad { height: 28px }
.page.fit1 .tb th, .page.fit1 .tb td { padding-top: 2px; padding-bottom: 2px }
.page.fit1 .flow { margin-top: 3px }
.page.fit2 { line-height: 1.3 }
.page.fit2 .kv dt, .page.fit2 .kv dd, .page.fit2 .chk .it, .page.fit2 ol.parts2 li, .page.fit2 .tb td { font-size: 12px }
.page.fit2 .chk .it { min-height: 16px }
.page.fit2 ol.parts2 li { padding: 0 }
.page.fit2 .note { margin-top: 2px }
.page.fit2 .env > div { padding-top: 0; padding-bottom: 0 }
.page.fit2 .rows .row { padding: 0 }
.page.fit3 ol.parts2 { display: block }
.page.fit3 ol.parts2 li { display: inline; border: none; padding: 0; margin-right: 12px }
.page.fit3 ol.parts2 li span::before { min-width: 0; margin-right: 4px }
.page.fit3 ol.parts2 li i { margin-left: 5px }
.page.fit3 .vt p { line-height: 1.25 }
"""

SCREEN = """
html, body { background: #E7E9EC }
.page { margin: 24px auto; box-shadow: 0 1px 5px rgba(0,0,0,.2) }
@media print { html, body { background: #fff } .page { margin: 0; box-shadow: none; break-after: page } }
"""
PRINT = """
html, body { background: #fff }
.page { break-after: page }
.page:last-child { break-after: auto }
"""


@lru_cache(maxsize=1)
def font_face() -> str:
    """@font-face ของ Sarabun 4 น้ำหนัก (ไฟล์ไม่ครบ = ข้าม ใช้ฟอนต์สำรอง Leelawadee UI ของ Windows)"""
    rules = []
    for weight, name in FONT_WEIGHTS.items():
        path = FONT_DIR / f"Sarabun-{name}.ttf"
        if not path.is_file():
            continue
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        rules.append(f"@font-face {{ font-family: 'Sarabun'; font-style: normal; font-weight: {weight}; "
                     f"src: url(data:font/ttf;base64,{data}) format('truetype') }}")
    return chr(10).join(rules)


def stylesheet(screen: bool = False) -> str:
    return (f"@page {{ size: {PAGE_W}px {PAGE_H}px; margin: 0 }}" + chr(10) + font_face() + chr(10) + TEMPLATE_CSS + EXTRA
            + (SCREEN if screen else PRINT))
