from typing import Any


class TokenXentList:
    def __init__(self, token_xent_pairs: list[tuple[str, float]], scale=1.0):
        self.pairs = token_xent_pairs
        self.scale = scale

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"TokenXentList({self.pairs}, scale={self.scale}"

    def _verify_compatible(self, other):
        if not isinstance(other, TokenXentList):
            raise TypeError(f"Cannot operate with {type(other)}")

        if len(self.pairs) != len(other.pairs):
            return False

        for (token1, _), (token2, _) in zip(self.pairs, other.pairs, strict=False):
            if token1 != token2:
                return False
        return True

    def serialize(self) -> dict[str, Any]:
        return {"pairs": [[p[0], p[1]] for p in self.pairs], "scale": self.scale}

    @classmethod
    def deserialize(cls, data: dict[str, Any]):
        pairs = [(p[0], p[1]) for p in data["pairs"]]
        return cls(pairs, float(data["scale"]))

    def total_xent(self):
        return self.scale * sum(xent for _, xent in self.pairs)

    def _apply_scale(self):
        if self.scale == 1.0:
            return self

        pairs = [(token, xent * self.scale) for token, xent in self.pairs]
        return TokenXentList(pairs)

    def __add__(self, other):
        if not isinstance(other, TokenXentList):
            return NotImplemented

        if not self._verify_compatible(other):
            # Can only sum if both lists have the same tokens
            return NotImplemented

        self_normalized = self._apply_scale()
        other_normalized = other._apply_scale()

        result = [
            (token1, xent1 + xent2)
            for (token1, xent1), (token2, xent2) in zip(
                self_normalized.pairs, other_normalized.pairs, strict=False
            )
        ]
        return TokenXentList(result)

    def __radd__(self, other):
        return NotImplemented

    def __sub__(self, other):
        if not isinstance(other, TokenXentList):
            return NotImplemented

        if not self._verify_compatible(other):
            # Can only subtract if both lists have the same tokens
            return NotImplemented

        self_normalized = self._apply_scale()
        other_normalized = other._apply_scale()

        result = [
            (token1, xent1 - xent2)
            for (token1, xent1), (token2, xent2) in zip(
                self_normalized.pairs, other_normalized.pairs, strict=False
            )
        ]
        return TokenXentList(result)

    def __rsub__(self, other):
        return NotImplemented

    def __mul__(self, other):
        if not isinstance(other, int | float):
            return NotImplemented

        return TokenXentList(self.pairs, scale=self.scale * other)

    def __rmul__(self, other):
        if not isinstance(other, int | float):
            return NotImplemented

        return TokenXentList(self.pairs, scale=self.scale * other)

    def __truediv__(self, other):
        return NotImplemented

    def __rtruediv__(self, other):
        return NotImplemented

    def __neg__(self):
        return TokenXentList(self.pairs, scale=-self.scale)

    def __pos__(self):
        return self

    def __eq__(self, other):
        if isinstance(other, TokenXentList):
            return ValidatedBool(self.total_xent() == other.total_xent())
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, TokenXentList):
            return ValidatedBool(self.total_xent() != other.total_xent())
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, TokenXentList):
            return ValidatedBool(self.total_xent() < other.total_xent())
        elif isinstance(other, int | float):
            return self.total_xent() < other
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, TokenXentList):
            return ValidatedBool(self.total_xent() <= other.total_xent())
        elif isinstance(other, int | float):
            return self.total_xent() <= other
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, TokenXentList):
            return ValidatedBool(self.total_xent() > other.total_xent())
        elif isinstance(other, int | float):
            return self.total_xent() > other
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, TokenXentList):
            return ValidatedBool(self.total_xent() >= other.total_xent())
        elif isinstance(other, int | float):
            return self.total_xent() >= other
        return NotImplemented


class ValidatedBool:
    def __init__(self, value):
        self.value = bool(value)

    def __bool__(self):
        return self.value

    def __and__(self, other):
        if isinstance(other, ValidatedBool):
            return ValidatedBool(bool(self) and bool(other))
        return bool(self) and bool(other)

    def __or__(self, other):
        if isinstance(other, ValidatedBool):
            return ValidatedBool(bool(self) or bool(other))
        return bool(self) or bool(other)

    def __invert__(self):
        return ValidatedBool(not bool(self))

    def __repr__(self):
        return f"ValidatedBool(value={self.value})"
