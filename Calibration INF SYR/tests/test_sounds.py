"""เสียงของโปรแกรม (services/sounds.py) + ไฟล์ที่สังเคราะห์ (tools/make_sounds.py)"""
import os
import unittest
import wave

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from config.settings import AppSettings
from services import sounds


class SoundsTest(unittest.TestCase):
    def test_every_sound_file_exists_and_is_short_mono(self):
        for name in sounds.NAMES:
            path = sounds.SOUND_DIR / f"{name}.wav"
            self.assertTrue(path.is_file(), name)
            with wave.open(str(path)) as f:
                self.assertEqual(f.getnchannels(), 1)
                self.assertLess(f.getnframes() / f.getframerate(), 2.0, name)     # สั้น ไม่ค้างหู

    def test_settings_and_silence_without_screen(self):
        ui = AppSettings().ui
        self.assertTrue(ui.sounds and ui.sound_clicks)
        self.assertEqual(ui.sound_volume, 60)
        player = sounds.SoundPlayer()
        player.configure(AppSettings())
        self.assertFalse(player.enabled)            # offscreen (เทสต์) ไม่ส่งเสียง
        player.play("pass")                          # ไม่ error แม้ยังไม่โหลด
        player.click()


if __name__ == "__main__":
    unittest.main()
