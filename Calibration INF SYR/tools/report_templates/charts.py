# ข้อมูลสมมติสำหรับกราฟของแบบ G–P (กำหนดได้ ไม่สุ่มใหม่)
import math
s = 12345
def rnd():
    global s
    s = (s * 16807) % 2147483647
    return s / 2147483647 - 0.5
def gauss():
    return (rnd() + rnd() + rnd()) / 1.5

# G: start-up curve 0–120 min ทุก 2 นาที, flow ml/h; กราฟ x 50..690, y = 170 - (q-40)*7.5 (40..60 ml/h)
pts = []
for i in range(61):
    t = i * 2
    q = 50.2 * (1 - math.exp(-t / 2.5)) + 0.35 * gauss()
    x = 50 + 640 * t / 120; y = 170 - (q - 40) * 7.5
    pts.append(f"{x:.0f},{max(y,10):.1f}")
print("STARTUP", " ".join(pts))

# M: สัญญาณน้ำหนัก 0–60 s (period 15.2 s), x 40..520 (8 px/s), weight 0..0.85 g -> y 120..20
T = 15.2; Q = 50.42 / 3600  # g/s
w = 0; wp = []; fp = []; peaks = []
prev = None
for i in range(0, 301):
    t = i * 0.2
    f = Q * (1 + 0.95 * math.sin(2 * math.pi * t / T - 1.2))
    w += f * 0.2
    x = 40 + 8 * t
    if i % 2 == 0:
        wp.append(f"{x:.0f},{120 - w / 0.85 * 100:.1f}")
        fl = f * 3600 + 3 * gauss()
        fp.append(f"{x:.0f},{110 - fl * 0.9:.1f}")
print("WEIGHT", " ".join(wp))
print("FLOW", " ".join(fp))
# จุด peak ของ flow: sin max at 2πt/T - 1.2 = π/2
for k in range(4):
    t = (math.pi / 2 + 1.2) * T / (2 * math.pi) + k * T
    if t <= 60: print("TOP", f"{40 + 8 * t:.0f}")
    t2 = t + T / 2
    if t2 <= 60: print("DOWN", f"{40 + 8 * t2:.0f}")

# P: histogram 58 ค่า flow รายรอบ 50 ml/h, bins 48.5..52.5 step .25
vals = [50.42 + 0.62 * gauss() * 1.7 for _ in range(58)]
bins = [0] * 16
for v in vals:
    b = int((v - 48.5) / 0.25)
    if 0 <= b < 16: bins[b] += 1
print("HIST", bins, sum(bins))
