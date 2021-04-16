import sys
import six
from io import open


# TODO: deprecated since cli-eaa requires python 3
def force_unicode(s):
    if six.PY2:
        return unicode(s)
    else:
        return s


def argument_tolist(arg):
    for item in arg:
        if item[0:1] == "@":
            filename = item[1:]
            if filename == "-":
                for line in sys.stdin:
                    yield force_unicode(line.strip())
            else:
                with open(filename, "r") as f:
                    for line in f:
                        yield force_unicode(line.strip())
        else:
            yield force_unicode(item)
