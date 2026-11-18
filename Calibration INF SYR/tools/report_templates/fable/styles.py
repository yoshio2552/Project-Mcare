"""หน้าตาของแบบ FableA–E — โครง HTML เดียวกัน (blocks.py) ต่างกันที่ CSS + ค่าของแบบ

แนวร่วม: เอกสารพิมพ์ ไม่ใช่หน้าเว็บ — ไม่มีมุมโค้ง เงา ป้ายแคปซูล ไล่สี · ตัวอักษรไม่เล็กกว่า 12 px
ผล "ผ่าน" เป็นตัวหมึกเข้ม พิมพ์ขาวดำได้ · สีเน้นมีสีเดียวต่อแบบ
"""

BASE = """
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
"""

# ---------------------------------------------------------------- A · Ledger: ใบงานวิศวกรรมแบบเส้นหมึก
A = """
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
"""

# ---------------------------------------------------------------- B · Editorial: หัวข้ออยู่ขอบซ้าย ตัวมีหัว
B = """
.page { --ink: #1B1B19; --mute: #66665F; --hair: #D6D4CC; --acc: #1F5A44; --mx: 44px; --mt: 46px;
        --font: 'Noto Sans Thai Looped', 'Leelawadee UI', sans-serif; font-size: 12.5px; line-height: 1.45 }
.hdr { grid-template-columns: auto 1fr; grid-template-areas: "ttl co" "ttl pg" }
.ttl { text-align: left } .co { text-align: right; align-self: end } .mark { font-size: 17px; font-family: 'Noto Serif Thai', serif }
h1 { font-family: 'Noto Serif Thai', serif; font-size: 30px; font-weight: 600; letter-spacing: -.2px } .kind { letter-spacing: 2.4px }
.sub { font-family: 'Noto Serif Thai', serif; font-size: 15px }
.meta { border-top: 1px solid var(--ink) }
.who h3, .two h3 { font-family: 'Noto Serif Thai', serif; font-size: 13px; color: var(--ink) }
.sec { display: grid; grid-template-columns: 128px 1fr; column-gap: 18px; border-top: 1px solid var(--ink); padding-top: 6px; margin-top: 11px }
.sec h2 { display: block; border: none; font-family: 'Noto Serif Thai', serif; font-size: 14px; line-height: 1.3; margin: 0; padding: 0 }
.sec h2 .no { display: block; font-size: 22px; font-weight: 400; line-height: 1 ; margin-bottom: 2px }
.pair { display: block } .chk { column-gap: 22px }
.chk .hd, .chk .cols { display: none } .word { display: inline; color: var(--acc); font-weight: 600 }
.word::before { content: "✓ "; font-family: 'Segoe UI Symbol', sans-serif }
.fin { flex-direction: row; gap: 22px }
.verdict { border: none; border-top: 1px solid var(--ink); border-bottom: 1px solid var(--ink); margin-top: 12px }
.vr { border: none; text-align: right; padding: 4px 0 4px 24px } .vt { padding: 8px 0 }
.vv { font-family: 'Noto Serif Thai', serif; font-size: 36px; font-weight: 600; color: var(--acc) }
.signs { margin-top: 14px } .fig span { font-family: 'Noto Serif Thai', serif; font-size: 24px }
.figs { column-gap: 8px } .meas .sec, .tech .sec, .cal .sec { margin-top: 13px }
.tb th, .tb td { padding: 4px 5px } .kv.wide { --kw: 170px } ol.parts { columns: 2 }
"""

# ---------------------------------------------------------------- C · Datasheet: แถบหัวหมึกเข้ม ตัวเลข mono
C = """
.page { --ink: #101828; --mute: #5B6474; --hair: #D0D5DD; --acc: #0B6FAE; --mx: 46px; --mt: 0px;
        --font: 'IBM Plex Sans Thai', 'Leelawadee UI', sans-serif; font-size: 12.8px }
.syringe { --acc: #B02E74 }
.hdr { background: var(--ink); color: #fff; margin: 0 calc(-1 * var(--mx)); padding: 26px var(--mx) 14px; border-bottom: 5px solid var(--acc) }
.hdr .coaddr, .hdr .kind, .hdr .pg { color: #C3CAD6 } .hdr .sub { color: #fff } .hdr .sub .alt { color: #C3CAD6 }
.mark { font-family: 'IBM Plex Mono', monospace; font-size: 20px; letter-spacing: 0 } h1 { font-size: 24px }
.meta { background: #F0F2F5; margin: 0 calc(-1 * var(--mx)); padding: 0 var(--mx); border: none }
.jobno, .fig span, .tb td, .kv.ident dd { font-family: 'IBM Plex Mono', 'IBM Plex Sans Thai', monospace }
.tb td.l, .tb td.pass { font-family: inherit } .tb td.l b { font-family: 'IBM Plex Mono', monospace }
.kv.ident { background: #F0F2F5; margin: 0 calc(-1 * var(--mx)); padding: 7px var(--mx); border: none }
.sec h2 { border: none; text-transform: uppercase; letter-spacing: 1px; font-size: 13px; align-items: center; margin-bottom: 2px }
.sec h2 .no { font-family: 'IBM Plex Mono', monospace; background: var(--ink); color: #fff; padding: 0 6px; font-weight: 500 }
.sec h2 .no::before { content: "0" }
.sec h2::after { content: ""; flex: 1; border-top: 1px solid var(--ink) }
.bx { border-width: 1px } .bx.on { background: var(--ink) } .bx.on::after { border-color: #fff; left: 3.6px; top: 0 }
.verdict { border: none; background: var(--ink); color: #fff } .vt b, .vl { color: #C3CAD6 }
.vr { border-left: 1px solid #5B6474 } .vv { font-family: 'IBM Plex Mono', 'IBM Plex Sans Thai', monospace }
.verdict .bx { border-color: #fff }
.tb thead th { background: #F0F2F5; padding-top: 5px; border-bottom: none } .tb .l { padding-left: 8px }
.figs { background: #F0F2F5; padding: 8px 10px } .fig span { font-size: 24px; font-weight: 500 }
"""

# ---------------------------------------------------------------- D · Form: แบบฟอร์มตีช่อง ผลเป็นช่องติ๊ก
D = """
.page { --ink: #1E2124; --mute: #585E66; --hair: #9AA1A9; --acc: #0F5E6E; --mx: 40px; --mt: 30px;
        --font: 'Bai Jamjuree', 'Leelawadee UI', sans-serif; font-size: 12.6px }
.hdr { border: 1.2px solid var(--ink); padding: 8px 12px; align-items: center } h1 { font-size: 23px } .mark { font-size: 21px }
.meta { margin-top: -1.2px; border: 1.2px solid var(--ink); grid-template-columns: 1fr 1fr 2.6fr }
.meta > div { padding: 4px 12px; border-left: 1px solid var(--hair) } .meta > div:first-child { border-left: none }
.who { margin-top: 7px; column-gap: 12px }
.who > div, .two > div { border: 1px solid var(--hair) } .two { column-gap: 12px }
.who h3, .two h3 { background: #ECEEF0; color: var(--ink); padding: 2px 10px; margin: 0; border-bottom: 1px solid var(--hair) }
.who .kv, .two .kv, .two p { padding: 3px 10px } .two .note { margin: 0; padding-top: 0 }
.sec { margin-top: 7px; border: 1px solid var(--hair) }
.sec h2 { background: #ECEEF0; border-bottom: 1px solid var(--hair); padding: 2px 10px 2px 0; margin: 0; align-items: stretch; font-size: 13.5px }
.sec h2 .no { background: var(--ink); color: #fff; min-width: 26px; text-align: center; margin-right: 2px }
.sec .body { padding: 2px 10px 3px }
.pair { column-gap: 12px } .pair .sec { margin-top: 7px }
.chk { column-gap: 20px } .chk .it { border-top: 1px dotted var(--hair) }
.verdict { margin-top: 7px; border: 1.2px solid var(--ink) } .vr { border-left: 1.2px solid var(--ink); text-align: left; padding: 8px 18px }
.vv { display: none } .vticks { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 600 } .vticks .bx { width: 17px; height: 17px; margin-left: 10px }
.vticks .bx:first-child { margin-left: 0 } .vticks .bx.on::after { left: 4.6px; top: 0; width: 5px; height: 11px; border-width: 0 2.2px 2.2px 0 }
.fv .vv { display: inline }
.signs { margin-top: 7px; column-gap: 12px } .sg { border: 1px solid var(--hair); padding: 0 10px 4px } .sg .ln { height: 32px }
.figs { column-gap: 0; padding: 0; margin: 4px 0 } .fig { border: 1px solid var(--hair); border-left: none; padding: 4px 10px } .fig.f0 { border-left: 1px solid var(--hair) }
.fig span { font-size: 23px }
.kv.ident { border: 1.2px solid var(--ink); margin-top: -1.2px; padding: 4px 12px }
.meas .sec, .tech .sec, .cal .sec { margin-top: 10px } .fine { margin-top: 8px }
.tb .l { padding-left: 4px }
"""

# ---------------------------------------------------------------- E · Quiet: ผลขึ้นก่อน ตัวเลขใหญ่ พื้นที่ว่างมาก
E = """
.page { --ink: #111111; --mute: #6B6B6B; --hair: #DADADA; --acc: #2443C0; --mx: 56px; --mt: 44px;
        --font: 'Anuphan', 'Leelawadee UI', sans-serif; font-size: 12.8px }
.hdr { grid-template-columns: 1fr auto; grid-template-areas: "ttl co" "ttl pg"; align-items: start }
.ttl { text-align: left } .co { text-align: right } .mark { font-size: 15px; letter-spacing: 0 } .coname { display: none }
h1 { font-size: 32px; font-weight: 300; letter-spacing: -.6px; line-height: 1.15 } .kind { letter-spacing: 3px; margin-bottom: 2px }
.sub { font-size: 15px; font-weight: 500 }
.meta { border-top: 1px solid var(--ink); border-bottom: none; margin-top: 14px }
.verdict { border: none; border-top: 1px solid var(--hair); border-bottom: 1px solid var(--hair); margin-top: 4px; grid-template-columns: auto 1fr }
.vr { order: -1; border: none; text-align: left; padding: 6px 28px 6px 0; min-width: 0 } .vl { display: none }
.vv { font-size: 46px; font-weight: 300; letter-spacing: -1px; line-height: 1.1 } .vt { padding: 10px 0; align-self: center }
.sec { margin-top: 12px } .sec h2 { border: none; font-size: 12px; font-weight: 600; letter-spacing: 1.6px; text-transform: uppercase; color: var(--mute); margin-bottom: 1px }
.sec h2 .no { color: var(--acc) }
.chk .hd, .chk .cols { display: none } .word { display: inline; font-weight: 500 }
.word::before { content: ""; display: inline-block; width: 7px; height: 7px; background: var(--acc); margin-right: 7px; vertical-align: 1px }
.chk .it { border-top: 1px solid var(--hair) }
.signs { margin-top: 10px }
.fig span { font-size: 34px; font-weight: 300; letter-spacing: -.8px } .fig.fv span { font-weight: 600 }
.tb th { border-bottom: 1px solid var(--hair) } .kv.ident { border-top: 1px solid var(--ink); border-bottom: none }
.foot { border-top: none }
"""


# ---------------------------------------------------------------- F · หน้าตาแบบ A-TH เดิม (ผู้ใช้ชอบแบบนี้) กับโครงเนื้อหาใหม่
F = """
.page { --ink: #111827; --mute: #6B7280; --hair: #D1D5DB; --acc: #0B6FAE; --bar: #38BDF8; --mx: 48px; --mt: 34px;
        --font: 'IBM Plex Sans Thai', 'Leelawadee UI', sans-serif; font-size: 12.8px }
.syringe { --acc: #B02E74; --bar: #F472B6 }
.page::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 6px; background: var(--bar) }
.hdr { grid-template-columns: auto 1fr auto; grid-template-areas: "mk co ttl" "mk co pg"; align-items: start; padding-bottom: 12px }
.co { display: contents } .mark { grid-area: mk; border: 1px solid #9CA3AF; width: 52px; height: 52px; display: flex; align-items: center;
      justify-content: center; font-size: 12px; font-weight: 600; letter-spacing: .4px; color: #4B5563; margin-right: 14px }
.coname { grid-area: co; font-size: 15px; font-weight: 700; align-self: start; margin-top: 2px }
.coaddr { grid-area: co; align-self: start; margin-top: 26px }
.ttl { display: flex; flex-direction: column; align-items: flex-end }
h1 { font-size: 25px; font-weight: 700; order: 1 } .kind { order: 2; letter-spacing: 1.8px; margin-top: 1px } .sub { order: 3; font-size: 13px }
.meta { border-top: 2px solid var(--ink); border-bottom: 1px solid var(--hair); margin-top: 0; grid-template-columns: 1fr 1fr 2.4fr }
.meta > div { padding: 6px 0 7px 12px; border-left: 1px solid var(--hair) } .meta > div:first-child { padding-left: 0; border-left: none }
.meta span { font-size: 14px } .meta .opt { font-size: 12.8px }
.kv.ident { border-top: 2px solid var(--ink); margin-top: 0 } .kv.ident dd { font-size: 13.5px; font-weight: 600 }
h3 { display: flex; justify-content: space-between; align-items: baseline; font-size: 14px; color: var(--ink); letter-spacing: 0;
     padding-bottom: 3px; border-bottom: 1px solid var(--ink); margin-bottom: 3px }
h3 .en, .sec h2 .en { display: inline; font-size: 12px; font-weight: 600; letter-spacing: 1px; color: #4B5563 }
.sec h2 .en { margin-left: auto }
.sec h2 .no { font-family: 'IBM Plex Mono', monospace; font-weight: 500; font-size: 13px } .sec h2 .no::before { content: "0" }
.two h3 .en { display: none } .who h3 .en { display: inline }
.chk .hd { background: #F3F4F6; padding: 3px 8px; margin-top: 2px } .chk .it { padding: 1px 8px }
.chk.nohd .it:nth-child(-n+2) { border-top: none }
.tb thead th { background: #F3F4F6; border-bottom: 1px solid var(--hair); padding-top: 5px } .tb .l { padding-left: 8px }
.verdict { border: 1.5px solid var(--ink) } .vt b { display: block; font-size: 13px; color: var(--ink); font-weight: 700 }
.vr { border-left: 1.5px solid var(--ink) } .vv, .tb .pass, .safe .okw { color: #166534 }
.figs { border-top: 1px solid var(--hair); border-bottom: 1px solid var(--hair); padding: 8px 0 }
.fig { border-left: 1px solid var(--hair); padding-left: 12px } .fig.f0 { border-left: none; padding-left: 0 }
.foot { font-family: 'IBM Plex Mono', 'IBM Plex Sans Thai', monospace }
.sec { margin-top: 8px } .meas .sec, .tech .sec, .cal .sec { margin-top: 13px } .signs { margin-top: 6px } .sg .ln { height: 32px }
"""


def chart(ink, mute, hair, acc, band, font):
    return dict(ink=ink, mute=mute, hair=hair, acc=acc, band=band, font=font)


VARIANTS = {
    "FableA": dict(
        name="Ledger", css=A, bw=698, builder="a",        # รุ่น 2 (2026-11-18): หน้า + CSS ของตัวเองใน a.py
        fonts="family=Sarabun:wght@400;500;600;700",
        chart=chart("#141414", "#5C5F66", "#C9CCD1", "#1D3557", "#E9EDF3", "Sarabun, sans-serif"),
        note="ใบงานวิศวกรรมแบบเส้นหมึก: เส้นคู่ใต้หัว หัวข้อตัวพิมพ์ใหญ่มีเส้นบน ช่องติ๊ก ผ่าน / ไม่ผ่าน / ไม่มี ผลอยู่ในกรอบเส้นคู่ · ฟอนต์ Sarabun"),
    # แบบย่อยของ FableA (2026-11-18) — แยกโฟลเดอร์ ไม่ทับตัวหลัก · โครงเดียวกับ a.py ต่างกันที่ตัวเลือก
    "FableA1": dict(
        name="Form control", css=None, bw=698, builder="a", opts=dict(control=True, quiet=True),
        fonts="family=Sarabun:wght@400;500;600;700",
        chart=chart("#141414", "#5C5F66", "#C9CCD1", "#1D3557", "#E9EDF3", "Sarabun, sans-serif"),
        note="เอกสารควบคุม: เลขแบบฟอร์ม + ครั้งที่แก้ไขที่หัวและท้ายกระดาษ · ลดสีและป้ายซ้ำ หัวข้อตัวพิมพ์ปกติ ตัวเลขผลเป็นหมึกดำ"),
    "MainFable": dict(
        name="Main Fable", folder="Main Fable", css=None, bw=698, builder="a",
        opts=dict(control=True, main=True, rate_error=True),
        fonts="family=Sarabun:wght@400;500;600;700",
        chart=chart("#141414", "#5C5F66", "#C9CCD1", "#1D3557", "#E9EDF3", "Sarabun, sans-serif"),
        note="แบบหลักที่เลือก (2026-11-18): FableA1 + ค่าคลาดเคลื่อน ± U สีตามชนิดเครื่องที่หัวของแต่ละ rate ในหน้าเทคนิค "
             "+ สีค่าคลาดเคลื่อนแบบ FableA3 + ป้ายหัวข้อภาษาอังกฤษด้านขวาในฉบับไทย"),
    "MainFable1": dict(
        name="Main Fable-1", folder="Main Fable-1", css=None, bw=698, builder="a",
        opts=dict(main=True, rate_error=True, lab=True),   # ไม่มีเลขแบบฟอร์ม (ผู้ใช้ขอ)
        fonts="family=Sarabun:wght@400;500;600;700",
        chart=chart("#141414", "#5C5F66", "#C9CCD1", "#1D3557", "#E9EDF3", "Sarabun, sans-serif"),
        note="Main Fable + หน้าเทคนิคไม่ซ้ำค่า: คลาดเคลื่อน ± U ขึ้นที่เดียวต่อ rate แบบ −1.3 ± 0.9 % · กราฟรวมไม่มีป้ายตัวเลข "
             "· กราฟราย rate มีมาตรวัดแนวตั้งด้านขวา"),
    "FableA2": dict(
        name="Summary first", css=None, bw=698, builder="a", opts=dict(summary_top=True, inline_gauge=True),
        fonts="family=Sarabun:wght@400;500;600;700",
        chart=chart("#141414", "#5C5F66", "#C9CCD1", "#1D3557", "#E9EDF3", "Sarabun, sans-serif"),
        note="ผลขึ้นก่อน: กล่องสรุปผลอยู่ใต้แถบข้อมูลงาน · ตารางผลสอบเทียบมีมาตรวัดเล็กราย rate แสดง error ± U ในเกณฑ์"),
    "FableA3": dict(
        name="Compact checks + remarks", css=None, bw=698, builder="a", opts=dict(compact_checks=True, remarks=True),
        fonts="family=Sarabun:wght@400;500;600;700",
        chart=chart("#141414", "#5C5F66", "#C9CCD1", "#1D3557", "#E9EDF3", "Sarabun, sans-serif"),
        note="ตารางติ๊กกระชับ 4 คอลัมน์ (ลดเส้นและช่องว่างที่ซ้ำ) · เพิ่มช่องหมายเหตุ 2 บรรทัดแบบใบงานเดิมของบริษัท"),
    "FableB": dict(
        name="Editorial", css=B, bw=794 - 88 - 128 - 18,
        fonts="family=Noto+Sans+Thai+Looped:wght@400;500;600&family=Noto+Serif+Thai:wght@400;600",
        chart=chart("#1B1B19", "#66665F", "#D6D4CC", "#1F5A44", "#E8EFEA", "Noto Sans Thai Looped, sans-serif"),
        note="หัวข้ออยู่คอลัมน์ขอบซ้ายแบบหนังสือ หัวเรื่องตัวมีเชิง เนื้อความตัวมีหัว รายการตรวจเป็นคำ ผ่าน สีเขียวเข้ม ผลเป็นตัวอักษรใหญ่ระหว่างเส้นบาง"),
    "FableC": dict(
        name="Datasheet", css=C, bw=702,
        fonts="family=IBM+Plex+Sans+Thai:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600",
        chart=chart("#101828", "#5B6474", "#D0D5DD", "#0B6FAE", "#E6EEF5", "IBM Plex Sans Thai, sans-serif"),
        note="แถบหัวหมึกเข้มเต็มกว้าง เส้นสีตามชนิดเครื่อง ฟ้า Infusion ชมพู Syringe เลขหัวข้อในกล่องดำ ตัวเลข mono ผลเป็นแถบกลับสี"),
    "FableD": dict(
        name="Form", css=D, bw=714 - 22,
        fonts="family=Bai+Jamjuree:wght@400;500;600;700",
        chart=chart("#1E2124", "#585E66", "#9AA1A9", "#0F5E6E", "#E5EEF0", "Bai Jamjuree, sans-serif"),
        note="แบบฟอร์มตีช่องทุกส่วน หัวข้อแถบเทามีเลขในช่องดำ ผลเป็นช่องติ๊ก ผ่าน / ไม่ผ่าน ลายเซ็นอยู่ในกรอบ · ใกล้ใบงานเดิมของบริษัทที่สุด"),
    "FableF": dict(
        name="A-TH", css=None, bw=698, builder="f",       # หน้า + CSS ของตัวเองทั้งหมด (f.py) ยกจากแบบ A-TH
        fonts="family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Thai:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700",
        chart=chart("#111827", "#6B7280", "#D1D5DB", "#1F2937", "#EEF2F6", "IBM Plex Sans Thai, sans-serif"),
        note="หน้าตาแบบ A-TH เดิม: แถบสีบนตามชนิดเครื่อง เลขหัวข้อ 01 + ชื่อไทย + ป้ายอังกฤษชิดขวา หัวตารางเทา ผลในกรอบตัวเขียว · โครงเนื้อหาใหม่"),
    "FableE": dict(
        name="Quiet", css=E, bw=682, verdict_top=True,
        fonts="family=Anuphan:wght@300;400;500;600",
        chart=chart("#111111", "#6B6B6B", "#DADADA", "#2443C0", "#E9ECF8", "Anuphan, sans-serif"),
        note="ผลขึ้นก่อนเป็นตัวบางขนาดใหญ่ใต้หัวเอกสาร เส้นบางอย่างเดียว พื้นที่ว่างมาก รายการตรวจเป็นจุดสีน้ำเงินกับคำ ผ่าน ตัวเลขผลวัดขนาดใหญ่"),
}
