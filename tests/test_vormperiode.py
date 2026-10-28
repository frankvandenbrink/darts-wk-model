import json
from datetime import date

import pytest

from dartswk import config
from dartswk.bronnen import vormperiode
from dartswk.parse import load_orakel


@pytest.mark.parametrize("jaar", sorted(config.JAREN))
@pytest.mark.parametrize("m", config.VENSTERS)
def test_vormperiode_eindigt_voor_wk_start(jaar, m):
    van, tot = vormperiode(jaar, m)
    assert van < tot < date.fromisoformat(config.JAREN[jaar].start)


def test_load_orakel_weigert_periode_tot_in_wk(tmp_path):
    start = config.JAREN[2026].start
    for m in config.VENSTERS:
        for naam in ("avg", "co"):
            tot = start if (naam, m) == ("co", 12) else "2025-12-10"
            (tmp_path / f"orakel_2026_{naam}_{m}m.json").write_text(json.dumps(dict(van="2024-12-10", tot=tot, data=[])))
    with pytest.raises(AssertionError):
        load_orakel(2026, tmp_path)
