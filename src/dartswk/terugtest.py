"""Terugtest: afstemmen op train-jaren, ongewijzigd toetsen op test-jaren; ook walk-forward.

Uitvoer bevat alleen samengevatte cijfers (geen ruwe odds per wedstrijd).
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config
from .dataset import bouw
from .evaluatie import (MARGE, bets, bootstrap_geclusterd, brier, drempeltabel, gemiddeld, kies_drempel,
                        logloss, roi)
from .vorm import MODELLEN


def laad(jaren: list[int]) -> tuple[dict[int, list[dict]], dict[int, list[str]]]:
    data, meld = {}, {}
    for j in sorted(set(jaren)):
        data[j], meld[j] = bouw(j)
    return data, meld


def _met_odds(data, jaren):
    return [r for j in jaren for r in data[j] if r["odd1"] is not None]


def bet_samenvatting(bl: list[dict]) -> dict:
    r = roi(bl)
    lo, hi = bootstrap_geclusterd(bl, n=config.BOOTSTRAP_N)
    return dict(
        bets=len(bl), gewonnen=sum(b["gewonnen"] for b in bl),
        underdog_bets=sum(b["underdog"] for b in bl),
        gem_odd=round(sum(b["odd"] for b in bl) / len(bl), 2) if bl else None,
        winst_units=round(sum(b["resultaat"] for b in bl), 2),
        roi=None if r is None else round(r, 4),
        roi_90_geclusterd=[None if lo is None else round(lo, 3), None if hi is None else round(hi, 3)],
    )


def samenvatting(rows: list[dict], ps: list[float], drempel, bl: list[dict] | None = None) -> dict:
    """Kansmetrics model vs markt, plus bets bij `drempel` (of de meegegeven betlijst `bl`)."""
    ys = [1 if r["winnaar"] == 1 else 0 for r in rows]
    uit = dict(n=len(rows))
    uit["brier_model"] = round(gemiddeld(brier, ps, ys), 4)
    uit["logloss_model"] = round(gemiddeld(logloss, ps, ys), 4)
    for naam, f in MARGE.items():
        q = [f(r["odd1"], r["odd2"]) for r in rows]
        uit[f"brier_markt_{naam}"] = round(gemiddeld(brier, q, ys), 4)
        uit[f"logloss_markt_{naam}"] = round(gemiddeld(logloss, q, ys), 4)
    fav = [(r["odd1"] < r["odd2"]) == (y == 1) for r, y in zip(rows, ys) if r["odd1"] != r["odd2"]]
    uit["favoriet_won"] = f"{sum(fav)}/{len(fav)}"
    uit["drempel"] = drempel
    uit.update(bet_samenvatting(bets(rows, ps, drempel) if bl is None else bl))
    return uit


def terugtest(model: str, train: list[int], test: list[int], data: dict) -> dict:
    afstemmen, kans = MODELLEN[model]
    tr, te = _met_odds(data, train), _met_odds(data, test)
    prm = afstemmen(tr)
    p_tr = [kans(r, prm) for r in tr]
    p_te = [kans(r, prm) for r in te]
    tab_tr = drempeltabel(tr, p_tr, config.DREMPELS)
    drempel, reden = kies_drempel(tab_tr, config.MIN_BETS_DREMPEL)
    return dict(
        model=model, train=train, test=test, parameters=prm.dict(),
        drempel=drempel, drempel_reden=reden,
        train_resultaat=samenvatting(tr, p_tr, drempel),
        test_resultaat=samenvatting(te, p_te, drempel),
        ter_info_vaste_drempel=dict(
            drempel=config.VASTE_DREMPEL, toelichting="zonder stopregel; niet het hoofdresultaat",
            train=samenvatting(tr, p_tr, config.VASTE_DREMPEL), test=samenvatting(te, p_te, config.VASTE_DREMPEL)),
        drempeltabel_train=tab_tr,
        drempeltabel_test_ter_info=drempeltabel(te, p_te, config.DREMPELS),
        _bets_test=bets(te, p_te, drempel), _bets_test_vast=bets(te, p_te, config.VASTE_DREMPEL),
        _p_test=p_te, _rows_test=te,
    )


def walk_forward(model: str, jaren: list[int], data: dict) -> dict:
    jaren = sorted(jaren)
    stappen = [terugtest(model, jaren[:i], [t], data) for i, t in enumerate(jaren) if i > 0]
    rows = [r for s in stappen for r in s["_rows_test"]]
    ps = [p for s in stappen for p in s["_p_test"]]
    return dict(
        model=model, jaren=jaren, stappen=stappen,
        totaal_test=samenvatting(rows, ps, "per stap", [b for s in stappen for b in s["_bets_test"]]),
        ter_info_vaste_drempel_totaal_test=samenvatting(
            rows, ps, config.VASTE_DREMPEL, [b for s in stappen for b in s["_bets_test_vast"]]),
    )


# ---------------------------------------------------------------- uitvoer
def _schoon(d):
    if isinstance(d, dict):
        return {k: _schoon(v) for k, v in d.items() if not k.startswith("_")}
    if isinstance(d, list):
        return [_schoon(x) for x in d]
    return d


def _pct(x):
    return "–" if x is None else f"{x:+.1%}"


def _ci(c):
    return "–" if c[0] is None else f"[{c[0]:+.1%}, {c[1]:+.1%}]"


def _jr(j):
    return "+".join(str(x) for x in j)


KOP = ("| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | "
       "Brier markt (prop.) | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |\n"
       "|---|---|---|---|---|---|---|---|---|---|---|---|---|")


def _regel(naam, jaren, s):
    d = s["drempel"]
    d = "niet wedden" if d is None else (d if isinstance(d, str) else f"{d:.2f}")
    return (f"| {naam} | {_jr(jaren)} | {s['n']} | {s['logloss_model']:.4f} | {s['logloss_markt_proportioneel']:.4f} | "
            f"{s['logloss_markt_shin']:.4f} | {s['brier_model']:.4f} | {s['brier_markt_proportioneel']:.4f} | {d} | "
            f"{s['bets']} | {s['underdog_bets']} | {_pct(s['roi'])} | {_ci(s['roi_90_geclusterd'])} |")


def _drempel_md(tab):
    return "\n".join(["| Drempel | Bets | ROI |", "|---|---|---|"] +
                     [f"| {x['drempel']:.2f} | {x['bets']} | {_pct(x['roi'])} |" for x in tab])


def markdown_terugtest(t: dict) -> str:
    p = t["parameters"]
    return "\n".join([
        f"# Terugtest model `{t['model']}`: train {_jr(t['train'])}, test {_jr(t['test'])}", "",
        f"Parameters (afgestemd op log-loss, train): w={p['w']}, L={p['L']}, k={p['k']}, kc={p['kc']}", "",
        f"Drempelkeuze: {t['drempel_reden']}.", "",
        KOP, _regel("train", t["train"], t["train_resultaat"]), _regel("test", t["test"], t["test_resultaat"]), "",
        "## Drempeltabel train (basis voor de keuze)", "", _drempel_md(t["drempeltabel_train"]), "",
        "## Drempeltabel test (alleen ter informatie, niet gebruikt voor de keuze)", "",
        _drempel_md(t["drempeltabel_test_ter_info"]), "",
        f"## Ter informatie: vaste drempel {config.VASTE_DREMPEL:.2f} zonder stopregel (niet het hoofdresultaat)", "",
        KOP, _regel("train", t["train"], t["ter_info_vaste_drempel"]["train"]),
        _regel("test", t["test"], t["ter_info_vaste_drempel"]["test"]), "",
    ])


def markdown_walk_forward(wf: dict) -> str:
    regels = [f"# Walk-forward model `{wf['model']}` ({_jr(wf['jaren'])})", "",
              "Per stap: afstemmen op alle jaren vóór t, ongewijzigd toetsen op t.", "", KOP]
    for s in wf["stappen"]:
        regels.append(_regel(f"test (train {_jr(s['train'])})", s["test"], s["test_resultaat"]))
    testjaren = [s["test"][0] for s in wf["stappen"]]
    regels.append(_regel("totaal test", testjaren, wf["totaal_test"]))
    regels += ["", "| Stap | Parameters | Drempelkeuze |", "|---|---|---|"]
    for s in wf["stappen"]:
        p = s["parameters"]
        regels.append(f"| test {_jr(s['test'])} | w={p['w']}, L={p['L']}, k={p['k']}, kc={p['kc']} | {s['drempel_reden']} |")
    regels += ["", f"## Ter informatie: vaste drempel {config.VASTE_DREMPEL:.2f} zonder stopregel (niet het hoofdresultaat)",
               "", KOP]
    for s in wf["stappen"]:
        regels.append(_regel(f"test (train {_jr(s['train'])})", s["test"], s["ter_info_vaste_drempel"]["test"]))
    regels.append(_regel("totaal test", testjaren, wf["ter_info_vaste_drempel_totaal_test"]))
    return "\n".join(regels) + "\n"


def schrijf(naam: str, obj: dict, md: str, map_: Path | None = None) -> tuple[Path, Path]:
    map_ = map_ or config.resultaten_map()
    map_.mkdir(parents=True, exist_ok=True)
    fj, fm = map_ / f"{naam}.json", map_ / f"{naam}.md"
    fj.write_text(json.dumps(_schoon(obj), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    fm.write_text(md, encoding="utf-8")
    return fj, fm
