# Architecture Review — projectkusi / backend

Дата: 2026-06-07
Ветка: `master`

Разбор несостыковок по слоям, ошибок в коде, неправильных названий и нарушений
взаимодействия между слоями. Сгруппировано по серьёзности.

Структура проекта (clean-ish architecture):

```
src/
├── __main__.py          # composition root / запуск
├── application/         # use-case слой (config, interface, use_case, dto)
├── domain/              # доменный слой (errors, utils)
├── infrasture/          # инфраструктура (database, auth, minio)  ← опечатка в имени
└── presenter/           # presenter (rest: api, middleware, app_factory)
```

---

## 🔴 Критичные баги (код не запустится / работает неверно)

### 1. `infrasture/database/base.py:13` — опечатка `__tablname__`
```python
@declared_attr.directive
def __tablname__(cls) -> str:        # ← должно быть __tablename__
    return camel_to_snake(cls.__name__)
```
SQLAlchemy ищет `__tablename__`. С опечаткой автогенерация имени таблицы **не
работает**, и любая модель без явного `__tablename__` упадёт при маппинге.

### 2. `infrasture/database/base.py:10` — `default=uuid4()` вызывается один раз
```python
id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4(), unique=True)
```
`uuid4()` вычисляется **в момент определения класса**, поэтому все строки получат
**один и тот же id**. Нужно передавать callable: `default=uuid4` (без скобок).
Плюс `unique=True` на первичном ключе избыточен.

### 3. `infrasture/database/migrations/env.py:8` — импорт несуществующего класса
```python
from database.base import ORModel        # класса ORModel нет
```
В `base.py` класс называется `BaseORModel`. → `ImportError`, alembic не стартует.
Строка 7 `# from database.table import ()` — мусорный комментарий с невалидным
синтаксисом.

### 4. `domain/errors/exceptions.py:12` — теряется дефолтное сообщение
```python
def __init__(self, message: Optional[str] = None, ...):
    self.message = message               # при None затирает class-default
```
Если `message` не передан, `self.message` становится `None`, а не
`"Некорректный запрос"`. Нужно `self.message = message or self.message`.

### 5. `__main__.py` / `app_factory.py` — сервис aiomisc не запускается корректно
```python
server = RestServer(config=config, router=router)
server.start()                           # корутина, которую никто не await-ит
```
`UvicornService.start()` — это асинхронный метод aiomisc-сервиса; его нельзя
вызывать напрямую. Сервисы aiomisc запускаются через `aiomisc.entrypoint`/`run`.
Сейчас `start()` вернёт неожиданную корутину, и сервер фактически не поднимется.
Хост/порт в `UvicornService` тоже нигде не задаются.

### 6. `infrasture/database/uow.py` — `UnitOfWork` не реализует протокол
```python
class UnitOfWork(IUnitOfWork):
    def __init__(self, make, session) -> None:
        self._make = make
        self._session = session
    # нет commit / rollback / __aenter__ / __aexit__
```
Объявлены только `__init__`. Методы протокола не реализованы — при использовании
как контекст-менеджера/UoW упадёт. Аргументы `make`/`session` без типов.

### 7. `docker-compose.yml` — пустой (0 байт)
`Makefile` имеет цели `up/down/build/logs/ps/restart`, завязанные на compose.
Все они упадут — сервиса не описано.

---

## 🟠 Нарушения слоёв (неправильное взаимодействие)

### 8. Инфраструктура импортирует presenter (обратная зависимость)
`infrasture/database/database.py:4`
```python
from presenter.rest.config import config
```
**Infrastructure → Presenter** — зависимость направлена не туда. Инфраструктура
не должна знать про presenter. Конфиг БД нужно получать из своего слоя
(`infrasture/database/config.py`) или через DI/composition root, а не тянуть
агрегированный объект из presenter.

### 9. Глобальный агрегатор `Config` живёт в presenter-слое
`presenter/rest/config.py` собирает воедино `ApplicationConfig`, `DatabaseConfig`,
`AuthConfig`, `MinioConfig`. Получается, что presenter зависит от всей
инфраструктуры и становится «хабом» конфигурации. Это задача composition root
(`__main__`/bootstrap) или application-слоя, а не presenter. Из-за этого и
возникает нарушение №8 (БД импортирует конфиг из presenter).

### 10. Доменный слой читает окружение и форматирует имена таблиц
- `domain/utils/get_value.py` напрямую обращается к `os.environ` — чтение env
  это инфраструктурная забота, домен должен быть «чистым».
- `domain/utils/formate.py::camel_to_snake` генерирует **имена таблиц БД** и
  используется в `infrasture/database/base.py`. Это инфраструктурный хелпер,
  лежащий в домене.
- В домене нет ни одной сущности/бизнес-модели — только `errors` и технические
  `utils`. Фактически доменный слой пуст по смыслу.

### 11. `__main__.py` смешивает корни импорта (`src.` vs без `src.`)
```python
from src.presenter.rest.app_factory import ApplicationFactory as RestServer
```
Везде в коде импорт идёт без префикса (`from presenter...`, `from domain...`),
а здесь — `from src.presenter...`. Поскольку `PYTHONPATH` содержит и `backend/`,
и `backend/src/` (см. Makefile), `src.presenter.rest.config` и
`presenter.rest.config` резолвятся в **два разных модуля** → два разных
экземпляра `config`/синглтонов. Тонкий баг двойного импорта.

### 12. Три корня импорта одновременно
Makefile документирует: `backend/`, `backend/src/`, `backend/src/infrasture`.
Третий корень нужен только ради `from database.base import ...` в alembic
`env.py`. Это хрупко: один и тот же модуль доступен под несколькими именами.
Лучше один корень (`src/`) и единый стиль импортов.

### 13. DI полностью заглушен, но dishka подключён
- `infrasture/database/di.py`, `infrasture/auth/di.py` — пустые.
- `application/interface/__init__.py`, `repository/__init__.py` — пустые.
- В `app_factory.py` импортируется `make_async_container` (не используется),
  а `_include_dependencies` закомментирован.
Контейнер нигде не собирается — слой внедрения зависимостей отсутствует.

### 14. Alembic не получает реальный URL БД
`alembic.ini:89` — `sqlalchemy.url = driver://user:pass@localhost/dbname`
(плейсхолдер). `env.py` берёт URL из `config.get_section(...)`/`get_main_option`,
но **не подгружает** `DatabaseConfig` приложения. Миграции пойдут на фейковый
URL. Нет моста между конфигом приложения и конфигом alembic.

---

## 🟡 Неправильные названия

| Где | Сейчас | Должно быть |
|-----|--------|-------------|
| директория | `src/infrasture/` | `infrastructure` (опечатка везде) |
| `domain/utils/formate.py` | `formate` | `format` (и имя функции вводит в заблуждение: она ещё и **плюрализует**, т.е. это `class_name_to_table_name`, а не просто camel→snake) |
| `.env.exparement` | `exparement` | `.env.example` (фигурирует в Makefile и .gitignore) |
| `database.py::DatabaseFabric` | `Fabric` (рус. «фабрика») | `DatabaseFactory` |
| `base.py` миксины | `MixinCreateAtORM` / `MixinUpdateAtORM` / `MixinDeleteAtORM` | `CreatedAtMixin` / `UpdatedAtMixin` / `SoftDeleteMixin` (грамматика: «CreateAt», колонки — `created_at`) |
| `database/config.py` | `POSTGRES_DRIVE` | `POSTGRES_DRIVER` |
| `base.py` | `BaseORModel` | согласовать с тем, что импортирует `env.py` (`ORModel`) — сейчас имена расходятся |

`MixinDeleteAtORM` к тому же содержит и `is_active`, и `deleted_at` — это
soft-delete, имя «DeleteAt» не отражает суть.

---

## 🟡 Типы и корректность

### 15. `application/config.py:9` — неверная аннотация
```python
APP_DEBUG: str = field(default_factory=lambda: get_bool_value("APP_DEBUG", True))
```
Значение `bool`, аннотация — `str`. Должно быть `bool`.

### 16. `database/config.py` — `POSTGRES_PORT: str`
Порт хранится строкой и затем передаётся в `URL.create(port=...)`, который ждёт
`int`. Лучше `int` через `get_int_value`.

### 17. `base.py` — неправильная типизация `id`
```python
from sqlalchemy import UUID
id: Mapped[UUID] = mapped_column(...)
```
`UUID` здесь — это SQLAlchemy-тип (TypeEngine), а не Python-тип. В `Mapped[...]`
должен стоять `uuid.UUID`: `Mapped[uuid.UUID] = mapped_column(SA_UUID(as_uuid=True), ...)`.

### 18. Несогласованные декораторы dataclass у конфигов
`ApplicationConfig` и `DatabaseConfig` — `@dataclass(frozen=True, kw_only=True,
slots=True)`, а `AuthConfig` и `MinioConfig` — просто `@dataclass` (мутабельные,
без slots/kw_only). Привести к единому стилю.

### 19. `domain/errors/codes.py` — значения как заголовки, а не коды
```python
VALIDATION_ERROR = "Validation Error"
```
В поле `code` уходит человекочитаемая строка («Validation Error»), хотя это
скорее `title`. Машинный код обычно `validation_error`. Смешение кода и текста.

### 20. `handlers.py:22` — грубый маппинг HTTP-статусов
```python
code = ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.BAD_REQUEST
```
401/403/500 и т.п. все схлопываются в `BAD_REQUEST`. Семантически неверно.

---

## 🟡 Незавершённое / мусор

- `infrasture/database/database.py`:
  - класс назван `DatabaseFabric`, методы `create_engine_path`/`create_engine`
    аннотированы `-> str`, но ничего не возвращают (присваивают в `self.*`);
  - `create_engine` использует `self.engine_path`, который установится только
    если до этого вызвали `create_engine_path()` — скрытая зависимость порядка;
  - нет геттера engine, нет фабрики сессий (`async_sessionmaker`);
  - `connect_args` под asyncpg c `ssl: "require"` захардкожен;
  - неиспользуемый импорт `Final`.
- `application/dto/` — директория без `__init__.py` и без содержимого.
- `application/use_case/` — есть только `UseCase` Protocol, ни одного use-case.
- `repository/` — пусто, реализаций репозиториев нет.
- `tests/` — пусто, хотя pytest и httpx настроены.
- `presenter/rest/api/v1/endpoint`, `.../schema` — только пустые `__init__.py`,
  ни одного эндпоинта/схемы; `v1/router.py` не подключает ни одного роутера.
- `migrations/versions/` — пусто, ни одной ревизии.
- `infrasture/auth/config.py` — есть JWT-параметры, но нет секрета/путей к
  ключам (для RS256 нужны ключи). `MinioConfig` — нет host/endpoint, только
  port/user/password.

---

## 🟢 Мелочи / стиль

- `get_value.py`: `get_int_value`/`get_float_value`/`get_bool_value` дублируют
  логику проверки `None` вместо переиспользования `_raw`.
- `app_factory.py`: неиспользуемый импорт `make_async_container`.
- `config.py` (application): неровные пробелы в `lambda:get_str_value(...)`
  (нет пробела после `:`) — поправит `ruff format`.
- `formate.camel_to_snake`: имя обещает только camel→snake, но функция ещё и
  плюрализует — легко получить двойную обработку при повторном вызове.

---

## Сводка приоритетов

1. Починить запуск: `__tablname__`→`__tablename__`, `uuid4()`→`uuid4`,
   `ORModel`/`BaseORModel`, запуск aiomisc-сервиса, реализовать `UnitOfWork`.
2. Развернуть зависимость БД↔presenter: вынести composition root конфигурации
   из `presenter.rest.config` и убрать `from presenter...` в инфраструктуре.
3. Свести импорты к одному корню (`src/`), убрать `src.`-префикс в `__main__`.
4. Переименования: `infrasture`→`infrastructure`, `Fabric`→`Factory`,
   `formate`→`format`, `POSTGRES_DRIVE`→`POSTGRES_DRIVER`, миксины.
5. Подвязать alembic к реальному `DatabaseConfig`, наполнить пустой
   `docker-compose.yml`.
6. Вынести `get_value`/`formate` из `domain` в инфраструктуру/утиль вне домена.
