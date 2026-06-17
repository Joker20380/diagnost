from django.core.management.base import BaseCommand
from django.utils.text import slugify

from diagnostics.models import (
    DTCImportBatch,
    DTCReference,
    DiagnosticCode,
    VehicleBrand,
)


BASIC_DTC = [
    {
        "code": "P0100",
        "title_ru": "Неисправность цепи датчика массового или объёмного расхода воздуха",
        "title_en": "Mass or Volume Air Flow Circuit Malfunction",
        "description_ru": "Код связан с цепью датчика MAF/VAF. Причина может быть в датчике, проводке, разъёме, подсосе воздуха или питании датчика.",
        "symptoms": "Потеря мощности, нестабильный холостой ход, повышенный расход топлива, Check Engine.",
        "possible_causes": "Загрязнённый MAF, повреждение проводки, плохой контакт, подсос воздуха, проблемы питания или массы.",
        "recommended_checks": "Проверить коды ошибок, live data по расходу воздуха, питание и массу датчика, состояние разъёма и впуска.",
        "severity": "medium",
    },
    {
        "code": "P0101",
        "title_ru": "Некорректный диапазон или производительность датчика массового расхода воздуха",
        "title_en": "Mass or Volume Air Flow Circuit Range/Performance Problem",
        "description_ru": "ЭБУ видит показания MAF/VAF вне ожидаемого диапазона. Часто требуется анализ live data, а не простая замена датчика.",
        "symptoms": "Провалы при разгоне, нестабильная работа двигателя, повышенный расход топлива.",
        "possible_causes": "Загрязнение датчика, подсос воздуха, негерметичный впуск, проблемы проводки, неверные данные других датчиков.",
        "recommended_checks": "Сравнить показания MAF с оборотами и нагрузкой, проверить впуск на подсос, разъём и проводку.",
        "severity": "medium",
    },
    {
        "code": "P0110",
        "title_ru": "Неисправность цепи датчика температуры воздуха на впуске",
        "title_en": "Intake Air Temperature Circuit Malfunction",
        "description_ru": "Код связан с датчиком температуры воздуха на впуске или его цепью.",
        "symptoms": "Check Engine, возможный рост расхода топлива, нестабильная работа на холодном запуске.",
        "possible_causes": "Неисправный IAT, повреждение проводки, плохой контакт, проблема в разъёме.",
        "recommended_checks": "Проверить температуру IAT в live data, сравнить с температурой окружающей среды, проверить цепь датчика.",
        "severity": "low",
    },
    {
        "code": "P0120",
        "title_ru": "Неисправность цепи датчика положения дроссельной заслонки или педали газа",
        "title_en": "Throttle/Pedal Position Sensor/Switch A Circuit Malfunction",
        "description_ru": "Код указывает на проблему в цепи датчика положения дросселя или педали.",
        "symptoms": "Плохая реакция на газ, аварийный режим, ограничение мощности, Check Engine.",
        "possible_causes": "Датчик положения дросселя, педаль газа, проводка, разъёмы, питание или масса.",
        "recommended_checks": "Проверить live data положения педали и дросселя, питание, массу, плавность изменения сигнала.",
        "severity": "high",
    },
    {
        "code": "P0130",
        "title_ru": "Неисправность цепи кислородного датчика, банк 1 датчик 1",
        "title_en": "O2 Sensor Circuit Malfunction Bank 1 Sensor 1",
        "description_ru": "Код связан с цепью кислородного датчика до катализатора.",
        "symptoms": "Check Engine, рост расхода топлива, нестабильная смесь.",
        "possible_causes": "Кислородный датчик, проводка, разъём, подсос воздуха, проблемы смеси.",
        "recommended_checks": "Проверить сигнал O2 в live data, состояние проводки, подсос воздуха, топливные коррекции.",
        "severity": "medium",
    },
    {
        "code": "P0171",
        "title_ru": "Слишком бедная смесь, банк 1",
        "title_en": "System Too Lean Bank 1",
        "description_ru": "ЭБУ фиксирует бедную смесь. Причина не всегда в кислородном датчике.",
        "symptoms": "Check Engine, провалы, нестабильный холостой ход, потеря тяги.",
        "possible_causes": "Подсос воздуха, низкое давление топлива, загрязнённый MAF, утечки во впуске, проблемы форсунок.",
        "recommended_checks": "Проверить топливные коррекции, MAF, давление топлива, впуск на подсос, дымогенератором при необходимости.",
        "severity": "medium",
    },
    {
        "code": "P0172",
        "title_ru": "Слишком богатая смесь, банк 1",
        "title_en": "System Too Rich Bank 1",
        "description_ru": "ЭБУ фиксирует чрезмерно богатую смесь.",
        "symptoms": "Повышенный расход, запах топлива, нестабильная работа, Check Engine.",
        "possible_causes": "Завышенное давление топлива, форсунки, MAF, датчики температуры, проблемы EVAP.",
        "recommended_checks": "Проверить топливные коррекции, давление топлива, MAF, форсунки и данные температурных датчиков.",
        "severity": "medium",
    },
    {
        "code": "P0300",
        "title_ru": "Обнаружены случайные или множественные пропуски зажигания",
        "title_en": "Random/Multiple Cylinder Misfire Detected",
        "description_ru": "Пропуски могут быть связаны с зажиганием, топливом, компрессией, подсосом воздуха или управлением двигателя.",
        "symptoms": "Троение, вибрация, мигающий Check Engine, потеря мощности.",
        "possible_causes": "Свечи, катушки, форсунки, компрессия, подсос воздуха, топливная система.",
        "recommended_checks": "Проверить счётчики пропусков, свечи, катушки, компрессию, топливные коррекции и live data.",
        "severity": "high",
    },
    {
        "code": "P0301",
        "title_ru": "Обнаружен пропуск зажигания в цилиндре 1",
        "title_en": "Cylinder 1 Misfire Detected",
        "description_ru": "Код указывает на пропуски в первом цилиндре, но причина требует диагностики.",
        "symptoms": "Троение, вибрация, потеря мощности, Check Engine.",
        "possible_causes": "Свеча, катушка, форсунка, компрессия, проводка, подсос воздуха.",
        "recommended_checks": "Поменять местами катушку/свечу для проверки, проверить форсунку, компрессию и счётчики пропусков.",
        "severity": "high",
    },
    {
        "code": "P0325",
        "title_ru": "Неисправность цепи датчика детонации",
        "title_en": "Knock Sensor Circuit Malfunction",
        "description_ru": "Код связан с датчиком детонации или его цепью.",
        "symptoms": "Check Engine, снижение мощности, изменение угла зажигания.",
        "possible_causes": "Датчик детонации, проводка, разъём, плохой контакт, механические шумы двигателя.",
        "recommended_checks": "Проверить цепь датчика, разъём, момент затяжки, наличие посторонних механических шумов.",
        "severity": "medium",
    },
    {
        "code": "P0420",
        "title_ru": "Эффективность катализатора ниже порога, банк 1",
        "title_en": "Catalyst System Efficiency Below Threshold Bank 1",
        "description_ru": "Код указывает на низкую эффективность катализатора, но перед заменой нужно исключить причины по смеси и пропускам.",
        "symptoms": "Check Engine, иногда без заметных симптомов.",
        "possible_causes": "Износ катализатора, пропуски зажигания, неправильная смесь, неисправные кислородные датчики, подсос воздуха.",
        "recommended_checks": "Сравнить сигналы O2 до и после катализатора, проверить пропуски, топливные коррекции и утечки выхлопа.",
        "severity": "medium",
    },
    {
        "code": "P0440",
        "title_ru": "Неисправность системы улавливания паров топлива EVAP",
        "title_en": "Evaporative Emission Control System Malfunction",
        "description_ru": "Код связан с системой EVAP.",
        "symptoms": "Check Engine, запах топлива, иногда без симптомов.",
        "possible_causes": "Крышка бака, клапан EVAP, утечки шлангов, адсорбер, проводка.",
        "recommended_checks": "Проверить крышку бака, герметичность EVAP, клапаны и шланги.",
        "severity": "low",
    },
    {
        "code": "P0500",
        "title_ru": "Неисправность датчика скорости автомобиля",
        "title_en": "Vehicle Speed Sensor Malfunction",
        "description_ru": "Код связан с датчиком скорости или сигналом скорости автомобиля.",
        "symptoms": "Не работает спидометр, ошибки ABS/ESP, проблемы переключения АКПП.",
        "possible_causes": "Датчик скорости, проводка, ABS-датчик, блок ABS, проблема сигнала по CAN.",
        "recommended_checks": "Проверить скорость в live data разных блоков, ABS-датчики, проводку и связь между блоками.",
        "severity": "medium",
    },
    {
        "code": "P0560",
        "title_ru": "Неисправность напряжения бортовой сети",
        "title_en": "System Voltage Malfunction",
        "description_ru": "Код связан с неправильным напряжением питания.",
        "symptoms": "Ошибки разных систем, проблемы запуска, нестабильная работа электроники.",
        "possible_causes": "Аккумулятор, генератор, масса, клеммы, проводка, регулятор напряжения.",
        "recommended_checks": "Проверить напряжение при запуске и на работающем двигателе, массу, клеммы и заряд генератора.",
        "severity": "high",
    },
    {
        "code": "P0700",
        "title_ru": "Неисправность системы управления трансмиссией",
        "title_en": "Transmission Control System Malfunction",
        "description_ru": "Общий код, указывающий, что в блоке управления трансмиссией есть дополнительные ошибки.",
        "symptoms": "Аварийный режим АКПП, рывки, задержки переключения, Check Engine.",
        "possible_causes": "Неисправности АКПП, проводка, датчики, соленоиды, TCM.",
        "recommended_checks": "Считать ошибки из блока трансмиссии, а не только из двигателя; проверить live data АКПП.",
        "severity": "high",
    },
    {
        "code": "U0100",
        "title_ru": "Потеря связи с блоком управления двигателем ECM/PCM",
        "title_en": "Lost Communication With ECM/PCM",
        "description_ru": "Код связан с отсутствием связи по сети с блоком управления двигателем.",
        "symptoms": "Не запускается двигатель, ошибки связи, не выходит на связь блок управления.",
        "possible_causes": "Питание блока, масса, CAN-шина, разъёмы, проводка, сам блок управления.",
        "recommended_checks": "Проверить питание и массу ECM/PCM, CAN-шину, наличие связи с другими блоками.",
        "severity": "critical",
    },
    {
        "code": "U0121",
        "title_ru": "Потеря связи с блоком ABS",
        "title_en": "Lost Communication With ABS Control Module",
        "description_ru": "Код указывает на потерю связи с блоком ABS.",
        "symptoms": "Ошибки ABS/ESP, не работает антиблокировочная система, ошибки связи.",
        "possible_causes": "Питание ABS, масса, CAN-шина, разъёмы, проводка, блок ABS.",
        "recommended_checks": "Проверить связь со всеми блоками, питание и массу ABS, CAN-линии и разъёмы.",
        "severity": "high",
    },
]


def normalize_code(value):
    return (value or "").strip().upper()


def code_system(code):
    code = normalize_code(code)
    return code[0] if code and code[0] in ["P", "C", "B", "U"] else ""


class Command(BaseCommand):
    help = "Import starter DTC references and link existing DiagnosticCode rows."

    def add_arguments(self, parser):
        parser.add_argument("--seed-basic", action="store_true")
        parser.add_argument("--from-existing-codes", action="store_true")
        parser.add_argument("--source-name", default="Curated starter DTC set")
        parser.add_argument("--link-existing", action="store_true")

    def handle(self, *args, **options):
        source_name = options["source_name"]

        batch = DTCImportBatch.objects.create(
            source_name=source_name,
            file_name="seed-basic",
        )

        created = 0
        updated = 0
        skipped = 0

        rows = []

        if options["seed_basic"]:
            rows.extend(BASIC_DTC)

        if options["from_existing_codes"]:
            existing_codes = (
                DiagnosticCode.objects
                .exclude(code="")
                .values_list("code", flat=True)
                .distinct()
            )

            known = {normalize_code(row["code"]) for row in rows}

            for code in existing_codes:
                code = normalize_code(code)

                if not code or code in known or code_system(code) == "":
                    continue

                rows.append({
                    "code": code,
                    "title_ru": f"Код неисправности {code}",
                    "title_en": "",
                    "description_ru": "Код найден в диагностической сессии. Подробная расшифровка требует уточнения по марке, модели, блоку управления и данным live data.",
                    "symptoms": "",
                    "possible_causes": "Возможные причины зависят от конкретного автомобиля, блока управления и условий появления ошибки.",
                    "recommended_checks": "Считать все блоки, проверить freeze frame/live data, сопутствующие ошибки, питание, массу, проводку и условия возникновения.",
                    "severity": "medium",
                })

        for row in rows:
            code = normalize_code(row.get("code"))
            system = code_system(code)

            if not code or not system:
                skipped += 1
                continue

            manufacturer = (row.get("manufacturer") or "").strip()
            brand = None

            if manufacturer:
                brand, _ = VehicleBrand.objects.get_or_create(
                    name=manufacturer,
                    defaults={
                        "slug": slugify(manufacturer) or manufacturer.lower().replace(" ", "-")
                    },
                )

            defaults = {
                "system": system,
                "scope": DTCReference.Scope.MANUFACTURER if manufacturer else DTCReference.Scope.GENERIC,
                "manufacturer": manufacturer,
                "brand": brand,
                "title_ru": row.get("title_ru", ""),
                "title_en": row.get("title_en", ""),
                "description_ru": row.get("description_ru", ""),
                "description_en": row.get("description_en", ""),
                "symptoms": row.get("symptoms", ""),
                "possible_causes": row.get("possible_causes", ""),
                "diagnostic_notes": row.get("diagnostic_notes", ""),
                "recommended_checks": row.get("recommended_checks", ""),
                "severity": row.get("severity") or DTCReference.Severity.MEDIUM,
                "source_name": source_name,
                "is_active": True,
                "import_batch": batch,
            }

            _, was_created = DTCReference.objects.update_or_create(
                code=code,
                manufacturer=manufacturer,
                defaults=defaults,
            )

            if was_created:
                created += 1
            else:
                updated += 1

        linked = 0

        if options["link_existing"]:
            for dc in DiagnosticCode.objects.filter(reference__isnull=True).exclude(code=""):
                ref = DTCReference.objects.filter(
                    code=normalize_code(dc.code),
                    manufacturer="",
                ).first()

                if ref:
                    dc.reference = ref
                    dc.save(update_fields=["reference"])
                    linked += 1

        batch.rows_total = len(rows)
        batch.rows_created = created
        batch.rows_updated = updated
        batch.rows_skipped = skipped
        batch.notes = f"linked_existing={linked}"
        batch.save()

        self.stdout.write(self.style.SUCCESS(
            f"DTC references imported: total={len(rows)} created={created} updated={updated} skipped={skipped} linked={linked}"
        ))
