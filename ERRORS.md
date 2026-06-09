# Ошибки, найденные в проекте

Дата проверки: 2026-06-09. Проверено: чтение всего кода, `ruff check`, `mypy`, реальный запуск приложения (TestClient), запуск alembic, валидация docker-compose, `pytest`.

---

## 🔴 Критические — функциональность сломана

### 1. ✅ ИСПРАВЛЕНО — Alembic полностью не работает: импорт несуществующей функции
**Файл:** `src/infrastructure/database/migrations/env.py:11`

```python
from infrastructure.database.factory import build_database_url
```

В `factory.py` нет модульной функции `build_database_url` — есть только **метод** `DatabaseFactory.build_database_url()`. Любая команда миграций (`make upgrade`, `make migration`, `make db-reset`) падает с `ImportError`. Подтверждено запуском:

```
ImportError: cannot import name 'build_database_url' from 'infrastructure.database.factory'
```

**Исправление (применено):** в `env.py` URL строится через `DatabaseFactory(app_config.database).build_database_url()`. Проверено: `alembic current` выполняется без ошибок.

### 2. ✅ ИСПРАВЛЕНО — `docker-compose.prod.yml` невалиден — прод-стек не поднимается
**Файл:** `docker-compose.prod.yml`, сервис `web`

```yaml
environment:
  ...
```

Литеральный placeholder `...` вместо реальных переменных. `docker compose config` падает:

```
services.web.environment must be a mapping
```

**Исправление (применено):** placeholder заменён на реальные переменные (`POSTGRES_HOST=postgres`, `APP_DEBUG=false`, креды БД через `${...}` с дефолтами), `depends_on` переведён на `condition: service_healthy`. Проверено: `docker compose config` валиден.

---

## 🟠 Серьёзные — баги логики

### 3. ✅ ИСПРАВЛЕНО — Кастомный обработчик ошибок не срабатывает для 404/405
**Файл:** `src/presenter/rest/errors/handlers.py:107`

Обработчик зарегистрирован на `fastapi.exceptions.HTTPException`, но ошибки роутинга (404 Not Found, 405 Method Not Allowed) Starlette кидает как `starlette.exceptions.HTTPException` — **родительский** класс, на который обработчик не распространяется. Проверено живым запросом:

```
GET /api/nonexistent → {"detail":"Not Found"}   # дефолтный формат, а не ErrorResponse
```

**Исправление (применено):** обработчик зарегистрирован на `StarletteHTTPException`, реэкспортируемый из `fastapi.exceptions` (без прямого импорта starlette). FastAPI-шный `HTTPException` — его подкласс и тоже ловится. Проверено: 404/405/403 возвращают единый формат `ErrorResponse`.

### 4. ✅ ИСПРАВЛЕНО — Dishka-контейнер никогда не закрывается → engine БД не освобождается
**Файл:** `src/presenter/rest/app_factory.py:54-59`

`make_async_container(...)` создаётся, но `container.close()` нигде не вызывается (нет lifespan/shutdown-хука). Поэтому финализатор APP-scope провайдера `get_factory` (`src/infrastructure/database/di.py:21-24` — код после `yield`, вызывающий `factory.dispose()`) **никогда не выполняется**: соединения пула не закрываются корректно при остановке.

**Исправление (применено):** в `app_factory.py` добавлен lifespan, вызывающий `await app.state.dishka_container.close()` на shutdown; он передан в `FastAPI(lifespan=...)`. Проверено: при остановке приложения в логах появляется "Disposing database engine".

### 5. UoW закрывает чужую сессию
**Файл:** `src/infrastructure/database/uow.py:25-27`

```python
async def close_transaction(self) -> None:
    if self.session.is_active:
        await self.session.close()
```

Метод называется `close_transaction`, но закрывает **сессию**, которой владеет DI-провайдер (`async with session_factory() as session` в `di.py:36`). После первого выхода из UoW сессия мертва — любой другой репозиторий в рамках того же запроса получит закрытую сессию. Нарушено владение ресурсом: закрывать сессию должен тот, кто её создал (DI), а UoW — только транзакцию (`self.transaction.close()` / `rollback`).

### 6. `AbstractUow.__aexit__`: commit/rollback молча пропускаются
**Файл:** `src/domain/uow.py:16-29`

Если `create_transaction` не создал транзакцию (например, сессия уже была в транзакции — условие в `SqlalchemyUow.create_transaction`), то `self.transaction` остаётся `None`, и при выходе из контекста **ни commit, ни rollback не вызываются** — даже при исключении. При этом `close_transaction` всё равно закроет сессию.

### 7. Неверная аннотация возврата у healthcheck-эндпоинта
**Файл:** `src/presenter/rest/api/healcheck/check.py:14-19`

Функция аннотирована `-> HealthCheckOutputDto`, а возвращает `Response[HealthCheckOutputDto]`. Ошибка mypy:

```
error: Incompatible return value type (got "Response[HealthCheckOutputDto]", expected "HealthCheckOutputDto")  [return-value]
```

Работает только потому, что задан `response_model=`. Исправить аннотацию на `Response[HealthCheckOutputDto]`.

---

## 🟡 Опечатки и нейминг

### 8. Слово «healthcheck» написано тремя разными способами
- `healtcheck` (пропущена `h`): `src/domain/repository/healtcheck.py`, `src/infrastructure/database/repository/healtcheck.py`, `src/common/output/healtcheck/`
- `healcheck` (пропущены `t` и `h`): `src/presenter/rest/api/healcheck/`
- `healthcheck` (правильно): `src/common/use_case/query/healthcheck/`

Это пути модулей — переименование затронет импорты в ~8 файлах.

---

## 🟡 Линтеры — `make check` падает

### 9. Ruff: 14 ошибок (все автофиксятся `make lint-fix`)
- **F401** неиспользуемые импорты: `types.TracebackType` и `typing.Protocol` в `src/infrastructure/database/uow.py:1-2`
- **I001** неотсортированные импорты: `src/config.py`, `src/domain/repository/healtcheck.py`, `src/domain/uow.py`, `src/infrastructure/database/uow.py`, `src/presenter/rest/api/healcheck/check.py`, `src/presenter/rest/api/router.py`, `src/presenter/rest/app_factory.py`, `src/presenter/rest/errors/handlers.py`, `src/presenter/rest/errors/models.py`
- **W291** хвостовой пробел: `src/presenter/rest/api/router.py:4`
- **W292/W293** нет перевода строки в конце файла + пробелы в пустой строке: `src/presenter/rest/api/healcheck/check.py:20`

### 10. Mypy: 2 ошибки
Описаны выше — пункты 1 (`env.py`) и 7 (аннотация эндпоинта). `make typecheck` (и CI `lint-ci`) падает.

---

## ⚪ Прочее / замечания

### 11. Тестов нет совсем
В `tests/` только пустые `__init__.py`. `pytest` → "no tests ran". CI-цель `test-ci` маскирует это (exit-код 5 трактуется как успех).

### 12. Мёртвый/пустой код
- `src/infrastructure/database/table.py` — пустой файл;
- `src/infrastructure/auth/di.py` — пустой файл; `AuthConfig` определён и включён в `Config`, но нигде не используется (auth-провайдера нет).

### 13. Хрупкий запуск alembic
`alembic.ini` содержит `prepend_sys_path = .` — при запуске alembic из каталога `src/infrastructure/database` локальный `config.py` (DatabaseConfig) шадовит корневой модуль `config`, и env.py падает с `ImportError: cannot import name 'config'`. Работает только через `make` из корня репозитория.

### 14. CORS по умолчанию `allow_origins=["*"]`
`src/presenter/rest/middleware.py:14` — для прода небезопасно; origins стоит брать из конфига.

### 15. Захардкоженные параметры пула БД
`src/infrastructure/database/factory.py:40-57` — `pool_size=10`, `max_overflow=20`, таймауты и `application_name="project"` зашиты в код, в `DatabaseConfig` их нет.

### 16. `BaseRepository.__slots__ = "_session"`
`src/infrastructure/database/repository/base.py:5` — строка вместо кортежа. Работает (одиночное имя допустимо), но конвенция — `__slots__ = ("_session",)`.

### 17. Странный дефолт статуса ответа
`src/presenter/rest/api/response.py:6` — `status: str = "data"`. Похоже, имелось в виду `"ok"`/`"success"`; "data" как значение статуса выглядит как ошибка копипасты (в `ErrorResponse` аналогичное поле — `"error"`).
