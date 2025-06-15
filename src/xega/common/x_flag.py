class XFlag:
    def __init__(self, name: str, line_num: int):
        self.name = name
        self.line_num = line_num

    def __str__(self):
        return f"Flag: {self.name} (line {self.line_num})"

    def __repr__(self):
        return f"XFlag({self.name}, {self.line_num})"
