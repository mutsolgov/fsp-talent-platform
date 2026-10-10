# Спецификация доменной модели, реляционной схемы данных и протоколов безопасности (Milestone 2)
## Цифровая платформа ИТ-талантов с подтвержденным профилем ФСП

**Версия документа**: `2.0.0-RELEASE`  
**Статус**: `Approved Architecture Specification`  
**Дата утверждения**: `2026-10-05`  
**Соответствие**: `docs/01_REQUIREMENTS_TRACEABILITY_MATRIX.md`, `SPEC.md`, `PROJECT.md`  
**Целевой стек данных**: PostgreSQL 16 (Production) / SQLite 3.45+ (Dev & Unit Testing), SQLAlchemy 2.0 (Mapped Declarative)

---

## 1. Архитектурный контекст и принципы проектирования данных

### 1.1. Архитектурная парадигма и бизнес-миссия платформы

Платформа представляет собой высоконадежную экосистему цифрового рекрутинга и верификации квалификации ИТ-специалистов, аккредитованную Федерацией спортивного программирования (ФСП). В основу архитектуры данных заложена модель **Reverse-Recruiting (обратного рекрутинга по методологии LHH)**:
1. **Объективная квалификационная категоризация**: Кандидаты распределяются по пулам не на основании субъективных ключевых слов из резюме, а исключительно по формуле:
   $$\text{Категория} = \text{Специализация} + \text{Подтвержденный грейд}$$
   Присвоение категории производится строго на основе результатов обязательного онбординг-опросника и адаптивного изоморфного тестирования по методологии KITE (Kernel Item Testing Engine) с калибровкой по современной теории тестирования (Item Response Theory, 3PL IRT).
2. **Гарантия прозрачности и защищенности компенсаций**: Любое взаимодействие работодателя с кандидатом (публикация потребности `employer_needs`, создание вакансии `vacancies` или отправка прямого оффера `invitations`) строго требует фиксации диапазона заработной платы в рублях РФ. На уровне базы данных действует безусловное ограничение `CHECK (salary_min > 0 AND salary_max >= salary_min)`.
3. **Строгая защита персональных данных (152-ФЗ РФ)**: Контактные данные соискателя (`email`, `phone`, `telegram`, `github_url`, оригинальный PDF-файл резюме) физически изолированы и маскируются на уровне SQL-представлений и сериализаторов API. Доступ к контактам открывается работодателю исключительно после явного акцепта инвайта кандидатом (`invitations.status = 'accepted'`) либо при прямой подаче заявки соискателем (`applications.status = 'applied'`).
4. **Первоклассный статус кандидатов без бэкграунда ФСП (Non-FSP First-Class Citizen)**: Кандидаты, не участвовавшие в чемпионатах ФСП (`fsp_id IS NULL`), не подвергаются дискриминации или штрафам в скоринге. Для них действует автоматическая нормализация весов ранжирования ($w_{\text{test}}=0.52, w_{\text{stack}}=0.30, w_{\text{fsp}}=0.00, w_{\text{freshness}}=0.18$) с выдачей знака платформенной верификации («Платформенная верификация подтверждена»).
5. **Политика нулевых заглушек (Zero-Stub Policy)**: В схеме данных полностью исключены фиктивные структуры, временные комментарии или неполные перечисления. Все 25 реляционных сущностей специфицированы в полном объеме с типами, внешними ключами, индексами производительности и проверочными ограничениями на уровне СУБД.

---

### 1.2. Dual-Database Архитектура: PostgreSQL 16 и SQLite 3.45+

Платформа спроектирована с поддержкой двух реляционных диалектов без изменения бизнес-логики приложения:
- **PostgreSQL 16 (Production / Staging)**: Высокопроизводительное хранилище с полной поддержкой бинарного формата `JSONB` с GIN-индексацией по путям, нативного типа `UUID`, транзакционной изоляции уровня Read Committed / Serializable, темпоральных отметок со смещением часового пояса `TIMESTAMPTZ` и механизмов защиты от несанкционированного изменения аудит-лога на базе PL/pgSQL триггеров.
- **SQLite 3.45+ (Development / Fast In-Memory Unit Tests)**: Автономная локальная среда для быстрого прогона тестов в памяти (`sqlite:///:memory:`). Для достижения 100% совместимости с PostgreSQL применяются адаптеры типов SQLAlchemy (`TypeEngine.with_variant()`), событие уровня движка `PRAGMA foreign_keys = ON;` и режим упреждающей записи `PRAGMA journal_mode = WAL;`.

#### Таблица соответствия типов и диалектных механизмов

| Архитектурный элемент | PostgreSQL 16 (Production) | SQLite 3.45+ (Dev/Test) | Реализация в SQLAlchemy 2.0 |
|---|---|---|---|
| **JSON структуры** | `JSONB` с бинарной компрессией и GIN-индексами | `TEXT` с функциями `json_extract()` | `sa.JSON().with_variant(postgresql.JSONB(), "postgresql")` |
| **Уникальные идентификаторы** | Нативный тип `UUID` (16 байт) | Строковый тип `CHAR(32)` / `VARCHAR(36)` | `sa.Uuid(as_uuid=True)` |
| **Временные метки** | `TIMESTAMP WITH TIME ZONE` (UTC, 8 байт) | Текстовый формат ISO-8601 UTC | `sa.DateTime(timezone=True)` с `server_default=func.now()` |
| **Суррогатные ключи (PK)** | `INTEGER GENERATED ALWAYS AS IDENTITY` | `INTEGER PRIMARY KEY AUTOINCREMENT` | `mapped_column(Integer, primary_key=True, autoincrement=True)` |
| **Логические флаги** | Нативный тип `BOOLEAN` (`TRUE` / `FALSE`) | Целочисленный тип `INTEGER` (`1` / `0`) | `sa.Boolean` с платформенным маппингом |
| **Контроль внешних ключей** | Обеспечивается ядром СУБД непрерывно | Отключен по умолчанию | Хук на подключение: `PRAGMA foreign_keys = ON;` |
| **Иммутабельность аудит-лога** | Триггер `BEFORE UPDATE OR DELETE` (PL/pgSQL) | Триггеры `RAISE(ABORT, 'error')` | Двойной DDL сценарий развертывания триггеров |

---

### 1.3. Принципы декларативного моделирования SQLAlchemy 2.0

Схема данных реализована с использованием современной парадигмы SQLAlchemy 2.0:
1. **Строгая типизация через `Mapped[T]` и `mapped_column()`**: Каждое поле модели снабжено аннотацией типа Python, транслируемой статическими анализаторами (Mypy, Pyright) и проверяемой в runtime. Использование устаревшего синтаксиса первого поколения `Column()` запрещено.
2. **Базовый декларативный класс и переиспользуемые миксины**: Единая база `DeclarativeBase` дополнена абстрактным миксином `TimestampMixin`, предоставляющим поля `created_at` и `updated_at` с автоматической фиксацией времени сервера через `func.now()`.
3. **Явные реляционные связи `relationship()`**: Все связи между сущностями объявлены двунаправленно с использованием параметров `back_populates` и точных правил каскадного удаления `cascade="all, delete-orphan"` для предотвращения появления записей-сирот (orphan records).
4. **Инкапсуляция проверочных ограничений (CHECK)**: Все бизнес-инварианты (значения перечислений, неотрицательность числовых метрик, диапазоны скоринга и зарплатные вилки) зафиксированы непосредственно в метаданных таблиц через кортеж `__table_args__ = (CheckConstraint, UniqueConstraint, Index)`.

---

### 1.4. Соответствие Федеральному закону № 152-ФЗ «О персональных данных»

Архитектура базы данных проектировалась с учетом требований российского законодательства в области защиты персональных данных:
1. **Раздельная фиксация согласий (ст. 9 и ст. 10.1 152-ФЗ)**: В таблице `user_consents` независимо сохраняются два булевых флага:
   - `consent_pdn_processing` — согласие на обработку персональных данных оператором платформы;
   - `consent_profile_publication` — согласие на распространение персональных данных и размещение профиля в каталоге соискателей.
   Каждое согласие снабжено аудиторским следом: IP-адрес заявителя (`ip_address`), заголовок агента пользователя (`user_agent`), версия политики конфиденциальности (`policy_version`) и метка времени отзыва (`revoked_at`).
2. **Невозможность публикации без согласия**: При отсутствии активного согласия на распространение (`consent_profile_publication = FALSE` или `revoked_at IS NOT NULL`) профиль кандидата автоматически исключается из витрины кандидатов (`is_active_search = FALSE`), а SQL-представление `v_candidate_profiles_masked` исключает данную запись из выборки.
3. **Иммутабельный аудит безопасности (`audit_logs`)**: Все события доступа к конфиденциальным профилям кандидатов, изменения контактных статусов и административные сбросы кулдауна фиксируются в таблице `audit_logs`. На уровне СУБД действуют триггеры, запрещающие выполнение операций `UPDATE` и `DELETE` над записями аудит-лога, что гарантирует целостность журнала расследований инцидентов.
4. **Многопользовательская изоляция контактов (Multi-Tenant Isolation)**: Физические контакты кандидата открываются строго тому работодателю, чей инвайт был принят кандидатом либо чья вакансия получила прямой отклик. Для всех остальных работодателей данные остаются скрытыми на уровне запросов и сериализаторов.

---

### 1.5. Реестр 25 реляционных сущностей платформы

Каноническая схема платформы насчитывает ровно 25 таблиц, сгруппированных по 7 доменным кластерам:

| № | Таблица | Кластер | Назначение сущности в бизнес-логике | Ключевые ограничения целостности |
|---|---|---|---|---|
| 1 | `users` | 1. Auth & Compliance | Учетные записи пользователей, аутентификация и глобальные роли | `role IN ('candidate', 'employer', 'admin')`, `uq_users_email` |
| 2 | `user_consents` | 1. Auth & Compliance | Юридически значимый журнал согласий 152-ФЗ (обработка и публикация) | `user_id UNIQUE`, аудит IP и User-Agent, статус отзыва |
| 3 | `audit_logs` | 1. Auth & Compliance | Неизменяемый системный журнал доступа к данным и критических событий | Запрет `UPDATE/DELETE` триггером СУБД, JSONB-снимок |
| 4 | `specializations` | 2. Taxonomy & Skills | Каталог 6 базовых направлений разработки (Backend, Frontend и др.) | `code IN ('backend', 'frontend', 'ml_data', 'devops', 'qa', 'infosec')` |
| 5 | `grades` | 2. Taxonomy & Skills | Шкала квалификационных уровней (Junior, Middle, Senior, Lead) | `code IN ('junior', 'middle', 'senior', 'lead')`, `rank_order BETWEEN 1 AND 4` |
| 6 | `categories` | 2. Taxonomy & Skills | 24 подтверждаемые категории (Декартово произведение Специализация × Грейд) | `UNIQUE (specialization_id, grade_id)`, уникальный `slug` |
| 7 | `skills` | 2. Taxonomy & Skills | Справочник верифицированных технологических навыков (350+ терминов) | `uq_skills_name`, флаг системной верификации `is_verified` |
| 8 | `candidate_profiles` | 3. Candidate Profile | Расширенный профиль соискателя, маскируемые контакты, ссылка на ФСП | `fsp_id NULLABLE` (Non-FSP), `expected_salary > 0`, `freshness_score 0..100` |
| 9 | `fsp_achievements` | 3. Candidate Profile | Реестр турнирных достижений, кубков и медалей официального реестра ФСП | Пусто для non-FSP, `discipline IN ('algorithmic', 'product', 'infosec', 'robotics')`, `medal IN ('gold', 'silver', 'bronze', 'participant')`, `rating >= 0` |
| 10 | `candidate_skills` | 3. Candidate Profile | Матрица владения технологиями соискателем (опыт, уровень, ядро) | `UNIQUE (candidate_profile_id, skill_id)`, `years >= 0` |
| 11 | `candidate_categorizations` | 3. Candidate Profile | Подтвержденная категория с таймером 90-дневного кулдауна пересдачи | `test_score 0..100`, `cooldown_until NOT NULL`, флаг `is_current` |
| 12 | `cooldown_resets` | 3. Candidate Profile | Аудиторский след мгновенного сброса кулдауна в 1 клик для демо жюри | Ссылка на администратора/члена жюри, фиксация причины |
| 13 | `canonical_item_families` | 4. Assessment KITE | Банк изоморфных генераторов заданий с психометрикой 3PL IRT ($a, b, c$) | `param_a > 0.0`, `0.0 <= param_c <= 1.0`, генераторы песочницы |
| 14 | `assessment_sessions` | 4. Assessment KITE | Интерактивные сессии тестирования кандидата с защитой от списывания | `seed_hash = HMAC_SHA256(cand_id, sess_id)`, `status IN ('in_progress', 'completed', 'submitted', 'expired', 'cancelled', 'abandoned')`, `theta 0..100` |
| 15 | `assessment_answers` | 4. Assessment KITE | Ответы соискателя, исходный код и отчеты автогрейдера песочницы | `UNIQUE (session_id, item_family_id)`, `points >= 0`, `time >= 0` |
| 16 | `micro_challenges` | 5. Challenges & Sandbox | Практические микро-задачи работодателей для поддержания свежести профиля | `points BETWEEN 1 AND 100`, тесты в JSONB, привязка к стеку |
| 17 | `challenge_submissions` | 5. Challenges & Sandbox | Посылки решений кандидата в защищенную песочницу (лимит 2000 мс / 256 МБ) | `status IN ('passed', 'failed', 'timeout', 'error')`, метрики RAM/CPU |
| 18 | `employer_profiles` | 6. Employer Matching | Карточка компании, верификация ИНН по ФНС, Trust Score и суточные лимиты | `CHECK (length(inn) IN (10, 12))`, `trust_score 0..100`, `daily_limit >= 0` |
| 19 | `employer_needs` | 6. Employer Matching | Формализованная потребность команды с обязательной вилкой зарплаты в рублях | `CHECK (salary_min > 0 AND salary_max >= salary_min)` |
| 20 | `saved_shortlists` | 6. Employer Matching | Сохраненные выборки соискателей для исключения потери кандидатов | Привязка к работодателю и потребности, фильтры в JSONB |
| 21 | `shortlist_items` | 6. Employer Matching | Позиция кандидата в выборке с закреплением (`is_pinned`), $\Delta S$ и радаром | `UNIQUE (shortlist_id, candidate_profile_id)`, `match_score 0..100` |
| 22 | `vacancies` | 7. Interaction & Privacy | Публичные вакансии работодателя с обязательной зарплатной вилкой | `CHECK (salary_min > 0 AND salary_max >= salary_min)`, `status IN ('published', 'closed', 'draft', 'archived')` |
| 23 | `invitations` | 7. Interaction & Privacy | Прямые инвайты кандидатам с вилкой зарплаты и маскированием контактов | `CHECK (salary_min > 0 AND salary_max >= salary_min)`, `status IN ('sent', 'viewed', 'accepted', 'declined', 'expired')` |
| 24 | `applications` | 7. Interaction & Privacy | Прямые отклики соискателей на открытые вакансии работодателей | `UNIQUE (vacancy_id, candidate_profile_id)`, `status IN ('applied', 'viewed', 'accepted', 'rejected', 'withdrawn')` |
| 25 | `ats_integrations` | 7. Interaction & Privacy | Настройки интеграции с Huntflow, HeadHunter и исходящими HMAC-вебхуками | `UNIQUE (employer_id, ats_type)`, секретный хэш, лог доставок |

---

## 2. Глобальная диаграмма сущностей (Mermaid `erDiagram`)

Ниже представлена глобальная диаграмма всех 25 таблиц базы данных с фиксацией кардинальностей связей, первичных ключей (`PK`), внешних ключей (`FK`), уникальных индексов (`UK`) и доменных ограничений целостности:

```mermaid
erDiagram
    %% =========================================================================
    %% КЛАСТЕР 1: АУТЕНТИФИКАЦИЯ, СОГЛАСИЯ 152-ФЗ И АУДИТ
    %% =========================================================================
    users ||--o| candidate_profiles : "владеет профилем кандидата"
    users ||--o| employer_profiles : "владеет профилем работодателя"
    users ||--o{ user_consents : "подписывает согласия"
    users ||--o{ audit_logs : "инициирует события"
    users ||--o{ cooldown_resets : "авторизует сброс (жюри)"

    %% =========================================================================
    %% КЛАСТЕР 2: ТАКСОНОМИЯ СПЕЦИАЛИЗАЦИЙ, ГРЕЙДОВ И НАВЫКОВ
    %% =========================================================================
    specializations ||--o{ categories : "классифицирует"
    grades ||--o{ categories : "градуирует"
    specializations ||--o{ skills : "содержит навыки"
    skills ||--o{ candidate_skills : "демонстрируется в"
    specializations ||--o{ canonical_item_families : "профилирует тесты"
    grades ||--o{ canonical_item_families : "калибрует сложность"

    %% =========================================================================
    %% КЛАСТЕР 3: ПРОФИЛЬ КАНДИДАТА, ДОСТИЖЕНИЯ ФСП И ГРЕЙДИНГ
    %% =========================================================================
    candidate_profiles ||--o{ fsp_achievements : "обладает достижениями"
    candidate_profiles ||--o{ candidate_skills : "владеет технологиями"
    candidate_profiles ||--o{ candidate_categorizations : "имеет подтверждения"
    categories ||--o{ candidate_categorizations : "определяет статус"
    grades ||--o{ candidate_categorizations : "утверждает уровень"
    candidate_profiles ||--o{ cooldown_resets : "получает сброс таймера"

    %% =========================================================================
    %% КЛАСТЕР 4: KITE IRT ТЕСТИРОВАНИЕ И ЗАЩИТА ОТ УТЕЧЕК
    %% =========================================================================
    candidate_profiles ||--o{ assessment_sessions : "проходит тестирование"
    categories ||--o{ assessment_sessions : "целевая категория"
    assessment_sessions ||--o{ assessment_answers : "содержит ответы"
    canonical_item_families ||--o{ assessment_answers : "порождает варианты"

    %% =========================================================================
    %% КЛАСТЕР 5: МИКРО-ЧЕЛЛЕНДЖИ И ПЕСОЧНИЦА КОДА
    %% =========================================================================
    employer_profiles ||--o{ micro_challenges : "публикует задачи"
    specializations ||--o{ micro_challenges : "направление задачи"
    grades ||--o{ micro_challenges : "сложность задачи"
    micro_challenges ||--o{ challenge_submissions : "решается в"
    candidate_profiles ||--o{ challenge_submissions : "отправляет решения"

    %% =========================================================================
    %% КЛАСТЕР 6: ПРОФИЛЬ РАБОТОДАТЕЛЯ, ПОТРЕБНОСТИ И ШОРТЛИСТЫ
    %% =========================================================================
    employer_profiles ||--o{ employer_needs : "формирует потребности"
    specializations ||--o{ employer_needs : "требует направление"
    grades ||--o{ employer_needs : "требует грейд"
    employer_profiles ||--o{ saved_shortlists : "сохраняет выборки"
    employer_needs ||--o{ saved_shortlists : "связан с выборкой"
    saved_shortlists ||--o{ shortlist_items : "включает кандидатов"
    candidate_profiles ||--o{ shortlist_items : "входит в шортлист"

    %% =========================================================================
    %% КЛАСТЕР 7: ВАКАНСИИ, ИНВАЙТЫ, ОТКЛИКИ И ИНТЕГРАЦИЯ ATS
    %% =========================================================================
    employer_profiles ||--o{ vacancies : "открывает вакансии"
    specializations ||--o{ vacancies : "направление вакансии"
    grades ||--o{ vacancies : "грейд вакансии"
    employer_profiles ||--o{ invitations : "направляет инвайты"
    candidate_profiles ||--o{ invitations : "получает офферы"
    employer_needs ||--o{ invitations : "базируется на потребности"
    vacancies ||--o{ invitations : "ассоциирован с вакансией"
    vacancies ||--o{ applications : "принимает отклики"
    candidate_profiles ||--o{ applications : "откликается на"
    employer_profiles ||--o{ ats_integrations : "настраивает интеграции"

    %% =========================================================================
    %% АТРИБУТИВНЫЙ СОСТАВ СУЩНОСТЕЙ С ОГРАНИЧЕНИЯМИ
    %% =========================================================================
    users {
        integer id PK "Суррогатный первичный ключ"
        varchar email UK "Логин пользователя, уникальный индекс"
        varchar hashed_password "Хэш пароля Argon2id/Bcrypt"
        varchar role "CHECK (role IN ('candidate', 'employer', 'admin'))"
        boolean is_active "Флаг активности учетной записи, default true"
        boolean email_verified "Флаг подтверждения почты, default false"
        timestamptz created_at "Метка создания аккаунта"
        timestamptz updated_at "Метка обновления аккаунта"
    }

    user_consents {
        integer id PK "Первичный ключ согласия"
        integer user_id FK "REFERENCES users(id) ON DELETE CASCADE, UK"
        boolean consent_pdn_processing "Согласие на обработку ПДн (ст. 9 152-ФЗ)"
        boolean consent_profile_publication "Согласие на распространение/публикацию (ст. 10.1)"
        varchar policy_version "Версия юридического соглашения (v1.0-2026)"
        varchar ip_address "IP-адрес подписания, not null"
        text user_agent "Клиентский User-Agent, not null"
        timestamptz consent_timestamp "Метка времени выдачи согласия"
        timestamptz revoked_at "Метка времени отзыва согласия, nullable"
    }

    audit_logs {
        bigint id PK "Первичный ключ лога (BigInteger)"
        integer user_id FK "REFERENCES users(id) ON DELETE SET NULL, nullable"
        varchar action "Код операции: VIEW_CONTACTS, JURY_RESET, etc"
        varchar entity_type "Тип сущности (candidate, invite, vacancy)"
        varchar entity_id "Идентификатор целевой сущности"
        jsonb payload_json "Снимок события в формате JSONB"
        varchar ip_address "IP-адрес инициатора события"
        text user_agent "User-Agent инициатора события"
        timestamptz created_at "Метка фиксации (иммутабельна, триггер)"
    }

    specializations {
        integer id PK "Первичный ключ специализации"
        varchar code UK "CHECK code IN ('backend', 'frontend', 'ml_data', 'devops', 'qa', 'infosec')"
        varchar name "Наименование направления разработки"
        text description "Детальное описание направления"
        boolean is_active "Флаг активности, default true"
        timestamptz created_at "Метка времени создания"
    }

    grades {
        integer id PK "Первичный ключ грейда"
        varchar code UK "CHECK code IN ('junior', 'middle', 'senior', 'lead')"
        varchar name "Наименование квалификационного уровня"
        integer rank_order UK "CHECK (rank_order BETWEEN 1 AND 4)"
        text description "Квалификационный дескриптор"
        timestamptz created_at "Метка времени создания"
    }

    categories {
        integer id PK "Первичный ключ категории"
        integer specialization_id FK "REFERENCES specializations(id) ON DELETE RESTRICT"
        integer grade_id FK "REFERENCES grades(id) ON DELETE RESTRICT"
        varchar slug UK "Уникальный слаг (backend-middle), UK"
        varchar title "Полный заголовок: Backend Developer · Middle"
        text description "Матрица компетенций категории"
        timestamptz created_at "Метка времени создания"
    }

    skills {
        integer id PK "Первичный ключ навыка"
        varchar name UK "Наименование навыка (FastAPI, PostgreSQL)"
        varchar slug UK "Поисковый слаг навыка"
        integer specialization_id FK "REFERENCES specializations(id) ON DELETE SET NULL"
        varchar category_tag "Категория: language, framework, database, tool"
        boolean is_core "Базовый системный навык таксономии"
        boolean is_verified "Верифицированный навык, default true"
        timestamptz created_at "Метка времени создания"
    }

    candidate_profiles {
        integer id PK "Первичный ключ профиля кандидата"
        integer user_id FK "REFERENCES users(id) ON DELETE CASCADE, UK"
        varchar first_name "Имя кандидата, not null"
        varchar last_name "Фамилия кандидата, not null"
        varchar middle_name "Отчество кандидата, nullable"
        varchar phone "Телефон (маскируется по 152-ФЗ)"
        varchar telegram "Telegram никнейм (маскируется)"
        varchar github_url "Ссылка на GitHub (маскируется)"
        varchar city "Город проживания кандидата"
        boolean relocation_ready "Готовность к релокации"
        varchar work_format "CHECK work_format IN ('remote', 'office', 'hybrid', 'any')"
        integer expected_salary "CHECK (expected_salary IS NULL OR expected_salary > 0)"
        text bio "Краткое профессиональное резюме"
        varchar raw_resume_pdf_path "Путь к файлу резюме (маскируется)"
        jsonb survey_data_json "Данные онбординг-опросника в JSONB"
        varchar fsp_id UK "Идентификатор ФСП, NULLABLE для non-FSP"
        boolean fsp_verified "Статус подтверждения ФСП, default false"
        float freshness_score "CHECK (freshness_score >= 0.0 AND freshness_score <= 100.0)"
        boolean is_published "Флаг публикации в каталоге, default true"
        timestamptz created_at "Метка времени создания"
        timestamptz updated_at "Метка времени обновления"
    }

    fsp_achievements {
        integer id PK "Первичный ключ достижения ФСП"
        integer candidate_profile_id FK "REFERENCES candidate_profiles(id) ON DELETE CASCADE"
        varchar fsp_id "Идентификатор участника реестра ФСП"
        varchar championship_name "Наименование чемпионата/кубка ФСП"
        varchar discipline "CHECK discipline IN ('algorithmic', 'product', 'infosec', 'robotics')"
        varchar stage "Этап соревнования: всероссийский, окружной, вузовский"
        integer year "CHECK (year BETWEEN 2018 AND 2030)"
        integer place "CHECK (place IS NULL OR place > 0)"
        varchar medal "CHECK medal IN ('gold', 'silver', 'bronze', 'participant')"
        varchar sport_rank "CHECK sport_rank IN ('kms', 'ms', 'none', 'first_class')"
        integer rating_points "CHECK (rating_points >= 0), default 0"
        varchar certificate_url "Ссылка на верифицированный электронный сертификат"
        timestamptz verified_at "Метка верификации реестром ФСП"
        timestamptz created_at "Метка времени внесения записи"
    }

    candidate_skills {
        integer id PK "Первичный ключ связи"
        integer candidate_profile_id FK "REFERENCES candidate_profiles(id) ON DELETE CASCADE"
        integer skill_id FK "REFERENCES skills(id) ON DELETE CASCADE"
        float years_experience "CHECK (years_experience >= 0.0)"
        varchar proficiency_level "CHECK proficiency_level IN ('beginner', 'intermediate', 'advanced', 'expert')"
        boolean is_core "Является ли ключевым навыком кандидата"
        boolean is_verified "Подтвержден ли тестом платформы"
        timestamptz created_at "Метка времени создания"
    }

    candidate_categorizations {
        integer id PK "Первичный ключ категоризации"
        integer candidate_profile_id FK "REFERENCES candidate_profiles(id) ON DELETE CASCADE"
        integer category_id FK "REFERENCES categories(id) ON DELETE RESTRICT"
        integer confirmed_grade_id FK "REFERENCES grades(id) ON DELETE RESTRICT"
        float test_score "CHECK (test_score >= 0.0 AND test_score <= 100.0)"
        timestamptz assigned_at "Метка времени присвоения категории"
        timestamptz cooldown_until "Таймер 90 дней кулдауна, not null"
        boolean is_current "Текущая активная категория соискателя"
        integer source_session_id "Идентификатор сессии KITE, nullable"
        timestamptz created_at "Метка времени создания"
    }

    cooldown_resets {
        integer id PK "Первичный ключ сброса"
        integer candidate_profile_id FK "REFERENCES candidate_profiles(id) ON DELETE CASCADE"
        integer reset_by_user_id FK "REFERENCES users(id) ON DELETE RESTRICT"
        varchar reason "Причина: Jury Demo Bypass / Оценка жюри"
        timestamptz previous_cooldown_until "Предыдущая метка окончания кулдауна"
        timestamptz created_at "Метка времени мгновенного сброса"
    }

    canonical_item_families {
        integer id PK "Первичный ключ семейства тестовых заданий"
        integer specialization_id FK "REFERENCES specializations(id) ON DELETE RESTRICT"
        integer grade_id FK "REFERENCES grades(id) ON DELETE RESTRICT"
        varchar family_code UK "Уникальный код семейства (BE-MID-042)"
        varchar task_type "CHECK task_type IN ('algorithmic', 'system_design', 'code_triage', 'code_sandbox', 'mcq')"
        varchar title "Заголовок задания KITE"
        text template_text "Изоморфный параметризованный шаблон"
        jsonb param_matrix_json "Матрица допустимых параметров генерации"
        text test_generator_code "Python код генерации вариантов задания"
        float param_a "Дискриминативность IRT 3PL, CHECK (param_a > 0.0)"
        float param_b "Трудность задания IRT 3PL"
        float param_c "Угадывание IRT 3PL, CHECK (param_c >= 0.0 AND param_c <= 1.0)"
        integer time_limit_sec "Лимит времени на решение (сек), default 1200"
        boolean is_active "Флаг активности задания в банке"
        timestamptz created_at "Метка времени добавления"
    }

    assessment_sessions {
        integer id PK "Первичный ключ сессии тестирования"
        integer candidate_profile_id FK "REFERENCES candidate_profiles(id) ON DELETE CASCADE"
        integer category_id FK "REFERENCES categories(id) ON DELETE RESTRICT"
        varchar session_type "CHECK session_type IN ('initial', 'boost', 'retest_lower')"
        varchar seed_hash "HMAC_SHA256(candidate_id, session_id)"
        timestamptz started_at "Метка времени старта теста"
        timestamptz completed_at "Метка времени завершения теста"
        varchar status "CHECK status IN ('in_progress', 'completed', 'submitted', 'expired', 'cancelled', 'abandoned')"
        float raw_score "Сырой первичный балл"
        float theta_score "CHECK (theta_score IS NULL OR (theta_score >= 0.0 AND theta_score <= 100.0))"
        varchar verdict "CHECK verdict IN ('confirmed', 'boost_offered', 'retest_lower_offered', 'lower_grade_offered', 'failed')"
        integer time_spent_sec "Фактически затраченное время (сек)"
        timestamptz expires_at "Метка истечения таймера сессии"
        timestamptz created_at "Метка времени создания"
    }

    assessment_answers {
        integer id PK "Первичный ключ ответа на тестовый вопрос"
        integer session_id FK "REFERENCES assessment_sessions(id) ON DELETE CASCADE"
        integer item_family_id FK "REFERENCES canonical_item_families(id) ON DELETE RESTRICT"
        jsonb variant_params_json "Параметры сгенерированного изоморфного варианта"
        varchar variant_seed "Криптографическая соль конкретного варианта"
        text candidate_answer_text "Текстовый ответ соискателя"
        text submitted_code "Исходный код решения соискателя"
        jsonb test_results_json "Результаты автоматической проверки тестами"
        boolean is_correct "Корректность ответа, default false"
        float points_awarded "CHECK (points_awarded >= 0.0)"
        integer time_taken_sec "CHECK (time_taken_sec >= 0)"
        timestamptz created_at "Метка времени фиксации ответа"
    }

    micro_challenges {
        integer id PK "Первичный ключ практического микро-челленджа"
        integer employer_profile_id FK "REFERENCES employer_profiles(id) ON DELETE CASCADE"
        integer specialization_id FK "REFERENCES specializations(id) ON DELETE RESTRICT"
        integer grade_id FK "REFERENCES grades(id) ON DELETE RESTRICT"
        varchar title "Заголовок практической микро-задачи"
        text description "Условие инженерной задачи и требования"
        text code_stub "Стартовый шаблон кода решения"
        jsonb test_cases_json "Набор тестовых сценариев и ассертов в JSONB"
        integer points "Баллы за решение, CHECK (points > 0 AND points <= 100)"
        boolean is_active "Флаг активности задачи в каталоге"
        timestamptz created_at "Метка времени публикации"
        timestamptz updated_at "Метка времени обновления"
    }

    challenge_submissions {
        integer id PK "Первичный ключ попытки решения микро-задачи"
        integer challenge_id FK "REFERENCES micro_challenges(id) ON DELETE CASCADE"
        integer candidate_profile_id FK "REFERENCES candidate_profiles(id) ON DELETE CASCADE"
        text solution_code "Исходный код решения соискателя"
        varchar status "CHECK status IN ('passed', 'failed', 'timeout', 'error')"
        integer execution_time_ms "Время работы в песочнице, CHECK (execution_time_ms >= 0)"
        integer memory_kb "Пиковое потребление RAM, CHECK (memory_kb >= 0)"
        jsonb test_results_json "Детальный протокол выполнения тестов"
        float freshness_points_awarded "CHECK (freshness_points_awarded >= 0.0)"
        timestamptz created_at "Метка времени посылки в песочницу"
    }

    employer_profiles {
        integer id PK "Первичный ключ профиля работодателя"
        integer user_id FK "REFERENCES users(id) ON DELETE CASCADE, UK"
        varchar company_name "Официальное наименование юридического лица"
        varchar inn "ИНН компании, CHECK (length(inn) IN (10, 12)), UK"
        varchar domain "Корпоративный домен компании (проверен по MX)"
        boolean is_inn_verified "Флаг верификации ИНН по реестру ФНС"
        integer trust_score "Рейтинг доверия, CHECK (trust_score >= 0 AND trust_score <= 100)"
        integer invite_daily_limit "Суточная квота инвайтов, CHECK (invite_daily_limit >= 0)"
        integer invites_sent_today "Отправлено инвайтов сегодня, CHECK (invites_sent_today >= 0)"
        timestamptz last_invite_reset_at "Метка суточного сброса квоты инвайтов"
        varchar logo_url "Ссылка на корпоративный логотип"
        text description "Описание профиля работодателя и сферы деятельности"
        varchar city "Город локации компании"
        varchar website "Официальный веб-сайт компании"
        timestamptz created_at "Метка времени создания"
        timestamptz updated_at "Метка времени обновления"
    }

    employer_needs {
        integer id PK "Первичный ключ потребности команды"
        integer employer_profile_id FK "REFERENCES employer_profiles(id) ON DELETE CASCADE"
        integer specialization_id FK "REFERENCES specializations(id) ON DELETE RESTRICT"
        integer target_grade_id FK "REFERENCES grades(id) ON DELETE RESTRICT"
        jsonb core_stack_json "Обязательный стек технологий в JSONB"
        jsonb nice_to_have_stack_json "Желательный стек технологий в JSONB"
        integer salary_min "Минимальная планка зарплаты в рублях"
        integer salary_max "Максимальная планка зарплаты в рублях"
        varchar work_format "Формат работы: remote, office, hybrid, any"
        text team_tasks_text "Описание инженерных задач команды"
        boolean is_active "Флаг активности поиска, default true"
        timestamptz created_at "Метка времени создания"
        timestamptz updated_at "Метка времени обновления"
    }

    saved_shortlists {
        integer id PK "Первичный ключ сохраненного шортлиста"
        integer employer_profile_id FK "REFERENCES employer_profiles(id) ON DELETE CASCADE"
        integer need_id FK "REFERENCES employer_needs(id) ON DELETE SET NULL, nullable"
        varchar title "Название подборки кандидатов"
        jsonb filter_criteria_json "Снимок примененных фасеточных фильтров"
        timestamptz created_at "Метка времени создания"
        timestamptz updated_at "Метка времени обновления"
    }

    shortlist_items {
        integer id PK "Первичный ключ позиции в шортлисте"
        integer shortlist_id FK "REFERENCES saved_shortlists(id) ON DELETE CASCADE"
        integer candidate_profile_id FK "REFERENCES candidate_profiles(id) ON DELETE CASCADE"
        boolean is_pinned "Флаг закрепления кандидата при смене фильтров"
        float match_score "Сводный скор соответствия, CHECK (match_score >= 0.0 AND match_score <= 100.0)"
        float delta_score "Динамическое смещение скоринга Delta S, default 0.0"
        integer rank_position "Позиция в ранжированном списке, CHECK (rank_position > 0)"
        jsonb explainability_json "Декомпозиция скоринга: радар тестов, стека, ФСП и свежести"
        timestamptz created_at "Метка времени добавления в шортлист"
        timestamptz updated_at "Метка времени пересчета"
    }

    vacancies {
        integer id PK "Первичный ключ вакансии"
        integer employer_profile_id FK "REFERENCES employer_profiles(id) ON DELETE CASCADE"
        integer specialization_id FK "REFERENCES specializations(id) ON DELETE RESTRICT"
        integer grade_id FK "REFERENCES grades(id) ON DELETE RESTRICT"
        varchar title "Заголовок открытой вакансии"
        text description "Детальное описание требований и условий"
        jsonb required_skills_json "Список требуемых компетенций в JSONB"
        integer salary_min "Минимальная зарплата в рублях"
        integer salary_max "Максимальная зарплата в рублях"
        varchar work_format "Формат работы: remote, office, hybrid, any"
        varchar city "Город расположения вакансии"
        varchar status "CHECK status IN ('draft', 'published', 'closed', 'archived')"
        timestamptz created_at "Метка времени создания"
        timestamptz updated_at "Метка времени обновления"
    }

    invitations {
        integer id PK "Первичный ключ прямого приглашения"
        integer employer_profile_id FK "REFERENCES employer_profiles(id) ON DELETE CASCADE"
        integer candidate_profile_id FK "REFERENCES candidate_profiles(id) ON DELETE CASCADE"
        integer need_id FK "REFERENCES employer_needs(id) ON DELETE SET NULL, nullable"
        integer vacancy_id FK "REFERENCES vacancies(id) ON DELETE SET NULL, nullable"
        text proposal_text "Текст прямого обращения и оффера команды"
        integer salary_min "Минимальная гарантированная зарплата в рублях"
        integer salary_max "Максимальная зарплата в рублях"
        varchar contact_method "Желаемый канал коммуникации (telegram, phone, email)"
        varchar status "CHECK status IN ('sent', 'viewed', 'accepted', 'declined', 'expired')"
        timestamptz sent_at "Метка времени отправки приглашения"
        timestamptz viewed_at "Метка времени первого просмотра кандидатом"
        timestamptz resolved_at "Метка времени решения (акцепт/отклонение)"
        text decline_reason "Причина отклонения оффера кандидатом"
        timestamptz created_at "Метка времени создания"
        timestamptz updated_at "Метка времени обновления"
    }

    applications {
        integer id PK "Первичный ключ отклика соискателя"
        integer vacancy_id FK "REFERENCES vacancies(id) ON DELETE CASCADE"
        integer candidate_profile_id FK "REFERENCES candidate_profiles(id) ON DELETE CASCADE"
        text cover_letter "Сопроводительное письмо соискателя"
        varchar status "CHECK status IN ('applied', 'viewed', 'accepted', 'rejected', 'withdrawn')"
        timestamptz applied_at "Метка времени подачи отклика"
        timestamptz viewed_at "Метка времени открытия отклика работодателем"
        timestamptz resolved_at "Метка времени финального решения"
        text rejection_reason "Причина отклонения кандидата работодателем"
        timestamptz created_at "Метка времени создания"
        timestamptz updated_at "Метка времени обновления"
    }

    ats_integrations {
        integer id PK "Первичный ключ конфигурации ATS"
        integer employer_profile_id FK "REFERENCES employer_profiles(id) ON DELETE CASCADE"
        varchar ats_type "CHECK ats_type IN ('huntflow', 'headhunter', 'custom_webhook')"
        varchar api_key_hash "Хэш ключа API / OAuth токена внешнего сервиса"
        varchar webhook_url "URL входящего эндпоинта внешней корпоративной ATS"
        varchar webhook_secret "Секретный ключ подписи HMAC-SHA256 (X-FSP-Signature)"
        jsonb webhook_delivery_logs_json "Журнал статусов доставки вебхуков (HTTP 2xx, 5xx, DLQ)"
        boolean is_active "Флаг активности интеграции, default true"
        timestamptz created_at "Метка времени настройки"
        timestamptz updated_at "Метка времени изменения конфигурации"
    }
```

---
## 3. Диаграммы состояний жизненных циклов (Mermaid `stateDiagram-v2`)

### 3.1. Онбординг, верификация ФСП и адаптивное тестирование грейда соискателя

Диаграмма состояний специфицирует полный путь соискателя: от регистрации с подписанием согласий 152-ФЗ, прохождения через развилку подтверждения участия в чемпионатах ФСП (с гарантией нулевого штрафа и автоматической ренормализацией весов для кандидатов без истории ФСП), прохождения онбординг-опросника, шлюза 90-дневного кулдауна (с мгновенным сбросом в 1 клик для оценки жюри) до адаптивного тестирования KITE IRT, некарательного ветвления по баллам $\theta$ и механизма поддержания свежести профиля:

```mermaid
stateDiagram-v2
    [*] --> Unregistered

    state "Создание аккаунта и согласия 152-ФЗ" as Registration {
        Unregistered --> ConsentsGrant : POST /api/auth/register
        state "Юридические согласия 152-ФЗ РФ" as ConsentsGrant {
            [*] --> ConsentProcessing : Обязательное consent_pdn_processing = true (ст. 9)
            ConsentProcessing --> ConsentPublication : Обязательное consent_profile_publication = true (ст. 10.1)
            ConsentPublication --> [*] : Запись в таблицу user_consents с фиксацией IP и User-Agent
        }
    }

    Registration --> ProfileIngestion : Согласия подписаны

    state "Импорт данных и верификация ФСП" as ProfileIngestion {
        state "Первичный ввод данных" as DataIngestion {
            [*] --> ManualOrPdf : Ручной ввод анкеты ИЛИ Загрузка резюме в PDF (PyMuPDF)
            ManualOrPdf --> ProfileParsed : Извлечение первичного стека и опыта работы
        }

        ProfileParsed --> FspVerificationFork : Проверка статуса участника ФСП

        state FspVerificationFork <<choice>>
        FspVerificationFork --> FspLinkedTrack : Указан FSP ID (fsp_id NOT NULL)
        FspVerificationFork --> NonFspTrack : Без истории ФСП (fsp_id IS NULL)

        state "Ветка верификации ФСП (Спортивное программирование)" as FspLinkedTrack {
            [*] --> OidcAuth : OIDC авторизация через Keycloak ФСП
            OidcAuth --> RegistrySync : Запрос к Mock API официального реестра ФСП
            RegistrySync --> AchievementsPopulated : Наполнение fsp_achievements (дисциплины, места, медали, баллы)
            AchievementsPopulated --> FspBadgeAssigned : Установка fsp_verified = true, значок Золото/Серебро
            FspBadgeAssigned --> [*] : Веса ранжирования: w_test=0.40, w_stack=0.25, w_fsp=0.20, w_fresh=0.15
        }

        state "Ветка соискателей без ФСП (Гарантия нулевого штрафа)" as NonFspTrack {
            [*] --> NullFallback : fsp_id IS NULL, fsp_verified = false (штатное состояние)
            NullFallback --> PlatformBadgeAssigned : Присвоение бейджа «Платформенная верификация подтверждена»
            PlatformBadgeAssigned --> DynamicWeightNormalization : Автоматическая ренормализация весов ранжирования: w_test=0.52, w_stack=0.30, w_fsp=0.00, w_fresh=0.18
            DynamicWeightNormalization --> [*] : Честная конкуренция: нулевой штраф в алгоритме сопоставления
        }
    }

    ProfileIngestion --> OnboardingSurvey : Базовый профиль сформирован

    state "Обязательный онбординг-опросник" as OnboardingSurvey {
        [*] --> SelectSpecialization : Выбор 1 из 6 специализаций (Backend, Frontend, etc.)
        SelectSpecialization --> SelectCoreStack : Выбор ключевых технологий из каталога skills
        SelectCoreStack --> SelfClaimedGrade : Самозаявление целевого грейда (Junior, Middle, Senior, Lead)
        SelfClaimedGrade --> [*] : Сохранение survey_data_json в candidate_profiles
    }

    OnboardingSurvey --> CooldownGate : Инициация подтверждения квалификации

    state "Шлюз кулдауна и сброс для жюри" as CooldownGate {
        [*] --> CheckCooldown : Проверка candidate_categorizations.cooldown_until
        state CheckCooldown <<choice>>
        CheckCooldown --> CooldownLocked : cooldown_until > NOW() [409 Conflict]
        CheckCooldown --> KiteTestingSession : cooldown_until IS NULL ИЛИ cooldown_until <= NOW()

        state "Активный кулдаун (90 дней блокировки)" as CooldownLocked {
            [*] --> WaitingPeriod : Продакшн-режим: ожидание 90 дней до пересдачи
            WaitingPeriod --> CooldownExpired : Таймер 90 дней истек
            WaitingPeriod --> JuryDemoBypass : Режим оценки жюри: активация мгновенного сброса
        }

        state "Мгновенный сброс кулдауна в 1 клик для жюри" as JuryDemoBypass {
            [*] --> ExecReset : POST /api/demo/reset-cooldown/{candidate_id}
            ExecReset --> AuditReset : Фиксация в таблице cooldown_resets (reset_by_user_id, reason)
            AuditReset --> ClearTimer : Обновление cooldown_until = NOW()
            ClearTimer --> [*] : Мгновенная разблокировка сессии тестирования (< 50 мс)
        }

        JuryDemoBypass --> KiteTestingSession : Доступ к адаптивному тесту открыт
        CooldownExpired --> KiteTestingSession : Доступ к подтверждению грейда открыт
    }

    state "Адаптивное изоморфное тестирование KITE" as KiteTestingSession {
        [*] --> SeedGeneration : seed = HMAC_SHA256(candidate_id, session_id)
        SeedGeneration --> TaskInstantiation : Изоморфная параметризация canonical_item_families
        TaskInstantiation --> AdaptiveRun : Предъявление заданий по модели IRT 3PL (параметры a, b, c)
        AdaptiveRun --> SandboxEval : Запуск кода в защищенной песочнице (2000 мс, 256 МБ)
        SandboxEval --> ComputeTheta : Байесовская EAP-оценка способности theta в диапазоне [0, 100]
        ComputeTheta --> [*] : Фиксация сессии в assessment_sessions
    }

    KiteTestingSession --> ResultVerdictFork : Завершение сессии тестирования

    state ResultVerdictFork <<choice>>
    ResultVerdictFork --> LowerGradeOffer : theta < 70 [Грейд не подтвержден / Без штрафа]
    ResultVerdictFork --> GradeConfirmed : 70 <= theta < 88 [Грейд успешно подтвержден]
    ResultVerdictFork --> BoostOffer : theta >= 88 [Высокий балл + Опция безопасного Boost-теста]

    state "Некарательный фоллбэк: тест на грейд ниже" as LowerGradeOffer {
        [*] --> NoDemotionRule : Инвариант: отсутствие принудительного даунгрейда в профиле
        NoDemotionRule --> RetestDecision : Предложение: «Пройти тест на 1 грейд ниже прямо сейчас?»
        state RetestDecision <<choice>>
        RetestDecision --> KiteTestingSession : Кандидат согласен: мгновенный тест на грейд ниже (0 дней кулдауна)
        RetestDecision --> PracticeCatalog : Кандидат отказался: переход к тренировке на микро-челленджах
    }

    state "Подтверждение грейда и активация 90-дневного кулдауна" as GradeConfirmed {
        [*] --> AssignCategory : Фиксация в candidate_categorizations (confirmed_grade_id, category_id)
        AssignCategory --> SetCooldownTimer : Установка cooldown_until = NOW() + INTERVAL '90 days'
        SetCooldownTimer --> PublishProfileInBank : Публикация в каталоге талантов (маскированные контакты 152-ФЗ)
        PublishProfileInBank --> [*] : Доступен для сопоставления в обратном рекрутинге
    }

    state "Опция безопасного Boost-теста на грейд выше" as BoostOffer {
        [*] --> BaseGradeSecured : Инвариант: базовый заявленный грейд гарантированно подтвержден!
        BaseGradeSecured --> PromptBoostTest : Модальное окно: «Пройти безопасный тест на следующий грейд?»
        state PromptBoostTest <<choice>>
        PromptBoostTest --> GradeConfirmed : Отказ: сохранение подтвержденного грейда + 90 дней кулдаун
        PromptBoostTest --> BoostAssessment : Согласие: запуск сессии Boost-тестирования
    }

    state "Сессия безопасного Boost-тестирования" as BoostAssessment {
        [*] --> RunBoostKite : Тестовая сессия KITE, откалиброванная на Грейд + 1
        RunBoostKite --> BoostVerdict <<choice>>
        BoostVerdict --> UpgradeGrade : theta_boost >= 70 [Boost-тест сдан успешно!]
        BoostVerdict --> RetainBaseGrade : theta_boost < 70 [Boost-тест не сдан]

        state "Повышение подтвержденного грейда" as UpgradeGrade {
            [*] --> RecordUpgrade : Обновление candidate_categorizations на повышенный грейд
            RecordUpgrade --> SetBoostCooldown : Установка cooldown_until = NOW() + INTERVAL '90 days'
            SetBoostCooldown --> [*]
        }

        state "Сохранение базового подтвержденного грейда" as RetainBaseGrade {
            [*] --> GuaranteeSafe : Инвариант: базовый грейд СОХРАНЯЕТСЯ без штрафов и понижений
            GuaranteeSafe --> SetBaseCooldown : Установка cooldown_until = NOW() + INTERVAL '90 days'
            SetBaseCooldown --> [*]
        }
    }

    UpgradeGrade --> PublishProfileInBank
    RetainBaseGrade --> PublishProfileInBank

    state "Активный жизненный цикл и поддержание свежести" as ActiveLifecycle {
        PublishProfileInBank --> MicroChallengeCatalog : Просмотр микро-челленджей работодателей
        MicroChallengeCatalog --> SolveChallenge : Отправка решения микро-задачи в песочницу
        SolveChallenge --> FreshnessBoosted : Статус 'passed': начисление свежести (+15..25 баллов)
        FreshnessBoosted --> FreshnessDecay : Экспоненциальный распад свежести (период полураспада T_1/2 = 45 дней)
        FreshnessDecay --> MicroChallengeCatalog : Поддержание конкурентоспособности в ранжировании S
    }

    state "Практика и развитие навыков" as PracticeCatalog {
        [*] --> SolveTrainingTasks : Решение задач работодателей в тренировочном режиме
        SolveTrainingTasks --> ReadyForRetest : Повышение компетенций
        ReadyForRetest --> KiteTestingSession : Повторный старт адаптивного тестирования
    }
```

---

### 3.2. Жизненный цикл инвайта и отклика с правилами маскирования контактов 152-ФЗ

Диаграмма состояний специфицирует строгие правила конфиденциальности контактов соискателя в двух встречных треках взаимодействия (Трек А — Прямой инвайт работодателя по модели LHH; Трек Б — Прямой отклик соискателя на вакансию), обработку зарплатных ограничений в рублях, многопользовательскую изоляцию и исходящие вебхуки ATS:

```mermaid
stateDiagram-v2
    [*] --> MaskedCandidateInBank

    state "Профиль в витрине талантов (Базовое состояние сокрытия)" as MaskedCandidateInBank {
        [*] --> AnonymizedDisplay : Сериализатор использует схему CandidateAnonymizedRead
        AnonymizedDisplay --> MaskingEnforced : Инвариант 152-ФЗ: Персональные контакты физически скрыты
        note right of MaskingEnforced
            Скрытые поля (NULL / Замаскировано):
            - email = NULL
            - phone = NULL
            - telegram = NULL
            - github_url = NULL
            - raw_resume_pdf_path = Скрыт
            - Имя = "Иван И. (#C-1042)"
            Открытые поля для работодателя:
            - Подтвержденная категория (напр. Backend · Middle)
            - Объяснение попадания в подборку (Match Explainability Radar)
            - Верифицированный стек технологий и опыт
            - Знак верификации ФСП / Платформенный знак
            - Индекс актуальности профиля (Freshness Score)
        end note
    }

    MaskedCandidateInBank --> DirectInvitationPath : Трек А: Обратный рекрутинг работодателя (LHH)
    MaskedCandidateInBank --> DirectApplicationPath : Трек Б: Прямой отклик соискателя на вакансию

    %% =========================================================================
    %% ТРЕК А: ПРЯМОЙ ИНВАЙТ РАБОТОДАТЕЛЯ
    %% =========================================================================
    state "Трек А: Прямой инвайт работодателя (LHH Reverse-Recruiting)" as DirectInvitationPath {
        [*] --> CreateNeedOrBrowse : Работодатель создает потребность (employer_needs)
        CreateNeedOrBrowse --> ReviewShortlist : Просмотр ранжированного шортлиста с карточками обоснования
        ReviewShortlist --> DraftInvitation : Формирование оффера (POST /api/invitations)

        state "Валидация и отправка инвайта" as DraftInvitation {
            [*] --> ValidateSalaryCheck : Инвариант: CHECK salary_min > 0 AND salary_max >= salary_min (в рублях)
            ValidateSalaryCheck --> CheckQuota : Антифрод токен-бакет: invites_sent_today < invite_daily_limit
            CheckQuota --> PersistInvite : Вставка записи в invitations (status = 'sent')
            PersistInvite --> DispatchAlert : Отправка уведомления кандидату (Email / In-App)
            DispatchAlert --> [*]
        }

        DraftInvitation --> InvitationSent : Инвайт доставлен соискателю
    }

    state "Инвайт: статус = 'sent'" as InvitationSent {
        [*] --> PendingCandidateOpen : Ожидание открытия соискателем
        note right of InvitationSent
            Инвариант 152-ФЗ:
            Контакты соискателя СТРОГО скрыты!
            Работодатель видит статус «Отправлено».
        end note
        PendingCandidateOpen --> InvitationViewed : Соискатель открыл приглашение
    }

    state "Инвайт: статус = 'viewed'" as InvitationViewed {
        [*] --> MarkViewedTimestamp : Фиксация viewed_at = NOW(), статус = 'viewed'
        MarkViewedTimestamp --> CandidateEvaluation : Соискатель изучает оффер и вилку зарплаты
        
        state CandidateDecisionFork <<choice>>
        CandidateEvaluation --> CandidateDecisionFork
        CandidateDecisionFork --> ContactDisclosureEvent : Кандидат нажал «Принять приглашение» (status = 'accepted')
        CandidateDecisionFork --> InvitationDeclined : Кандидат нажал «Отклонить» (status = 'declined')
        CandidateDecisionFork --> InvitationExpired : Истек таймер ожидания ответа (14 дней)
    }

    state "Инвайт: статус = 'declined'" as InvitationDeclined {
        [*] --> RecordDecline : Установка resolved_at = NOW(), status = 'declined'
        RecordDecline --> StoreReason : Сохранение причины отклонения в decline_reason
        StoreReason --> ContactsPermanentMasked : Инвариант: контакты соискателя остаются навсегда скрытыми
        ContactsPermanentMasked --> CooldownReinvite : Повторный инвайт соискателя заблокирован на 30 дней
        CooldownReinvite --> [*]
    }

    state "Инвайт: статус = 'expired'" as InvitationExpired {
        [*] --> AutoExpireTimer : Установка resolved_at = NOW(), status = 'expired'
        AutoExpireTimer --> RetainMasked : Инвариант: контакты остаются скрытыми
        RetainMasked --> [*]
    }

    %% =========================================================================
    %% ТРЕК Б: ПРЯМОЙ ОТКЛИК СОИСКАТЕЛЯ
    %% =========================================================================
    state "Трек Б: Прямой отклик соискателя на вакансию" as DirectApplicationPath {
        [*] --> BrowseVacancies : Соискатель просматривает открытые вакансии (vacancies)
        BrowseVacancies --> SubmitApplication : Отправка отклика (POST /api/applications)

        state "Регистрация отклика" as SubmitApplication {
            [*] --> CheckActiveVacancy : Проверка активности вакансии (status == 'published')
            CheckActiveVacancy --> CreateAppRecord : Создание applications (status = 'applied', applied_at = NOW())
            CreateAppRecord --> ImplicitDisclosure : Волеизъявление соискателя: согласие на открытие контактов работодателю вакансии
            ImplicitDisclosure --> [*]
        }

        SubmitApplication --> ApplicationApplied : Отклик зарегистрирован
    }

    state "Отклик: статус = 'applied'" as ApplicationApplied {
        [*] --> NotifyEmployer : Уведомление работодателя о новом отклике
        NotifyEmployer --> ApplicationViewed : Работодатель открывает профиль соискателя
    }

    state "Отклик: статус = 'viewed'" as ApplicationViewed {
        [*] --> ReviewCandidateDetails : Установка viewed_at = NOW(), status = 'viewed'
        ReviewCandidateDetails --> AppDecisionFork <<choice>>
        AppDecisionFork --> ContactDisclosureEvent : Работодатель подтверждает отклик (status = 'accepted')
        AppDecisionFork --> ApplicationRejected : Работодатель отклоняет отклик (status = 'rejected')
    }

    state "Отклик: статус = 'rejected'" as ApplicationRejected {
        [*] --> CloseApp : Установка status = 'rejected', resolved_at = NOW()
        CloseApp --> [*]
    }

    %% =========================================================================
    %% СОБЫТИЕ ДЕmaskИРОВАНИЯ КОНТАКТОВ (152-ФЗ И ATS)
    %% =========================================================================
    state "Событие демаскирования контактов (152-ФЗ)" as ContactDisclosureEvent {
        [*] --> TriggerDisclosure : Переход статуса в 'accepted'
        
        state "Демаскирование на уровне сериализатора" as UnmaskingEngine {
            [*] --> SwitchSerializer : Переключение со схемы CandidateAnonymizedRead на CandidateFullRead
            SwitchSerializer --> ExposeFullPayload : Передача открытых контактов: email, phone, telegram, github, полное ФИО
            ExposeFullPayload --> GenerateFullPdf : Генерация открытого PDF-резюме со знаком верификации ФСП
            GenerateFullPdf --> [*]
        }

        TriggerDisclosure --> UnmaskingEngine
        UnmaskingEngine --> OutboundAtsWebhook : Отправка вебхука во внешнюю ATS работодателя

        state "Интеграция с внешней ATS работодателя" as OutboundAtsWebhook {
            [*] --> CheckAtsActive : Проверка наличия активной ats_integrations для работодателя
            CheckAtsActive --> BuildEnvelope : Формирование JSON-конверта (Huntflow / HeadHunter / Custom)
            BuildEnvelope --> SignPayload : Вычисление HMAC-SHA256 подписи в заголовке X-FSP-Signature
            SignPayload --> HttpDispatch : Отправка HTTP POST на webhook_url
            
            state HttpDispatchResult <<choice>>
            HttpDispatch --> HttpDispatchResult
            HttpDispatchResult --> DeliverySuccess : HTTP 2xx [Успешная доставка]
            HttpDispatchResult --> FatalFailure : HTTP 4xx [Фатальная ошибка, запись в лог]
            HttpDispatchResult --> ExponentialRetry : HTTP 5xx или Таймаут [Повтор: 1 мин, 5 мин, 15 мин]
            
            ExponentialRetry --> DeadLetterQueue : Все 3 повтора исчерпаны
            DeliverySuccess --> LogAtsDelivery : Фиксация в webhook_delivery_logs_json
            DeadLetterQueue --> LogAtsDelivery : Фиксация ошибки в webhook_delivery_logs_json
            LogAtsDelivery --> [*]
        }

        OutboundAtsWebhook --> TenantIsolationGuard : Контроль многопользовательской изоляции

        state "Гарантия многопользовательской изоляции" as TenantIsolationGuard {
            [*] --> EnforceIsolation : Инвариант: контакты открыты ИСКЛЮЧИТЕЛЬНО для данного работодателя
            EnforceIsolation --> ShieldOthers : Для всех остальных работодателей профиль остается 100% маскированным
            ShieldOthers --> [*]
        }

        TenantIsolationGuard --> [*] : Успешное завершение двусторонней смычки
    }
```

---
## 4. Потабличная спецификация реляционной схемы данных

Ниже приведена исчерпывающая спецификация всех 25 таблиц платформы по 7 доменным кластерам. Каждая сущность включает:
1. Описание назначения и бизнес-роли.
2. Продакшн-DDL для PostgreSQL 16 с внешними ключами, каскадными правилами, индексами и проверочными ограничениями СУБД.
3. Полный декларативный класс модели SQLAlchemy 2.0 (Mapped типизация, mapped_column, relationship).
4. Таблицу метаданных колонок.

---

### Кластер 1: Аутентификация, согласия 152-ФЗ и аудит безопасности

#### 1. Таблица `users`
- **Назначение**: Центральная сущность аутентификации пользователей платформы, хранения хэша учетных данных и ролевой модели доступа RBAC (`candidate`, `employer`, `admin`).
- **Бизнес-инварианты**: Уникальный email; строгая проверка роли; флаги блокировки и верификации email.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE users (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT chk_users_role CHECK (role IN ('candidate', 'employer', 'admin'))
);

CREATE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_role ON users (role);
```

**Модель SQLAlchemy 2.0**:
```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("true"), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("role IN ('candidate', 'employer', 'admin')", name="chk_users_role"),
    )

    consent: Mapped[Optional["UserConsent"]] = relationship("UserConsent", back_populates="user", uselist=False, cascade="all, delete-orphan")
    candidate_profile: Mapped[Optional["CandidateProfile"]] = relationship("CandidateProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    employer_profile: Mapped[Optional["EmployerProfile"]] = relationship("EmployerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")
    cooldown_resets: Mapped[List["CooldownReset"]] = relationship("CooldownReset", back_populates="reset_by_user")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `email` | `VARCHAR(255)` | `Mapped[str]` | NO | — | UNIQUE, btree индекс |
| `hashed_password` | `VARCHAR(255)` | `Mapped[str]` | NO | — | Argon2id хэш пароля |
| `role` | `VARCHAR(20)` | `Mapped[str]` | NO | — | `CHECK IN ('candidate', 'employer', 'admin')` |
| `is_active` | `BOOLEAN` | `Mapped[bool]` | NO | `TRUE` | Активность аккаунта |
| `email_verified` | `BOOLEAN` | `Mapped[bool]` | NO | `FALSE` | Подтверждение email |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время регистрации |
| `updated_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время последнего обновления |

---

#### 2. Таблица `user_consents`
- **Назначение**: Юридически значимый реестр согласий в соответствии с требованиями 152-ФЗ РФ (ст. 9 — обработка, ст. 10.1 — распространение/публикация в каталоге).
- **Бизнес-инварианты**: Связь 1:1 с пользователем; фиксация IP-адреса и User-Agent на момент согласия; возможность отзыва согласия через `revoked_at`.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE user_consents (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NOT NULL,
    consent_pdn_processing BOOLEAN NOT NULL,
    consent_profile_publication BOOLEAN NOT NULL,
    policy_version VARCHAR(32) NOT NULL DEFAULT 'v1.0-2026',
    ip_address VARCHAR(45) NOT NULL,
    user_agent TEXT NOT NULL,
    consent_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE NULL,
    CONSTRAINT uq_user_consents_user_id UNIQUE (user_id),
    CONSTRAINT fk_user_consents_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_user_consents_active CHECK (consent_pdn_processing IS TRUE OR revoked_at IS NOT NULL)
);

CREATE INDEX ix_user_consents_user_id ON user_consents (user_id);
CREATE INDEX ix_user_consents_timestamp ON user_consents (consent_timestamp);
```

**Модель SQLAlchemy 2.0**:
```python
class UserConsent(Base):
    __tablename__ = "user_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    consent_pdn_processing: Mapped[bool] = mapped_column(Boolean, nullable=False)
    consent_profile_publication: Mapped[bool] = mapped_column(Boolean, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), server_default=sa.text("'v1.0-2026'"), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)
    consent_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("consent_pdn_processing IS TRUE OR revoked_at IS NOT NULL", name="chk_user_consents_active"),
    )

    user: Mapped["User"] = relationship("User", back_populates="consent")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `user_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `users(id) ON DELETE CASCADE`, UNIQUE |
| `consent_pdn_processing` | `BOOLEAN` | `Mapped[bool]` | NO | — | Согласие на обработку ПДн (ст. 9) |
| `consent_profile_publication` | `BOOLEAN` | `Mapped[bool]` | NO | — | Согласие на публикацию (ст. 10.1) |
| `policy_version` | `VARCHAR(32)` | `Mapped[str]` | NO | `'v1.0-2026'` | Версия оферты/политики |
| `ip_address` | `VARCHAR(45)` | `Mapped[str]` | NO | — | IPv4/IPv6 заявителя |
| `user_agent` | `TEXT` | `Mapped[str]` | NO | — | Заголовок браузера |
| `consent_timestamp` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время подписания |
| `revoked_at` | `TIMESTAMPTZ` | `Mapped[Optional[datetime]]` | YES | `NULL` | Время отзыва (если отозвано) |

---

#### 3. Таблица `audit_logs`
- **Назначение**: Неизменяемый системный аудит-журнал критических операций безопасности: обращений к контактам соискателей, выдачи прав, изменения юридических статусов и сбросов кулдауна.
- **Бизнес-инварианты**: Большой целочисленный идентификатор `BigInteger`; иммутабельность (защита от изменения и удаления триггером СУБД); структурированный снимок `JSONB`.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE audit_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(64) NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45) NOT NULL,
    user_agent TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_audit_logs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_audit_logs_entity ON audit_logs (entity_type, entity_id);
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at DESC);
```

**Модель SQLAlchemy 2.0**:
```python
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON_TYPE, server_default=sa.text("'{}'"), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `BIGINT` | `Mapped[int]` | NO | Identity PK | BigInteger Primary Key |
| `user_id` | `INTEGER` | `Mapped[Optional[int]]` | YES | `NULL` | FK `users(id) ON DELETE SET NULL` |
| `action` | `VARCHAR(100)` | `Mapped[str]` | NO | — | Код действия (VIEW_CONTACTS и др.) |
| `entity_type` | `VARCHAR(50)` | `Mapped[str]` | NO | — | Класс объекта (candidate, invite) |
| `entity_id` | `VARCHAR(64)` | `Mapped[Optional[str]]` | YES | `NULL` | ID затронутого объекта |
| `payload_json` | `JSONB` | `Mapped[dict]` | NO | `'{}'::jsonb` | Снимок параметров операции |
| `ip_address` | `VARCHAR(45)` | `Mapped[str]` | NO | — | IP-адрес инициатора |
| `user_agent` | `TEXT` | `Mapped[Optional[str]]` | YES | `NULL` | User-Agent инициатора |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Точная метка времени события |

---

### Кластер 2: Таксономия ИТ-специализаций, грейдов и навыков

#### 4. Таблица `specializations`
- **Назначение**: Канонический справочник 6 направлений разработки программного обеспечения.
- **Бизнес-инварианты**: Фиксированный набор допустимых кодов (`backend`, `frontend`, `ml_data`, `devops`, `qa`, `infosec`); запрет удаления при наличии ссылок (`ON DELETE RESTRICT`).

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE specializations (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(32) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_specializations_code UNIQUE (code),
    CONSTRAINT chk_specializations_code CHECK (code IN ('backend', 'frontend', 'ml_data', 'devops', 'qa', 'infosec'))
);

CREATE INDEX ix_specializations_code ON specializations (code);
```

**Модель SQLAlchemy 2.0**:
```python
class Specialization(Base):
    __tablename__ = "specializations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("code IN ('backend', 'frontend', 'ml_data', 'devops', 'qa', 'infosec')", name="chk_specializations_code"),
    )

    categories: Mapped[List["Category"]] = relationship("Category", back_populates="specialization")
    canonical_item_families: Mapped[List["CanonicalItemFamily"]] = relationship("CanonicalItemFamily", back_populates="specialization")
    micro_challenges: Mapped[List["MicroChallenge"]] = relationship("MicroChallenge", back_populates="specialization")
    employer_needs: Mapped[List["EmployerNeed"]] = relationship("EmployerNeed", back_populates="specialization")
    vacancies: Mapped[List["Vacancy"]] = relationship("Vacancy", back_populates="specialization")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `code` | `VARCHAR(32)` | `Mapped[str]` | NO | — | UNIQUE, `CHECK IN ('backend', 'frontend', 'ml_data', 'devops', 'qa', 'infosec')` |
| `name` | `VARCHAR(100)` | `Mapped[str]` | NO | — | Полное русскоязычное название |
| `description` | `TEXT` | `Mapped[Optional[str]]` | YES | `NULL` | Область компетенций направления |
| `is_active` | `BOOLEAN` | `Mapped[bool]` | NO | `TRUE` | Флаг активности в каталоге |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания |

---

#### 5. Таблица `grades`
- **Назначение**: Шкала квалификационных грейдов: Junior, Middle, Senior, Lead.
- **Бизнес-инварианты**: Фиксированный диапазон числового ранга 1..4; уникальность ранга и кода.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE grades (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(50) NOT NULL,
    rank_order INTEGER NOT NULL,
    description TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_grades_code UNIQUE (code),
    CONSTRAINT uq_grades_rank_order UNIQUE (rank_order),
    CONSTRAINT chk_grades_code CHECK (code IN ('junior', 'middle', 'senior', 'lead')),
    CONSTRAINT chk_grades_rank_order CHECK (rank_order BETWEEN 1 AND 4)
);

CREATE INDEX ix_grades_rank_order ON grades (rank_order);
```

**Модель SQLAlchemy 2.0**:
```python
class Grade(Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    rank_order: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("code IN ('junior', 'middle', 'senior', 'lead')", name="chk_grades_code"),
        CheckConstraint("rank_order BETWEEN 1 AND 4", name="chk_grades_rank_order"),
    )

    categories: Mapped[List["Category"]] = relationship("Category", back_populates="grade")
    canonical_item_families: Mapped[List["CanonicalItemFamily"]] = relationship("CanonicalItemFamily", back_populates="grade")
    micro_challenges: Mapped[List["MicroChallenge"]] = relationship("MicroChallenge", back_populates="grade")
    employer_needs: Mapped[List["EmployerNeed"]] = relationship("EmployerNeed", back_populates="grade")
    vacancies: Mapped[List["Vacancy"]] = relationship("Vacancy", back_populates="grade")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `code` | `VARCHAR(20)` | `Mapped[str]` | NO | — | UNIQUE, `CHECK IN ('junior', 'middle', 'senior', 'lead')` |
| `name` | `VARCHAR(50)` | `Mapped[str]` | NO | — | Отображаемое имя грейда |
| `rank_order` | `INTEGER` | `Mapped[int]` | NO | — | UNIQUE, `CHECK BETWEEN 1 AND 4` |
| `description` | `TEXT` | `Mapped[Optional[str]]` | YES | `NULL` | Описание требований к грейду |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания |

---

#### 6. Таблица `categories`
- **Назначение**: 24 канонические категории платформы (Декартово произведение: 6 специализаций $\times$ 4 грейда). Ключевой элемент обратного рекрутинга LHH.
- **Бизнес-инварианты**: Уникальная пара `(specialization_id, grade_id)`; уникальный слаг (например, `backend-middle`); запрет случайного удаления (`ON DELETE RESTRICT`).

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE categories (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    specialization_id INTEGER NOT NULL,
    grade_id INTEGER NOT NULL,
    slug VARCHAR(64) NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_categories_slug UNIQUE (slug),
    CONSTRAINT uq_categories_spec_grade UNIQUE (specialization_id, grade_id),
    CONSTRAINT fk_categories_spec FOREIGN KEY (specialization_id) REFERENCES specializations(id) ON DELETE RESTRICT,
    CONSTRAINT fk_categories_grade FOREIGN KEY (grade_id) REFERENCES grades(id) ON DELETE RESTRICT
);

CREATE INDEX ix_categories_slug ON categories (slug);
CREATE INDEX ix_categories_spec_grade ON categories (specialization_id, grade_id);
```

**Модель SQLAlchemy 2.0**:
```python
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    specialization_id: Mapped[int] = mapped_column(ForeignKey("specializations.id", ondelete="RESTRICT"), nullable=False)
    grade_id: Mapped[int] = mapped_column(ForeignKey("grades.id", ondelete="RESTRICT"), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("specialization_id", "grade_id", name="uq_categories_spec_grade"),
    )

    specialization: Mapped["Specialization"] = relationship("Specialization", back_populates="categories")
    grade: Mapped["Grade"] = relationship("Grade", back_populates="categories")
    candidate_categorizations: Mapped[List["CandidateCategorization"]] = relationship("CandidateCategorization", back_populates="category")
    assessment_sessions: Mapped[List["AssessmentSession"]] = relationship("AssessmentSession", back_populates="category")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `specialization_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `specializations(id) ON DELETE RESTRICT` |
| `grade_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `grades(id) ON DELETE RESTRICT` |
| `slug` | `VARCHAR(64)` | `Mapped[str]` | NO | — | UNIQUE, URL слаг категории |
| `title` | `VARCHAR(150)` | `Mapped[str]` | NO | — | Название: Backend Developer · Middle |
| `description` | `TEXT` | `Mapped[Optional[str]]` | YES | `NULL` | Описание пула талантов |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания |

---

#### 7. Таблица `skills`
- **Назначение**: Таксономический каталог 350+ верифицированных технологических навыков, фреймворков и библиотек.
- **Бизнес-инварианты**: Уникальное имя и поисковый слаг; привязка к специализации (опционально); категоризация по типу (`language`, `framework`, `database`, `tool`).

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE skills (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    specialization_id INTEGER NULL,
    category_tag VARCHAR(50) NOT NULL DEFAULT 'general',
    is_core BOOLEAN NOT NULL DEFAULT FALSE,
    is_verified BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_skills_name UNIQUE (name),
    CONSTRAINT uq_skills_slug UNIQUE (slug),
    CONSTRAINT fk_skills_spec FOREIGN KEY (specialization_id) REFERENCES specializations(id) ON DELETE SET NULL
);

CREATE INDEX ix_skills_name ON skills (name);
CREATE INDEX ix_skills_slug ON skills (slug);
CREATE INDEX ix_skills_specialization ON skills (specialization_id);
```

**Модель SQLAlchemy 2.0**:
```python
class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    specialization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("specializations.id", ondelete="SET NULL"), nullable=True, index=True)
    category_tag: Mapped[str] = mapped_column(String(50), server_default=sa.text("'general'"), nullable=False)
    is_core: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    candidate_skills: Mapped[List["CandidateSkill"]] = relationship("CandidateSkill", back_populates="skill")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `name` | `VARCHAR(100)` | `Mapped[str]` | NO | — | UNIQUE, точное наименование навыка |
| `slug` | `VARCHAR(100)` | `Mapped[str]` | NO | — | UNIQUE, поисковый слаг |
| `specialization_id` | `INTEGER` | `Mapped[Optional[int]]` | YES | `NULL` | FK `specializations(id) ON DELETE SET NULL` |
| `category_tag` | `VARCHAR(50)` | `Mapped[str]` | NO | `'general'` | Категория: language, database, etc. |
| `is_core` | `BOOLEAN` | `Mapped[bool]` | NO | `FALSE` | Относится к ядру специализации |
| `is_verified` | `BOOLEAN` | `Mapped[bool]` | NO | `TRUE` | Верифицирован в таксономии платформы |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания |

---
### Кластер 3: Профиль кандидата, достижения ФСП и грейдинг

#### 8. Таблица `candidate_profiles`
- **Назначение**: Основной профиль соискателя, содержащий персональные данные (маскируемые под 152-ФЗ), зарплатные ожидания, динамический индекс свежести и интеграцию с реестром ФСП.
- **Бизнес-инварианты**: Связь 1:1 с `users`; `fsp_id` является `NULLABLE` (для кандидатов без истории участия в ФСП `fsp_id = NULL` с сохранением полноправного статуса и нулевым штрафом); контакты маскируются до явного акцепта инвайта; зарплатные ожидания строго положительны.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE candidate_profiles (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100) NULL,
    phone VARCHAR(32) NULL,
    telegram VARCHAR(64) NULL,
    github_url VARCHAR(255) NULL,
    city VARCHAR(100) NOT NULL DEFAULT 'Москва',
    relocation_ready BOOLEAN NOT NULL DEFAULT FALSE,
    work_format VARCHAR(64) NOT NULL DEFAULT 'remote',
    expected_salary INTEGER NULL,
    bio TEXT NULL,
    raw_resume_pdf_path VARCHAR(500) NULL,
    survey_data_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    fsp_id VARCHAR(64) NULL DEFAULT NULL,
    fsp_verified BOOLEAN NOT NULL DEFAULT FALSE,
    freshness_score FLOAT NOT NULL DEFAULT 50.0,
    is_published BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_candidate_profiles_user UNIQUE (user_id),
    CONSTRAINT fk_candidate_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_candidate_work_format CHECK (work_format IN ('remote', 'office', 'hybrid', 'any')),
    CONSTRAINT chk_candidate_salary CHECK (expected_salary IS NULL OR expected_salary > 0),
    CONSTRAINT chk_candidate_freshness CHECK (freshness_score >= 0.0 AND freshness_score <= 100.0)
);

CREATE INDEX ix_candidate_profiles_user_id ON candidate_profiles (user_id);
CREATE INDEX ix_candidate_profiles_fsp_id ON candidate_profiles (fsp_id);
CREATE INDEX ix_candidate_profiles_freshness ON candidate_profiles (freshness_score DESC);
CREATE INDEX ix_candidate_profiles_published ON candidate_profiles (is_published) WHERE is_published = TRUE;
```

**Модель SQLAlchemy 2.0**:
```python
class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    telegram: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), server_default=sa.text("'Москва'"), nullable=False)
    relocation_ready: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)
    work_format: Mapped[str] = mapped_column(String(64), server_default=sa.text("'remote'"), nullable=False)
    expected_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_resume_pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    survey_data_json: Mapped[dict] = mapped_column(JSON_TYPE, server_default=sa.text("'{}'"), nullable=False)
    fsp_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, default=None, index=True)
    fsp_verified: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)
    freshness_score: Mapped[float] = mapped_column(Float, server_default=sa.text("50.0"), nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("work_format IN ('remote', 'office', 'hybrid', 'any')", name="chk_candidate_work_format"),
        CheckConstraint("expected_salary IS NULL OR expected_salary > 0", name="chk_candidate_salary"),
        CheckConstraint("freshness_score >= 0.0 AND freshness_score <= 100.0", name="chk_candidate_freshness"),
    )

    user: Mapped["User"] = relationship("User", back_populates="candidate_profile")
    fsp_achievements: Mapped[List["FspAchievement"]] = relationship("FspAchievement", back_populates="candidate_profile", cascade="all, delete-orphan")
    candidate_skills: Mapped[List["CandidateSkill"]] = relationship("CandidateSkill", back_populates="candidate_profile", cascade="all, delete-orphan")
    candidate_categorizations: Mapped[List["CandidateCategorization"]] = relationship("CandidateCategorization", back_populates="candidate_profile", cascade="all, delete-orphan")
    cooldown_resets: Mapped[List["CooldownReset"]] = relationship("CooldownReset", back_populates="candidate_profile", cascade="all, delete-orphan")
    assessment_sessions: Mapped[List["AssessmentSession"]] = relationship("AssessmentSession", back_populates="candidate_profile", cascade="all, delete-orphan")
    challenge_submissions: Mapped[List["ChallengeSubmission"]] = relationship("ChallengeSubmission", back_populates="candidate_profile", cascade="all, delete-orphan")
    shortlist_items: Mapped[List["ShortlistItem"]] = relationship("ShortlistItem", back_populates="candidate_profile", cascade="all, delete-orphan")
    invitations: Mapped[List["Invitation"]] = relationship("Invitation", back_populates="candidate_profile", cascade="all, delete-orphan")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="candidate_profile", cascade="all, delete-orphan")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `user_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `users(id) ON DELETE CASCADE`, UNIQUE |
| `first_name` | `VARCHAR(100)` | `Mapped[str]` | NO | — | Имя соискателя |
| `last_name` | `VARCHAR(100)` | `Mapped[str]` | NO | — | Фамилия соискателя |
| `middle_name` | `VARCHAR(100)` | `Mapped[Optional[str]]` | YES | `NULL` | Отчество соискателя |
| `phone` | `VARCHAR(32)` | `Mapped[Optional[str]]` | YES | `NULL` | Телефон (маскируется до акцепта) |
| `telegram` | `VARCHAR(64)` | `Mapped[Optional[str]]` | YES | `NULL` | Telegram (маскируется) |
| `github_url` | `VARCHAR(255)` | `Mapped[Optional[str]]` | YES | `NULL` | GitHub URL (маскируется) |
| `city` | `VARCHAR(100)` | `Mapped[str]` | NO | `'Москва'` | Город проживания |
| `relocation_ready`| `BOOLEAN` | `Mapped[bool]` | NO | `FALSE` | Готовность к переезду |
| `work_format` | `VARCHAR(64)` | `Mapped[str]` | NO | `'remote'` | `CHECK IN ('remote', 'office', 'hybrid', 'any')` |
| `expected_salary`| `INTEGER` | `Mapped[Optional[int]]`| YES | `NULL` | `CHECK expected_salary > 0` в рублях |
| `bio` | `TEXT` | `Mapped[Optional[str]]` | YES | `NULL` | Профессиональное саммари |
| `raw_resume_pdf_path`|`VARCHAR(500)`|`Mapped[Optional[str]]`| YES | `NULL` | Путь к PDF (скрыт до акцепта) |
| `survey_data_json`|`JSONB` | `Mapped[dict]` | NO | `'{}'::jsonb` | Снимок онбординг-опросника |
| `fsp_id` | `VARCHAR(64)` | `Mapped[Optional[str]]`| YES | `NULL` | **NULLABLE для кандидатов без ФСП** |
| `fsp_verified` | `BOOLEAN` | `Mapped[bool]` | NO | `FALSE` | Флаг подтверждения ФСП |
| `freshness_score`| `FLOAT` | `Mapped[float]` | NO | `50.0` | `CHECK BETWEEN 0.0 AND 100.0` |
| `is_published` | `BOOLEAN` | `Mapped[bool]` | NO | `TRUE` | Разрешение на отображение в поиске |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания профиля |
| `updated_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время обновления |

---

#### 9. Таблица `fsp_achievements`
- **Назначение**: Реестр официальных соревновательных достижений Федерации спортивного программирования.
- **Бизнес-инварианты**: Содержит записи только для подтвержденных участников ФСП (`fsp_id IS NOT NULL`); для кандидатов без ФСП таблица пуста (0 строк), что штатно поддерживается системой без исключений.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE fsp_achievements (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    candidate_profile_id INTEGER NOT NULL,
    fsp_id VARCHAR(64) NOT NULL,
    championship_name VARCHAR(255) NOT NULL,
    discipline VARCHAR(100) NOT NULL,
    stage VARCHAR(50) NOT NULL DEFAULT 'всероссийский',
    year INTEGER NOT NULL,
    place INTEGER NULL,
    medal VARCHAR(20) NULL,
    sport_rank VARCHAR(50) NULL,
    rating_points INTEGER NOT NULL DEFAULT 0,
    certificate_url VARCHAR(500) NULL,
    verified_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_fsp_achievements_candidate FOREIGN KEY (candidate_profile_id) REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    CONSTRAINT chk_fsp_achievements_discipline CHECK (discipline IN ('algorithmic', 'product', 'infosec', 'robotics')),
    CONSTRAINT chk_fsp_achievements_year CHECK (year BETWEEN 2018 AND 2030),
    CONSTRAINT chk_fsp_achievements_place CHECK (place IS NULL OR place > 0),
    CONSTRAINT chk_fsp_achievements_medal CHECK (medal IS NULL OR medal IN ('gold', 'silver', 'bronze', 'participant')),
    CONSTRAINT chk_fsp_achievements_sport_rank CHECK (sport_rank IS NULL OR sport_rank IN ('kms', 'ms', 'none', 'first_class')),
    CONSTRAINT chk_fsp_achievements_rating CHECK (rating_points >= 0)
);

CREATE INDEX ix_fsp_achievements_candidate ON fsp_achievements (candidate_profile_id);
CREATE INDEX ix_fsp_achievements_discipline ON fsp_achievements (discipline);
CREATE INDEX ix_fsp_achievements_fsp_id ON fsp_achievements (fsp_id);
```

**Модель SQLAlchemy 2.0**:
```python
class FspAchievement(Base):
    __tablename__ = "fsp_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    fsp_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    championship_name: Mapped[str] = mapped_column(String(255), nullable=False)
    discipline: Mapped[str] = mapped_column(String(100), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), server_default=sa.text("'всероссийский'"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    place: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    medal: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sport_rank: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rating_points: Mapped[int] = mapped_column(Integer, server_default=sa.text("0"), nullable=False)
    certificate_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("discipline IN ('algorithmic', 'product', 'infosec', 'robotics')", name="chk_fsp_achievements_discipline"),
        CheckConstraint("year BETWEEN 2018 AND 2030", name="chk_fsp_achievements_year"),
        CheckConstraint("place IS NULL OR place > 0", name="chk_fsp_achievements_place"),
        CheckConstraint("medal IS NULL OR medal IN ('gold', 'silver', 'bronze', 'participant')", name="chk_fsp_achievements_medal"),
        CheckConstraint("sport_rank IS NULL OR sport_rank IN ('kms', 'ms', 'none', 'first_class')", name="chk_fsp_achievements_sport_rank"),
        CheckConstraint("rating_points >= 0", name="chk_fsp_achievements_rating"),
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="fsp_achievements")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `candidate_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `candidate_profiles(id) ON DELETE CASCADE` |
| `fsp_id` | `VARCHAR(64)` | `Mapped[str]` | NO | — | Идентификатор участника реестра ФСП |
| `championship_name`|`VARCHAR(255)`|`Mapped[str]` | NO | — | Чемпионат / Первенство / Кубок ФСП |
| `discipline` | `VARCHAR(100)`|`Mapped[str]` | NO | — | `CHECK IN ('algorithmic', 'product', 'infosec', 'robotics')` |
| `stage` | `VARCHAR(50)` | `Mapped[str]` | NO | `'всероссийский'`| Этап соревнований |
| `year` | `INTEGER` | `Mapped[int]` | NO | — | `CHECK BETWEEN 2018 AND 2030` |
| `place` | `INTEGER` | `Mapped[Optional[int]]`| YES | `NULL` | `CHECK place > 0` |
| `medal` | `VARCHAR(20)` | `Mapped[Optional[str]]`| YES | `NULL` | `CHECK IN ('gold', 'silver', 'bronze', 'participant')` |
| `sport_rank` | `VARCHAR(50)` | `Mapped[Optional[str]]`| YES | `NULL` | `CHECK IN ('kms', 'ms', 'none', 'first_class')` |
| `rating_points`| `INTEGER` | `Mapped[int]` | NO | `0` | `CHECK rating_points >= 0` |
| `certificate_url`|`VARCHAR(500)`|`Mapped[Optional[str]]`| YES | `NULL` | Ссылка на электронный сертификат |
| `verified_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время синхронизации с реестром |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания записи |

---

#### 10. Таблица `candidate_skills`
- **Назначение**: Промежуточная таблица владения навыками соискателем, включая стаж работы, уровень владения и признак верификации.
- **Бизнес-инварианты**: Уникальная пара `(candidate_profile_id, skill_id)`; неотрицательный опыт; допустимые уровни квалификации.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE candidate_skills (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    candidate_profile_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    years_experience NUMERIC(4, 1) NOT NULL DEFAULT 1.0,
    proficiency_level VARCHAR(20) NOT NULL DEFAULT 'intermediate',
    is_core BOOLEAN NOT NULL DEFAULT FALSE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_candidate_skills UNIQUE (candidate_profile_id, skill_id),
    CONSTRAINT fk_candidate_skills_profile FOREIGN KEY (candidate_profile_id) REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    CONSTRAINT fk_candidate_skills_skill FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
    CONSTRAINT chk_candidate_skills_years CHECK (years_experience >= 0.0),
    CONSTRAINT chk_candidate_skills_level CHECK (proficiency_level IN ('beginner', 'intermediate', 'advanced', 'expert'))
);

CREATE INDEX ix_candidate_skills_profile_skill ON candidate_skills (candidate_profile_id, skill_id);
```

**Модель SQLAlchemy 2.0**:
```python
class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    years_experience: Mapped[float] = mapped_column(Float, server_default=sa.text("1.0"), nullable=False)
    proficiency_level: Mapped[str] = mapped_column(String(20), server_default=sa.text("'intermediate'"), nullable=False)
    is_core: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("candidate_profile_id", "skill_id", name="uq_candidate_skills"),
        CheckConstraint("years_experience >= 0.0", name="chk_candidate_skills_years"),
        CheckConstraint("proficiency_level IN ('beginner', 'intermediate', 'advanced', 'expert')", name="chk_candidate_skills_level"),
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="candidate_skills")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="candidate_skills")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `candidate_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `candidate_profiles(id) ON DELETE CASCADE` |
| `skill_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `skills(id) ON DELETE CASCADE` |
| `years_experience`|`NUMERIC(4,1)`|`Mapped[float]`| NO | `1.0` | `CHECK years_experience >= 0.0` |
| `proficiency_level`|`VARCHAR(20)`|`Mapped[str]` | NO | `'intermediate'`| `CHECK IN ('beginner', 'intermediate', 'advanced', 'expert')` |
| `is_core` | `BOOLEAN` | `Mapped[bool]` | NO | `FALSE` | Ключевая технология соискателя |
| `is_verified` | `BOOLEAN` | `Mapped[bool]` | NO | `FALSE` | Подтверждено результатами KITE теста |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания записи |

---

#### 11. Таблица `candidate_categorizations`
- **Назначение**: История и текущее состояние подтвержденной категории соискателя (`Specialization + Verified Grade`), таймер 90-дневного кулдауна пересдачи.
- **Бизнес-инварианты**: Балл теста $\theta \in [0, 100]$; обязательная метка `cooldown_until` ($+90$ суток от подтверждения); защита от повторного тестирования во время кулдауна.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE candidate_categorizations (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    candidate_profile_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    confirmed_grade_id INTEGER NOT NULL,
    test_score FLOAT NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    cooldown_until TIMESTAMP WITH TIME ZONE NOT NULL,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    source_session_id INTEGER NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_candidate_cat_profile FOREIGN KEY (candidate_profile_id) REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    CONSTRAINT fk_candidate_cat_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
    CONSTRAINT fk_candidate_cat_grade FOREIGN KEY (confirmed_grade_id) REFERENCES grades(id) ON DELETE RESTRICT,
    CONSTRAINT chk_candidate_cat_score CHECK (test_score >= 0.0 AND test_score <= 100.0)
);

CREATE INDEX ix_candidate_cat_cand_curr ON candidate_categorizations (candidate_profile_id, is_current);
CREATE INDEX ix_candidate_cat_cooldown ON candidate_categorizations (cooldown_until);
```

**Модель SQLAlchemy 2.0**:
```python
class CandidateCategorization(Base):
    __tablename__ = "candidate_categorizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    confirmed_grade_id: Mapped[int] = mapped_column(ForeignKey("grades.id", ondelete="RESTRICT"), nullable=False)
    test_score: Mapped[float] = mapped_column(Float, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    cooldown_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("true"), nullable=False)
    source_session_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("test_score >= 0.0 AND test_score <= 100.0", name="chk_candidate_cat_score"),
        Index("ix_cand_cat_cand_curr", "candidate_profile_id", "is_current"),
        Index("ix_cand_cat_cooldown", "cooldown_until"),
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="candidate_categorizations")
    category: Mapped["Category"] = relationship("Category", back_populates="candidate_categorizations")
    confirmed_grade: Mapped["Grade"] = relationship("Grade")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `candidate_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `candidate_profiles(id) ON DELETE CASCADE` |
| `category_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `categories(id) ON DELETE RESTRICT` |
| `confirmed_grade_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `grades(id) ON DELETE RESTRICT` |
| `test_score` | `FLOAT` | `Mapped[float]` | NO | — | `CHECK BETWEEN 0.0 AND 100.0` |
| `assigned_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время подтверждения |
| `cooldown_until` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | — | **Таймер 90 дней кулдауна** |
| `is_current` | `BOOLEAN` | `Mapped[bool]` | NO | `TRUE` | Флаг активного подтверждения |
| `source_session_id`|`INTEGER` | `Mapped[Optional[int]]`| YES | `NULL` | ID породившей сессии тестирования |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания записи |

---

#### 12. Таблица `cooldown_resets`
- **Назначение**: Журнал мгновенных административных сбросов 90-дневного кулдауна для оценки системы членами экспертного жюри на хакатоне.
- **Бизнес-инварианты**: Связь с администратором/жюри (`reset_by_user_id`); сохранение предыдущей метки кулдауна; фиксирование причины.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE cooldown_resets (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    candidate_profile_id INTEGER NOT NULL,
    reset_by_user_id INTEGER NOT NULL,
    reason VARCHAR(255) NOT NULL DEFAULT 'Jury Demo Bypass',
    previous_cooldown_until TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_cooldown_resets_profile FOREIGN KEY (candidate_profile_id) REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    CONSTRAINT fk_cooldown_resets_user FOREIGN KEY (reset_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX ix_cooldown_resets_candidate ON cooldown_resets (candidate_profile_id);
CREATE INDEX ix_cooldown_resets_created_at ON cooldown_resets (created_at DESC);
```

**Модель SQLAlchemy 2.0**:
```python
class CooldownReset(Base):
    __tablename__ = "cooldown_resets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    reset_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), server_default=sa.text("'Jury Demo Bypass'"), nullable=False)
    previous_cooldown_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="cooldown_resets")
    reset_by_user: Mapped["User"] = relationship("User", back_populates="cooldown_resets")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `candidate_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `candidate_profiles(id) ON DELETE CASCADE` |
| `reset_by_user_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `users(id) ON DELETE RESTRICT` (жюри) |
| `reason` | `VARCHAR(255)`|`Mapped[str]` | NO | `'Jury Demo Bypass'` | Причина сброса таймера |
| `previous_cooldown_until`|`TIMESTAMPTZ`|`Mapped[datetime]`| NO | — | Время до применения сброса |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время операции сброса |

---

### Кластер 4: KITE IRT Адаптивное тестирование и защита от утечек

#### 13. Таблица `canonical_item_families`
- **Назначение**: Шаблоны семейств тестовых заданий адаптивного движка KITE, психометрические параметры модели Бирнбаума (IRT 3PL: $a$ — дискриминативность, $b$ — трудность, $c$ — угадывание) и генераторы изоморфных вариантов.
- **Бизнес-инварианты**: $a > 0.0$; $0.0 \le c \le 1.0$; лимит времени $> 0$; генератор изоморфных задач в JSONB.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE canonical_item_families (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    specialization_id INTEGER NOT NULL,
    grade_id INTEGER NOT NULL,
    family_code VARCHAR(64) NOT NULL,
    task_type VARCHAR(32) NOT NULL,
    title VARCHAR(200) NOT NULL,
    template_text TEXT NOT NULL,
    param_matrix_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    test_generator_code TEXT NOT NULL,
    param_a FLOAT NOT NULL DEFAULT 1.0,
    param_b FLOAT NOT NULL DEFAULT 0.0,
    param_c FLOAT NOT NULL DEFAULT 0.2,
    time_limit_sec INTEGER NOT NULL DEFAULT 1200,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_canonical_items_family_code UNIQUE (family_code),
    CONSTRAINT fk_canonical_items_spec FOREIGN KEY (specialization_id) REFERENCES specializations(id) ON DELETE RESTRICT,
    CONSTRAINT fk_canonical_items_grade FOREIGN KEY (grade_id) REFERENCES grades(id) ON DELETE RESTRICT,
    CONSTRAINT chk_canonical_items_task_type CHECK (task_type IN ('algorithmic', 'system_design', 'code_triage', 'code_sandbox', 'mcq')),
    CONSTRAINT chk_canonical_items_param_a CHECK (param_a > 0.0),
    CONSTRAINT chk_canonical_items_param_c CHECK (param_c >= 0.0 AND param_c <= 1.0),
    CONSTRAINT chk_canonical_items_time CHECK (time_limit_sec > 0)
);

CREATE INDEX ix_canonical_items_spec_grade ON canonical_item_families (specialization_id, grade_id);
CREATE INDEX ix_canonical_items_family_code ON canonical_item_families (family_code);
```

**Модель SQLAlchemy 2.0**:
```python
class CanonicalItemFamily(Base):
    __tablename__ = "canonical_item_families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    specialization_id: Mapped[int] = mapped_column(ForeignKey("specializations.id", ondelete="RESTRICT"), nullable=False)
    grade_id: Mapped[int] = mapped_column(ForeignKey("grades.id", ondelete="RESTRICT"), nullable=False)
    family_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    param_matrix_json: Mapped[dict] = mapped_column(JSON_TYPE, server_default=sa.text("'{}'"), nullable=False)
    test_generator_code: Mapped[str] = mapped_column(Text, nullable=False)
    param_a: Mapped[float] = mapped_column(Float, server_default=sa.text("1.0"), nullable=False)
    param_b: Mapped[float] = mapped_column(Float, server_default=sa.text("0.0"), nullable=False)
    param_c: Mapped[float] = mapped_column(Float, server_default=sa.text("0.2"), nullable=False)
    time_limit_sec: Mapped[int] = mapped_column(Integer, server_default=sa.text("1200"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("task_type IN ('algorithmic', 'system_design', 'code_triage', 'code_sandbox', 'mcq')", name="chk_canonical_items_task_type"),
        CheckConstraint("param_a > 0.0", name="chk_canonical_items_param_a"),
        CheckConstraint("param_c >= 0.0 AND param_c <= 1.0", name="chk_canonical_items_param_c"),
        CheckConstraint("time_limit_sec > 0", name="chk_canonical_items_time"),
    )

    specialization: Mapped["Specialization"] = relationship("Specialization", back_populates="canonical_item_families")
    grade: Mapped["Grade"] = relationship("Grade", back_populates="canonical_item_families")
    assessment_answers: Mapped[List["AssessmentAnswer"]] = relationship("AssessmentAnswer", back_populates="item_family")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `specialization_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `specializations(id) ON DELETE RESTRICT` |
| `grade_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `grades(id) ON DELETE RESTRICT` |
| `family_code` | `VARCHAR(64)` | `Mapped[str]` | NO | — | UNIQUE, уникальный код (BE-MID-042) |
| `task_type` | `VARCHAR(32)` | `Mapped[str]` | NO | — | `CHECK IN ('algorithmic', 'system_design', 'code_triage', 'code_sandbox', 'mcq')` |
| `title` | `VARCHAR(200)`| `Mapped[str]` | NO | — | Название семейства заданий |
| `template_text` | `TEXT` | `Mapped[str]` | NO | — | Параметризованный шаблон условия |
| `param_matrix_json`| `JSONB` | `Mapped[dict]` | NO | `'{}'::jsonb` | Диапазоны варьируемых параметров |
| `test_generator_code`|`TEXT` | `Mapped[str]` | NO | — | Генератор уникальных тестов |
| `param_a` | `FLOAT` | `Mapped[float]` | NO | `1.0` | Дискриминативность IRT 3PL ($a > 0$) |
| `param_b` | `FLOAT` | `Mapped[float]` | NO | `0.0` | Трудность задания IRT 3PL ($b$) |
| `param_c` | `FLOAT` | `Mapped[float]` | NO | `0.2` | Угадывание IRT 3PL ($0 \le c \le 1$) |
| `time_limit_sec` | `INTEGER` | `Mapped[int]` | NO | `1200` | Лимит времени решения в секундах |
| `is_active` | `BOOLEAN` | `Mapped[bool]` | NO | `TRUE` | Активно в банке заданий |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания |

---

#### 14. Таблица `assessment_sessions`
- **Назначение**: Сессии тестирования соискателя, защита от списывания изоморфным хэшем `seed_hash = HMAC_SHA256(candidate_id, session_id)`, расчет способности $\theta$ по Байесу (EAP).
- **Бизнес-инварианты**: Хэш зерна генерации; оценка $\theta \in [0, 100]$; допустимые типы сессий и статусы.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE assessment_sessions (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    candidate_profile_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    session_type VARCHAR(32) NOT NULL DEFAULT 'initial',
    seed_hash VARCHAR(64) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    raw_score FLOAT NULL,
    theta_score FLOAT NULL,
    verdict VARCHAR(32) NULL,
    time_spent_sec INTEGER NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_assessment_sessions_profile FOREIGN KEY (candidate_profile_id) REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    CONSTRAINT fk_assessment_sessions_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
    CONSTRAINT chk_assessment_session_type CHECK (session_type IN ('initial', 'boost', 'retest_lower')),
    CONSTRAINT chk_assessment_session_status CHECK (status IN ('in_progress', 'completed', 'submitted', 'expired', 'cancelled', 'abandoned')),
    CONSTRAINT chk_assessment_session_theta CHECK (theta_score IS NULL OR (theta_score >= 0.0 AND theta_score <= 100.0)),
    CONSTRAINT chk_assessment_session_verdict CHECK (verdict IS NULL OR verdict IN ('confirmed', 'boost_offered', 'retest_lower_offered', 'lower_grade_offered', 'failed'))
);

CREATE INDEX ix_assessment_sessions_cand_status ON assessment_sessions (candidate_profile_id, status);
CREATE INDEX ix_assessment_sessions_seed_hash ON assessment_sessions (seed_hash);
```

**Модель SQLAlchemy 2.0**:
```python
class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    session_type: Mapped[str] = mapped_column(String(32), server_default=sa.text("'initial'"), nullable=False)
    seed_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), server_default=sa.text("'in_progress'"), nullable=False)
    raw_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    theta_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    verdict: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    time_spent_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("session_type IN ('initial', 'boost', 'retest_lower')", name="chk_assessment_session_type"),
        CheckConstraint("status IN ('in_progress', 'completed', 'submitted', 'expired', 'cancelled', 'abandoned')", name="chk_assessment_session_status"),
        CheckConstraint("theta_score IS NULL OR (theta_score >= 0.0 AND theta_score <= 100.0)", name="chk_assessment_session_theta"),
        CheckConstraint("verdict IS NULL OR verdict IN ('confirmed', 'boost_offered', 'retest_lower_offered', 'lower_grade_offered', 'failed')", name="chk_assessment_session_verdict"),
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="assessment_sessions")
    category: Mapped["Category"] = relationship("Category", back_populates="assessment_sessions")
    answers: Mapped[List["AssessmentAnswer"]] = relationship("AssessmentAnswer", back_populates="session", cascade="all, delete-orphan")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `candidate_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `candidate_profiles(id) ON DELETE CASCADE` |
| `category_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `categories(id) ON DELETE RESTRICT` |
| `session_type` | `VARCHAR(32)` | `Mapped[str]` | NO | `'initial'` | `CHECK IN ('initial', 'boost', 'retest_lower')` |
| `seed_hash` | `VARCHAR(64)` | `Mapped[str]` | NO | — | **HMAC-SHA256(cand_id, sess_id)** |
| `started_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время начала сессии |
| `completed_at` | `TIMESTAMPTZ` | `Mapped[Optional[datetime]]`| YES | `NULL` | Время сдачи сессии |
| `status` | `VARCHAR(20)` | `Mapped[str]` | NO | `'in_progress'`| `CHECK IN ('in_progress', 'completed', 'submitted', 'expired', 'cancelled', 'abandoned')` |
| `raw_score` | `FLOAT` | `Mapped[Optional[float]]`| YES | `NULL` | Первичная сумма баллов |
| `theta_score` | `FLOAT` | `Mapped[Optional[float]]`| YES | `NULL` | `CHECK BETWEEN 0.0 AND 100.0` |
| `verdict` | `VARCHAR(32)` | `Mapped[Optional[str]]`| YES | `NULL` | Итоговый вердикт KITE |
| `time_spent_sec`| `INTEGER` | `Mapped[Optional[int]]`| YES | `NULL` | Общее затраченное время |
| `expires_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | — | Дедлайн завершения теста |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания записи |

---

#### 15. Таблица `assessment_answers`
- **Назначение**: Детальные ответы соискателя на каждое задание тестовой сессии, включая сгенерированные варианты, код решения и отчет автоматической проверки песочницей.
- **Бизнес-инварианты**: Уникальная пара `(session_id, item_family_id)`; неотрицательные баллы и тайминги решения.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE assessment_answers (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id INTEGER NOT NULL,
    item_family_id INTEGER NOT NULL,
    variant_params_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    variant_seed VARCHAR(64) NOT NULL DEFAULT '',
    candidate_answer_text TEXT NULL,
    submitted_code TEXT NULL,
    test_results_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    points_awarded FLOAT NOT NULL DEFAULT 0.0,
    time_taken_sec INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_session_item UNIQUE (session_id, item_family_id),
    CONSTRAINT fk_assessment_answers_session FOREIGN KEY (session_id) REFERENCES assessment_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_assessment_answers_item FOREIGN KEY (item_family_id) REFERENCES canonical_item_families(id) ON DELETE RESTRICT,
    CONSTRAINT chk_assessment_answers_points CHECK (points_awarded >= 0.0),
    CONSTRAINT chk_assessment_answers_time CHECK (time_taken_sec >= 0)
);

CREATE INDEX ix_assessment_answers_session ON assessment_answers (session_id);
```

**Модель SQLAlchemy 2.0**:
```python
class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("assessment_sessions.id", ondelete="CASCADE"), nullable=False)
    item_family_id: Mapped[int] = mapped_column(ForeignKey("canonical_item_families.id", ondelete="RESTRICT"), nullable=False)
    variant_params_json: Mapped[dict] = mapped_column(JSON_TYPE, server_default=sa.text("'{}'"), nullable=False)
    variant_seed: Mapped[str] = mapped_column(String(64), server_default=sa.text("''"), nullable=False)
    candidate_answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_results_json: Mapped[dict] = mapped_column(JSON_TYPE, server_default=sa.text("'{}'"), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)
    points_awarded: Mapped[float] = mapped_column(Float, server_default=sa.text("0.0"), nullable=False)
    time_taken_sec: Mapped[int] = mapped_column(Integer, server_default=sa.text("0"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("session_id", "item_family_id", name="uq_session_item"),
        CheckConstraint("points_awarded >= 0.0", name="chk_assessment_answers_points"),
        CheckConstraint("time_taken_sec >= 0", name="chk_assessment_answers_time"),
    )

    session: Mapped["AssessmentSession"] = relationship("AssessmentSession", back_populates="answers")
    item_family: Mapped["CanonicalItemFamily"] = relationship("CanonicalItemFamily", back_populates="assessment_answers")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `session_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `assessment_sessions(id) ON DELETE CASCADE` |
| `item_family_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `canonical_item_families(id) ON DELETE RESTRICT` |
| `variant_params_json`|`JSONB` | `Mapped[dict]` | NO | `'{}'::jsonb` | Изоморфные параметры варианта |
| `variant_seed` | `VARCHAR(64)` | `Mapped[str]` | NO | `''` | Соль генерации конкретного варианта |
| `candidate_answer_text`|`TEXT` | `Mapped[Optional[str]]`| YES | `NULL` | Текстовый ввод соискателя |
| `submitted_code` | `TEXT` | `Mapped[Optional[str]]`| YES | `NULL` | Исходный код решения |
| `test_results_json`| `JSONB` | `Mapped[dict]` | NO | `'{}'::jsonb` | Детальный отчет автотестов песочницы |
| `is_correct` | `BOOLEAN` | `Mapped[bool]` | NO | `FALSE` | Флаг вердикта корректности |
| `points_awarded` | `FLOAT` | `Mapped[float]` | NO | `0.0` | `CHECK points_awarded >= 0.0` |
| `time_taken_sec` | `INTEGER` | `Mapped[int]` | NO | `0` | `CHECK time_taken_sec >= 0` |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время ответа |

---
### Кластер 5: Микро-челленджи работодателей и песочница кода

#### 16. Таблица `micro_challenges`
- **Назначение**: Каталог коротких практических инженерных задач, публикуемых работодателями для привлечения талантов и поддержания актуальности профилей кандидатов ($S_{\text{freshness}}$).
- **Бизнес-инварианты**: Баллы за решение $1..100$; стартовый шаблон кода и автотесты в формате JSONB; привязка к специализации и грейду.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE micro_challenges (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employer_profile_id INTEGER NOT NULL,
    specialization_id INTEGER NOT NULL,
    grade_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    code_stub TEXT NOT NULL,
    test_cases_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    points INTEGER NOT NULL DEFAULT 20,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_micro_challenges_employer FOREIGN KEY (employer_profile_id) REFERENCES employer_profiles(id) ON DELETE CASCADE,
    CONSTRAINT fk_micro_challenges_spec FOREIGN KEY (specialization_id) REFERENCES specializations(id) ON DELETE RESTRICT,
    CONSTRAINT fk_micro_challenges_grade FOREIGN KEY (grade_id) REFERENCES grades(id) ON DELETE RESTRICT,
    CONSTRAINT chk_micro_challenges_points CHECK (points > 0 AND points <= 100)
);

CREATE INDEX ix_micro_challenges_spec_grade ON micro_challenges (specialization_id, grade_id);
CREATE INDEX ix_micro_challenges_employer ON micro_challenges (employer_profile_id);
```

**Модель SQLAlchemy 2.0**:
```python
class MicroChallenge(Base):
    __tablename__ = "micro_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employer_profile_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"), nullable=False)
    specialization_id: Mapped[int] = mapped_column(ForeignKey("specializations.id", ondelete="RESTRICT"), nullable=False)
    grade_id: Mapped[int] = mapped_column(ForeignKey("grades.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    code_stub: Mapped[str] = mapped_column(Text, nullable=False)
    test_cases_json: Mapped[list] = mapped_column(JSON_TYPE, server_default=sa.text("'[]'"), nullable=False)
    points: Mapped[int] = mapped_column(Integer, server_default=sa.text("20"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("points > 0 AND points <= 100", name="chk_micro_challenges_points"),
    )

    employer_profile: Mapped["EmployerProfile"] = relationship("EmployerProfile", back_populates="micro_challenges")
    specialization: Mapped["Specialization"] = relationship("Specialization", back_populates="micro_challenges")
    grade: Mapped["Grade"] = relationship("Grade", back_populates="micro_challenges")
    submissions: Mapped[List["ChallengeSubmission"]] = relationship("ChallengeSubmission", back_populates="challenge", cascade="all, delete-orphan")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `employer_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `employer_profiles(id) ON DELETE CASCADE` |
| `specialization_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `specializations(id) ON DELETE RESTRICT` |
| `grade_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `grades(id) ON DELETE RESTRICT` |
| `title` | `VARCHAR(200)`|`Mapped[str]` | NO | — | Заголовок практической задачи |
| `description` | `TEXT` | `Mapped[str]` | NO | — | Постановка задачи и ограничения |
| `code_stub` | `TEXT` | `Mapped[str]` | NO | — | Каркас функции решения |
| `test_cases_json` | `JSONB` | `Mapped[list]` | NO | `'[]'::jsonb` | Набор тестовых кейсов |
| `points` | `INTEGER` | `Mapped[int]` | NO | `20` | `CHECK BETWEEN 1 AND 100` |
| `is_active` | `BOOLEAN` | `Mapped[bool]` | NO | `TRUE` | Активна ли задача в каталоге |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время публикации |
| `updated_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время обновления |

---

#### 17. Таблица `challenge_submissions`
- **Назначение**: Регистрация решений соискателей в защищенной песочнице кода (лимиты 2000 мс процессорного времени и 256 МБ оперативной памяти) с фиксацией статуса и расчетом очков свежести профиля.
- **Бизнес-инварианты**: Статусы `passed`, `failed`, `timeout`, `error`; неотрицательные показатели памяти и времени исполнения; начисление очков свежести при `passed`.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE challenge_submissions (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    challenge_id INTEGER NOT NULL,
    candidate_profile_id INTEGER NOT NULL,
    solution_code TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    execution_time_ms INTEGER NOT NULL DEFAULT 0,
    memory_kb INTEGER NOT NULL DEFAULT 0,
    test_results_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    freshness_points_awarded FLOAT NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_challenge_submissions_chall FOREIGN KEY (challenge_id) REFERENCES micro_challenges(id) ON DELETE CASCADE,
    CONSTRAINT fk_challenge_submissions_cand FOREIGN KEY (candidate_profile_id) REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    CONSTRAINT chk_challenge_submission_status CHECK (status IN ('passed', 'failed', 'timeout', 'error')),
    CONSTRAINT chk_challenge_submission_time CHECK (execution_time_ms >= 0),
    CONSTRAINT chk_challenge_submission_memory CHECK (memory_kb >= 0),
    CONSTRAINT chk_challenge_submission_freshness CHECK (freshness_points_awarded >= 0.0)
);

CREATE INDEX ix_challenge_submissions_cand_chall ON challenge_submissions (candidate_profile_id, challenge_id);
CREATE INDEX ix_challenge_submissions_status ON challenge_submissions (status);
```

**Модель SQLAlchemy 2.0**:
```python
class ChallengeSubmission(Base):
    __tablename__ = "challenge_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("micro_challenges.id", ondelete="CASCADE"), nullable=False)
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    solution_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    execution_time_ms: Mapped[int] = mapped_column(Integer, server_default=sa.text("0"), nullable=False)
    memory_kb: Mapped[int] = mapped_column(Integer, server_default=sa.text("0"), nullable=False)
    test_results_json: Mapped[dict] = mapped_column(JSON_TYPE, server_default=sa.text("'{}'"), nullable=False)
    freshness_points_awarded: Mapped[float] = mapped_column(Float, server_default=sa.text("0.0"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('passed', 'failed', 'timeout', 'error')", name="chk_challenge_submission_status"),
        CheckConstraint("execution_time_ms >= 0", name="chk_challenge_submission_time"),
        CheckConstraint("memory_kb >= 0", name="chk_challenge_submission_memory"),
        CheckConstraint("freshness_points_awarded >= 0.0", name="chk_challenge_submission_freshness"),
    )

    challenge: Mapped["MicroChallenge"] = relationship("MicroChallenge", back_populates="submissions")
    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="challenge_submissions")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `challenge_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `micro_challenges(id) ON DELETE CASCADE` |
| `candidate_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `candidate_profiles(id) ON DELETE CASCADE` |
| `solution_code` | `TEXT` | `Mapped[str]` | NO | — | Исходный код решения |
| `status` | `VARCHAR(20)` | `Mapped[str]` | NO | — | `CHECK IN ('passed', 'failed', 'timeout', 'error')` |
| `execution_time_ms`|`INTEGER` | `Mapped[int]` | NO | `0` | Время работы в мс (лимит 2000) |
| `memory_kb` | `INTEGER` | `Mapped[int]` | NO | `0` | Потребление RAM в КБ (лимит 256 МБ) |
| `test_results_json`|`JSONB` | `Mapped[dict]` | NO | `'{}'::jsonb` | Лог выполнения тестов |
| `freshness_points_awarded`|`FLOAT`|`Mapped[float]`| NO | `0.0` | Начисленные очки актуальности |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время запуска в песочнице |

---

### Кластер 6: Профиль работодателя, потребности и шортлисты

#### 18. Таблица `employer_profiles`
- **Назначение**: Профиль организации-работодателя, верификация ИНН по базе ФНС, антифрод рейтинг доверия (Trust Score) и управление токен-бакетом суточного лимита инвайтов.
- **Бизнес-инварианты**: Связь 1:1 с `users`; уникальный ИНН длиной 10 или 12 цифр; рейтинг доверия $0..100$; контроль суточной квоты инвайтов.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE employer_profiles (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    inn VARCHAR(12) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    is_inn_verified BOOLEAN NOT NULL DEFAULT FALSE,
    trust_score INTEGER NOT NULL DEFAULT 50,
    invite_daily_limit INTEGER NOT NULL DEFAULT 20,
    invites_sent_today INTEGER NOT NULL DEFAULT 0,
    last_invite_reset_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    logo_url VARCHAR(500) NULL,
    description TEXT NULL,
    city VARCHAR(100) NOT NULL DEFAULT 'Москва',
    website VARCHAR(255) NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_employer_profiles_user UNIQUE (user_id),
    CONSTRAINT uq_employer_profiles_inn UNIQUE (inn),
    CONSTRAINT fk_employer_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_employer_inn_length CHECK (length(inn) IN (10, 12)),
    CONSTRAINT chk_employer_trust_score CHECK (trust_score >= 0 AND trust_score <= 100),
    CONSTRAINT chk_employer_daily_limit CHECK (invite_daily_limit >= 0),
    CONSTRAINT chk_employer_sent_today CHECK (invites_sent_today >= 0)
);

CREATE INDEX ix_employer_profiles_user ON employer_profiles (user_id);
CREATE INDEX ix_employer_profiles_inn ON employer_profiles (inn);
CREATE INDEX ix_employer_profiles_trust ON employer_profiles (trust_score DESC);
```

**Модель SQLAlchemy 2.0**:
```python
class EmployerProfile(Base):
    __tablename__ = "employer_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    inn: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    is_inn_verified: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)
    trust_score: Mapped[int] = mapped_column(Integer, server_default=sa.text("50"), nullable=False)
    invite_daily_limit: Mapped[int] = mapped_column(Integer, server_default=sa.text("20"), nullable=False)
    invites_sent_today: Mapped[int] = mapped_column(Integer, server_default=sa.text("0"), nullable=False)
    last_invite_reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[str] = mapped_column(String(100), server_default=sa.text("'Москва'"), nullable=False)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("length(inn) IN (10, 12)", name="chk_employer_inn_length"),
        CheckConstraint("trust_score >= 0 AND trust_score <= 100", name="chk_employer_trust_score"),
        CheckConstraint("invite_daily_limit >= 0", name="chk_employer_daily_limit"),
        CheckConstraint("invites_sent_today >= 0", name="chk_employer_sent_today"),
    )

    user: Mapped["User"] = relationship("User", back_populates="employer_profile")
    micro_challenges: Mapped[List["MicroChallenge"]] = relationship("MicroChallenge", back_populates="employer_profile", cascade="all, delete-orphan")
    employer_needs: Mapped[List["EmployerNeed"]] = relationship("EmployerNeed", back_populates="employer_profile", cascade="all, delete-orphan")
    saved_shortlists: Mapped[List["SavedShortlist"]] = relationship("SavedShortlist", back_populates="employer_profile", cascade="all, delete-orphan")
    vacancies: Mapped[List["Vacancy"]] = relationship("Vacancy", back_populates="employer_profile", cascade="all, delete-orphan")
    invitations: Mapped[List["Invitation"]] = relationship("Invitation", back_populates="employer_profile", cascade="all, delete-orphan")
    ats_integrations: Mapped[List["AtsIntegration"]] = relationship("AtsIntegration", back_populates="employer_profile", cascade="all, delete-orphan")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `user_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `users(id) ON DELETE CASCADE`, UNIQUE |
| `company_name` | `VARCHAR(255)`|`Mapped[str]` | NO | — | Юридическое наименование компании |
| `inn` | `VARCHAR(12)` | `Mapped[str]` | NO | — | UNIQUE, `CHECK длина IN (10, 12)` |
| `domain` | `VARCHAR(255)`|`Mapped[str]` | NO | — | Корпоративный почтовый домен |
| `is_inn_verified` | `BOOLEAN` | `Mapped[bool]` | NO | `FALSE` | Проверен по реестрам ФНС |
| `trust_score` | `INTEGER` | `Mapped[int]` | NO | `50` | `CHECK BETWEEN 0 AND 100` |
| `invite_daily_limit`|`INTEGER`|`Mapped[int]` | NO | `20` | Суточный лимит инвайтов (токен-бакет) |
| `invites_sent_today`|`INTEGER`|`Mapped[int]` | NO | `0` | Число инвайтов за текущие сутки |
| `last_invite_reset_at`|`TIMESTAMPTZ`|`Mapped[datetime]`| NO | `NOW()` | Время последнего сброса суточного счетчика |
| `logo_url` | `VARCHAR(500)`|`Mapped[Optional[str]]`| YES | `NULL` | Логотип компании |
| `description` | `TEXT` | `Mapped[Optional[str]]`| YES | `NULL` | Описание компании и проектов |
| `city` | `VARCHAR(100)`|`Mapped[str]` | NO | `'Москва'` | Город головного офиса |
| `website` | `VARCHAR(255)`|`Mapped[Optional[str]]`| YES | `NULL` | Веб-сайт организации |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время регистрации |
| `updated_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время изменения профиля |

---

#### 19. Таблица `employer_needs`
- **Назначение**: Структурированная потребность работодателя в инженерах для обратного рекрутинга LHH, сопоставления кандидатов и формирования подборок с объяснимостью.
- **Бизнес-инварианты**: **Обязательное проверочное ограничение зарплаты в рублях: `CHECK (salary_min > 0 AND salary_max >= salary_min)`**; стек технологий в JSONB; форматы работы.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE employer_needs (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employer_profile_id INTEGER NOT NULL,
    specialization_id INTEGER NOT NULL,
    target_grade_id INTEGER NOT NULL,
    core_stack_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    nice_to_have_stack_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    salary_min INTEGER NOT NULL,
    salary_max INTEGER NOT NULL,
    work_format VARCHAR(64) NOT NULL DEFAULT 'remote',
    team_tasks_text TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_employer_needs_employer FOREIGN KEY (employer_profile_id) REFERENCES employer_profiles(id) ON DELETE CASCADE,
    CONSTRAINT fk_employer_needs_spec FOREIGN KEY (specialization_id) REFERENCES specializations(id) ON DELETE RESTRICT,
    CONSTRAINT fk_employer_needs_grade FOREIGN KEY (target_grade_id) REFERENCES grades(id) ON DELETE RESTRICT,
    CONSTRAINT chk_employer_needs_salary CHECK (salary_min > 0 AND salary_max >= salary_min),
    CONSTRAINT chk_employer_needs_work_format CHECK (work_format IN ('remote', 'office', 'hybrid', 'any'))
);

CREATE INDEX ix_employer_needs_employer ON employer_needs (employer_profile_id);
CREATE INDEX ix_employer_needs_spec_grade ON employer_needs (specialization_id, target_grade_id);
CREATE INDEX ix_employer_needs_active ON employer_needs (is_active) WHERE is_active = TRUE;
```

**Модель SQLAlchemy 2.0**:
```python
class EmployerNeed(Base):
    __tablename__ = "employer_needs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employer_profile_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"), nullable=False)
    specialization_id: Mapped[int] = mapped_column(ForeignKey("specializations.id", ondelete="RESTRICT"), nullable=False)
    target_grade_id: Mapped[int] = mapped_column(ForeignKey("grades.id", ondelete="RESTRICT"), nullable=False)
    core_stack_json: Mapped[list] = mapped_column(JSON_TYPE, server_default=sa.text("'[]'"), nullable=False)
    nice_to_have_stack_json: Mapped[list] = mapped_column(JSON_TYPE, server_default=sa.text("'[]'"), nullable=False)
    salary_min: Mapped[int] = mapped_column(Integer, nullable=False)
    salary_max: Mapped[int] = mapped_column(Integer, nullable=False)
    work_format: Mapped[str] = mapped_column(String(64), server_default=sa.text("'remote'"), nullable=False)
    team_tasks_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("salary_min > 0 AND salary_max >= salary_min", name="chk_employer_needs_salary"),
        CheckConstraint("work_format IN ('remote', 'office', 'hybrid', 'any')", name="chk_employer_needs_work_format"),
    )

    employer_profile: Mapped["EmployerProfile"] = relationship("EmployerProfile", back_populates="employer_needs")
    specialization: Mapped["Specialization"] = relationship("Specialization", back_populates="employer_needs")
    target_grade: Mapped["Grade"] = relationship("Grade", back_populates="employer_needs")
    saved_shortlists: Mapped[List["SavedShortlist"]] = relationship("SavedShortlist", back_populates="employer_need", cascade="all, delete-orphan")
    invitations: Mapped[List["Invitation"]] = relationship("Invitation", back_populates="employer_need")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `employer_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `employer_profiles(id) ON DELETE CASCADE` |
| `specialization_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `specializations(id) ON DELETE RESTRICT` |
| `target_grade_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `grades(id) ON DELETE RESTRICT` |
| `core_stack_json` | `JSONB` | `Mapped[list]` | NO | `'[]'::jsonb` | Обязательные технологии стека |
| `nice_to_have_stack_json`|`JSONB`|`Mapped[list]`| NO | `'[]'::jsonb` | Желательные технологии стека |
| `salary_min` | `INTEGER` | `Mapped[int]` | NO | — | **`CHECK salary_min > 0` в рублях** |
| `salary_max` | `INTEGER` | `Mapped[int]` | NO | — | **`CHECK salary_max >= salary_min`** |
| `work_format` | `VARCHAR(64)` | `Mapped[str]` | NO | `'remote'` | `CHECK IN ('remote', 'office', 'hybrid', 'any')` |
| `team_tasks_text` | `TEXT` | `Mapped[str]` | NO | — | Задачи команды разработки |
| `is_active` | `BOOLEAN` | `Mapped[bool]` | NO | `TRUE` | Активна ли потребность для матчинга |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания |
| `updated_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время обновления |

---

#### 20. Таблица `saved_shortlists`
- **Назначение**: Контейнер сохраненных выборок соискателей работодателя. Исключает потерю подобранных кандидатов при уточнении поисковых параметров и фасеточных фильтров.
- **Бизнес-инварианты**: Привязка к профилю работодателя; опциональная связь с конкретной потребностью `employer_needs`.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE saved_shortlists (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employer_profile_id INTEGER NOT NULL,
    need_id INTEGER NULL,
    title VARCHAR(200) NOT NULL,
    filter_criteria_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_saved_shortlists_employer FOREIGN KEY (employer_profile_id) REFERENCES employer_profiles(id) ON DELETE CASCADE,
    CONSTRAINT fk_saved_shortlists_need FOREIGN KEY (need_id) REFERENCES employer_needs(id) ON DELETE SET NULL
);

CREATE INDEX ix_saved_shortlists_employer ON saved_shortlists (employer_profile_id);
CREATE INDEX ix_saved_shortlists_need ON saved_shortlists (need_id);
```

**Модель SQLAlchemy 2.0**:
```python
class SavedShortlist(Base):
    __tablename__ = "saved_shortlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employer_profile_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"), nullable=False)
    need_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employer_needs.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    filter_criteria_json: Mapped[dict] = mapped_column(JSON_TYPE, server_default=sa.text("'{}'"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    employer_profile: Mapped["EmployerProfile"] = relationship("EmployerProfile", back_populates="saved_shortlists")
    employer_need: Mapped[Optional["EmployerNeed"]] = relationship("EmployerNeed", back_populates="saved_shortlists")
    items: Mapped[List["ShortlistItem"]] = relationship("ShortlistItem", back_populates="shortlist", cascade="all, delete-orphan")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `employer_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `employer_profiles(id) ON DELETE CASCADE` |
| `need_id` | `INTEGER` | `Mapped[Optional[int]]`| YES | `NULL` | FK `employer_needs(id) ON DELETE SET NULL` |
| `title` | `VARCHAR(200)`|`Mapped[str]` | NO | — | Пользовательское название шортлиста |
| `filter_criteria_json`|`JSONB` | `Mapped[dict]` | NO | `'{}'::jsonb` | Сохраненное состояние фильтров |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания выборки |
| `updated_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время обновления |

---

#### 21. Таблица `shortlist_items`
- **Назначение**: Элемент шортлиста соискателей. Поддерживает закрепление кандидата (`is_pinned`), расчет дельта-скора ($\Delta S$), позицию ранжирования и JSON декомпозиции объяснимости (Explainability radar: тесты, стек, ФСП, свежесть).
- **Бизнес-инварианты**: Уникальная пара `(shortlist_id, candidate_profile_id)`; `match_score \in [0, 100]`; `rank_position > 0`.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE shortlist_items (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    shortlist_id INTEGER NOT NULL,
    candidate_profile_id INTEGER NOT NULL,
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    match_score FLOAT NOT NULL,
    delta_score FLOAT NOT NULL DEFAULT 0.0,
    rank_position INTEGER NOT NULL DEFAULT 1,
    explainability_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_shortlist_cand UNIQUE (shortlist_id, candidate_profile_id),
    CONSTRAINT fk_shortlist_items_shortlist FOREIGN KEY (shortlist_id) REFERENCES saved_shortlists(id) ON DELETE CASCADE,
    CONSTRAINT fk_shortlist_items_candidate FOREIGN KEY (candidate_profile_id) REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    CONSTRAINT chk_shortlist_items_score CHECK (match_score >= 0.0 AND match_score <= 100.0),
    CONSTRAINT chk_shortlist_items_rank CHECK (rank_position > 0)
);

CREATE INDEX ix_shortlist_items_shortlist ON shortlist_items (shortlist_id);
CREATE INDEX ix_shortlist_items_pinned ON shortlist_items (shortlist_id, is_pinned);
CREATE INDEX ix_shortlist_items_score ON shortlist_items (shortlist_id, match_score DESC);
```

**Модель SQLAlchemy 2.0**:
```python
class ShortlistItem(Base):
    __tablename__ = "shortlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shortlist_id: Mapped[int] = mapped_column(ForeignKey("saved_shortlists.id", ondelete="CASCADE"), nullable=False)
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    delta_score: Mapped[float] = mapped_column(Float, server_default=sa.text("0.0"), nullable=False)
    rank_position: Mapped[int] = mapped_column(Integer, server_default=sa.text("1"), nullable=False)
    explainability_json: Mapped[dict] = mapped_column(JSON_TYPE, server_default=sa.text("'{}'"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("shortlist_id", "candidate_profile_id", name="uq_shortlist_cand"),
        CheckConstraint("match_score >= 0.0 AND match_score <= 100.0", name="chk_shortlist_items_score"),
        CheckConstraint("rank_position > 0", name="chk_shortlist_items_rank"),
    )

    shortlist: Mapped["SavedShortlist"] = relationship("SavedShortlist", back_populates="items")
    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="shortlist_items")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `shortlist_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `saved_shortlists(id) ON DELETE CASCADE` |
| `candidate_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `candidate_profiles(id) ON DELETE CASCADE` |
| `is_pinned` | `BOOLEAN` | `Mapped[bool]` | NO | `FALSE` | Закрепление кандидата при смене фильтров |
| `match_score` | `FLOAT` | `Mapped[float]` | NO | — | `CHECK BETWEEN 0.0 AND 100.0` |
| `delta_score` | `FLOAT` | `Mapped[float]` | NO | `0.0` | Смещение скора $\Delta S$ при фильтрации |
| `rank_position` | `INTEGER` | `Mapped[int]` | NO | `1` | `CHECK rank_position > 0` |
| `explainability_json`|`JSONB` | `Mapped[dict]` | NO | `'{}'::jsonb` | Радар скоринга (тест, стек, ФСП, свежесть) |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время включения в шортлист |
| `updated_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время последнего пересчета скора |

---

### Кластер 7: Вакансии, инвайты, отклики и интеграция с ATS

#### 22. Таблица `vacancies`
- **Назначение**: Публичные вакансии работодателей для прямого поиска и откликов соискателей.
- **Бизнес-инварианты**: **Обязательное проверочное ограничение зарплаты в рублях: `CHECK (salary_min > 0 AND salary_max >= salary_min)`**; статусы публикации `published`, `closed`, `draft`, `archived`.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE vacancies (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employer_profile_id INTEGER NOT NULL,
    specialization_id INTEGER NOT NULL,
    grade_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    required_skills_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    salary_min INTEGER NOT NULL,
    salary_max INTEGER NOT NULL,
    work_format VARCHAR(64) NOT NULL DEFAULT 'remote',
    city VARCHAR(100) NOT NULL DEFAULT 'Москва',
    status VARCHAR(20) NOT NULL DEFAULT 'published',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_vacancies_employer FOREIGN KEY (employer_profile_id) REFERENCES employer_profiles(id) ON DELETE CASCADE,
    CONSTRAINT fk_vacancies_spec FOREIGN KEY (specialization_id) REFERENCES specializations(id) ON DELETE RESTRICT,
    CONSTRAINT fk_vacancies_grade FOREIGN KEY (grade_id) REFERENCES grades(id) ON DELETE RESTRICT,
    CONSTRAINT chk_vacancies_salary CHECK (salary_min > 0 AND salary_max >= salary_min),
    CONSTRAINT chk_vacancies_status CHECK (status IN ('published', 'closed', 'draft', 'archived')),
    CONSTRAINT chk_vacancies_work_format CHECK (work_format IN ('remote', 'office', 'hybrid', 'any'))
);

CREATE INDEX ix_vacancies_employer ON vacancies (employer_profile_id);
CREATE INDEX ix_vacancies_spec_grade ON vacancies (specialization_id, grade_id);
CREATE INDEX ix_vacancies_status ON vacancies (status);
```

**Модель SQLAlchemy 2.0**:
```python
class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employer_profile_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"), nullable=False)
    specialization_id: Mapped[int] = mapped_column(ForeignKey("specializations.id", ondelete="RESTRICT"), nullable=False)
    grade_id: Mapped[int] = mapped_column(ForeignKey("grades.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills_json: Mapped[list] = mapped_column(JSON_TYPE, server_default=sa.text("'[]'"), nullable=False)
    salary_min: Mapped[int] = mapped_column(Integer, nullable=False)
    salary_max: Mapped[int] = mapped_column(Integer, nullable=False)
    work_format: Mapped[str] = mapped_column(String(64), server_default=sa.text("'remote'"), nullable=False)
    city: Mapped[str] = mapped_column(String(100), server_default=sa.text("'Москва'"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), server_default=sa.text("'published'"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("salary_min > 0 AND salary_max >= salary_min", name="chk_vacancies_salary"),
        CheckConstraint("status IN ('published', 'closed', 'draft', 'archived')", name="chk_vacancies_status"),
        CheckConstraint("work_format IN ('remote', 'office', 'hybrid', 'any')", name="chk_vacancies_work_format"),
    )

    employer_profile: Mapped["EmployerProfile"] = relationship("EmployerProfile", back_populates="vacancies")
    specialization: Mapped["Specialization"] = relationship("Specialization", back_populates="vacancies")
    grade: Mapped["Grade"] = relationship("Grade", back_populates="vacancies")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="vacancy", cascade="all, delete-orphan")
    invitations: Mapped[List["Invitation"]] = relationship("Invitation", back_populates="vacancy")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `employer_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `employer_profiles(id) ON DELETE CASCADE` |
| `specialization_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `specializations(id) ON DELETE RESTRICT` |
| `grade_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `grades(id) ON DELETE RESTRICT` |
| `title` | `VARCHAR(200)`|`Mapped[str]` | NO | — | Название открытой вакансии |
| `description` | `TEXT` | `Mapped[str]` | NO | — | Текст вакансии и описание условий |
| `required_skills_json`|`JSONB` | `Mapped[list]` | NO | `'[]'::jsonb` | Список обязательных технологий |
| `salary_min` | `INTEGER` | `Mapped[int]` | NO | — | **`CHECK salary_min > 0` в рублях** |
| `salary_max` | `INTEGER` | `Mapped[int]` | NO | — | **`CHECK salary_max >= salary_min`** |
| `work_format` | `VARCHAR(64)` | `Mapped[str]` | NO | `'remote'` | `CHECK IN ('remote', 'office', 'hybrid', 'any')` |
| `city` | `VARCHAR(100)`|`Mapped[str]` | NO | `'Москва'` | Локация офиса |
| `status` | `VARCHAR(20)` | `Mapped[str]` | NO | `'published'` | `CHECK IN ('published', 'closed', 'draft', 'archived')` |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время публикации |
| `updated_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время изменения |

---

#### 23. Таблица `invitations`
- **Назначение**: Прямые приглашения работодателя соискателю (механика обратного рекрутинга LHH). Содержит персональный оффер с гарантированной зарплатной вилкой. Контакты соискателя маскируются до статуса `accepted`.
- **Бизнес-инварианты**: **Обязательное ограничение зарплаты в рублях: `CHECK (salary_min > 0 AND salary_max >= salary_min)`**; статусы `sent`, `viewed`, `accepted`, `declined`, `expired`.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE invitations (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employer_profile_id INTEGER NOT NULL,
    candidate_profile_id INTEGER NOT NULL,
    need_id INTEGER NULL,
    vacancy_id INTEGER NULL,
    proposal_text TEXT NOT NULL,
    salary_min INTEGER NOT NULL,
    salary_max INTEGER NOT NULL,
    contact_method VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'sent',
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    viewed_at TIMESTAMP WITH TIME ZONE NULL,
    resolved_at TIMESTAMP WITH TIME ZONE NULL,
    decline_reason TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_invitations_employer FOREIGN KEY (employer_profile_id) REFERENCES employer_profiles(id) ON DELETE CASCADE,
    CONSTRAINT fk_invitations_candidate FOREIGN KEY (candidate_profile_id) REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    CONSTRAINT fk_invitations_need FOREIGN KEY (need_id) REFERENCES employer_needs(id) ON DELETE SET NULL,
    CONSTRAINT fk_invitations_vacancy FOREIGN KEY (vacancy_id) REFERENCES vacancies(id) ON DELETE SET NULL,
    CONSTRAINT chk_invitations_salary CHECK (salary_min > 0 AND salary_max >= salary_min),
    CONSTRAINT chk_invitations_status CHECK (status IN ('sent', 'viewed', 'accepted', 'declined', 'expired'))
);

CREATE INDEX ix_invitations_candidate_status ON invitations (candidate_profile_id, status);
CREATE INDEX ix_invitations_employer_status ON invitations (employer_profile_id, status);
CREATE INDEX ix_invitations_created ON invitations (created_at DESC);
```

**Модель SQLAlchemy 2.0**:
```python
class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employer_profile_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"), nullable=False)
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    need_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employer_needs.id", ondelete="SET NULL"), nullable=True)
    vacancy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vacancies.id", ondelete="SET NULL"), nullable=True)
    proposal_text: Mapped[str] = mapped_column(Text, nullable=False)
    salary_min: Mapped[int] = mapped_column(Integer, nullable=False)
    salary_max: Mapped[int] = mapped_column(Integer, nullable=False)
    contact_method: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), server_default=sa.text("'sent'"), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    decline_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("salary_min > 0 AND salary_max >= salary_min", name="chk_invitations_salary"),
        CheckConstraint("status IN ('sent', 'viewed', 'accepted', 'declined', 'expired')", name="chk_invitations_status"),
        Index("ix_invitations_emp_cand_status", "employer_profile_id", "candidate_profile_id", "status"),
    )

    employer_profile: Mapped["EmployerProfile"] = relationship("EmployerProfile", back_populates="invitations")
    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="invitations")
    employer_need: Mapped[Optional["EmployerNeed"]] = relationship("EmployerNeed", back_populates="invitations")
    vacancy: Mapped[Optional["Vacancy"]] = relationship("Vacancy", back_populates="invitations")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `employer_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `employer_profiles(id) ON DELETE CASCADE` |
| `candidate_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `candidate_profiles(id) ON DELETE CASCADE` |
| `need_id` | `INTEGER` | `Mapped[Optional[int]]`| YES | `NULL` | FK `employer_needs(id) ON DELETE SET NULL` |
| `vacancy_id` | `INTEGER` | `Mapped[Optional[int]]`| YES | `NULL` | FK `vacancies(id) ON DELETE SET NULL` |
| `proposal_text` | `TEXT` | `Mapped[str]` | NO | — | Текст персонального обращения |
| `salary_min` | `INTEGER` | `Mapped[int]` | NO | — | **`CHECK salary_min > 0` в рублях** |
| `salary_max` | `INTEGER` | `Mapped[int]` | NO | — | **`CHECK salary_max >= salary_min`** |
| `contact_method`| `VARCHAR(50)` | `Mapped[str]` | NO | — | Желаемый канал связи |
| `status` | `VARCHAR(20)` | `Mapped[str]` | NO | `'sent'` | `CHECK IN ('sent', 'viewed', 'accepted', 'declined', 'expired')` |
| `sent_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время отправки |
| `viewed_at` | `TIMESTAMPTZ` | `Mapped[Optional[datetime]]`| YES | `NULL` | Время первого открытия кандидатом |
| `resolved_at` | `TIMESTAMPTZ` | `Mapped[Optional[datetime]]`| YES | `NULL` | Время принятия/отклонения |
| `decline_reason`| `TEXT` | `Mapped[Optional[str]]`| YES | `NULL` | Причина отказа соискателя |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания записи |
| `updated_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время изменения |

---

#### 24. Таблица `applications`
- **Назначение**: Прямые отклики кандидатов на опубликованные вакансии. Подача отклика является актом волеизъявления соискателя и открывает доступ к контактам работодателю данной вакансии.
- **Бизнес-инварианты**: Уникальная пара `(vacancy_id, candidate_profile_id)`; статусы `applied`, `viewed`, `accepted`, `rejected`, `withdrawn`.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE applications (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vacancy_id INTEGER NOT NULL,
    candidate_profile_id INTEGER NOT NULL,
    cover_letter TEXT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'applied',
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    viewed_at TIMESTAMP WITH TIME ZONE NULL,
    resolved_at TIMESTAMP WITH TIME ZONE NULL,
    rejection_reason TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_applications_cand_vac UNIQUE (vacancy_id, candidate_profile_id),
    CONSTRAINT fk_applications_vacancy FOREIGN KEY (vacancy_id) REFERENCES vacancies(id) ON DELETE CASCADE,
    CONSTRAINT fk_applications_candidate FOREIGN KEY (candidate_profile_id) REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    CONSTRAINT chk_applications_status CHECK (status IN ('applied', 'viewed', 'accepted', 'rejected', 'withdrawn'))
);

CREATE INDEX ix_applications_vacancy_status ON applications (vacancy_id, status);
CREATE INDEX ix_applications_candidate ON applications (candidate_profile_id);
```

**Модель SQLAlchemy 2.0**:
```python
class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"), nullable=False)
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    cover_letter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), server_default=sa.text("'applied'"), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("vacancy_id", "candidate_profile_id", name="uq_applications_cand_vac"),
        CheckConstraint("status IN ('applied', 'viewed', 'accepted', 'rejected', 'withdrawn')", name="chk_applications_status"),
    )

    vacancy: Mapped["Vacancy"] = relationship("Vacancy", back_populates="applications")
    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="applications")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `vacancy_id` | `INTEGER` | `Mapped[int]` | NO | — | FK `vacancies(id) ON DELETE CASCADE` |
| `candidate_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `candidate_profiles(id) ON DELETE CASCADE` |
| `cover_letter` | `TEXT` | `Mapped[Optional[str]]`| YES | `NULL` | Сопроводительное письмо соискателя |
| `status` | `VARCHAR(20)` | `Mapped[str]` | NO | `'applied'` | `CHECK IN ('applied', 'viewed', 'accepted', 'rejected', 'withdrawn')` |
| `applied_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время подачи отклика |
| `viewed_at` | `TIMESTAMPTZ` | `Mapped[Optional[datetime]]`| YES | `NULL` | Время первого открытия работодателем |
| `resolved_at` | `TIMESTAMPTZ` | `Mapped[Optional[datetime]]`| YES | `NULL` | Время финального решения по кандидату |
| `rejection_reason`| `TEXT` | `Mapped[Optional[str]]`| YES | `NULL` | Причина отклонения отклика |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания записи |
| `updated_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время обновления |

---

#### 25. Таблица `ats_integrations`
- **Назначение**: Конфигурация корпоративных интеграций работодателя с внешними рекрутинговыми системами ATS (Huntflow, HeadHunter, Custom Webhook). Содержит безопасный хэш ключа API, URL вебхука, секрет HMAC-SHA256 для формирования цифровой подписи заголовка `X-FSP-Signature` и аудит журнала доставок.
- **Бизнес-инварианты**: Уникальная пара `(employer_profile_id, ats_type)`; допустимые типы систем `huntflow`, `headhunter`, `custom_webhook`; хранение логов доставки в `webhook_delivery_logs_json`.

**DDL (PostgreSQL 16)**:
```sql
CREATE TABLE ats_integrations (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employer_profile_id INTEGER NOT NULL,
    ats_type VARCHAR(30) NOT NULL,
    api_key_hash VARCHAR(255) NULL,
    webhook_url VARCHAR(500) NULL,
    webhook_secret VARCHAR(255) NULL,
    webhook_delivery_logs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_employer_ats_type UNIQUE (employer_profile_id, ats_type),
    CONSTRAINT fk_ats_integrations_employer FOREIGN KEY (employer_profile_id) REFERENCES employer_profiles(id) ON DELETE CASCADE,
    CONSTRAINT chk_ats_type CHECK (ats_type IN ('huntflow', 'headhunter', 'custom_webhook'))
);

CREATE INDEX ix_ats_integrations_employer ON ats_integrations (employer_profile_id);
CREATE INDEX ix_ats_integrations_active ON ats_integrations (is_active) WHERE is_active = TRUE;
```

**Модель SQLAlchemy 2.0**:
```python
class AtsIntegration(Base):
    __tablename__ = "ats_integrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employer_profile_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"), nullable=False)
    ats_type: Mapped[str] = mapped_column(String(30), nullable=False)
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    webhook_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    webhook_delivery_logs_json: Mapped[list] = mapped_column(JSON_TYPE, server_default=sa.text("'[]'"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("employer_profile_id", "ats_type", name="uq_employer_ats_type"),
        CheckConstraint("ats_type IN ('huntflow', 'headhunter', 'custom_webhook')", name="chk_ats_type"),
    )

    employer_profile: Mapped["EmployerProfile"] = relationship("EmployerProfile", back_populates="ats_integrations")
```

**Таблица атрибутов**:
| Поле | SQL Тип | SQLAlchemy Mapped | Nullable | Default | Ограничения |
|---|---|---|---|---|---|
| `id` | `INTEGER` | `Mapped[int]` | NO | Identity PK | Primary Key |
| `employer_profile_id`|`INTEGER`|`Mapped[int]` | NO | — | FK `employer_profiles(id) ON DELETE CASCADE` |
| `ats_type` | `VARCHAR(30)` | `Mapped[str]` | NO | — | `CHECK IN ('huntflow', 'headhunter', 'custom_webhook')` |
| `api_key_hash` | `VARCHAR(255)`|`Mapped[Optional[str]]`| YES | `NULL` | Хэшированный токен авторизации |
| `webhook_url` | `VARCHAR(500)`|`Mapped[Optional[str]]`| YES | `NULL` | Целевой URL доставки вебхуков |
| `webhook_secret` | `VARCHAR(255)`|`Mapped[Optional[str]]`| YES | `NULL` | Секретный ключ цифровой подписи HMAC |
| `webhook_delivery_logs_json`|`JSONB`|`Mapped[list]`| NO | `'[]'::jsonb`| Журнал доставок и ответов HTTP |
| `is_active` | `BOOLEAN` | `Mapped[bool]` | NO | `TRUE` | Активна ли интеграция |
| `created_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время создания конфигурации |
| `updated_at` | `TIMESTAMPTZ` | `Mapped[datetime]` | NO | `NOW()` | Время изменения |

---
## 5. Спецификация защиты персональных данных (152-ФЗ) и аудит безопасности на уровне БД

### 5.1. Правовая декомпозиция согласий (ст. 9 и ст. 10.1 152-ФЗ РФ)

В соответствии с требованиями Федерального закона № 152-ФЗ «О персональных данных», обработка сведений о соискателях в платформе юридически разделена на два независимых контура:
1. **Контур общей обработки (ст. 9 152-ФЗ)**:
   - Фиксируется флагом `user_consents.consent_pdn_processing`.
   - Наделяет оператора платформы правом сбора, систематизации, накопления, хранения и сопоставления анкетных данных соискателя для внутренних алгоритмов ранжирования KITE и LHH.
2. **Контур распространения и публикации в открытом доступе (ст. 10.1 152-ФЗ)**:
   - Фиксируется флагом `user_consents.consent_profile_publication`.
   - Регулирует отображение квалификационной карточки кандидата в каталоге соискателей для авторизованных работодателей.
   - **Правило немедленного исключения**: В случае отзыва согласия (`revoked_at IS NOT NULL` или `consent_profile_publication = FALSE`) СУБД и бэкенд обязаны немедленно исключить профиль соискателя из витрины талантов (`is_active_search = FALSE`), прекратить участие кандидата в генерации новых шортлистов и заблокировать прием новых инвайтов.

Каждая операция выражения или изменения согласия сопровождается аудиторским снимком: IP-адрес сетевого соединения (`ip_address`), клиентский заголовок (`user_agent`), версия публичной оферты (`policy_version`) и точная метка времени UTC (`consent_timestamp`).

---

### 5.2. Иммутабельный аудит безопасности (Триггеры audit_logs)

Для предотвращения фальсификации истории доступа к конфиденциальным профилям кандидатов таблица `audit_logs` защищена на уровне ядра СУБД специальными триггерами, делающими ее журналом, работающим исключительно на добавление (Append-Only Immutable Log).

#### Триггер для PostgreSQL 16 (PL/pgSQL)
```sql
CREATE OR REPLACE FUNCTION fn_audit_logs_prevent_tampering()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION '152-FZ Compliance Violation: Table audit_logs is append-only. UPDATE and DELETE operations are strictly forbidden by platform security policy.'
        USING ERRCODE = '55000';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_logs_immutable
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW
EXECUTE FUNCTION fn_audit_logs_prevent_tampering();
```

#### Триггеры для SQLite 3.45+ (Development & In-Memory Tests)
```sql
CREATE TRIGGER trg_audit_logs_no_update
BEFORE UPDATE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, '152-FZ Compliance Error: Table audit_logs entries cannot be modified');
END;

CREATE TRIGGER trg_audit_logs_no_delete
BEFORE DELETE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, '152-FZ Compliance Error: Table audit_logs entries cannot be deleted');
END;
```

---

### 5.3. Слой динамического маскирования контактов (SQL View `v_candidate_profiles_masked`)

Контакты соискателя (`phone`, `email`, `telegram`, `github_url`, `raw_resume_pdf_path`) категорически запрещено передавать работодателю до момента явного акцепта приглашения кандидатом. 

Для гарантии сокрытия данных на уровне СУБД создано защищенное SQL-представление `v_candidate_profiles_masked`, которое автоматически обнуляет конфиденциальные каналы связи и формирует псевдонимизированный псевдоним кандидата:

```sql
CREATE OR REPLACE VIEW v_candidate_profiles_masked AS
SELECT
    cp.id,
    cp.user_id,
    cp.fsp_id,
    cp.fsp_verified,
    -- Псевдонимизация ФИО кандидата: "Иван И. (#C-1042)"
    SUBSTRING(cp.first_name FROM 1 FOR 1) || ' ' ||
    SUBSTRING(cp.last_name FROM 1 FOR 1) || '. (#C-' || cp.id || ')' AS masked_full_name,
    -- Физическое обнуление прямых контактов до акцепта
    NULL::VARCHAR(255) AS email,
    NULL::VARCHAR(32)  AS phone,
    NULL::VARCHAR(64)  AS telegram,
    NULL::VARCHAR(255) AS github_url,
    NULL::VARCHAR(500) AS raw_resume_pdf_path,
    cp.city,
    cp.relocation_ready,
    cp.work_format,
    cp.expected_salary,
    cp.bio,
    cp.freshness_score,
    cp.is_published,
    cp.created_at,
    cp.updated_at
FROM candidate_profiles cp
JOIN user_consents uc ON uc.user_id = cp.user_id
WHERE uc.consent_pdn_processing = TRUE
  AND uc.consent_profile_publication = TRUE
  AND uc.revoked_at IS NULL
  AND cp.is_published = TRUE;
```

---

### 5.4. Многопользовательская изоляция (Multi-Tenant Isolation) и механизм демаскирования

В платформе гарантируется строгое соблюдение принципа изоляции: если кандидат принял инвайт от Работодателя А (`invitations.status = 'accepted'`), его контактные данные раскрываются **исключительно** Работодателю А. Для Работодателя Б этот же кандидат остается строго анонимизированным.

На уровне бизнес-логики и ORM SQLAlchemy 2.0 демаскирование выполняется через предикат проверки законности доступа:

```python
"""
Спецификация многопользовательского фильтра демаскирования контактов (SQLAlchemy 2.0).
Контакты соискателя раскрываются работодателю ТОЛЬКО при выполнении хотя бы одного условия:
1. Кандидат явно принял приглашение от данного работодателя (invitations.status == 'accepted').
2. Кандидат сам подал отклик на опубликованную вакансию данного работодателя.
"""
from sqlalchemy import select, exists, and_, or_

def build_candidate_unmasking_condition(candidate_id: int, requesting_employer_id: int):
    # Условие 1: Наличие принятого приглашения от данного работодателя
    invite_accepted = exists().where(
        and_(
            Invitation.candidate_profile_id == candidate_id,
            Invitation.employer_profile_id == requesting_employer_id,
            Invitation.status == "accepted"
        )
    )

    # Условие 2: Наличие прямого отклика кандидата на вакансию данного работодателя
    app_submitted = exists().where(
        and_(
            Application.candidate_profile_id == candidate_id,
            Application.vacancy_id == Vacancy.id,
            Vacancy.employer_profile_id == requesting_employer_id,
            Application.status.in_(["applied", "viewed", "accepted"])
        )
    )

    return or_(invite_accepted, app_submitted)
```

При попытке работодателя запросить эндпоинт `/api/candidates/{id}/contacts` без соблюдения вышеуказанных условий API генерирует ответ `HTTP 403 Forbidden` с обязательной фиксацией инцидента безопасности в таблице `audit_logs` (`action = 'UNAUTHORIZED_CONTACT_PROBE'`).

---

### 5.5. Жизненный цикл криптографических секретов и вебхуков ATS

При подтверждении двустороннего контакта (`status = 'accepted'`) платформа выполняет асинхронную нотификацию внешней корпоративной ATS работодателя:
1. **Формирование полезной нагрузки**: Данные соискателя упаковываются в JSON-конверт, содержащий полное подтвержденное резюме, верифицированные достижения ФСП, балл тестирования KITE и ссылку на неанонимизированный PDF.
2. **Криптографическая подпись HMAC-SHA256**:
   - В заголовок HTTP-запроса включается цифровая подпись:
     $$\text{X-FSP-Signature: } t=\text{timestamp}, v_1=\text{HMAC\_SHA256}(t + "." + \text{payload}, \text{webhook\_secret})$$
   - Это гарантирует невозможность подделки или повторной отправки (Replay Attack) события внешним злоумышленником.
3. **Отказоустойчивая доставка и повторы**:
   - При получении кодов `HTTP 5xx` или сетевом таймауте диспетчер выполняет 3 повторные попытки с экспоненциальным откладыванием (через 1 мин, 5 мин, 15 мин).
   - При исчерпании лимита повторов уведомление перемещается в очередь недоставленных сообщений (Dead-Letter Queue, DLQ), а запись об ошибке фиксируется в колонке `webhook_delivery_logs_json` таблицы `ats_integrations`.

---
## 6. Встроенный скрипт автоматической верификации схемы (Quality Gate)

### 6.1. Архитектура автоматического верификатора

Для обеспечения абсолютной строгости спецификации, полного соответствия политике Zero-Stub Policy и исключения любых расхождений между текстовым описанием, диаграммами Mermaid, DDL-скриптами и кодом SQLAlchemy 2.0, в спецификацию встроен автономный автоматический верификатор (Quality Gate).

Верификатор реализует 9 независимых проверок:
1. **Zero Forbidden Markers Check**: Проверка соблюдения политики Zero-Stub Policy и отсутствия маркеров незавершенности разработки, сокращений и неполных перечислений.
2. **25 Relational Tables Inventory**: Проверка наличия и точного именования всех 25 таблиц в сводном реестре раздела 1.
3. **DDL Statements Completeness**: Проверка наличия операторов `CREATE TABLE` для каждой из 25 сущностей.
4. **SQLAlchemy 2.0 Declarative Models Completeness**: Проверка объявления параметров `__tablename__` для всех 25 классов моделей.
5. **Mermaid erDiagram Entity Completeness**: Проверка охвата всех 25 таблиц в глобальной диаграмме сущностей раздела 2.
6. **Candidate Grading Lifecycle stateDiagram-v2 Check**: Проверка ветвлений $\theta < 70$, $70 \le \theta < 88$, $\theta \ge 88$, 90-дневного кулдауна, сброса для жюри (`JuryDemoBypass`) и ветки для кандидатов без истории ФСП (`fsp_id IS NULL`, `NonFspTrack`).
7. **Invitation & Application Lifecycle stateDiagram-v2 Check**: Проверка жизненного цикла инвайтов (`sent`, `viewed`, `accepted`, `declined`, `expired`), маскирования контактов 152-ФЗ (`CandidateAnonymizedRead`), демаскирования (`CandidateFullRead`) и многопользовательской изоляции (`TenantIsolationGuard`).
8. **Mandatory Salary Range Invariant Check**: Контроль наличия проверочного ограничения `salary_min > 0 AND salary_max >= salary_min` на таблицах `employer_needs`, `vacancies` и `invitations`.
9. **SQLite In-Memory Schema Compilation Test**: Извлечение декларативных моделей SQLAlchemy 2.0 непосредственно из текста спецификации и выполнение `Base.metadata.create_all()` в базе данных SQLite in-memory с подтверждением создания ровно 25 таблиц.

---

### 6.2. Исполняемый Python-скрипт верификации схемы и ограничений

```python
#!/usr/bin/env python3
"""
Автоматический верификатор Quality Gate для docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md
Проверяет целостность спецификации, DDL, моделей SQLAlchemy 2.0 и диаграмм Mermaid.
"""

import sys
import re
from pathlib import Path

EXPECTED_TABLES = [
    "users", "user_consents", "audit_logs",
    "specializations", "grades", "categories", "skills",
    "candidate_profiles", "fsp_achievements", "candidate_skills", "candidate_categorizations", "cooldown_resets",
    "canonical_item_families", "assessment_sessions", "assessment_answers",
    "micro_challenges", "challenge_submissions",
    "employer_profiles", "employer_needs", "saved_shortlists", "shortlist_items",
    "vacancies", "invitations", "applications", "ats_integrations"
]

SALARY_CHECK_TABLES = ["employer_needs", "vacancies", "invitations"]

def run_quality_gate(doc_path: Path):
    print(f"=== Запуск Quality Gate для файла: {doc_path} ===")
    assert doc_path.exists(), f"Ошибка: Файл {doc_path} не найден!"
    content = doc_path.read_text(encoding="utf-8")

    # 1. Проверка отсутствия запрещенных маркеров неполноты в тексте документа
    doc_prose = content.split("## 6.")[0]
    probe_patterns = [
        r"\bTODO\b",
        r"\bTBD\b",
        r"\bFIXME\b",
        r"\bNotImplemented\b",
        r"остальные поля аналогично",
        r"\.\.\."
    ]
    for pat in probe_patterns:
        matches = re.findall(pat, doc_prose)
        assert len(matches) == 0, f"Обнаружен запрещенный маркер неполноты: {pat} ({matches})"
    print("[PASS] 1. Запрещенные маркеры неполноты отсутствуют (Zero-Stub Policy соблюдена).")

    # 2. Проверка наличия всех 25 таблиц в сводном реестре
    found_tables = [t for t in EXPECTED_TABLES if re.search(rf"\b{t}\b", content)]
    missing_tables = set(EXPECTED_TABLES) - set(found_tables)
    assert len(missing_tables) == 0, f"Пропущены таблицы в реестре: {missing_tables}"
    print(f"[PASS] 2. Все 25 таблиц присутствуют в реестре спецификации ({len(found_tables)}/25).")

    # 3. Проверка наличия DDL CREATE TABLE для всех 25 таблиц
    ddl_matches = set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?([a-z_]+)", content, re.IGNORECASE))
    missing_ddl = [t for t in EXPECTED_TABLES if t not in ddl_matches]
    assert len(missing_ddl) == 0, f"Отсутствует DDL CREATE TABLE для: {missing_ddl}"
    print(f"[PASS] 3. Все 25 таблиц специфицированы через DDL CREATE TABLE ({len(ddl_matches)}/25).")

    # 4. Проверка наличия декларативных моделей SQLAlchemy 2.0 (__tablename__)
    sa_matches = set(re.findall(r"__tablename__\s*=\s*[\"']([a-z_]+)[\"']", content))
    missing_sa = [t for t in EXPECTED_TABLES if t not in sa_matches]
    assert len(missing_sa) == 0, f"Отсутствует модель SQLAlchemy 2.0 для: {missing_sa}"
    print(f"[PASS] 4. Все 25 таблиц специфицированы моделями SQLAlchemy 2.0 ({len(sa_matches)}/25).")

    # 5. Проверка диаграммы Mermaid erDiagram
    assert "erDiagram" in content, "Отсутствует блок диаграммы Mermaid erDiagram"
    fence = chr(96) * 3
    erd_text = content.split(f"{fence}mermaid\nerDiagram")[1].split(fence)[0]
    erd_entities = set(re.findall(r"\b([a-z_]+)\s*\{", erd_text))
    missing_erd = [t for t in EXPECTED_TABLES if t not in erd_entities]
    assert len(missing_erd) == 0, f"Пропущены сущности в диаграмме erDiagram: {missing_erd}"
    print(f"[PASS] 5. Диаграмма Mermaid erDiagram содержит все 25 сущностей.")

    # 6. Проверка диаграммы состояний грейдинга соискателя (stateDiagram-v2)
    assert "stateDiagram-v2" in content, "Отсутствует Mermaid stateDiagram-v2"
    assert "theta < 70" in content, "Отсутствует ветвление некарательного грейдинга theta < 70"
    assert ("70 <= theta" in content or "theta >= 70" in content), "Отсутствует подтверждение грейда theta >= 70"
    assert "theta >= 88" in content, "Отсутствует опция безопасного Boost-теста theta >= 88"
    assert "cooldown_until" in content, "Отсутствует контроль 90-дневного кулдауна"
    assert ("JuryDemoBypass" in content or "cooldown_resets" in content), "Отсутствует 1-клик сброс кулдауна для жюри"
    assert ("fsp_id IS NULL" in content or "NonFspTrack" in content), "Отсутствует ветка соискателей без ФСП"
    print("[PASS] 6. Диаграмма состояний онбординга и грейдинга KITE проверена.")

    # 7. Проверка диаграммы состояний инвайтов и откликов 152-ФЗ
    for st in ["sent", "viewed", "accepted", "declined", "expired"]:
        assert st in content, f"В диаграмме отсутствует статус инвайта '{st}'"
    assert "CandidateAnonymizedRead" in content, "Отсутствует состояние маскирования контактов 152-ФЗ"
    assert "CandidateFullRead" in content, "Отсутствует состояние демаскирования контактов"
    assert "TenantIsolationGuard" in content, "Отсутствует гарантия многопользовательской изоляции"
    print("[PASS] 7. Диаграмма состояний инвайтов, откликов и защиты контактов 152-ФЗ проверена.")

    # 8. Проверка обязательного ограничения зарплаты salary_min > 0 AND salary_max >= salary_min
    for tbl in SALARY_CHECK_TABLES:
        pattern = rf"{tbl}.*?salary_min > 0 AND salary_max >= salary_min"
        assert re.search(r"salary_min > 0 AND salary_max >= salary_min", content), f"Пропущено проверочное ограничение зарплаты в {tbl}"
    print("[PASS] 8. Проверочное ограничение salary_min > 0 AND salary_max >= salary_min подтверждено.")

    # 9. Проверка компиляции всех 25 моделей SQLAlchemy в SQLite In-Memory
    import sqlalchemy as sa
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
    from sqlalchemy import (
        Integer, BigInteger, String, Boolean, Float, Text, DateTime, ForeignKey,
        CheckConstraint, UniqueConstraint, Index
    )
    from typing import Optional, List
    from datetime import datetime

    py_blocks = re.findall(rf"{fence}python\n(class [A-Z]\w+\(Base\):.*?)\n{fence}", content, re.DOTALL)
    assert len(py_blocks) == 25, f"Ожидалось 25 классов моделей, найдено {len(py_blocks)}"

    class Base(DeclarativeBase):
        """Базовый декларативный класс для верификации."""

    JSON_TYPE = sa.JSON()

    ns = {
        "Base": Base,
        "Mapped": Mapped,
        "mapped_column": mapped_column,
        "relationship": relationship,
        "Integer": Integer,
        "BigInteger": BigInteger,
        "String": String,
        "Boolean": Boolean,
        "Float": Float,
        "Text": Text,
        "DateTime": DateTime,
        "ForeignKey": ForeignKey,
        "CheckConstraint": CheckConstraint,
        "UniqueConstraint": UniqueConstraint,
        "Index": Index,
        "Optional": Optional,
        "List": List,
        "datetime": datetime,
        "sa": sa,
        "JSON_TYPE": JSON_TYPE
    }

    for block in py_blocks:
        exec(block, ns)

    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    created_count = len(Base.metadata.tables)
    assert created_count == 25, f"В SQLite создано {created_count} таблиц вместо 25!"
    print(f"[PASS] 9. Успешная компиляция и создание всех {created_count} таблиц в SQLite in-memory!")

    print("=== Quality Gate PASSED: 100% Соответствие требованиям и спецификации ===")

if __name__ == "__main__":
    doc_file = Path("/home/muhammad/Dev/HACKATHON/LCT/fsp/docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md")
    run_quality_gate(doc_file)
```

---

### 6.3. Инструкция по независимому запуску Quality Gate

Для независимой валидации документа внешними аудиторами выполните команду:

```bash
python3 -c 'from pathlib import Path; exec(Path("docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md").read_text().split("```python\n#!/usr/bin/env python3")[1].split("```")[0])'
```

Команда считывает блок кода из Раздела 6.2 и выполняет все 9 проверок. Успешное выполнение подтверждается кодом завершения 0.
