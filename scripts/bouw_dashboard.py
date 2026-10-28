#!/usr/bin/env python3
"""Bouwt het statische tussenstanden-dashboard (site/index.html en site/data.json).

Alleen standaardbibliotheek. Leest alle ``resultaten/*.json`` en verzamelt 'run'-records:

- een los run-object op topniveau (``terugtest_*.json``);
- ``{"stappen": [run, ...], "totaal_test": {...}}`` (``walkforward_*.json``);
- ``{"runs": [run, ...], "data": {...}, "blind_underdog": {...}, "meldingen": {...}}`` (``vergelijking.json``).

Runs worden ontdubbeld op (model, train, test). Bij dubbelen wint het bestand met het rijkste formaat
(vergelijking > walk-forward > los), daarna de run met de meeste keys, daarna het nieuwste bestand.

Een run mag een key ``verloop`` hebben (of ``test_resultaat.verloop``): een lijst met de cumulatieve winst in
units na elke bet, chronologisch. Die wordt als lijn getekend.

Live-bestand ``resultaten/live_2027.json`` (optioneel)::

    {
      "toernooi": "WK 2026/27",          # optioneel
      "model": "vorm",                   # optioneel
      "bijgewerkt": "2026-12-12",        # optioneel
      "wedstrijden": [
        {
          "datum": "2026-12-11",         # ISO-datum
          "ronde": "1",                  # 1, 2, 3, 4, QF, SF, F
          "speler1": "...", "speler2": "...",
          "kans_model": 0.62,            # kans dat speler1 wint, vooraf vastgelegd
          "kans_markt": 0.58,            # optioneel, marktkans speler1 na margecorrectie
          "odd1": 1.60, "odd2": 2.35,    # optioneel, slotodds
          "bet": 1,                      # optioneel: 1, 2 of null (geen bet); inzet 1 unit
          "winnaar": null,               # 1 of 2 na afloop, null zolang niet gespeeld
          "sets1": null, "sets2": null   # optioneel, uitslag
        }
      ]
    }

Gebruik: ``python scripts/bouw_dashboard.py [--resultaten resultaten] [--uit site]``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import os
import sys
from pathlib import Path

REPO_URL = "https://github.com/frankvandenbrink/darts-wk-model"
LIVE_BESTAND = "live_2027.json"
LIVE_LEEG = "Nog geen voorspellingen; het toernooi start op 11 december 2026."
DISCLAIMER = "Hobbyproject. Wedden kan verliesgevend zijn. 18+. Geen advies."

SOORT_LABEL = {"richting": "Vaste richting (train → test)", "walk-forward": "Walk-forward"}
SOORT_VOLGORDE = ["richting", "walk-forward"]
FORMAAT_PRIO = {"los": 0, "stappen": 1, "runs": 2}

STREEP = "–"
MIN = "−"


# --------------------------------------------------------------------------- laden

def _lees_json(pad: Path):
    try:
        return json.loads(pad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as fout:
        print(f"waarschuwing: {pad.name} overgeslagen ({fout})", file=sys.stderr)
        return None


def _is_run(obj) -> bool:
    return isinstance(obj, dict) and "model" in obj and "test" in obj


def _jaren(waarde) -> tuple:
    if waarde is None:
        return ()
    if isinstance(waarde, (list, tuple)):
        return tuple(waarde)
    return (waarde,)


def run_sleutel(run: dict) -> tuple:
    return (str(run.get("model")), _jaren(run.get("train")), _jaren(run.get("test")))


def _rijkdom(run: dict) -> int:
    test = run.get("test_resultaat")
    return len(run) + (len(test) if isinstance(test, dict) else 0)


def verzamel(resultaten: Path) -> dict:
    """Verzamelt runs, walk-forward-totalen en extra's uit alle JSON-bestanden in ``resultaten``."""
    beste: dict[tuple, tuple] = {}
    totalen: dict[str, dict] = {}
    extra: dict[str, dict] = {}
    bestanden = sorted(p for p in Path(resultaten).glob("*.json") if p.name != LIVE_BESTAND)
    for pad in bestanden:
        inhoud = _lees_json(pad)
        if not isinstance(inhoud, dict):
            continue
        mtime = pad.stat().st_mtime
        if isinstance(inhoud.get("runs"), list):
            formaat, runs, standaard_soort = "runs", inhoud["runs"], None
            for key in ("data", "blind_underdog", "meldingen"):
                if key in inhoud:
                    extra[key] = inhoud[key]
        elif isinstance(inhoud.get("stappen"), list):
            formaat, runs, standaard_soort = "stappen", inhoud["stappen"], "walk-forward"
            if isinstance(inhoud.get("totaal_test"), dict):
                totalen[str(inhoud.get("model", "?"))] = inhoud["totaal_test"]
        elif _is_run(inhoud):
            formaat, runs, standaard_soort = "los", [inhoud], "richting"
        else:
            continue
        for run in runs:
            if not _is_run(run):
                continue
            run = dict(run)
            run.setdefault("soort", standaard_soort or "richting")
            run["_bron"] = pad.name
            rang = (FORMAAT_PRIO[formaat], _rijkdom(run), mtime)
            sleutel = run_sleutel(run)
            if sleutel not in beste or rang >= beste[sleutel][0]:
                beste[sleutel] = (rang, run)
    runs = [r for _, r in beste.values()]
    runs.sort(key=lambda r: (_soort_index(r["soort"]), str(r["model"]), _jaren(r["test"]), _jaren(r["train"])))
    return {"runs": runs, "totalen": totalen, "extra": extra}


def _soort_index(soort: str) -> int:
    return SOORT_VOLGORDE.index(soort) if soort in SOORT_VOLGORDE else len(SOORT_VOLGORDE)


def lees_live(resultaten: Path):
    pad = Path(resultaten) / LIVE_BESTAND
    if not pad.exists():
        return None
    inhoud = _lees_json(pad)
    if not isinstance(inhoud, dict) or not isinstance(inhoud.get("wedstrijden", []), list):
        return None
    return inhoud


# --------------------------------------------------------------------------- opmaak

def e(tekst) -> str:
    return html.escape(str(tekst), quote=True)


def _getal(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def fmt(x, cijfers: int = 4) -> str:
    return f"{x:.{cijfers}f}".replace("-", MIN) if _getal(x) else STREEP


def fmt_teken(x, cijfers: int = 4) -> str:
    return (f"{x:+.{cijfers}f}".replace("-", MIN)) if _getal(x) else STREEP


def pct(x, cijfers: int = 1) -> str:
    return f"{x * 100:+.{cijfers}f}%".replace("-", MIN) if _getal(x) else STREEP


def interval(iv) -> str:
    if isinstance(iv, (list, tuple)) and len(iv) == 2 and all(_getal(v) for v in iv):
        return f"[{pct(iv[0])}, {pct(iv[1])}]"
    return STREEP


def jaren_label(jaren) -> str:
    j = _jaren(jaren)
    return "+".join(str(x) for x in j) if j else STREEP


def run_label(run: dict) -> str:
    return f"{run.get('model')} · {jaren_label(run.get('train'))} → {jaren_label(run.get('test'))}"


def soort_label(soort: str) -> str:
    return SOORT_LABEL.get(soort, str(soort).capitalize())


def parameters_label(par) -> str:
    if not isinstance(par, dict) or not par:
        return STREEP
    return ", ".join(f"{k}={v}" for k, v in par.items())


def oordeel(test: dict) -> str:
    m, k = test.get("logloss_model"), test.get("logloss_markt_proportioneel")
    if not (_getal(m) and _getal(k)):
        return ""
    if m < k:
        return '<span class="badge goed">model beter</span>'
    if m > k:
        return '<span class="badge slecht">markt wint</span>'
    return '<span class="badge">gelijk</span>'


# --------------------------------------------------------------------------- tabellen

def _rij(label_cellen: list[str], test: dict, run: dict | None) -> str:
    m, k = test.get("logloss_model"), test.get("logloss_markt_proportioneel")
    verschil = m - k if _getal(m) and _getal(k) else None
    bets = test.get("bets")
    bets_txt = str(bets) if _getal(bets) else STREEP
    if _getal(bets) and _getal(test.get("underdog_bets")):
        bets_txt += f" ({test['underdog_bets']} underdog)"
    if run is not None:
        drempel = run.get("drempel")
        drempel_txt = fmt(drempel, 2) if _getal(drempel) else ("niet wedden" if "drempel" in run else STREEP)
        reden = e(run.get("drempel_reden", STREEP))
    else:
        drempel_txt, reden = e(test.get("drempel", STREEP)), ""
    cellen = label_cellen + [
        e(test.get("n", STREEP)),
        f"<strong>{fmt(m)}</strong>",
        f"{fmt(k)}<br><small>Shin {fmt(test.get('logloss_markt_shin'))}</small>",
        f"{fmt_teken(verschil)} {oordeel(test)}",
        f"{fmt(test.get('brier_model'))}",
        f"{fmt(test.get('brier_markt_proportioneel'))}<br><small>Shin {fmt(test.get('brier_markt_shin'))}</small>",
        bets_txt,
        pct(test.get("roi")),
        interval(test.get("roi_90_geclusterd")),
        drempel_txt,
        f"<small>{reden}</small>",
    ]
    tds = [f"<td>{c}</td>" for c in cellen]
    tds[-1] = tds[-1].replace("<td>", '<td class="reden">', 1)
    return "<tr>" + "".join(tds) + "</tr>"


KOPPEN = ["Model", "Train", "Test-WK", "n", "Log-loss model", "Log-loss markt (prop.)", "Verschil (model − markt)",
          "Brier model", "Brier markt (prop.)", "Bets", "ROI", "90%-interval ROI", "Drempel", "Reden"]


def tabel_kerncijfers(runs: list[dict], totalen: dict) -> str:
    if not runs:
        return '<p class="melding">Geen resultaten gevonden in <code>resultaten/</code>.</p>'
    delen = []
    for soort in sorted({r["soort"] for r in runs}, key=_soort_index):
        groep = [r for r in runs if r["soort"] == soort]
        rijen = []
        for run in groep:
            test = run.get("test_resultaat") if isinstance(run.get("test_resultaat"), dict) else {}
            label = [e(run.get("model")), e(jaren_label(run.get("train"))),
                     f"<strong>{e(jaren_label(run.get('test')))}</strong>"]
            rijen.append(_rij(label, test, run))
        if soort == "walk-forward":
            for model in sorted({str(r.get("model")) for r in groep}):
                if model in totalen:
                    rijen.append(_rij([e(model), "per stap", "<strong>Totaal</strong>"], totalen[model], None)
                                 .replace("<tr>", '<tr class="totaal">', 1))
        kop = "".join(f"<th scope=\"col\">{e(k)}</th>" for k in KOPPEN)
        delen.append(
            f"<h3>{e(soort_label(soort))}</h3>\n<div class=\"tabel-wrap\"><table>\n<thead><tr>{kop}</tr></thead>\n"
            f"<tbody>\n" + "\n".join(rijen) + "\n</tbody></table></div>")
        params = "".join(f"<li>{e(run_label(r))}: {e(parameters_label(r.get('parameters')))}</li>" for r in groep)
        delen.append(f"<details><summary>Parameters</summary><ul>{params}</ul></details>")
    return "\n".join(delen)


def _waarde(v) -> str:
    if isinstance(v, float):
        return fmt(v)
    if isinstance(v, (list, tuple)) and all(not isinstance(x, (dict, list)) for x in v):
        return e(", ".join(str(x) for x in v))
    if isinstance(v, (dict, list)):
        return f"<code>{e(json.dumps(v, ensure_ascii=False))}</code>"
    return e(v)


def tabel_generiek(titel: str, obj) -> str:
    """Toont een dict (eventueel dict van dicts) als tabel; anders als JSON."""
    if isinstance(obj, dict) and obj and all(isinstance(v, dict) for v in obj.values()):
        kolommen: list[str] = []
        for v in obj.values():
            kolommen += [k for k in v if k not in kolommen]
        kop = "<th></th>" + "".join(f"<th scope=\"col\">{e(k)}</th>" for k in kolommen)
        rijen = "".join(
            f"<tr><th scope=\"row\">{e(n)}</th>" + "".join(f"<td>{_waarde(v.get(k, STREEP))}</td>" for k in kolommen)
            + "</tr>" for n, v in obj.items())
        inhoud = f"<div class=\"tabel-wrap\"><table><thead><tr>{kop}</tr></thead><tbody>{rijen}</tbody></table></div>"
    elif isinstance(obj, dict):
        rijen = "".join(f"<tr><th scope=\"row\">{e(k)}</th><td>{_waarde(v)}</td></tr>" for k, v in obj.items())
        inhoud = f"<div class=\"tabel-wrap\"><table><tbody>{rijen}</tbody></table></div>"
    elif isinstance(obj, list):
        inhoud = "<ul>" + "".join(f"<li>{_waarde(x)}</li>" for x in obj) + "</ul>"
    else:
        inhoud = f"<p>{_waarde(obj)}</p>"
    return f"<h3>{e(titel)}</h3>\n{inhoud}"


# --------------------------------------------------------------------------- grafieken (inline SVG)

def _schaal(lo: float, hi: float, a: float, b: float):
    if hi == lo:
        hi = lo + 1
    return lambda v: a + (v - lo) / (hi - lo) * (b - a)


def _ticks(lo: float, hi: float, aantal: int = 5) -> list[float]:
    stap_ruw = (hi - lo) / max(aantal, 1) or 1
    macht = 10 ** math.floor(math.log10(stap_ruw))
    stap = next(m * macht for m in (1, 2, 2.5, 5, 10) if m * macht >= stap_ruw)
    eerste = math.ceil(lo / stap) * stap
    uit, v = [], eerste
    while v <= hi + 1e-12:
        uit.append(round(v, 10))
        v += stap
    return uit


def _rijen_grafiek(runs: list[dict]) -> list[tuple[str, dict]]:
    uit = []
    for run in runs:
        test = run.get("test_resultaat")
        if isinstance(test, dict):
            uit.append((f"{run['soort']} · {run_label(run)}", test))
    return uit


def svg_logloss(runs: list[dict]) -> str:
    rijen = [(l, t) for l, t in _rijen_grafiek(runs)
             if _getal(t.get("logloss_model")) and _getal(t.get("logloss_markt_proportioneel"))]
    if not rijen:
        return '<p class="melding">Geen log-loss-cijfers beschikbaar.</p>'
    waarden = [t[k] for _, t in rijen for k in ("logloss_model", "logloss_markt_proportioneel")]
    lo, hi = min(waarden), max(waarden)
    marge = (hi - lo) * 0.15 or 0.01
    lo, hi = lo - marge, hi + marge
    links, rechts, rij_h, boven = 290, 20, 34, 30
    breedte = 760
    hoogte = boven + rij_h * len(rijen) + 30
    x = _schaal(lo, hi, links, breedte - rechts)
    d = [f'<svg viewBox="0 0 {breedte} {hoogte}" role="img" aria-labelledby="ll-titel" class="grafiek">',
         '<title id="ll-titel">Log-loss op het test-WK: model tegenover markt (proportioneel). Lager is beter.</title>']
    for t in _ticks(lo, hi):
        xp = x(t)
        d.append(f'<line class="grid" x1="{xp:.1f}" x2="{xp:.1f}" y1="{boven - 8}" y2="{hoogte - 26}"/>')
        d.append(f'<text class="as" x="{xp:.1f}" y="{hoogte - 10}" text-anchor="middle">{fmt(t, 3)}</text>')
    for i, (label, t) in enumerate(rijen):
        y = boven + rij_h * i + rij_h / 2
        m, k = t["logloss_model"], t["logloss_markt_proportioneel"]
        d.append(f'<text class="label" x="{links - 10}" y="{y + 4:.1f}" text-anchor="end">{e(label)}</text>')
        d.append(f'<line class="verbinder" x1="{x(m):.1f}" x2="{x(k):.1f}" y1="{y:.1f}" y2="{y:.1f}"/>')
        d.append(f'<g class="punt"><circle class="markt" cx="{x(k):.1f}" cy="{y:.1f}" r="6">'
                 f'<title>{e(label)}: markt {fmt(k)}</title></circle></g>')
        d.append(f'<g class="punt"><circle class="model" cx="{x(m):.1f}" cy="{y:.1f}" r="6">'
                 f'<title>{e(label)}: model {fmt(m)} (verschil {fmt_teken(m - k)})</title></circle></g>')
    d.append("</svg>")
    legenda = ('<p class="legenda"><span class="sw model"></span>model <span class="sw markt"></span>markt '
               '(proportioneel) · <strong>lager is beter</strong>; staat de oranje stip links, dan wint de markt.</p>')
    return legenda + '<div class="grafiek-wrap">' + "\n".join(d) + "</div>"


def svg_roi(runs: list[dict]) -> str:
    rijen = _rijen_grafiek(runs)
    if not rijen:
        return '<p class="melding">Geen ROI-cijfers beschikbaar.</p>'
    waarden = [0.0]
    for _, t in rijen:
        iv = t.get("roi_90_geclusterd")
        for v in ([t.get("roi")] + (list(iv) if isinstance(iv, (list, tuple)) else [])):
            if _getal(v):
                waarden.append(v)
    lo, hi = min(waarden), max(waarden)
    marge = (hi - lo) * 0.08 or 0.1
    lo, hi = lo - marge, hi + marge
    links, rechts, rij_h, boven, breedte = 290, 20, 34, 30, 760
    hoogte = boven + rij_h * len(rijen) + 30
    x = _schaal(lo, hi, links, breedte - rechts)
    d = [f'<svg viewBox="0 0 {breedte} {hoogte}" role="img" aria-labelledby="roi-titel" class="grafiek">',
         '<title id="roi-titel">ROI op het test-WK met 90%-interval (geclusterde bootstrap).</title>']
    for t in _ticks(lo, hi):
        xp = x(t)
        d.append(f'<line class="grid" x1="{xp:.1f}" x2="{xp:.1f}" y1="{boven - 8}" y2="{hoogte - 26}"/>')
        d.append(f'<text class="as" x="{xp:.1f}" y="{hoogte - 10}" text-anchor="middle">{pct(t, 0)}</text>')
    d.append(f'<line class="nul" x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{boven - 8}" y2="{hoogte - 26}"/>')
    for i, (label, t) in enumerate(rijen):
        y = boven + rij_h * i + rij_h / 2
        d.append(f'<text class="label" x="{links - 10}" y="{y + 4:.1f}" text-anchor="end">{e(label)}</text>')
        roi, iv = t.get("roi"), t.get("roi_90_geclusterd")
        if not _getal(roi):
            reden = "geen bets (stopregel)" if t.get("bets") == 0 else "geen ROI"
            d.append(f'<text class="as" x="{x(0) + 8:.1f}" y="{y + 4:.1f}">{e(reden)}</text>')
            continue
        tip = f"{label}: ROI {pct(roi)}, 90%-int. {interval(iv)}, {t.get('bets', STREEP)} bets"
        if isinstance(iv, (list, tuple)) and len(iv) == 2 and all(_getal(v) for v in iv):
            d.append(f'<line class="interval" x1="{x(iv[0]):.1f}" x2="{x(iv[1]):.1f}" y1="{y:.1f}" y2="{y:.1f}"/>')
            for v in iv:
                d.append(f'<line class="interval" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{y - 6:.1f}" y2="{y + 6:.1f}"/>')
        d.append(f'<g class="punt"><circle class="model" cx="{x(roi):.1f}" cy="{y:.1f}" r="6">'
                 f'<title>{e(tip)}</title></circle></g>')
    d.append("</svg>")
    legenda = ('<p class="legenda"><span class="sw model"></span>ROI bij vaste inzet 1, balk = 90%-interval. '
               'Snijdt de balk de nullijn, dan is er geen aantoonbaar voordeel.</p>')
    return legenda + '<div class="grafiek-wrap">' + "\n".join(d) + "</div>"


def _verloop(run: dict):
    v = run.get("verloop")
    if v is None and isinstance(run.get("test_resultaat"), dict):
        v = run["test_resultaat"].get("verloop")
    if isinstance(v, list) and v and all(_getal(x) for x in v):
        return v
    return None


def svg_verloop(runs: list[dict]) -> str:
    lijnen = [(run_label(r) + f" ({r['soort']})", _verloop(r)) for r in runs if _verloop(r)][:8]
    if not lijnen:
        return ('<p class="melding">Geen winstverloop beschikbaar: de resultaten bevatten (nog) geen '
                '<code>verloop</code> per bet.</p>')
    alle = [0.0] + [v for _, l in lijnen for v in l]
    lo, hi = min(alle), max(alle)
    marge = (hi - lo) * 0.08 or 1
    lo, hi = lo - marge, hi + marge
    n_max = max(len(l) for _, l in lijnen)
    links, rechts, boven, onder, breedte, hoogte = 56, 20, 16, 36, 720, 300
    x = _schaal(0, n_max, links, breedte - rechts)
    y = _schaal(lo, hi, hoogte - onder, boven)
    d = [f'<svg viewBox="0 0 {breedte} {hoogte}" role="img" aria-labelledby="vl-titel" class="grafiek">',
         '<title id="vl-titel">Cumulatieve winst in units per bet op het test-WK.</title>']
    for t in _ticks(lo, hi):
        d.append(f'<line class="grid" x1="{links}" x2="{breedte - rechts}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>')
        d.append(f'<text class="as" x="{links - 6}" y="{y(t) + 4:.1f}" text-anchor="end">{fmt(t, 0)}</text>')
    for t in _ticks(0, n_max):
        if t == int(t):
            d.append(f'<text class="as" x="{x(t):.1f}" y="{hoogte - onder + 16}" text-anchor="middle">{int(t)}</text>')
    d.append(f'<text class="as" x="{breedte - rechts}" y="{hoogte - 4}" text-anchor="end">bet nr.</text>')
    d.append(f'<line class="nul" x1="{links}" x2="{breedte - rechts}" y1="{y(0):.1f}" y2="{y(0):.1f}"/>')
    legenda = []
    for i, (label, l) in enumerate(lijnen):
        punten = " ".join(f"{x(j):.1f},{y(v):.1f}" for j, v in enumerate([0.0] + l))
        d.append(f'<polyline class="lijn s{i + 1}" points="{punten}"><title>{e(label)}: eindstand '
                 f'{fmt(l[-1], 2)} units na {len(l)} bets</title></polyline>')
        legenda.append(f'<span class="sw s{i + 1}"></span>{e(label)}')
    d.append("</svg>")
    return ('<p class="legenda">' + " ".join(legenda) + '</p>\n<div class="grafiek-wrap">' + "\n".join(d)
            + "</div>")


# --------------------------------------------------------------------------- live

def _logloss(p: float, uitkomst: int) -> float:
    p = min(max(p, 1e-12), 1 - 1e-12)
    return -math.log(p if uitkomst == 1 else 1 - p)


def sectie_live(live) -> str:
    if not live or not live.get("wedstrijden"):
        return f'<p class="melding">{e(LIVE_LEEG)}</p>'
    wedstrijden = live["wedstrijden"]
    gespeeld = [w for w in wedstrijden if w.get("winnaar") in (1, 2)]
    ll_model = [_logloss(w["kans_model"], w["winnaar"]) for w in gespeeld if _getal(w.get("kans_model"))]
    ll_markt = [_logloss(w["kans_markt"], w["winnaar"]) for w in gespeeld if _getal(w.get("kans_markt"))]
    winst, bets = 0.0, 0
    for w in gespeeld:
        if w.get("bet") in (1, 2):
            odd = w.get(f"odd{w['bet']}")
            if _getal(odd):
                bets += 1
                winst += (odd - 1) if w["bet"] == w["winnaar"] else -1
    samenvatting = [
        f"{len(gespeeld)} van {len(wedstrijden)} wedstrijden gespeeld",
        f"log-loss model {fmt(sum(ll_model) / len(ll_model)) if ll_model else STREEP}",
        f"markt {fmt(sum(ll_markt) / len(ll_markt)) if ll_markt else STREEP}",
        f"{bets} bets, winst {fmt_teken(winst, 2) if bets else STREEP} units"
        + (f" (ROI {pct(winst / bets)})" if bets else ""),
    ]
    rijen = []
    for w in sorted(wedstrijden, key=lambda w: str(w.get("datum", ""))):
        uitslag = STREEP
        if w.get("winnaar") in (1, 2):
            sets = f"{w.get('sets1')}–{w.get('sets2')}" if _getal(w.get("sets1")) and _getal(w.get("sets2")) else ""
            uitslag = f"{e(w.get('speler' + str(w['winnaar']), '?'))} wint {e(sets)}".strip()
        bet = e(w.get(f"speler{w['bet']}", w["bet"])) if w.get("bet") in (1, 2) else STREEP
        cellen = [e(w.get("datum", STREEP)), e(w.get("ronde", STREEP)),
                  f"{e(w.get('speler1', '?'))} – {e(w.get('speler2', '?'))}",
                  fmt(w.get("kans_model"), 3), fmt(w.get("kans_markt"), 3),
                  f"{fmt(w.get('odd1'), 2)} / {fmt(w.get('odd2'), 2)}", bet, uitslag]
        rijen.append("<tr>" + "".join(f"<td>{c}</td>" for c in cellen) + "</tr>")
    kop = "".join(f"<th scope=\"col\">{k}</th>" for k in
                  ["Datum", "Ronde", "Wedstrijd", "Kans speler 1 (model)", "Kans speler 1 (markt)", "Odds",
                   "Bet", "Uitslag"])
    meta = []
    if live.get("model"):
        meta.append(f"model: {e(live['model'])}")
    if live.get("bijgewerkt"):
        meta.append(f"bijgewerkt: {e(live['bijgewerkt'])}")
    return (f"<p>{e('; '.join(samenvatting))}.</p>"
            + (f"<p><small>{' · '.join(meta)}</small></p>" if meta else "")
            + "<p><small>Voorspellingen worden vóór de wedstrijd vastgelegd; kansen gelden voor speler 1.</small></p>"
            + f"<div class=\"tabel-wrap\"><table><thead><tr>{kop}</tr></thead><tbody>{''.join(rijen)}"
            + "</tbody></table></div>")


# --------------------------------------------------------------------------- pagina

CSS = """
:root{color-scheme:light;--bg:#f9f9f7;--vlak:#fcfcfb;--tekst:#0b0b0b;--tekst2:#52514e;--mute:#898781;
--grid:#e1e0d9;--as:#c3c2b7;--rand:rgba(11,11,11,.10);--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;
--s5:#e87ba4;--s6:#008300;--s7:#6250d6;--s8:#e34948;--goed:#006300;--slecht:#d03b3b;--link:#1c5cab}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--bg:#0d0d0d;--vlak:#1a1a19;--tekst:#f0efec;
--tekst2:#c3c2b7;--grid:#2c2c2a;--as:#383835;--rand:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926;
--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9;--s8:#e66767;--goed:#0ca30c;--slecht:#e66767;
--link:#86b6ef}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tekst);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1100px;margin:0 auto;padding:1rem}
a{color:var(--link)}
h1{font-size:1.7rem;margin:.5rem 0}
h2{margin-top:2rem;border-bottom:1px solid var(--grid);padding-bottom:.25rem}
.disclaimer{background:var(--vlak);border:1px solid var(--rand);border-left:4px solid var(--slecht);
padding:.6rem .9rem;border-radius:4px}
section{background:var(--vlak);border:1px solid var(--rand);border-radius:6px;padding:0 1rem 1rem;margin:1rem 0}
.tabel-wrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:.88rem;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:.35rem .5rem;border-bottom:1px solid var(--grid);vertical-align:top}
th{color:var(--tekst2);font-weight:600}
tr.totaal td{font-weight:600;border-top:2px solid var(--as)}
small{color:var(--tekst2)}
.badge{display:inline-block;font-size:.75rem;padding:0 .4rem;border-radius:3px;border:1px solid currentColor;
white-space:nowrap}
.badge.goed{color:var(--goed)}.badge.slecht{color:var(--slecht)}
.badge.goed::before{content:"▲ "}.badge.slecht::before{content:"▼ "}
.melding{color:var(--tekst2);font-style:italic}
.grafiek{width:100%;min-width:600px;height:auto;display:block}
.grafiek-wrap{overflow-x:auto}
td.reden{min-width:14em}
.grafiek text{font-size:12px;fill:var(--tekst2)}
.grafiek text.label{fill:var(--tekst)}
.grafiek .grid{stroke:var(--grid);stroke-width:1}
.grafiek .nul{stroke:var(--as);stroke-width:1.5}
.grafiek .verbinder{stroke:var(--as);stroke-width:2}
.grafiek .interval{stroke:var(--tekst2);stroke-width:2;stroke-linecap:round}
.grafiek circle{stroke:var(--vlak);stroke-width:2}
.grafiek circle.model{fill:var(--s1)}.grafiek circle.markt{fill:var(--s2)}
.grafiek .punt:hover circle{r:8}
.grafiek .lijn{fill:none;stroke-width:2;stroke-linejoin:round}
.legenda{font-size:.88rem;color:var(--tekst2)}
.sw{display:inline-block;width:.8em;height:.8em;border-radius:50%;margin:0 .3em 0 .6em;vertical-align:-.05em}
.sw.model{background:var(--s1)}.sw.markt{background:var(--s2)}
""" + "".join(f".lijn.s{i}{{stroke:var(--s{i})}}.sw.s{i}{{background:var(--s{i})}}" for i in range(1, 9)) + """
footer{color:var(--mute);font-size:.85rem;margin:2rem 0 1rem}
@media (max-width:600px){main{padding:.5rem}section{padding:0 .6rem .6rem}h1{font-size:1.35rem}}
"""


def sectie_methode(runs: list[dict]) -> str:
    punten = [
        "<strong>Vormmodel</strong>: recente three-dart average en checkout% van vóór het toernooi (Dartsorakel, "
        "alle wedstrijden tot en met de dag vóór het WK), <code>vorm = w·waarde(3 mnd) + (1−w)·waarde(L mnd)</code> "
        "met L ∈ {6, 12}.",
        "<strong>Kans per leg</strong> voor de speler die begint: "
        "<code>logistic(logit(0.60) + k·(avgA−avgB) + kc·(coA−coB))</code>.",
        "<strong>Set/match-DP</strong>: de wedstrijdkans volgt exact uit het WK-format (sets first to 3 legs, "
        "beslissende set met twee legs verschil en sudden death bij 5-5, wisselende beginner, gemiddeld over wie de "
        "bull wint). Het aantal sets volgt uit de ronde (R1/R2 3, R3/R4 4, QF 5, SF 6, F 7).",
        "<strong>Margecorrectie</strong>: slotodds van Oddsportal (gemiddelde over bookmakers); de marge gaat eruit "
        "met proportionele normalisatie (de benchmark) en daarnaast met Shin.",
        "<strong>Afstemmen en stopregel</strong>: grid search over w, L, k, kc op log-loss (train); daarna de drempel "
        "<code>eigen kans × odd &gt; drempel</code> met de hoogste ROI op train (min. 10 bets). Is die ROI ≤ 0, dan "
        "wordt er niet gewed.",
        "<strong>Toetsen</strong>: ongewijzigd op het testjaar met Brier, log-loss en ROI bij vaste inzet 1; het "
        "90%-interval van de ROI komt uit een bootstrap die per ronde (jaar, ronde) resamplet.",
        "<strong>Walk-forward</strong>: voor elk jaar t afstemmen op alle jaren vóór t en toetsen op t. Bij de vaste "
        "richting 2026 → 2025 bevat het 12-maandenvenster van 2026 het WK 2025 zelf; walk-forward heeft dat "
        "probleem niet.",
    ]
    andere = sorted({str(r.get("model")) for r in runs} - {"vorm"})
    if andere:
        punten.append("De resultaten bevatten ook " + ", ".join(f"<code>{e(m)}</code>" for m in andere)
                      + "-model(len); zie de <a href=\"" + REPO_URL + "#readme\">README</a> voor de opzet.")
    return ("<ul>" + "".join(f"<li>{p}</li>" for p in punten) + "</ul>"
            f'<p>Bron: <a href="{REPO_URL}#readme">README</a>. Alle cijfers komen uit <code>resultaten/</code>.</p>')


def sectie_bronnen() -> str:
    wiki = "".join(
        f'<li><a href="https://en.wikipedia.org/wiki/{j}_PDC_World_Darts_Championship">{j} PDC World Darts '
        f'Championship</a> (Wikipedia, CC BY-SA 4.0): uitslagen en rondes</li>' for j in (2024, 2025, 2026))
    return ("<ul>" + wiki
            + '<li><a href="https://www.oddsportal.com/">Oddsportal</a>: slotodds (niet herverspreid)</li>'
            '<li><a href="https://dartsorakel.com/">Dartsorakel</a>: spelersstatistieken en eventuitslagen '
            "(niet herverspreid)</li>"
            f'<li><a href="{REPO_URL}/blob/main/docs/review-claude.md">Review (docs/review-claude.md)</a></li>'
            "</ul>")


def bouw_html(verzameld: dict, live, nu: dt.datetime | None = None, sha: str | None = None) -> str:
    runs, totalen, extra = verzameld["runs"], verzameld["totalen"], verzameld["extra"]
    nu = nu or dt.datetime.now(dt.timezone.utc)
    if sha:
        commit = f'commit <a href="{REPO_URL}/commit/{e(sha)}"><code>{e(sha[:7])}</code></a>'
    else:
        commit = "commit onbekend (lokaal gebouwd)"
    extra_html = ""
    titels = {"data": "Gegevens per WK", "blind_underdog": "Vergelijking: blind op de underdog",
              "meldingen": "Meldingen"}
    if extra:
        extra_html = ("<section><h2>Aanvullende vergelijking</h2>"
                      + "\n".join(tabel_generiek(titels[k], v) for k, v in extra.items()) + "</section>")
    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Darts-WK-model: tussenstanden</title>
<style>{CSS}</style>
</head>
<body>
<main>
<header>
<h1>Darts-WK-model: tussenstanden</h1>
<p class="disclaimer"><strong>{e(DISCLAIMER)}</strong> Code en methode: <a href="{REPO_URL}">{e(REPO_URL)}</a>.</p>
</header>

<section>
<h2>Kerncijfers per test-WK</h2>
<p>Log-loss en Brier: <strong>lager is beter</strong>. Verschil = model − markt; positief betekent dat de markt
beter voorspelt (<span class="badge slecht">markt wint</span>). Markt = slotodds met proportionele margecorrectie;
Shin klein eronder. ROI bij vaste inzet 1 met 90%-interval (bootstrap per ronde). Drempel en reden komen uit de
train-jaren.</p>
{tabel_kerncijfers(runs, totalen)}
</section>

<section>
<h2>Grafieken</h2>
<h3>Log-loss: model tegenover markt</h3>
{svg_logloss(runs)}
<h3>ROI met 90%-interval</h3>
{svg_roi(runs)}
<h3>Winstverloop</h3>
{svg_verloop(runs)}
</section>
{extra_html}
<section>
<h2>WK 2026/27 live</h2>
{sectie_live(live)}
</section>

<section>
<h2>Methode</h2>
{sectie_methode(runs)}
</section>

<section>
<h2>Bronnen</h2>
{sectie_bronnen()}
</section>

<footer>
<p>{e(DISCLAIMER)}</p>
<p>Gegenereerd op {e(nu.strftime("%Y-%m-%d %H:%M %Z").strip())} · {commit} ·
<a href="data.json">data.json</a></p>
</footer>
</main>
</body>
</html>
"""


def main(argv=None) -> int:
    basis = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--resultaten", type=Path, default=basis / "resultaten")
    parser.add_argument("--uit", type=Path, default=basis / "site")
    args = parser.parse_args(argv)

    verzameld = verzamel(args.resultaten)
    live = lees_live(args.resultaten)
    sha = os.environ.get("GITHUB_SHA") or None
    nu = dt.datetime.now(dt.timezone.utc)
    args.uit.mkdir(parents=True, exist_ok=True)
    (args.uit / "index.html").write_text(bouw_html(verzameld, live, nu, sha), encoding="utf-8")
    data = {"gegenereerd": nu.isoformat(timespec="seconds"), "commit": sha, **verzameld, "live": live}
    (args.uit / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(verzameld['runs'])} runs → {args.uit / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
