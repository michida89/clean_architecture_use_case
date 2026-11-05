import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from infrastructure.database.naming import class_name_to_table_name


class BaseORModel(DeclarativeBase):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return class_name_to_table_name(cls.__name__)


class CreatedAtMixin:
    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(server_default=func.now())


class UpdatedAtMixin:
    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        return mapped_column(
            server_default=func.now(),
            onupdate=func.now(),
        )


class SoftDeleteMixin:
    is_active: Mapped[bool] = mapped_column(default=True)

    @declared_attr
    def deleted_at(cls) -> Mapped[datetime | None]:
        return mapped_column(default=None, nullable=True)
