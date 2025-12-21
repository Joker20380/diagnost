import os
from django.core.management.base import BaseCommand
from diagnostics.models import DiagnosticSession
from diagnostics.analyzer import analyze_dtc

UPLOAD_DIR = '/home/joker2038/diagnostics_uploads'

class Command(BaseCommand):
    help = 'Импорт файлов диагностики из FTP-папки'

    def handle(self, *args, **kwargs):
        for filename in os.listdir(UPLOAD_DIR):
            if filename.endswith('.json') or filename.endswith('.txt'):  # Укажи нужные форматы
                file_path = os.path.join(UPLOAD_DIR, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        session = DiagnosticSession.objects.create(
                            vin='UNKNOWN',
                            raw_data=content
                        )
                        analyze_dtc(session)  # если используешь анализатор
                        print(f"[+] Загружен файл: {filename}")
                    os.remove(file_path)
                except Exception as e:
                    print(f"[!] Ошибка при обработке {filename}: {e}")