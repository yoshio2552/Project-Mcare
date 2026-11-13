"""popup ชุดสายต่างจากมาตรฐานของโรงพยาบาล (wizard ขั้น 1 -> 2)

โรงพยาบาลนี้ใช้ IV set / syringe ใดกับเครื่องรุ่นนี้เป็นมาตรฐาน (ตาราง site_accessory_standards) —
ถ้าครั้งนี้กรอกต่างจากเดิม ให้ผู้ใช้เลือก:
    temporary     ใช้ชั่วคราว (ครั้งนี้เท่านั้น — มาตรฐานเดิมคงไว้)
    new_standard  เปลี่ยนมาใช้รุ่นนี้ถาวร (ตั้งเป็นมาตรฐานใหม่ตอนสร้างการทดสอบ)
    None          กลับไปแก้
ผลเก็บใน JobInfo.accessory_usage + คอลัมน์ sessions.iv_set_usage (สถิติ: โรงพยาบาลไหนใช้ชุดสายอะไร)
"""
from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from config.i18n import tr


def ask_accessory_change(parent, site: str, device: str, kind: str, standard: str, new: str) -> str | None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(tr("{kind} differs from before", kind=kind))
    box.setText(tr("{site} usually uses {standard} with {device}.\nThis time: {new}", site=site,
                   standard=standard, device=device, new=new))
    box.setInformativeText(tr("Is this a temporary change, or the new standard for this hospital?"))
    temporary = box.addButton(tr("Temporary (this time only)"), QMessageBox.ButtonRole.AcceptRole)
    permanent = box.addButton(tr("New standard from now on"), QMessageBox.ButtonRole.AcceptRole)
    box.addButton(tr("Go back and edit"), QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(temporary)
    box.exec()
    clicked = box.clickedButton()
    if clicked is temporary:
        return "temporary"
    if clicked is permanent:
        return "new_standard"
    return None
