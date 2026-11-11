# Мониторинг популяции диких животных

## 1. Название проекта

**Wildlife Monitoring DB** — база данных для мониторинга популяции диких животных.

## 2. Краткое описание идеи проекта

Приложение предназначено для сбора, хранения и анализа данных о популяции диких животных в разных природных зонах. Оно позволяет фиксировать наблюдения за животными, учитывать места обитания и отслеживать изменения численности популяций во времени. Система будет полезна для исследователей и сотрудников природоохранных организаций, которым важно получать структурированные и актуальные данные.

## 3. Краткое описание предметной области

Предметная область — экологический мониторинг и учет популяции диких животных. Основные сущности предметной области: Животные или виды животных (Animals / Species), Наблюдения (Observations), Локации наблюдения (Locations), Исследователи (Researchers), а также Учеты численности (PopulationRecords). Система позволяет сохранять сведения о том, какие животные были замечены, где и когда это произошло, кем было выполнено наблюдение, а также анализировать динамику популяции по территориям и временным периодам.

## 4. Краткий анализ аналогичных решений


| Критерий                                 | Wildlife Insights                               | SMART Conservation Software                                    | Самописные таблицы / Excel                                      |
| ---------------------------------------- | ----------------------------------------------- | -------------------------------------------------------------- | --------------------------------------------------------------- |
| Структурированность и целостность данных | Высокая, данные организованы в рамках платформы | Высокая, поддерживается формализованная структура              | Низкая, высок риск дублей, пропусков и несогласованности данных |
| Гибкость настройки под локальные задачи  | Ограничена возможностями платформы              | Средняя, настройка возможна, но зависит от архитектуры системы | Формально высокая, но без контроля связей и ограничений         |
| Удобство анализа динамики популяции      | Высокое, доступны исследовательские инструменты | Высокое, возможно формирование отчетности и аналитики          | Низкое, анализ требует ручной обработки                         |
| Контроль качества вводимых данных        | Высокий, за счет правил платформы               | Высокий, благодаря централизованному управлению                | Низкий, ошибки ввода сложно предотвращать                       |




## 5. Краткое обоснование целесообразности и актуальности проекта

Мониторинг диких животных важен для оценки состояния экосистем, выявления угроз для отдельных видов и планирования природоохранных мероприятий. На практике данные часто собираются разрозненно, что затрудняет их анализ, сопоставление и долгосрочное хранение. Разработка специализированной базы данных позволит централизовать информацию о наблюдениях и популяциях, упростить работу исследователей и повысить качество экологического учета.

## 6. Краткое описание акторов (ролей)

- **Исследователь** – пользователь, который фиксирует наблюдения за животными, вносит информацию о месте, времени и результатах учета. Может просматривать историю собственных наблюдений и аналитические данные.
- **Администратор** – пользователь, который управляет справочниками видов и локаций, контролирует корректность данных, а также имеет доступ ко всем наблюдениям и отчетам в системе.



## 7. Use-Case диаграмма

![](./diagrams/use-case.svg)

## 8. ER-диаграмма сущностей

![](./diagrams/er.svg)

## 9. Пользовательские сценарии



### Сценарий 1 (актор: Исследователь)

1. Исследователь авторизуется в системе.
2. Переходит в раздел добавления нового наблюдения.
3. Выбирает вид животного, указывает локацию и дату наблюдения.
4. Вводит количество замеченных особей и дополнительные заметки.
5. Система сохраняет наблюдение в базе данных.



### Сценарий 2 (актор: Исследователь)

1. Исследователь открывает раздел статистики.
2. Выбирает интересующий вид животного.
3. Указывает временной диапазон и территорию наблюдения.
4. Система формирует выборку по сохраненным наблюдениям.
5. Исследователь получает данные о динамике численности популяции.



### Сценарий 3 (актор: Администратор)

1. Администратор авторизуется в системе.
2. Переходит в раздел управления справочником видов.
3. Добавляет новый вид животного или редактирует существующую запись.
4. При необходимости корректирует список локаций наблюдения.
5. Система обновляет справочные данные, которые затем доступны исследователям.



## 10. Формализация ключевых бизнес-процессов



### 10.1 Управление справочником видов

![](./diagrams/1.svg)

### 10.2 Фиксация учетных данных о популяции

![](./diagrams/2.svg)

### 10.3 Анализ динамики популяции

![](./diagrams/3.svg)

---



# Лабораторная работа №2 — UML и C4



## 11. Тип приложения и технологический стек


| Параметр                        | Выбор                                                                    |
| ------------------------------- | ------------------------------------------------------------------------ |
| Тип с точки зрения пользователя | **Web MPA** — многостраничное веб-приложение (формы и отчёты в браузере) |
| Язык                            | **Python 3.12**                                                          |
| UI (план)                       | **Flask** + **Jinja2** (MVC)                                             |
| Доступ к данным (план)          | **SQLAlchemy**, паттерн **Repository**                                   |
| СУБД                            | **PostgreSQL**                                                           |
| Принципы                        | Слои UI / сервисы / данные; **DIP** — сервисы зависят от `IRepository`   |


Уровень L4 на лаб. №2 раскрыт **диаграммами UML** (п. 15), без реализации слоя данных и UI.

Схема БД: [database/schema.dbml](./database/schema.dbml).

## 12. C4 — уровень L1 (контекст)

![C4 L1](./diagrams/lab2/svg/L1-context.svg)

Исходник: [diagrams/lab2/c4/L1-context.puml](./diagrams/lab2/c4/L1-context.puml)

## 13. C4 — уровень L2 (контейнеры)

Для веб-приложения выделены три контейнера: **Web UI**, **Backend API**, **PostgreSQL**.

![C4 L2](./diagrams/lab2/svg/L2-container.svg)

Исходник: [diagrams/lab2/c4/L2-container.puml](./diagrams/lab2/c4/L2-container.puml)

## 14. C4 — уровень L3 (компоненты)

Внутри Backend API: контроллеры (UI-слой API), сервисы (бизнес-логика), репозитории (доступ к данным). Web UI обращается только к API, не к БД напрямую.

![C4 L3](./diagrams/lab2/svg/L3-component.svg)

Исходник: [diagrams/lab2/c4/L3-component.puml](./diagrams/lab2/c4/L3-component.puml)

## 15. C4 — уровень L4 (UML диаграммы классов)



### 15.1 Компонент доступа к данным

ORM-модели, доменные сущности, интерфейс `IRepository` и `PostgresRepository`.

![Классы: слой данных](./diagrams/lab2/svg/class-data-layer.svg)

Исходник: [diagrams/lab2/uml/class-data-layer.puml](./diagrams/lab2/uml/class-data-layer.puml)

### 15.2 Компонент бизнес-логики

Сервисы работают с DTO и доменными объектами; зависят от абстракции `IRepository` (DIP). Черновик на момент лаб. №2:

![](./diagrams/lab2/svg/class-business-layer.svg)

Исходник: [diagrams/lab2/uml/class-business-layer.puml](./diagrams/lab2/uml/class-business-layer.puml)

## 16. UML — диаграммы последовательностей (по BPMN из п. 10)


| BPMN (п. 10)                   | Диаграмма последовательности                                                     |
| ------------------------------ | -------------------------------------------------------------------------------- |
| 10.1 Добавление наблюдения     | [seq-add-observation.puml](./diagrams/lab2/uml/seq-add-observation.puml)         |
| 10.2 Анализ динамики популяции | [seq-population-analysis.puml](./diagrams/lab2/uml/seq-population-analysis.puml) |
| 10.3 Управление справочниками  | [seq-catalog-manage.puml](./diagrams/lab2/uml/seq-catalog-manage.puml)           |


![Sequence: добавление наблюдения](./diagrams/lab2/svg/seq-add-observation.svg)

![Sequence: анализ популяции](./diagrams/lab2/svg/seq-population-analysis.svg)

![Sequence: справочники](./diagrams/lab2/svg/seq-catalog-manage.svg)

## 17. Схема базы данных (DBML, PostgreSQL)

Исходник: [database/schema.dbml](./database/schema.dbml)

Таблицы: `species`, `locations`, `researchers`, `observations`, `population_records` (связи — как в ER, п. 8). Уникальный ключ учёта численности: вид + локация + дата.

---



# Лабораторная работа №3 — бизнес-логика и тесты



## 18. Компонент бизнес-логики (реализация)

Код только для слоя бизнес-логики — каталог `[src/business/](src/business/)`:


| Модуль                   | Публичный API                                             |
| ------------------------ | --------------------------------------------------------- |
| `observation_service.py` | `create_observation(request)`                             |
| `analytics_service.py`   | `analyze_population(request)`                             |
| `catalog_service.py`     | `add_species(request)`                                    |
| `exceptions.py`          | `ValidationError`, `DuplicateSpeciesError`, `NoDataError` |


Вспомогательно для сервисов: `[src/entities.py](src/entities.py)`, `[src/dto.py](src/dto.py)`, интерфейс `[IRepository](src/repository.py)` (реализация — лаб. №4).

Сервисы зависят от `IRepository` (DIP). Правила по BPMN из п. 10.

Запуск тестов (классические + лондонские, без реальной БД):

```bash
pip install -r requirements.txt
py -m pytest
```

Локальный HTML-отчёт покрытия: `htmlcov/index.html`.

Отчёт Allure (шаги, эпики, классическая и лондонская школы):

```powershell
.\scripts\allure-report.bat
```

`py -m pytest` сам пишет сырые результаты в `allure-results/`. Скрипт собирает HTML в `allure-report/` и открывает его. Для HTML нужны Java 17+ и Allure CLI: если CLI нет в PATH, скрипт скачивает Allure 2.46.1 в `tools/`.

UI SonarQube (Coverage на дашборде проекта):

```powershell
.\scripts\sonar-coverage.bat
```

Если PowerShell ругается на execution policy, то же самое так:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sonar-coverage.ps1
```

После загрузки: http://localhost:9000/dashboard?id=wildlife-monitoring



## 19. C4 L4 — обновлённая диаграмма бизнес-логики (лаб. №3)

![](./diagrams/lab3/svg/class-business-layer.svg)

Исходник: [diagrams/lab3/uml/class-business-layer.puml](./diagrams/lab3/uml/class-business-layer.puml)

Пересборка SVG: `.\diagrams\render-lab3.ps1`

---



# Лабораторная работа №4 — доступ к данным



## 20. Компонент доступа к данным (реализация)

Код слоя данных — каталог `[src/repositories/](src/repositories/)`:


| Модуль                 | Назначение                                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `sqlite_repository.py` | `SqliteRepository` — SQL без ORM, файл SQLite                                                                       |
| `schema.py`            | DDL таблиц по [database/schema.dbml](database/schema.dbml)                                                          |
| `exceptions.py`        | `DataAccessError`, `DataValidationError`, `EntityNotFoundError`, `DuplicateEntityError`, `IntegrityConstraintError` |


Контракт задаёт бизнес-логика: `[IRepository](src/repository.py)` и доменные сущности `[src/entities.py](src/entities.py)`. Репозиторий **реализует** этот интерфейс (DIP): слой данных зависит от бизнес-слоя, а не наоборот. Конкретная СУБД за интерфейсом не видна — `SqliteRepository` можно заменить другой реализацией.

CRUD видов: `save_species`, `get_species`, `update_species`, `delete_species`. Также реализованы `add_observation`, `find_population_records`, `species_exists`.

Запуск тестов:

```bash
pip install -r requirements.txt
py -m pytest
```



## 21. C4 L4 — обновлённая диаграмма доступа к данным (лаб. №4)

![](./diagrams/lab4/svg/class-data-layer.svg)

Исходник: [diagrams/lab4/uml/class-data-layer.puml](diagrams/lab4/uml/class-data-layer.puml)

Пересборка SVG: `.\diagrams\render-lab4.ps1`

---



# Лабораторная работа №5 — технологический UI



## 22. Технологический UI (реализация)

Консоль в `[src/wildlife_ui/](src/wildlife_ui/)` вызывает **те же сервисы**, что будет использовать будущий GUI (`ObservationService`, `CatalogService`, `AnalyticsService`). До SQLite UI не обращается: конкретный репозиторий собирается только в `[src/wildlife_app/main.py](src/wildlife_app/main.py)`.


| Модуль                       | Назначение                                          |
| ---------------------------- | --------------------------------------------------- |
| `wildlife_ui/console_app.py` | Меню ролей и сценарии из ТЗ                         |
| `wildlife_ui/io.py`          | `IUserIO` / `ConsoleIO` — ввод-вывод за интерфейсом |
| `wildlife_app/main.py`       | Composition root: SQLite + сервисы + консоль        |


Покрытие use case: выбор роли (авторизация-заглушка), добавить/смотреть наблюдения, аналитика популяции, справочник видов (добавить/изменить), локации, исследователи. Ошибки валидации показываются на экране.

Запуск:

```bash
py -m wildlife_app
```

Файл БД по умолчанию: `wildlife.db` (можно передать путь первым аргументом).

Классические тесты длинного сценария:

```bash
py -m pytest -m classical
```



## 23. C4 L2 и L3 (обновление, лаб. №5)

Вместо запланированного Web UI на этом этапе — консольный технологический UI.

![C4 L2](./diagrams/lab5/svg/L2-container.svg)

Исходник: [diagrams/lab5/c4/L2-container.puml](diagrams/lab5/c4/L2-container.puml)

![C4 L3](./diagrams/lab5/svg/L3-component.svg)

Исходник: [diagrams/lab5/c4/L3-component.puml](diagrams/lab5/c4/L3-component.puml)

## 24. C4 L4 — диаграмма технологического UI

![](./diagrams/lab5/svg/class-ui-layer.svg)

Исходник: [diagrams/lab5/uml/class-ui-layer.puml](diagrams/lab5/uml/class-ui-layer.puml)

Пересборка SVG: `.\diagrams\render-lab5.ps1`

---



# Лабораторная работа №6 — сборка, логирование, конфигурирование



## 25. Сборка компонентов

Каждый компонент — отдельная единица развёртывания:


| Сборка              | Исходники                                          | Назначение                                         |
| ------------------- | -------------------------------------------------- | -------------------------------------------------- |
| `wildlife-business` | `[src/wildlife_business/](src/wildlife_business/)` | Сервисы, `IRepository`, сущности, DTO              |
| `wildlife-data`     | `[src/wildlife_data/](src/wildlife_data/)`         | `SqliteRepository`, SQL без ORM                    |
| `wildlife-ui`       | `[src/wildlife_ui/](src/wildlife_ui/)`             | Технологический UI                                 |
| `wildlife-app`      | `[src/wildlife_app/](src/wildlife_app/)`           | Связывает три компонента, читает конфиг, пишет лог |


Описания сборок: `[components/](components/)`. Готовые файлы: `[assembled/](assembled/)`.

Собрать заново:

```bash
.\scripts\build_components.ps1
```



## 26. Конфигурация и логирование

Файл `[config.ini](config.ini)`:

- `database.connection_string` — строка подключения к SQLite
- `business.min_records_for_trend` — порог записей для тренда (бизнес-логика)
- `logging.level` / `logging.file` — уровень и файл лога

В лог пишутся действия пользователя (INFO) и все исключения (WARNING/ERROR с трассировкой): `logs/app.log`.

## 27. Запуск не из IDE

Двойной щелчок или из проводника/терминала:

```text
run.bat
```

Либо из папки собранных компонентов (ставится venv и колёса):

```text
assembled\run.bat
```



## 28. C4 L1–L4 (уточнение на всё приложение)

![C4 L1](./diagrams/lab6/svg/L1-context.svg)

![C4 L2](./diagrams/lab6/svg/L2-container.svg)

![C4 L3](./diagrams/lab6/svg/L3-component.svg)

![](./diagrams/lab6/svg/class-application.svg)

Исходники: [diagrams/lab6/c4/](diagrams/lab6/c4/), [diagrams/lab6/uml/class-application.puml](diagrams/lab6/uml/class-application.puml).

Пересборка: `.\diagrams\render-lab6.ps1`

## 29. Собранные компоненты (файлы сборок)

![Каталог assembled](./diagrams/lab6/assembled-components.png)

Папка: `[assembled/](assembled/)` — `.whl` компонентов, `config.ini`, `run.bat`.

---



# Лабораторная работа №7 — графический UI (MVC)



## 30. Компонент графического интерфейса

GUI — каталог `[src/wildlife_gui/](src/wildlife_gui/)`, сборка `wildlife-gui`. Паттерн **MVC**:


| Слой             | Код                                                              | Назначение                                            |
| ---------------- | ---------------------------------------------------------------- | ----------------------------------------------------- |
| Model            | сервисы `wildlife_business` и DTO                                | Те же сценарии, что и у консоли                       |
| Controller       | `[controllers.py](src/wildlife_gui/controllers.py)`              | Роли, viewmodel, обработка ошибок домена              |
| View             | шаблоны Jinja2 и `[flask_app.py](src/wildlife_gui/flask_app.py)` | HTTP: маршруты Flask, сессия роли, отрисовка          |
| Связь с бизнесом | `[forms.py](src/wildlife_gui/forms.py)`                          | Формы GUI → DTO; GUI не зависит от `SqliteRepository` |


Экраны разнесены: выбор роли; у исследователя — список наблюдений, добавление, аналитика; у администратора — виды, локации, исследователи. Текущие роль и раздел всегда видны в шапке, результат операции — сообщением на экране.

Технологический UI сохранён: `py -m wildlife_app` или `--ui console`. Графический UI:

```bash
py -m wildlife_app --ui gui
```

Либо `run-gui.bat`. Адрес по умолчанию: http://127.0.0.1:5000 (секция `[gui]` в `[config.ini](config.ini)`).

Пересборка колёс: `.\scripts\build_components.ps1` — в `[assembled/](assembled/)` появляется `wildlife_gui-*.whl`. Запуск GUI из сборок: `assembled\run-gui.bat`.

Лондонские тесты взаимодействий:

```bash
py -m pytest -m london
```

## 31. C4 L1–L3 (обновление) и L4 GUI

![C4 L1](./diagrams/lab7/svg/L1-context.svg)

![C4 L2](./diagrams/lab7/svg/L2-container.svg)

![C4 L3](./diagrams/lab7/svg/L3-component.svg)

## 32. C4 L4 — диаграмма компонента GUI

![](./diagrams/lab7/svg/class-gui-layer.svg)

Исходники: [diagrams/lab7/c4/](diagrams/lab7/c4/), [diagrams/lab7/uml/class-gui-layer.puml](diagrams/lab7/uml/class-gui-layer.puml).

Пересборка: `.\diagrams\render-lab7.ps1`

---

# ТИОПО — Лабораторная работа №2: integration, E2E, CI/CD

## 33. Структура тестов и порядок этапов

| Этап | Каталог | Суффикс файлов | Что проверяет |
| --- | --- | --- | --- |
| 1. Unit | `tests/unit/` | `test_*.py` | тесты ЛР1 (классическая и лондонская школы) |
| 2. Integration | `tests/integration/` | `*_it.py` (Integration Test) | `CatalogService`/`ObservationService`/`AnalyticsService` + `SqliteRepository` на отдельном файловом инстансе SQLite |
| 3. E2E | `tests/e2e/` | `*_e2e.py` | демонстрационный сценарий MVP через HTTP API стенда в Docker (без GUI) |

Один файл — один тест; arrange в начале, затем шаги `act` / `assert` (шаги Allure).
Каждый тест получает метку этапа (`parentSuite` в Allure, маркер pytest `unit|integration|e2e`).

## 34. Тестовое хранилище

Отдельный инстанс поднимается последовательным запуском скриптов [db/sql](db/sql):

1. `01_schema.sql` — генерация таблиц;
2. `02_seed.sql` — тестовые данные (явные id, одинаковые при каждом запуске);
3. `90_rollback.sql` + `02_seed.sql` — откат к состоянию до прогона (одной транзакцией).

Управление — [db/dbctl.py](db/dbctl.py): `init | rollback | verify | fingerprint`.
`verify` проверяет `PRAGMA integrity_check`, `foreign_key_check` и совпадение отпечатка данных с эталоном,
построенным теми же скриптами.

* **integration**: на прогон создаётся уникальный файл в tmp; после **каждого** теста (в т.ч. упавшего) —
  принудительный `rollback` + `verify`. С `WILDLIFE_IT_DB=<путь>` используется постоянный инстанс:
  перед стартом он обязан быть эталонным.
* **e2e**: стенд (`docker/app.Dockerfile`) при старте делает `init`/`verify` хранилища в томе `/data`;
  после E2E (успешного или нет) `ci/stand.sh cleanup` завершает все сессии, откатывает и проверяет хранилище.

Брокера сообщений в проекте нет. Активные сессии есть у HTTP API (`SessionRegistry`): E2E закрывает
свои сессии и проверяет, что токены больше не действуют; `cleanup` стенда завершает все сессии (`DELETE /api/v1/sessions`).

## 35. Docker и стенд

* [docker/tests.Dockerfile](docker/tests.Dockerfile) — контейнер запуска тестов: **выкачивает репозиторий**
  (`REPO_URL`, `GIT_REF`), ставит зависимости, точка входа [ci/run-tests.sh](ci/run-tests.sh) `<этап>`.
* [docker/app.Dockerfile](docker/app.Dockerfile) — тестируемая система (Flask GUI + JSON API `/api/v1`).
* [docker-compose.test.yml](docker-compose.test.yml) — стенд, контейнер тестов, `tcpdump` и `curl`-имитация.
* [ci/stand.sh](ci/stand.sh) — `up | e2e | cleanup | replay | down | all`.

Локально (Git Bash + Docker Desktop), полный аналог CI:

```bash
bash ci/local-pipeline.sh
```

Без Docker — unit + integration:

```bash
py -m pytest
```

**Параллельные разработчики.** Integration-хранилище — свой файл на каждый запуск. Стенд — свой
compose-проект (`STAND` с именем пользователя, временем и случайным числом): своя сеть, том и
контейнеры, порт хоста выбирается случайно. E2E-данные помечаются уникальным `run_tag`, поэтому даже
на общем стенде прогоны не пересекаются.

**Повторный запуск.** `ci/run-tests.sh integration` после основного прогона ещё дважды запускает
integration-тесты на одном постоянном инстансе и сравнивает результаты (JUnit XML).

## 36. CI/CD (GitHub Actions) и отчёт Allure

Пайплайн [.github/workflows/tests.yml](.github/workflows/tests.yml):

```
unit ──► integration ──► e2e
  └──────────┴────────────┴──► report (if: always())
```

* каждый этап — отдельный job в тестовом контейнере, следующий стартует только после успеха предыдущего (`needs`);
* `report` выполняется всегда: этапы без результатов прогоняются с `WILDLIFE_STAGE_SKIPPED` и попадают в
  отчёт как **skipped** (категория «Этап не запускался»);
* история (`history/`) берётся из ветки `gh-pages` → в отчёте есть **тренды** между запусками;
* отчёт публикуется в ветку **`gh-pages`**: `index.html` (GitHub Pages) и `allure-report.html` —
  один самодостаточный файл, который открывается без Allure и без сервера; он же лежит в артефакте `allure-report`.

Однократная настройка репозитория на GitHub: сделать репозиторий публичным,
**Settings → Pages → Deploy from a branch → `gh-pages` / root**. Отчёт:
`https://<owner>.github.io/<repo>/`.

## 37. Имитация E2E запросами и захват трафика

* [e2e/curl/replay.sh](e2e/curl/replay.sh) — тот же сценарий через `curl`;
* [e2e/postman/wildlife-e2e.postman_collection.json](e2e/postman/wildlife-e2e.postman_collection.json) — коллекция Postman (Run collection, `baseUrl` = адрес стенда).

В CI шаг «Имитация E2E через curl + захват трафика» запускает `tcpdump` в сетевом namespace
контейнера приложения и `curl`-сценарий; `curl-replay.pcap` (открывается в Wireshark, фильтр `http`)
и `curl-replay.log` — в артефакте `traffic`. Локально: `ci/stand.sh up`, затем `STAND=<имя> bash ci/stand.sh replay`,
либо Postman + Wireshark на loopback с фильтром `tcp.port == <порт стенда>`.
