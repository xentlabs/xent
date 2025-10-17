from typing import Any


class XFlag:
    def __init__(self, name: str, line_num: int):
        self.name = name
        self.line_num = line_num

    def __str__(self):
        return f"Flag: {self.name} (line {self.line_num})"

    def __repr__(self):
        return f"XFlag({self.name}, {self.line_num})"

    def serialize(self) -> dict[str, Any]:
        return {
            "type": "XFlag",
            "name": self.name,
            "line_num": self.line_num,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]):
        return cls(data["name"], int(data["line_num"]))
