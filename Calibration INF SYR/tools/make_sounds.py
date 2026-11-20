"""สร้างเสียงของโปรแกรม (ui/assets/sounds/*.wav) — สังเคราะห์เองทั้งหมด ไม่ติดลิขสิทธิ์

    python tools/make_sounds.py          สร้าง/เขียนทับไฟล์ทั้งหมด

แนวเสียง: มาริมบา/ระฆังแก้วนุ่มๆ (sine + ฮาร์มอนิกบางๆ + เสียงตีเบาๆ ตอนต้น + จางแบบ exponential)
โน้ตอยู่ในบันไดเสียงเพนทาโทนิก C major (ฟังสบาย ไม่ขัดกันแม้เล่นซ้อน) · ดังไม่เกิน −6 dBFS · มี fade-in 3 ms กันเสียงคลิก
เปลี่ยนเสียง: แก้ SOUNDS ข้างล่างแล้วรันใหม่ (services/sounds.py โหลดตามชื่อไฟล์)
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

RATE = 44100
OUT = Path(__file__).resolve().parents[1] / "ui" / "assets" / "sounds"
NOTE = {"C4": 261.63, "E4": 329.63, "G4": 392.00, "A4": 440.00, "C5": 523.25, "D5": 587.33, "E5": 659.25,
        "G5": 783.99, "A5": 880.00, "C6": 1046.50, "E6": 1318.51, "G6": 1567.98}


def tone(freq: float, length: float, decay: float, volume: float = 1.0, bright: float = 0.25) -> np.ndarray:
    """โน้ตแนวมาริมบา: พื้นฐาน + ฮาร์มอนิกที่ 4 (ลักษณะไม้) + ฮาร์มอนิกที่ 10 จางเร็ว (เสียงตี)"""
    t = np.arange(int(RATE * length)) / RATE
    body = np.sin(2 * np.pi * freq * t) * np.exp(-t / decay)
    wood = bright * np.sin(2 * np.pi * freq * 3.98 * t) * np.exp(-t / (decay * 0.25))
    strike = 0.12 * np.sin(2 * np.pi * freq * 9.9 * t) * np.exp(-t / 0.006)
    out = (body + wood + strike) * volume
    fade = min(len(out), int(RATE * 0.003))
    out[:fade] *= np.linspace(0, 1, fade)
    return out


def sequence(notes: list[tuple[str, float, float]], length: float, decay: float, bright: float = 0.25) -> np.ndarray:
    """[(โน้ต, เวลาเริ่ม s, ความดัง)] รวมเป็นเสียงเดียว"""
    out = np.zeros(int(RATE * length))
    for name, start, volume in notes:
        part = tone(NOTE[name], length - start, decay, volume, bright)
        begin = int(RATE * start)
        part = part[:len(out) - begin]
        out[begin:begin + len(part)] += part
    return out


def tick() -> np.ndarray:
    """คลิก: เสียงไม้เคาะเบาๆ สั้นมาก (ไม่รบกวนแม้กดถี่)"""
    t = np.arange(int(RATE * 0.045)) / RATE
    body = np.sin(2 * np.pi * 1850 * t) * np.exp(-t / 0.0055)
    low = 0.5 * np.sin(2 * np.pi * 620 * t) * np.exp(-t / 0.009)
    out = body + low
    out[:40] *= np.linspace(0, 1, 40)
    return out


def beeps(freq: float, pattern: list[float], pulse: float, length: float, volume: float = 1.0) -> np.ndarray:
    """สัญญาณเตือนแบบทันสมัย (แนว IEC 60601-1-8): พัลส์เสียงสั้นขอบนุ่ม + ฮาร์มอนิก 2–3 ให้ได้ยินชัดในห้องเสียงดัง
    pattern = เวลาเริ่มของแต่ละพัลส์ (s)"""
    out = np.zeros(int(RATE * length))
    t = np.arange(int(RATE * pulse)) / RATE
    edge = int(RATE * 0.012)
    shape = np.ones(len(t))
    shape[:edge] = np.linspace(0, 1, edge)
    shape[-edge:] = np.linspace(1, 0, edge)
    wave_ = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2 * t)
             + 0.18 * np.sin(2 * np.pi * freq * 3 * t)) * shape * volume
    for start in pattern:
        begin = int(RATE * start)
        part = wave_[:max(0, len(out) - begin)]
        out[begin:begin + len(part)] += part
    return out


SOUNDS = {
    "click": lambda: tick() * 0.55,
    "toggle": lambda: sequence([("E6", 0.0, 0.45)], 0.12, 0.03, bright=0.15),
    "start": lambda: sequence([("C5", 0.0, 0.8), ("G5", 0.09, 0.8)], 0.7, 0.18),
    "stop": lambda: sequence([("G5", 0.0, 0.75), ("C5", 0.10, 0.75)], 0.7, 0.18),
    "pass": lambda: sequence([("C5", 0.0, 0.7), ("E5", 0.10, 0.7), ("G5", 0.20, 0.75), ("C6", 0.32, 0.6)], 1.4, 0.32),
    "fail": lambda: sequence([("E4", 0.0, 0.85), ("C4", 0.16, 0.9)], 1.1, 0.30, bright=0.15),
    "invalid": lambda: sequence([("A4", 0.0, 0.8), ("A4", 0.18, 0.8)], 0.9, 0.22, bright=0.15),
    "notify": lambda: sequence([("G5", 0.0, 0.6), ("E6", 0.08, 0.5)], 0.8, 0.22),
    "saved": lambda: sequence([("E5", 0.0, 0.55), ("A5", 0.07, 0.6)], 0.8, 0.25),
    # ---- ระบบความปลอดภัยของบีกเกอร์ (ผู้ใช้ 2026-11-20)
    # remind = เตือนนุ่ม "ทดสอบเสร็จแล้ว หยุดปั๊มได้" (เล่นเป็นจังหวะ) · warn = ใกล้เต็ม · alarm = จะล้น/ล้น (ดัง ชัด เร่งด่วน)
    "remind": lambda: sequence([("A5", 0.0, 0.55), ("E5", 0.16, 0.5)], 0.9, 0.22, bright=0.12),
    "warn": lambda: beeps(880.0, [0.0, 0.22, 0.44], 0.15, 0.75),
    "alarm": lambda: beeps(988.0, [0.0, 0.16, 0.32, 0.72, 0.88], 0.11, 1.15),
}
# ความดังสูงสุดของแต่ละเสียง (สัดส่วนของเต็มสเกล) — ค่าเริ่มต้น −6 dBFS · สัญญาณเตือนดังกว่าเพื่อให้ได้ยินแน่
LEVEL = {"alarm": 0.89, "warn": 0.71}


def write(name: str, samples: np.ndarray) -> Path:
    peak = float(np.max(np.abs(samples))) or 1.0
    samples = samples / peak * LEVEL.get(name, 0.5)     # −6 dBFS (สัญญาณเตือนดังกว่า)
    data = (samples * 32767).astype("<i2")
    path = OUT / f"{name}.wav"
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(data.tobytes())
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, make in SOUNDS.items():
        print(write(name, make()))


if __name__ == "__main__":
    main()
