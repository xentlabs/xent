from __future__ import annotations

from typing import TYPE_CHECKING, Any

from xent.common.errors import XentTypeError

if TYPE_CHECKING:
    from xent.common.x_list import XList


class XString:
    primary_string: str

    def __init__(
        self,
        primary_string: str | XString,
        static=False,
        public=False,
        name: str | None = None,
    ):
        if isinstance(primary_string, XString):
            primary_string = primary_string.primary_string

        if not isinstance(primary_string, str):
            raise XentTypeError(
                f"XString constructor requires a string argument. Got: {type(primary_string).__name__}"
            )

        self.primary_string = primary_string
        self.prefix = ""
        self.static = static
        self.public = public
        self.name = name

    def __str__(self):
        return str(self.primary_string)

    def __repr__(self):
        return f"XString('{self.primary_string}', prefix='{self.prefix}', static={self.static}, public={self.public}, name='{self.name}')"

    def serialize(self) -> dict[str, Any]:
        return {
            "type": "XString",
            "primary_string": self.primary_string,
            "prefix": self.prefix,
            "static": self.static,
            "public": self.public,
            "name": self.name,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]):
        xstr = cls(data["primary_string"], data["static"], data["public"], data["name"])
        xstr.prefix = data["prefix"]
        return xstr

    def _verify_other_operand(self, other):
        if not isinstance(other, str) and not isinstance(other, XString):
            raise XentTypeError(
                f"Unsupported operand type(s): '{type(self).__name__}' and '{type(other).__name__}'. "
                "Operand must be a String."
            )

    def __eq__(self, other):
        if isinstance(other, XString):
            return self.primary_string == other.primary_string
        elif isinstance(other, str):
            return self.primary_string == other
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, XString):
            return self.primary_string != other.primary_string
        elif isinstance(other, str):
            return self.primary_string != other
        return NotImplemented

    def __or__(self, other):
        """This implements the prefix decoration operator |"""
        self._verify_other_operand(other)
        new_xstring = XString(self.primary_string)
        new_xstring.prefix = str(other)
        return new_xstring

    def __ror__(self, other):
        """This implements the prefix decoration operator |"""
        self._verify_other_operand(other)
        new_xstring = XString(str(other))
        new_xstring.prefix = str(self.primary_string)
        return new_xstring

    def __add__(self, other):
        self._verify_other_operand(other)
        return XString(self.primary_string + str(other))

    def __radd__(self, other):
        self._verify_other_operand(other)
        return XString(str(other) + self.primary_string)

    def _cut_front(self, left, right):
        if not right:
            return XString(left)

        try:
            index = left.index(right)
            return XString(left[:index])
        except ValueError:
            return XString(left)

    def __floordiv__(self, other):
        self._verify_other_operand(other)
        s_str = self.primary_string
        t_str = str(other)
        return self._cut_front(s_str, t_str)

    def __rfloordiv__(self, other):
        self._verify_other_operand(other)
        s_str = str(other)
        t_str = self.primary_string
        return self._cut_front(s_str, t_str)

    def _cut_back(self, left, right):
        if not right:
            return XString("")
        try:
            index = left.index(right)
            return XString(left[index + len(right) :])
        except ValueError:
            return XString("")

    def __mod__(self, other):
        """This implements the cut back operator %"""
        self._verify_other_operand(other)
        s_str = self.primary_string
        t_str = str(other)
        return self._cut_back(s_str, t_str)

    def __rmod__(self, other):
        """This implements the cut back operator %"""
        self._verify_other_operand(other)
        print("*****************IN RMOD*****************")
        print(f"Other: {other}")
        s_str = str(other)
        t_str = self.primary_string
        return self._cut_back(s_str, t_str)

    def __len__(self):
        return len(self.primary_string)

    def __contains__(self, item):
        return str(item) in self.primary_string

    def join(self, items: XList) -> XString:
        from xent.common.x_list import XList

        if not isinstance(items, XList):
            raise XentTypeError(
                f"XString.join requires an XList argument. Got: {type(items).__name__}"
            )

        joined_parts: list[str] = []
        for element in items:
            if not isinstance(element, XString):
                raise XentTypeError(
                    "XString.join requires all elements of the XList to be XString instances. "
                    f"Got: {type(element).__name__}"
                )
            joined_parts.append(element.primary_string)

        return XString(self.primary_string.join(joined_parts))

    def split(
        self,
        separator: str | XString | None = None,
    ) -> XList:
        from xent.common.x_list import XList

        if separator is None:
            sep_value: str | None = None
        elif isinstance(separator, XString):
            sep_value = separator.primary_string
        elif isinstance(separator, str):
            sep_value = separator
        else:
            raise XentTypeError(
                "XString.split separator must be None, str, or XString. "
                f"Got: {type(separator).__name__}"
            )

        split_result = self.primary_string.split(sep_value)

        return XList([XString(part) for part in split_result])
