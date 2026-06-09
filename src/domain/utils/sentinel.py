from typing import Final


class Unset:
    __slots__ = ()

    def __repr__(self) -> str:
        return "<unset>"


unset: Final[Unset] = Unset()
