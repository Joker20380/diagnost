# AI-Diagnostics: план превращения в рабочий продукт для автосервисов

Статус документа: основной исполнимый roadmap продукта  
Версия: 1.0  
Дата: 16 августа 2026 года

## 1. Цель продукта

AI-Diagnostics должен стать операционной системой доказуемой технической
компетентности автосервиса.

Платформа должна позволять автосервису:

- стандартизировать диагностику и контроль выполненных работ;
- безопасно делегировать типовые операции сотрудникам средней квалификации;
- масштабировать экспертизу старшего диагноста на команду и филиалы;
- управлять ролями, навыками, допусками и обязательной эскалацией;
- фиксировать факты, измерения, решения, отклонения и результаты ремонта;
- доказывать качество работы клиенту, партнёру, сети или гарантийному оператору;
- создавать техническую основу для внутренней квалификации, партнёрской
  сертификации и гарантийных программ.

Короткое позиционирование:

> От опыта отдельных мастеров — к системной компетентности всего сервиса.

Платформа не заменяет специалиста, не сертифицирует безопасность автомобиля и
не выдаёт юридические лицензии без уполномоченного внешнего партнёра.

## 2. Измеримый результат внедрения

Ценность продукта должна подтверждаться следующими показателями:

- сокращение среднего времени диагностики;
- сокращение времени участия senior в одном успешно закрытом случае;
- рост first-time-fix rate;
- снижение повторных визитов с той же неисправностью;
- снижение необоснованной замены деталей;
- рост доли типовых случаев, безопасно закрытых junior-сотрудниками;
- сокращение времени обучения нового сотрудника;
- рост пропускной способности диагностического поста;
- доля работ с полным доказательным пакетом;
- снижение числа нарушений утверждённых процедур.

Главная метрика продукта:

```text
Senior Leverage Ratio =
успешно закрытые диагностические случаи команды / часы участия senior
```

## 3. Целевой первый рынок

Первый сегмент — независимые автосервисы с 3–20 мастерами, использующие Launch
и выполняющие диагностику двигателя и автомобильной электроники.

Первый законченный сценарий:

```text
Launch PDF
→ подтверждение автомобиля и извлечённых фактов
→ жалоба и симптомы
→ группировка DTC
→ диагностические гипотезы
→ следующий разрешённый тест
→ результат измерения и evidence
→ пересчёт гипотез или эскалация
→ подтверждённая причина
→ ремонт
→ контроль после ремонта
→ подписанный отчёт и outcome
```

До завершения первого пилота не расширять продукт одновременно на страховые,
leasing, fleet, частных владельцев и все марки диагностических сканеров.

## 4. Принципы разработки

1. Факт, гипотеза, рекомендация и решение человека — разные сущности.
2. Данные одного автомобиля не становятся автоматически глобальным знанием.
3. Каждая рекомендация содержит основание, источник, версию и confidence.
4. Недостаток данных приводит к следующему тесту или эскалации, а не к догадке.
5. Critical action невозможно выполнить только по свободному тексту LLM.
6. Разрешение определяется ролью, навыками, автомобилем, риском и процедурой.
7. Подписанная запись неизменяема; исправление создаёт новую ревизию.
8. AI объясняет и помогает навигации; допуск и safety gates детерминированы.
9. Реальный outcome ремонта важнее пользовательской оценки рекомендации.
10. Новая функция считается готовой только после тестов и измеримого результата.

## 5. Целевая доменная модель

### Организация и компетенции

```text
Organization
Workshop
WorkshopLocation
User
TechnicianProfile
Role
Permission
Skill
Certification
TechnicianSkill
ProcedureQualification
SupervisorAssignment
```

### Автомобиль и диагностический случай

```text
Vehicle
VehicleConfiguration
DiagnosticCase
DiagnosticSnapshot
CustomerComplaint
Symptom
FaultCodeObservation
LiveDataCapture
Measurement
Attachment
```

`VehicleConfiguration` минимально хранит make, model, generation, year,
engine code, transmission, fuel type, ECU hardware/software, mileage и market.

### Диагностический процесс

```text
DiagnosticHypothesis
HypothesisEvidence
DiagnosticProcedure
ProcedureRevision
ProcedureStep
StepPermissionPolicy
ProcedureExecution
StepExecution
TestResult
Escalation
ExpertDecision
```

### Ремонт, качество и гарантия

```text
RepairAction
PartUsed
PostRepairVerification
CaseOutcome
QAEvent
VerifiedWorkRecord
WarrantyRule
WarrantyAssessment
WarrantyCertificate
```

### База знаний и provenance

```text
CanonicalDTC
ManufacturerDTC
KnowledgeSource
KnowledgeRevision
DiagnosticRule
RuleRevision
SourceObservation
ParserRun
AnalysisRun
```

## 6. Роли и уровни допуска

Начальная ролевая модель:

- `L0 Service Advisor`: жалоба, автомобиль, документы; без технических решений.
- `L1 Junior Technician`: безопасные стандартизированные тесты.
- `L2 Diagnostic Technician`: изменение плана и подтверждение обычных ремонтов.
- `L3 Senior/Expert`: сложная электрика, исключения, утверждение процедур.
- `Technical Manager`: организация, допуски, аудит, гарантийные правила.
- `Auditor/Partner`: read-only доступ к согласованному evidence.

Роль не равна компетенции. Разрешение вычисляется по формуле:

```text
Role + verified skills + active certifications + vehicle scope
+ procedure risk + tool availability + part/action cost
= ALLOW | ALLOW_WITH_APPROVAL | ESCALATE | DENY
```

Каждая процедура должна иметь:

```text
minimum_role
required_skills
required_certifications
allowed_vehicle_scope
required_tools
risk_level
maximum_action_cost
evidence_requirements
supervisor_approval_required
stop_conditions
```

Автоматическая эскалация обязательна для safety systems, high-voltage EV,
противоречивых измерений, неизвестной конфигурации, programming/coding,
дорогой замены, повторного ремонта и низкого confidence.

## 7. Фазы реализации

### Phase 0 — продуктовая валидация и baseline

Задачи:

- выбрать три design-partner автосервиса;
- провести 15–20 problem interviews по реальным последним случаям;
- собрать 30–50 обезличенных диагностических кейсов;
- зафиксировать текущие workflow, роли, стоимость ошибки и время senior;
- определить 20–30 повторяемых сценариев и 2–3 марки для первого scope;
- согласовать pilot data agreement, privacy и retention;
- измерить baseline до внедрения.

Критерий выхода:

- минимум три сервиса готовы к пилоту;
- известны baseline metrics;
- выбран один чёткий workflow и ограниченный vehicle scope;
- подтверждено, что сервисы предоставят repair outcomes.

### Phase 1 — стабилизация существующего фундамента

Статус: **завершено**. Обновлено 16 августа 2026 года.

Обозначения: `[x]` — выполнено; `[-]` — выполнено частично; `[ ]` — не выполнено.

Задачи:

- [x] разделить canonical DTC и наблюдения из загруженных отчётов;
- [x] прекратить обновление общего справочника данными отдельного автомобиля;
- [x] добавить parser version, content hash, provenance и replay;
- [x] заменить двусмысленный `ai_generated_at` на method/version metadata;
- [x] добавить настоящий обезличенный fixture PDF и regression tests для Launch parser;
- [x] сделать повторный импорт идемпотентным;
- [x] обеспечить неизменяемость подписанного результата на уровне
  domain/service layer:
  - [x] новый `DiagnosticRecord` и его измерения неизменяемы после утверждения;
  - [x] исправление создаёт связанную новую ревизию;
  - [x] legacy `SuspensionInspection`, его детали и attachments защищены;
- [x] превратить QA warnings из логов в записи `QAEvent`:
  - [x] создана модель `QAEvent`;
  - [x] фиксируются неполный акт, самосогласование и checksum mismatch;
  - [x] ошибки Launch parser и противоречия осмотра сохраняются как `QAEvent`;
- [x] документировать local changes и вести работу в контролируемых feature-ветках.

Дополнительно реализовано в рамках Phase 1:

- [x] структурированные контрольные измерения;
- [x] независимое согласование акта другим специалистом;
- [x] append-only история решений проверяющего;
- [x] SHA-256 snapshot акта при передаче на проверку;
- [x] минимальное управление актами и QA-событиями через Django Admin;
- [x] статус `parse_failed` с сохранением неуспешного импорта для аудита;
- [x] runtime-зависимость `pypdf` добавлена в воспроизводимую сборку;
- [x] устранено падение view после сохранения осмотра подвески.

Реализующие коммиты:

- `9d929d0 feat: preserve diagnostic parse provenance`;
- `834f1fe feat: add verified diagnostic records`;
- `6bef2ed feat: complete phase 1 foundation hardening`.

Критерий выхода:

- [x] импорт одного файла воспроизводим и не загрязняет knowledge base;
- [x] утверждённый `DiagnosticRecord` нельзя молча изменить;
- [x] parser regressions обнаруживаются на настоящем обезличенном PDF fixture;
- [x] для результата парсинга известны источник и версия обработки;
- [x] legacy-подписанные осмотры также защищены от изменения;
- [x] значимые parser/runtime warnings сохраняются как `QAEvent`.

### Phase 2 — multi-tenant основа и Vehicle Identity

Статус: **в работе**. Первые пять срезов завершены 16 августа 2026 года.

Задачи:

- [x] реализовать `Organization`, `Workshop`, `TechnicianProfile`;
- [x] обеспечить tenant isolation для диагностических сессий и осмотров:
  - [x] сотрудники видят кейсы своей организации;
  - [x] чужая организация получает 404;
  - [x] обычный `staff` не обходит tenant boundary;
  - [x] legacy-сессии без tenant доступны только владельцу;
- [x] нормализовать `Vehicle` и `VehicleConfiguration`:
  - [x] VIN уникален в пределах организации;
  - [x] конфигурация хранит двигатель, трансмиссию, топливо, ECU, пробег и рынок;
  - [x] подтверждённая конфигурация имеет автора и время;
  - [x] полнота имеет статус complete, incomplete или needs review;
  - [x] отсутствующие и сомнительные поля перечислены явно;
  - [x] needs review не разблокирует диагностический анализ;
- [x] создать новый `DiagnosticCase` с lifecycle:
  - [x] реализованы контролируемые переходы от intake до closed/cancelled;
  - [x] старт диагностики запрещён до готовности приёмки и идентификации;
  - [x] lifecycle хранит время старта, разрешения и закрытия;
- [x] добавить complaint, symptoms, recent repairs и operating conditions:
  - [x] анализ публикуется только после подтверждения идентичности и фактов приёмки;
  - [x] факты приёмки хранятся в отдельных доменных сущностях;
  - [x] обязательны жалоба и минимум один наблюдаемый симптом;
  - [x] экран приёмки защищён tenant boundary;
- [x] создать экран подтверждения распознанных из PDF данных;
- [x] хранить original observation и исправление пользователя отдельно;
- [x] запретить повторному парсингу перезаписывать подтверждённую идентичность;
- [-] определить RBAC и audit log:
  - [x] добавлена начальная ролевая шкала L0–L3, manager и auditor;
  - [x] tenant scope вычисляется централизованным queryset;
  - [ ] реализовать permission policies, skills и полный audit log.

Реализующие коммиты:

- `c7a834a feat: add tenant-aware workshop foundation`.
- `c048419 feat: add confirmed vehicle identity workflow`.
- `64d5a7b feat: add diagnostic case intake lifecycle`.
- `0e8dd1a feat: gate analysis on confirmed case facts`.
- `c528ca7 feat: assess vehicle configuration completeness`.

Критерий выхода:
- [x] два сервиса не видят данные друг друга в диагностических workflow;
- [x] автомобиль определён до variant/engine level либо явно помечен incomplete;
- [x] мастер подтверждает факты до начала анализа;
- [-] критичные диагностические изменения имеют автора и время, но общий
  tenant-wide audit log ещё не реализован.

### Phase 3 — исполнимые диагностические процедуры

Задачи:

- реализовать versioned DiagnosticProcedure и ProcedureStep;
- описать первые 20–30 утверждённых сценариев;
- добавить required tools, conditions, ranges, evidence и safety warnings;
- реализовать ProcedureExecution и StepExecution;
- проверять правдоподобность значений и единицы измерения;
- поддержать фото, файл, scanner capture и supervisor confirmation как evidence;
- добавить stop conditions и обязательную эскалацию;
- запретить выполнение шага без требуемого допуска.

Критерий выхода:

- L1 проходит типовой сценарий без свободного угадывания;
- система блокирует недопустимое действие на backend;
- все обязательные измерения и evidence присутствуют до завершения;
- senior получает структурированный escalation package.

### Phase 4 — hypothesis and reasoning engine v1

Задачи:

- кластеризовать связанные DTC, симптомы и модули;
- реализовать versioned deterministic diagnostic rules;
- хранить supporting и contradicting evidence;
- ранжировать гипотезы с объяснением confidence;
- выбирать следующий тест по safety, стоимости, времени и information gain;
- пересчитывать гипотезы после результата теста;
- выдавать `INSUFFICIENT_DATA`, когда вывод невозможен;
- разрешать специалисту отклонить план с обязательным объяснением.

Критерий выхода:

- каждая гипотеза объяснима и воспроизводима;
- следующий тест связан с различением конкретных гипотез;
- система не рекомендует замену детали по одному DTC;
- golden cases дают ожидаемую последовательность проверок.

### Phase 5 — live-data и дополнительные источники

Задачи:

- нормализовать PID, unit, module, timestamp и capture conditions;
- хранить RPM, temperature, load и vehicle state во время измерения;
- импортировать freeze-frame и live-data сначала из одного согласованного формата;
- добавить reference ranges по vehicle context и procedure;
- обнаруживать невозможные, противоречивые и context-invalid readings;
- подготовить adapter interface для других сканеров без их немедленного подключения.

Критерий выхода:

- значение без единицы и условий не влияет на финансовое/техническое решение;
- raw capture воспроизводимо преобразуется в normalized readings;
- ошибки контекста вызывают повтор теста или эскалацию.

### Phase 6 — repair outcome и обучающий контур

Задачи:

- добавить confirmed cause, repair actions, parts и labor;
- создать обязательный post-repair verification;
- фиксировать resolved, unresolved и returned-with-same-problem;
- сохранять disagreement системы и специалиста;
- создать expert review queue для новых знаний;
- продвигать observation в knowledge base только после review;
- рассчитывать качество правил, процедур и источников;
- запретить автоматическое повышение допуска только по числу кейсов.

Критерий выхода:

- завершённый кейс содержит outcome;
- можно связать рекомендацию, решение, ремонт и результат;
- новые знания проходят human approval;
- доступны first-time-fix и repeat-visit metrics.

### Phase 7 — competency management

Задачи:

- реализовать skills, certifications и scope ограничений;
- дать senior возможность подтверждать практическую квалификацию;
- добавить supervised execution и temporary permissions;
- отслеживать срок действия допусков;
- создать technician competence profile;
- показывать gaps, training needs и качество по типам процедур;
- создать workshop competence profile.

Критерий выхода:

- сервис видит, кто имеет право выполнять конкретную работу;
- истёкший допуск немедленно учитывается permission engine;
- каждое повышение квалификации имеет основание и approver;
- система измеряет самостоятельность junior без сокрытия ошибок.

### Phase 8 — verified work и гарантийная готовность

Задачи:

- создать immutable `VerifiedWorkRecord`;
- включить исполнителя, допуск, procedure revision, tools и evidence;
- добавить deviation и supervisor approval workflow;
- реализовать configurable WarrantyRule;
- рассчитывать `ELIGIBLE`, `REVIEW_REQUIRED` или `NOT_ELIGIBLE`;
- сформировать клиентский и партнёрский evidence package;
- добавить цифровую подпись/hash и revoke/supersede workflow;
- юридически проверить тексты до использования слова «гарантия».

Критерий выхода:

- eligibility воспроизводима по версии правила;
- missing evidence нельзя скрыть;
- certificate не означает гарантию без указанного warrantor;
- внешний партнёр может проверить запись без доступа к лишним данным.

### Phase 9 — LLM/RAG слой

LLM подключается только после структурированного case engine.

Разрешённые задачи:

- структурирование жалобы и заметок;
- поиск по разрешённым техническим источникам;
- объяснение гипотез и процедур;
- формирование вопросов мастеру;
- подготовка понятного отчёта клиенту;
- перевод с сохранением technical terms.

Обязательные ограничения:

- retrieval только из лицензированных/разрешённых источников;
- citations до конкретной revision/source;
- output schema validation;
- запрет прямого изменения permissions и signed outcomes;
- prompt/model/version logging;
- redaction персональных данных;
- evaluation set и fallback при недоступности модели;
- LLM confidence не заменяет domain confidence.

Критерий выхода:

- LLM можно отключить без потери safety workflow;
- unsupported claim виден и не становится фактом;
- critical instruction всегда подтверждена процедурой;
- evaluation показывает измеримую пользу относительно rule-only baseline.

### Phase 10 — пилот в реальном сервисе

Пилот: три сервиса, 8–12 недель, минимум 20 завершённых случаев на сервис.

Группы:

- обычный процесс;
- junior + AI-Diagnostics + senior escalation.

Измерять:

- diagnostic time;
- senior minutes per resolved case;
- first-time-fix rate;
- repeat visits;
- incorrectly replaced parts;
- escalation rate и качество эскалации;
- procedure/evidence completeness;
- safety incidents и near misses;
- пользовательское принятие и время ввода данных.

Критерий выхода в эксплуатацию:

- нет необработанных safety incidents;
- не ухудшены accuracy и repeat-visit rate;
- senior time снижен либо throughput доказан;
- outcome completion достаточно для достоверной аналитики;
- сервис готов платить за следующий период.

### Phase 11 — production readiness

Задачи:

- threat model, security review и dependency scanning;
- MFA для privileged roles;
- encryption, backup/restore drill и disaster recovery;
- retention/deletion/export policies для VIN и документов;
- monitoring, alerting, error budgets и incident response;
- async processing и безопасная обработка файлов;
- performance/load tests;
- billing, subscription и organization onboarding;
- support workflow и status communication;
- DPIA/privacy, terms, DPA и insurance/legal review;
- release, migration и rollback procedures.

Критерий выхода:

- restore проверен практически;
- tenant isolation и authorization покрыты тестами;
- определены SLA/SLO и владелец incident response;
- onboarding одного сервиса не требует разработчика;
- production release имеет rollback plan.

### Phase 12 — startup readiness

Материалы строятся на данных пилота, а не обещаниях:

- проблема и стоимость текущего процесса;
- before/after workflow;
- Senior Leverage Ratio;
- diagnostic time, first-time-fix и repeat visits;
- кейс безопасного делегирования junior;
- профиль компетентности сервиса;
- пример Verified Work Record;
- гарантийный use case с указанным внешним warrantor;
- рынок, ICP, pricing и unit economics;
- product/data/institutional moat;
- regulatory boundaries и roadmap партнёрств;
- demonstrable product, а не mock-up.

Критерий готовности презентации:

- минимум два активных design partners;
- минимум один платящий или подписавший коммерческий pilot клиент;
- воспроизводимая product demo на реальном обезличенном кейсе;
- подтверждённая метрика экономического эффекта;
- понятный wedge и план расширения;
- честно отделены реализованные функции, pilot evidence и future vision.

## 8. Сквозные требования

### Safety

- hazard classification каждого procedure step;
- role/skill gate на backend;
- stop conditions и escalation;
- запрет «догадок» при отсутствии данных;
- отдельные политики для SRS, brakes, steering и high-voltage EV;
- журнал near misses и периодический safety review.

### Auditability

- immutable event trail;
- version всех parsers, rules, procedures, models и warranty policies;
- автор, время и причина overrides;
- signed records supersede, но не перезаписываются;
- воспроизводимый расчёт результата.

### Data quality

- raw и normalized data хранятся отдельно;
- units и operating conditions обязательны;
- confidence имеет объяснение;
- unknown остаётся unknown;
- knowledge promotion требует review.

### Testing

- unit tests для permission/rule engines;
- parser fixtures и replay tests;
- integration tests полного case lifecycle;
- authorization/tenant-isolation tests;
- golden diagnostic cases;
- safety regression suite;
- restore, migration и rollback tests;
- LLM evaluation отдельно от domain engine tests.

## 9. Приоритет на ближайший цикл

До добавления нового AI-функционала выполнить:

1. design-partner interviews и baseline;
2. разделение canonical DTC и source observations;
3. parser provenance/versioning/fixtures;
4. Organization, Workshop, Technician и VehicleConfiguration;
5. DiagnosticCase, complaint и symptoms;
6. роли, skills и backend permission engine;
7. versioned procedure и первый end-to-end сценарий;
8. evidence capture и escalation;
9. repair outcome и QAEvent;
10. pilot dashboard с бизнес-метриками.

## 10. Definition of Done для продукта

Продукт готов к реальной ограниченной работе в автосервисе, когда:

- сервис и сотрудники изолированы по организациям;
- автомобиль и входные факты подтверждаются;
- junior видит только разрешённые действия;
- типовой кейс проводится по versioned procedure;
- опасный или неопределённый случай эскалируется;
- каждое измерение имеет контекст и evidence;
- final decision принадлежит уполномоченному человеку;
- outcome ремонта зафиксирован;
- подписанная работа неизменяема и проверяема;
- production security, backup и support проверены;
- пилот показывает отсутствие ухудшения качества и измеримую пользу бизнесу.

Стартап готов к сильной презентации, когда поверх этого существуют реальные
pilot metrics, платёжный сигнал и демонстрируемый путь от диагностического случая
до доказуемого результата работы.

## 11. Управление этим roadmap

- Этот файл — источник порядка фаз и критериев выхода.
- Каждая фаза превращается в отдельный epic с небольшими проверяемыми задачами.
- Нельзя объявлять фазу завершённой только по наличию UI или документации.
- Любое изменение safety scope требует обновления risk assessment и тестов.
- Каждая продуктовая итерация заканчивается review с участием практикующего
  диагноста и владельца автосервиса.
- Будущая функция не описывается в презентации как существующая.
- После каждого пилотного цикла обновляются приоритеты, но не ослабляются safety,
  provenance и auditability gates.
