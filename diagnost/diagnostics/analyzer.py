import os
import json

# Путь до файла
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DTC_JSON_PATH = os.path.join(BASE_DIR, 'dtc_data.json')

# Загружаем один раз при импорте модуля
with open(DTC_JSON_PATH, 'r', encoding='utf-8') as f:
    DTC_DATABASE = json.load(f)


def analyze_dtc(codes: list[str]) -> str:
    """
    Принимает список DTC-кодов (например, ['P0171', 'P0300']),
    возвращает текстовое заключение с рекомендациями.
    """
    report = []
    for code in codes:
        data = DTC_DATABASE.get(code)
        if data:
            report.append(f"{code} — {data['description']}\n→ {data['recommendation']}")
        else:
            report.append(f"{code} — Неизвестный код\n→ Нет рекомендаций.")
    return "\n\n".join(report)