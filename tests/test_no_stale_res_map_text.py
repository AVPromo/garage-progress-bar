"""The mod no longer uses res_map / ModDynAccessor; stale mentions in shipped source or
current docs mislead. Historical plans (docs/superpowers) and TASKS/ are not scanned."""
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
_PAT = re.compile(r"res_map|ModDynAccessor")
_SCAN = ["src", "tests", ".claude", "README.md", "INSTALL.md", "CONTRIBUTING.md",
         os.path.join("tools", "dev", "README.md"), os.path.join("installer", "README.md")]
_EXT = (".py", ".js", ".css", ".json", ".md", ".txt")


def _files():
    for entry in _SCAN:
        path = os.path.join(ROOT, entry)
        if os.path.isfile(path):
            yield path
        for d, _, names in os.walk(path):
            for n in names:
                if n.endswith(_EXT):
                    yield os.path.join(d, n)


def test_no_res_map_or_moddynaccessor_mentions():
    me = os.path.abspath(__file__)
    hits = []
    for p in _files():
        if os.path.abspath(p) == me:
            continue
        with open(p, encoding="utf-8", errors="ignore") as f:
            hits += ["%s:%d" % (os.path.relpath(p, ROOT), i)
                     for i, line in enumerate(f, 1) if _PAT.search(line)]
    assert not hits, "stale res_map/ModDynAccessor text: %s" % hits
