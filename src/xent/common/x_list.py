from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from xent.common.errors import XentTypeError
from xent.common.x_string import XString


class XList:
    items: list[XString]

    def __init__(
        self,
        items: list[XString] | None = None,
        static=False,
        public=False,
        name: str | None = None,
    ):
        self.items = items if items else []
        self.static = static
        self.public = public
        self.name = name

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"XList(items={self.items}, static={self.static}, public={self.public}, name='{self.name}')"

    def serialize(self) -> dict[str, Any]:
        return {
            "type": "XList",
            "items": [i.serialize() for i in self.items],
            "static": self.static,
            "public": self.public,
            "name": self.name,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]):
        items = [XString.deserialize(item) for item in data["items"]]
        xlist = cls(items, data["static"], data["public"], data["name"])
        return xlist

    def _verify_other_operand(self, other):
        if not isinstance(other, XList):
            raise XentTypeError(
                f"Unsupported operand type(s): '{type(self).__name__}' and '{type(other).__name__}'. "
                "Operand must be an XList."
            )

    def __eq__(self, other):
        if isinstance(other, XList):
            return self.items == other.items
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, XList):
            return not self.__eq__(other)
        return NotImplemented

    def __add__(self, other):
        self._verify_other_operand(other)
        return XList(
            self.items + other.items,
            static=self.static,
            public=self.public,
            name=self.name,
        )

    def __len__(self):
        return len(self.items)

    def __contains__(self, item):
        return item in self.items

    def __iter__(self) -> Iterator[XString]:
        return iter(self.items)
