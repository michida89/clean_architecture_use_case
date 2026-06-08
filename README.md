# · backend

Асинхронный REST-бэкенд на **FastAPI** с чистой (clean-ish) архитектурой:
слои изолированы, домен ничего не знает о фреймворках, зависимости собираются
через DI-контейнер, транзакции БД живут в Unit of Work.

| | |
|---|---|
| Язык | Python 3.12 |
| Web | FastAPI + Uvicorn (запускается как сервис `aiomisc`) |
| БД | PostgreSQL + SQLAlchemy 2.0 (async, `asyncpg`) |
| Миграции | Alembic |
| DI | [dishka](https://github.com/reagento/dishka) |
| Хранилище файлов | MinIO (S3-совместимое) |
| Менеджер пакетов | [uv](https://docs.astral.sh/uv/) |
| Качество | ruff (lint + format), mypy, pytest |

---

## Содержание

1. [Архитектура](#архитектура)
2. [Как начать](#как-начать)
3. [Как писать код](#как-писать-код)
4. [Гайд по Makefile](#гайд-по-makefile)
5. [Конфигурация (.env)](#конфигурация-env)

---

## Архитектура

### Идея в одном абзаце

Код разбит на слои. **Стрелки зависимостей всегда направлены внутрь, к домену.**
Внешние слои (presenter, infrastructure) знают про внутренние (domain), но не
наоборот. Домен оперирует только абстракциями (`Protocol`-интерфейсами), а их
конкретные реализации подставляет DI-контейнер в точке сборки. Благодаря этому
бизнес-логику можно тестировать без БД и без HTTP, а инфраструктуру —
менять, не трогая логику.

### Слои

```
HTTP-запрос
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  presenter/        — «как с нами говорят снаружи»            │
│  REST: роутеры, эндпоинты, middleware, обработчики ошибок,   │
│  фабрика приложения (app_factory)                           │
└─────────────────────────────────────────────────────────────┘
    │ вызывает use-case
    ▼
┌─────────────────────────────────────────────────────────────┐
│  common/           — «что приложение умеет делать»          │
│  use-case'ы (Query / Command), их DTO (input/output),       │
│  общая конфигурация приложения                              │
└─────────────────────────────────────────────────────────────┘
    │ зависит от абстракций
    ▼
┌─────────────────────────────────────────────────────────────┐
│  domain/           — ядро, без фреймворков                  │
│  интерфейсы репозиториев (Protocol), AbstractUow,           │
│  ошибки/исключения, мелкие сервисы (чтение env, sentinel)   │
└─────────────────────────────────────────────────────────────┘
    ▲ реализуется снаружи
    │
┌─────────────────────────────────────────────────────────────┐
│  infrastructure/   — «грязные» детали: БД, auth, S3         │
│  SQLAlchemy-репозитории, фабрика движка/сессий, UoW,        │
│  ORM-модели, миграции Alembic, DI-провайдеры (dishka)       │
└─────────────────────────────────────────────────────────────┘
```

И две точки сборки наверху:

- **`src/config.py`** — composition root конфигурации. Собирает воедино
  `ApplicationConfig`, `DatabaseConfig`, `AuthConfig` в один объект `config`.
- **`src/__main__.py`** — точка входа. Создаёт `ApplicationFactory` и запускает
  её как сервис `aiomisc` (`python -m src`).

### Дерево каталогов

```
src/
├── __main__.py                  # точка входа: python -m src
├── config.py                    # composition root: общий объект config
│
├── domain/                      # ❶ ЯДРО — без зависимостей от фреймворков
│   ├── errors/                  #    коды ошибок, AppException, ErrorResponse-модели
│   ├── repository/              #    интерфейсы репозиториев (Protocol)
│   ├── uow.py                   #    AbstractUow — контракт Unit of Work
│   ├── interface/               #    прочие доменные интерфейсы
│   └── services/                #    env-ридеры, sentinel (мелкие утилиты)
│
├── common/                      # ❷ ПРИКЛАДНОЙ СЛОЙ — что мы умеем делать
│   ├── config.py                #    ApplicationConfig (host/port/title/debug…)
│   ├── use_case/
│   │   ├── base.py              #    IUseCase / IQuery / ICommand (Protocol)
│   │   ├── query/               #    read-сценарии (HealthCheckQuery, …)
│   │   └── command/             #    write-сценарии
│   ├── input/                   #    входные DTO
│   └── output/                  #    выходные DTO (HealthCheckOutputDto, …)
│
├── infrastructure/              # ❸ ИНФРАСТРУКТУРА — детали реализации
│   ├── database/
│   │   ├── config.py            #    DatabaseConfig (POSTGRES_*)
│   │   ├── factory.py           #    DatabaseFactory: engine + session factory
│   │   ├── uow.py               #    SqlalchemyUow — реализация AbstractUow
│   │   ├── base.py              #    BaseORModel + миксины (created_at, soft-delete)
│   │   ├── naming.py            #    имя класса → имя таблицы
│   │   ├── repository/          #    реализации репозиториев (SQLAlchemy)
│   │   ├── di.py                #    DatabaseProvider — провайдеры dishka
│   │   ├── alembic.ini
│   │   └── migrations/          #    окружение и версии Alembic
│   └── auth/                    #    JWT-конфиг и DI
│
└── presenter/                   # ❹ ВХОД СНАРУЖИ — REST
    └── rest/
        ├── app_factory.py       #    ApplicationFactory: собирает FastAPI
        ├── middleware.py        #    CORS и пр.
        └── api/
            ├── router.py        #    корневой /api роутер
            ├── healcheck/       #    эндпоинт /api/healthcheck
            └── v1/              #    версионированные эндпоинты /api/v1/...
```

### Правило зависимостей

```
presenter ──▶ common ──▶ domain ◀── infrastructure
                            ▲                │
                            └─ реализует ─────┘
```

- **domain** не импортирует ничего из `common`, `infrastructure`, `presenter` и
  никаких веб-фреймворков. Только stdlib и абстракции.
- **infrastructure** реализует интерфейсы из `domain`
  (`HealthCheckRepository` реализует `IHealthCheckRepository`,
  `SqlalchemyUow` реализует `AbstractUow`).
- **common** (use-case'ы) зависит только от абстракций domain, не от их
  конкретных реализаций.
- **presenter** дёргает use-case'ы; конкретные зависимости в них подставляет DI.

Если потянуло написать `from presenter...` внутри `infrastructure` или
`import sqlalchemy` внутри `domain` — это сигнал, что стрелка зависимости
развернулась не туда.

### Как путешествует запрос

На примере живого эндпоинта `GET /api/healthcheck`:

```
1. presenter/rest/api/healcheck/check.py
   эндпоинт health_check() получает HealthCheckQuery через FromDishka

2. common/use_case/query/healthcheck/check.py
   HealthCheckQuery.execute() открывает UoW и зовёт репозиторий

3. domain/repository/healtcheck.py
   IHealthCheckRepository — интерфейс (Protocol), .check() -> bool

4. infrastructure/database/repository/healtcheck.py
   HealthCheckRepository выполняет SELECT 1 через AsyncSession

5. ответ заворачивается в common/output/.../HealthCheckOutputDto
```

Эндпоинт ничего не знает о SQLAlchemy — он работает с типом `HealthCheckQuery`,
а DI-контейнер решает, какие сессию, UoW и репозиторий в него передать.

### Unit of Work и транзакции

`AbstractUow` (`domain/uow.py`) — асинхронный контекст-менеджер. Открытие
блока `async with uow:` начинает транзакцию, выход — коммитит её (или
откатывает, если внутри было исключение) и закрывает сессию. Use-case'ы
оборачивают свою работу в UoW и не думают про `commit()/rollback()` вручную:

```python
async def execute(self, *, input_dto: None) -> bool:
    async with self._uow:
        return await self._repository.check()
```

### Dependency Injection (dishka)

Сборка зависимостей описана провайдерами. Пример — `DatabaseProvider`
(`infrastructure/database/di.py`) с областями жизни (scopes):

| Scope | Что живёт | Пример |
|-------|-----------|--------|
| `APP` | один на всё приложение | `DatabaseFactory`, фабрика сессий |
| `REQUEST` | новый на каждый HTTP-запрос | `AsyncSession`, `AbstractUow`, репозитории |

Провайдер связывает абстракцию с реализацией —
например, `IHealthCheckRepository → HealthCheckRepository`. Эндпоинт просит
`FromDishka[HealthCheckQuery]`, а контейнер строит весь граф зависимостей под
него. Сессия аккуратно открывается и закрывается на границах запроса через
`yield`-провайдер.

### Конфигурация

Конфиг читается из переменных окружения через типобезопасные ридеры
(`domain/services/env.py`: `get_str_value`, `get_int_value`, `get_bool_value`).
Если у переменной нет дефолта и она не задана — приложение падает на старте с
понятной ошибкой `MissingEnvVar`, а не молча работает на пустом значении.
Каждый слой описывает свою часть конфига (`ApplicationConfig`,
`DatabaseConfig`, `AuthConfig`), а `config.py` склеивает их в один
неизменяемый (`frozen`) объект `config`.

### Обработка ошибок

Все обработчики собраны в `domain/errors/handlers.py` и регистрируются в
`app_factory` из карты `HANDLERS_MAP`. Любая ошибка отдаётся клиенту в едином
формате `ErrorResponseModel` (`{ "error": { "code", "message", "extra" } }`):

- `AppException` — бизнес-ошибки (свой `status_code` и `error_code`);
- HTTP-ошибки FastAPI/Starlette — маппятся в человекочитаемые коды;
- ошибки валидации запроса (422) — со списком полей;
- всё непойманное — превращается в аккуратный 500 без утечки трейсбэка.

---

## Как начать

### Требования

- **Python 3.12** (зафиксирован в `.python-version`)
- **[uv](https://docs.astral.sh/uv/)** — менеджер пакетов и окружений
- **Docker** + Docker Compose — для PostgreSQL и MinIO

Установка uv (если ещё нет):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh    # Linux / macOS
# Windows (PowerShell):
# powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Запуск за пять шагов

```bash
# 1. Зависимости (создаст .venv и поставит prod + dev + test)
make install

# 2. Файл окружения из шаблона
make env                # скопирует .env.example → .env, при наличии не тронет

# 3. Поднять PostgreSQL и MinIO
make up

# 4. Накатить миграции на свежую БД
make upgrade

# 5. Запустить API
make run
```

После старта:

- API — http://localhost:8000
- Swagger UI — http://localhost:8000/docs
- ReDoc — http://localhost:8000/redoc
- Проверка живости — http://localhost:8000/api/healthcheck
- Консоль MinIO — http://localhost:9001

Перед коммитом полезно прогнать:

```bash
make check        # ruff lint + проверка форматирования + mypy
make test         # тесты
```

---

## Как писать код

Общий принцип: **новая функциональность добавляется сверху вниз по слоям**, и на
каждом слое вы трогаете «свой» тип файла. Ниже — рецепт на примере нового
сценария чтения. Команды (write) делаются так же, но в `command/`.

### Шаг 1. Домен — опишите контракт

Если сценарию нужны данные из БД, заведите интерфейс репозитория в
`domain/repository/` (чистый `Protocol`, без SQLAlchemy):

```python
# domain/repository/user.py
from abc import abstractmethod
from typing import Protocol

class IUserRepository(Protocol):
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...
```

### Шаг 2. DTO — опишите вход и выход

```python
# common/output/user/get.py
from pydantic import BaseModel

class UserOutputDto(BaseModel):
    id: UUID
    email: str
```

### Шаг 3. Use-case — бизнес-сценарий

Read-сценарии кладём в `common/use_case/query/`, write — в
`common/use_case/command/`. Use-case принимает абстракции через конструктор и
оборачивает работу в UoW:

```python
# common/use_case/query/user/get.py
from common.use_case.base import IQuery
from domain.repository.user import IUserRepository
from domain.uow import AbstractUow

class GetUserQuery(IQuery[UUID, UserOutputDto]):
    def __init__(self, uow: AbstractUow, repository: IUserRepository) -> None:
        self._uow = uow
        self._repository = repository

    async def execute(self, *, input_dto: UUID) -> UserOutputDto:
        async with self._uow:
            user = await self._repository.get_by_id(input_dto)
            ...
```

### Шаг 4. Инфраструктура — реализация репозитория

Реализуйте доменный интерфейс через SQLAlchemy, наследуясь от `BaseRepository`
(он держит `self._session`):

```python
# infrastructure/database/repository/user.py
from domain.repository.user import IUserRepository
from infrastructure.database.repository.base import BaseRepository

class UserRepository(IUserRepository, BaseRepository):
    async def get_by_id(self, user_id: UUID) -> User | None:
        ...  # работа с self._session
```

ORM-модель наследуйте от `BaseORModel` — он сам даёт `id: UUID` и имя таблицы из
имени класса. Нужны временные метки/мягкое удаление — подмешайте миксины
`CreatedAtMixin`, `UpdatedAtMixin`, `SoftDeleteMixin` из
`infrastructure/database/base.py`.

### Шаг 5. DI — свяжите интерфейс с реализацией

Добавьте провайдер в `infrastructure/database/di.py`, выбрав правильный scope
(репозитории — `REQUEST`):

```python
@provide(scope=Scope.REQUEST)
def get_user_repository(self, session: AsyncSession) -> IUserRepository:
    return UserRepository(session)
```

### Шаг 6. Presenter — эндпоинт

Эндпоинты живут в `presenter/rest/api/v1/`. Зависимости берём из контейнера
через `FromDishka`, не создаём руками:

```python
# presenter/rest/api/v1/endpoint/user.py
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/{user_id}", response_model=UserOutputDto)
@inject
async def get_user(user_id: UUID, use_case: FromDishka[GetUserQuery]) -> UserOutputDto:
    return await use_case.execute(input_dto=user_id)
```

Не забудьте подключить роутер в `presenter/rest/api/v1/router.py`.

### Шаг 7. Миграция

Если меняли ORM-модели — сгенерируйте и накатите ревизию:

```bash
make migration m="add users table"
make upgrade
```

### Договорённости по стилю

- **Импорты — от корня `src/`, без префикса `src.`**: пишем
  `from domain.uow import AbstractUow`, а не `from src.domain...`.
  `PYTHONPATH` (см. Makefile) включает и `backend/`, и `backend/src/`.
- **Интерфейсы — `Protocol`** с префиксом `I` (`IUserRepository`), реализации —
  без него (`UserRepository`).
- **Бизнес-ошибки** наследуем от `AppException` со своими `status_code` и
  `error_code` — обработчик сам приведёт их к единому JSON.
- **Конфиг читаем только через `domain/services/env.py`**, новые поля кладём в
  соответствующий `*Config`-датакласс — никаких `os.environ` врассыпную.
- Длина строки — **100** символов. Форматирует и проверяет всё `ruff`; перед
  коммитом гоняем `make check`.

---

## Гайд по Makefile

`make` без аргументов (или `make help`) печатает шпаргалку по всем целям.
Под капотом всё идёт через `uv run` с автоподхватом `.env` (если файл есть),
а `PYTHONPATH` настроен так, чтобы импорты резолвились от корня `src/`.

### Setup — установка и окружение

| Цель | Что делает |
|------|------------|
| `make install` | Поставить **все** зависимости: prod + dev + test (`uv sync`) |
| `make install-prod` | Только продовые зависимости, без dev/test |
| `make install-test` | Prod + test (без dev-тулинга) — для CI-прогона тестов |
| `make lock` | Пересобрать `uv.lock` после правок зависимостей |
| `make env` | Создать `.env` из `.env.example` (существующий не перезапишет) |

### Run / quality — запуск и проверки

| Цель | Что делает |
|------|------------|
| `make run` | Запустить API (`python -m src`) |
| `make lint` | Проверка линтером ruff |
| `make lint-fix` | ruff с автоисправлением (`--fix`) |
| `make format` | Отформатировать код (ruff format) |
| `make format-check` | Проверить форматирование, ничего не меняя |
| `make typecheck` | Статическая проверка типов (mypy по `src`) |
| `make check` | Всё сразу: **lint + format-check + typecheck** |
| `make test` | Прогнать тесты (pytest) |

> `make check` — то, что стоит запускать перед каждым коммитом/PR.

### Migrations — Alembic

| Цель | Что делает |
|------|------------|
| `make migration m="..."` | Сгенерировать новую ревизию по изменениям моделей. **`m` обязателен**, иначе цель остановится с ошибкой |
| `make upgrade` | Накатить БД до `head` (или до `REV=<id>`) |
| `make downgrade` | Откатить на одну ревизию назад (или до `REV=<id>`) |
| `make migrate-history` | Показать историю ревизий |
| `make migrate-current` | Показать текущую ревизию БД |
| `make db-reset` | Откатить до `base`, затем накатить до `head` (полный пересбор схемы) |

Примеры:

```bash
make migration m="add users table"   # создать ревизию
make upgrade                          # накатить всё
make upgrade REV=ae1027a6acf         # накатить до конкретной ревизии
make downgrade                        # откатить один шаг
```

Alembic берёт URL БД не из плейсхолдера в `alembic.ini`, а из реального
`DatabaseConfig` приложения (см. `migrations/env.py`) — отдельно прокидывать
строку подключения не нужно.

### Docker — окружение разработки

| Цель | Что делает |
|------|------------|
| `make up` | Поднять стек (PostgreSQL + MinIO) в фоне (`-d`) |
| `make down` | Остановить стек |
| `make build` | Собрать образы |
| `make logs` | Смотреть логи в реальном времени |
| `make ps` | Показать запущенные сервисы |
| `make restart` | `down` + `up` |

### Housekeeping и CI

| Цель | Что делает |
|------|------------|
| `make clean` | Удалить кеши (`__pycache__`, `.ruff_cache`, `.pytest_cache`) |
| `make develop` | CI: установить все зависимости |
| `make lint-ci` | CI: то же, что `make check` |
| `make test-ci` | CI: тесты с покрытием и junit-отчётом (отсутствие тестов = успех) |

Цели кросс-платформенные: `env` и `clean` имеют отдельные ветки для Windows
(`cmd.exe`); на Windows Makefile удобнее всего запускать из Git Bash или WSL.

---

## Конфигурация (.env)

Все настройки — через переменные окружения. Шаблон со всеми ключами лежит в
`.env.example`; `make env` копирует его в `.env`.

| Группа | Переменные | Назначение |
|--------|-----------|------------|
| Приложение | `APP_HOST`, `APP_PORT`, `APP_TITLE`, `APP_DESCRIPTION`, `APP_VERSION`, `APP_DEBUG`, `APP_DOCS_URL`, `APP_REDOC_URL` | хост/порт, метаданные OpenAPI, debug, пути к докам |
| PostgreSQL | `POSTGRES_DRIVER`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DATABASE` | подключение к БД |
| JWT | `JWT_ALGORITHM`, `JWT_PRIVATE_KEY_PATH`, `JWT_PUBLIC_KEY_PATH`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | алгоритм и ключи токенов, время жизни |
| MinIO | `MINIO_HOST`, `MINIO_PORT`, `MINIO_USER`, `MINIO_PASSWORD`, `MINIO_SECURE` | S3-совместимое хранилище |

Значения из `.env` автоматически подхватываются всеми `make`-целями (через
`uv run --env-file`) и `docker compose`.
