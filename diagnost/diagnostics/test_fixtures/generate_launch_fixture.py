"""Generate the anonymized Launch parser regression fixture.

This script is not used by the application. It requires reportlab and is kept so
the committed binary fixture can be regenerated and audited.
"""

import os
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


FIXTURE_PATH = Path(__file__).with_name("launch_anonymized_report.pdf")


def main() -> None:
    font_path = Path(os.environ.get(
        "FIXTURE_FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ))
    pdfmetrics.registerFont(TTFont("FixtureFont", font_path))

    document = canvas.Canvas(
        str(FIXTURE_PATH),
        pagesize=(595, 842),
        invariant=1,
        pageCompression=0,
    )
    document.setFont("FixtureFont", 10)
    y = 810
    lines = [
        "Launch X-431 — All System Diagnostic Report",
        "Время испытания: 2026-08-16 10:30",
        "Год выпуска: 2018",
        "Серии а/м: BMW",
        "Модель: X3",
        "VIN: TESTVIN1234567890",
        "Пробег: 123456 km",
        "Версия ПО а/м: 2024.01",
        "Версия диагностической прикладной программы: V12.50",
        "Диагностический путь: Automatically Search",
        "Серийный номер: ANONYMIZED",
        "",
        "The following systems is abnormal:",
        "DME (Digital Motor Electronics) 2 Существуют проблемы",
        "1.P0300 Обнаружены множественные пропуски зажигания",
        "Current",
        "2.930AB2 Контрольная лампа двигателя",
        "Intermittent",
        "",
        "Следующие системы в порядке:",
        "1.ABS (Антиблокировочная система)",
    ]
    for line in lines:
        document.drawString(36, y, line)
        y -= 18
    document.save()


if __name__ == "__main__":
    main()
