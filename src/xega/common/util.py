import json

from xega.common.token_xent_list import TokenXentList
from xega.common.x_string import XString


class XEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, XString):
            return str(o)
        elif isinstance(o, tuple):
            return {"__tuple__": True, "items": list(o)}
        elif isinstance(o, TokenXentList):
            return {"__TokenXentList__": True, "pairs": o.pairs, "scale": o.scale}
        return super().default(o)


# No need to load XString from JSON
def x_decoder(dct):
    if "__tuple__" in dct:
        return tuple(dct["items"])
    elif "__TokenXentList__" in dct:
        return TokenXentList(dct["pairs"], dct["scale"])
    return dct


def dumps(obj, **kwargs):
    return json.dumps(obj, cls=XEncoder, **kwargs)


def loads(s, **kwargs):
    return json.loads(s, object_hook=x_decoder, **kwargs)
