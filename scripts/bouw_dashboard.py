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
import re
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
    overslaan = (LIVE_BESTAND, EXPERIMENTEN_BESTAND)
    bestanden = sorted(p for p in Path(resultaten).glob("*.json") if p.name not in overslaan)
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


# --------------------------------------------------------------------------- experimenten en inhoud

EXPERIMENTEN_BESTAND = "experimenten.json"
KERNMODELLEN = ["E001", "E006", "E007", "E009", "E014", "E015", "E017", "E020"]   # kalibratieplots
ROI_MODELLEN = ["E003", "E004", "E002", "E006", "E009", "E014", "E015", "E020"]   # winstverloop
VRIENDEN_LEEG = "Komt later: een eenvoudige pagina voor vrienden met de voorspellingen per speeldag."


def lees_experimenten(resultaten: Path):
    pad = Path(resultaten) / EXPERIMENTEN_BESTAND
    inhoud = _lees_json(pad) if pad.exists() else None
    if not isinstance(inhoud, dict) or not isinstance(inhoud.get("resultaten"), list):
        return None
    return inhoud


def lees_inhoud(map_: Path) -> dict:
    uit = {}
    for naam in ("aanbeveling", "sentiment", "onderzoek", "ideeen", "roadmap"):
        pad = Path(map_) / f"{naam}.json"
        uit[naam] = _lees_json(pad) if pad.exists() else None
    return uit


def _wf(res: dict) -> list[dict]:
    """Walk-forward-uitkomsten met een vergelijking met de markt (niet E027/E028, die hebben een eigen vorm)."""
    return [u for u in res.get("uitkomsten", []) if u.get("soort") == "walk-forward" and "verschil_markt" in u]


def _reg(exp: dict) -> dict:
    return {x["id"]: x for x in exp.get("register", [])}


def _naam(reg: dict, id_: str) -> str:
    x = reg.get(id_, {})
    return f"{id_} {x.get('naam', x.get('model', ''))}".strip()


def _oordeel_ruis(u: dict) -> str:
    r = u.get("ruis", "")
    klasse = {"beter dan de markt": "goed", "slechter dan de markt": "slecht"}.get(r, "")
    return f'<span class="badge {klasse}">{e(r)}</span>' if r else STREEP


def sectie_aanbeveling(inh) -> str:
    if not isinstance(inh, dict):
        return '<p class="melding">Nog geen aanbeveling (inhoud/aanbeveling.json ontbreekt).</p>'
    punten = "".join(f"<li>{e(p)}</li>" for p in inh.get("punten", []))
    meta = f"<p><small>bijgewerkt: {e(inh['bijgewerkt'])}</small></p>" if inh.get("bijgewerkt") else ""
    return f"<h3>{e(inh.get('titel', 'Huidige aanbeveling'))}</h3><ul>{punten}</ul>{meta}"


def sectie_samenvatting(exp) -> str:
    if not exp:
        return '<p class="melding">Nog geen experimenten gedraaid (<code>dartswk experimenten</code>).</p>'
    reg = _reg(exp)
    per_jaar: dict = {}
    for res in exp["resultaten"]:
        if res.get("status") != "ok" or reg.get(res["id"], {}).get("soort") == "controle":
            continue
        for u in _wf(res):
            j = u["test"][0]
            if j not in per_jaar or u["logloss"] < per_jaar[j][1]["logloss"]:
                per_jaar[j] = (res["id"], u)
    rijen = []
    for j in sorted(per_jaar):
        id_, u = per_jaar[j]
        rijen.append(f"<tr><td><strong>{j}</strong></td><td>{e(_naam(reg, id_))}</td><td>{fmt(u['logloss'])}</td>"
                     f"<td>{fmt(u['logloss_markt'])}</td><td>{fmt_teken(u['verschil_markt'])} ± "
                     f"{fmt(u['verschil_se'])}</td><td>{_oordeel_ruis(u)}</td></tr>")
    tabel = ('<div class="tabel-wrap"><table><thead><tr><th>Test-WK</th><th>Beste model (laagste log-loss)</th>'
             '<th>Log-loss</th><th>Markt</th><th>Δ vs markt ± se</th><th>Oordeel</th></tr></thead><tbody>'
             + "".join(rijen) + "</tbody></table></div>")
    uitleg = ("<p><strong>In gewone woorden:</strong> per WK staat hier het model dat achteraf het best voorspelde "
              "(walk-forward: alleen afgestemd op eerdere WK's). Log-loss meet hoe goed de kansen waren; lager is "
              "beter. Δ is het verschil met de bookmakers. Is het verschil kleiner dan twee keer de standaardfout, dan "
              "is het <em>binnen de ruis</em>: met ongeveer 100 wedstrijden per WK is het dan niet te onderscheiden "
              "van toeval. Let op: 'het beste van ruim twintig modellen' kiezen is zelf al een vorm van geluk "
              "(meervoudig testen).</p>")
    return tabel + uitleg


def _ci_tekst(c) -> str:
    return interval(c) if c else STREEP


def _exp_rij(reg, res, u) -> str:
    x = reg.get(res["id"], {})
    status = res.get("status")
    klasse = "" if status == "ok" else ' class="mislukt"'
    ruw = str(x.get("hypothese", ""))
    hyp, kort = e(ruw), e(ruw if len(ruw) < 90 else ruw[:87] + "…")
    b = res.get("beoordeling") or {}
    crit = {True: '<span class="badge goed">gehaald</span>', False: '<span class="badge slecht">niet gehaald</span>'}
    crit_txt = crit.get(b.get("succes"), "n.v.t.")
    vlag = ""
    if x.get("na_test_aangepast", {}).get("waarde"):
        vlag += ' <span class="badge" title="na het zien van testcijfers aangepast">aangepast</span>'
    if x.get("test_vooraf_bekend"):
        vlag += ' <span class="badge" title="testcijfers waren al bekend vóór registratie">vooraf bekend</span>'
    if status != "ok":
        cel = f'<td colspan="9"><span class="badge slecht">{e(status)}</span> {e(res.get("fout", ""))}</td>'
        return (f"<tr{klasse}><td>{e(res['id'])}</td><td>{e(x.get('naam', res.get('model')))}{vlag}</td>"
                f'<td title="{hyp}">{kort}</td>{cel}<td>{crit_txt}</td></tr>')
    h = u.get("helling")
    split = f"{jaren_label(u['train'])} → {u['test'][0]}"
    if "verschil_naief" in u:  # E028: setstanden, vergelijking met een naïeve verdeling
        d, se = u["verschil_naief"], u["verschil_se"]
        oord = "binnen de ruis" if abs(d) <= 2 * se else ("beter dan naïef" if d < 0 else "slechter dan naïef")
        cellen = [f'<td data-s="{e(split)}">{e(split)}</td>',
                  f'<td data-s="{u["logloss_dp"]}" title="log-loss van de exacte setstand">{fmt(u["logloss_dp"])}</td>',
                  f'<td data-s="{d}" title="set-DP − binomiaal (niet t.o.v. de markt)">{fmt_teken(d)} ± {fmt(se)} '
                  "(vs naïef)</td>", f"<td>{e(oord)}</td>"] + [f"<td>{STREEP}</td>"] * 5
        return (f"<tr{klasse}><td>{e(res['id'])}</td><td>{e(x.get('naam', res.get('model')))}{vlag}</td>"
                f'<td title="{hyp}">{kort}</td>' + "".join(cellen) + f"<td>{crit_txt}</td></tr>")
    if "kelly" in u:  # E027: inzetbeleid, zie de euro-simulatie
        r1 = u["vast_1"] / u["bets"] if u["bets"] else None
        cellen = [f'<td data-s="{e(split)}">{e(split)}</td>', f"<td>{STREEP}</td>",
                  '<td><a href="#inzet">euro-simulatie</a></td>'] + [f"<td>{STREEP}</td>"] * 3 + [
                  f'<td data-s="{u["bets"]}">{u["bets"]}</td>',
                  f'<td data-s="{r1 if _getal(r1) else ""}">{pct(r1)}</td>', f"<td>{STREEP}</td>"]
        return (f"<tr{klasse}><td>{e(res['id'])}</td><td>{e(x.get('naam', res.get('model')))}{vlag}</td>"
                f'<td title="{hyp}">{kort}</td>' + "".join(cellen) + f"<td>{crit_txt}</td></tr>")
    cellen = [
        f'<td data-s="{e(split)}">{e(split)}</td>',
        f'<td data-s="{u["logloss"]}">{fmt(u["logloss"])}</td>',
        f'<td data-s="{u["verschil_markt"]}">{fmt_teken(u["verschil_markt"])} ± {fmt(u["verschil_se"])}</td>',
        f'<td>{_oordeel_ruis(u)}</td>',
        f'<td data-s="{u["brier"]}">{fmt(u["brier"])}</td>',
        f'<td data-s="{h if _getal(h) else ""}">{fmt(h, 2)}</td>',
        f'<td data-s="{u["bets"]}">{u["bets"]}</td>',
        f'<td data-s="{u["roi"] if _getal(u.get("roi")) else ""}">{pct(u.get("roi"))}</td>',
        f'<td>{_ci_tekst(u.get("roi_90"))}' + (f' <small>({u["clusters"]} cl.)</small>' if u.get("clusters") else "")
        + "</td>",
    ]
    return (f"<tr{klasse}><td>{e(res['id'])}</td><td>{e(x.get('naam', res.get('model')))}{vlag}</td>"
            f'<td title="{hyp}">{kort}</td>' + "".join(cellen) + f"<td>{crit_txt}</td></tr>")


EXP_KOPPEN = ["Id", "Model", "Hypothese (vooraf)", "Train → test", "Log-loss", "Δ vs markt ± se", "Oordeel",
              "Brier", "Helling", "Bets", "ROI", "90%-int. ROI", "Criterium"]


def _exp_tabel(exp, soort: str) -> str:
    reg = _reg(exp)
    rijen = []
    for res in exp["resultaten"]:
        us = [u for u in res.get("uitkomsten", []) if u.get("soort") == soort]
        if res.get("status") != "ok":
            if soort == "walk-forward":
                rijen.append(_exp_rij(reg, res, None))
            continue
        rijen += [_exp_rij(reg, res, u) for u in us]
    kop = "".join(f'<th scope="col"><button type="button" class="sorteer">{e(k)}</button></th>' for k in EXP_KOPPEN)
    return (f'<div class="tabel-wrap"><table class="sorteerbaar"><thead><tr>{kop}</tr></thead><tbody>'
            + "\n".join(rijen) + "</tbody></table></div>")


def sectie_experimenten(exp) -> str:
    if not exp:
        return '<p class="melding">Geen <code>resultaten/experimenten.json</code>.</p>'
    return ("<p>Alle experimenten uit <code>experimenten/register.json</code>. Klik op een kolomkop om te sorteren. "
            "Rood gemarkeerde rijen zijn mislukt of niet gedraaid. 'Oordeel': binnen de ruis als |Δ| ≤ 2 se. "
            "Criterium: zoals vooraf vastgelegd, getoetst op de walk-forward. Labels <em>aangepast</em> en "
            "<em>vooraf bekend</em> markeren experimenten die niet volledig vooraf zijn vastgelegd.</p>"
            "<h3>Walk-forward (hoofdresultaat)</h3>" + _exp_tabel(exp, "walk-forward")
            + "<details><summary>Vaste richtingen (ter vergelijking)</summary>" + _exp_tabel(exp, "richting")
            + "</details>")


def sectie_werkwijze() -> str:
    stappen = [
        "<strong>Hypothese registreren.</strong> Vóór er iets draait, komen model, features, grid, hypothese en een "
        "succescriterium in <code>experimenten/register.json</code>, en dat wordt gecommit.",
        "<strong>Afstemmen op train.</strong> Hyperparameters, kalibratie, regularisatie en de wed-drempel worden "
        "alleen op de trainjaren gekozen. Het testjaar blijft buiten beeld.",
        "<strong>Eén keer toetsen.</strong> Het afgestemde model gaat ongewijzigd naar het testjaar (walk-forward: "
        "2024 → 2025, 2024+2025 → 2026). Daar wordt het vergeleken met de markt.",
        "<strong>Loggen.</strong> Elke run komt in <code>experimenten/runlog.jsonl</code>, ook mislukkingen, met een "
        "vingerafdruk van het register, een hash van config en splits, en de git-commit.",
        "<strong>Beslissen.</strong> Haalt het model het vooraf vastgelegde criterium, dan is het een kandidaat. Zo "
        "niet, dan blijft de markt de maatstaf. Wordt er na het zien van testcijfers iets aangepast, dan komt dat "
        "in <code>na_test_aangepast</code> en wordt het een nieuw experiment.",
    ]
    return ("<ol>" + "".join(f"<li>{x}</li>" for x in stappen) + "</ol>"
            f'<p>Details: <a href="{REPO_URL}/blob/main/docs/protocol.md">docs/protocol.md</a> · kritische review '
            f'van het kader: <a href="{REPO_URL}/blob/main/docs/review-ronde2.md">docs/review-ronde2.md</a>.</p>')


def _inzet_res(exp):
    if not exp:
        return None
    return next((r for r in exp["resultaten"] if r.get("model") == "inzet" and r.get("status") == "ok"), None)


def sectie_inzet(exp) -> str:
    """E027: ¼-Kelly en vaste inzet met weekbudget, in euro's, walk-forward."""
    res = _inzet_res(exp)
    if not res:
        return '<p class="melding">E027 is nog niet gedraaid.</p>'
    g = _reg(exp).get(res["id"], {}).get("grid", {})
    us = sorted([u for u in res["uitkomsten"] if u.get("soort") == "walk-forward"], key=lambda u: u["test"][0])
    rijen = []
    for u in us:
        k = u["kelly"]
        rijen.append(f"<tr><td>WK {u['test'][0]}</td><td>{u['bets']}</td><td>¼-Kelly (start €{k['start']:.0f})</td>"
                     f"<td>€{k['ingezet']:.2f}</td><td>€{k['winst']:+.2f}</td><td>€{k['max_drawdown']:.2f}</td>"
                     f"<td>{STREEP}</td></tr>")
        for w in u["weekbudget"]:
            rijen.append(f"<tr><td>WK {u['test'][0]}</td><td>{w['bets']}"
                         + (f" <small>({w['overgeslagen']} overgeslagen)</small>" if w["overgeslagen"] else "")
                         + f"</td><td>€{w['inzet']:.0f} vast, max €{w['budget']:.0f}/week</td>"
                         f"<td>€{w['ingezet']:.2f}</td><td>€{w['eind']:+.2f}</td><td>€{w['max_drawdown']:.2f}</td>"
                         f"<td>{w['weken_budget_op']} van {len(w['weken'])}</td></tr>")
    tabel = ('<div class="tabel-wrap"><table><thead><tr><th scope="col">Test</th><th scope="col">Bets</th>'
             '<th scope="col">Beleid</th><th scope="col">Ingezet</th><th scope="col">Winst</th>'
             '<th scope="col">Max. drawdown</th><th scope="col">Weken budget op</th></tr></thead><tbody>'
             + "".join(rijen) + "</tbody></table></div>")
    return ("<p>Dezelfde bets als E020 (marktblend, drempel op train) in euro's. Weken lopen van maandag tot en met "
            f"zondag, op speeldatum. Bij vaste inzet gaat er hoogstens €{g.get('weekbudget', 50)} per week in; "
            "past een bet niet meer in het budget, dan valt hij af. Dit zijn twee WK's, dus de winst is vooral ruis.</p>"
            + tabel + svg_inzet_weken(us))


def svg_inzet_weken(us: list[dict]) -> str:
    """Cumulatieve winst per week voor elke vaste inzet; weken van WK 2025 en daarna WK 2026 achter elkaar."""
    if not us or not us[0]["weekbudget"]:
        return ""
    reeksen = []
    for i, w0 in enumerate(us[0]["weekbudget"]):
        labels, waarden, som = [], [], 0.0
        for u in us:
            for wk in u["weekbudget"][i]["weken"]:
                som += wk["winst"]
                labels.append(wk["week"])
                waarden.append(round(som, 2))
        reeksen.append((f"€{w0['inzet']:.0f} vast", labels, waarden))
    n = max(len(l) for _, l, _ in reeksen)
    if not n:
        return ""
    alle = [0.0] + [v for _, _, l in reeksen for v in l]
    lo, hi = min(alle), max(alle)
    marge = (hi - lo) * 0.08 or 1
    lo, hi = lo - marge, hi + marge
    links, rechts, boven, onder, breedte, hoogte = 56, 20, 16, 52, 720, 280
    x = _schaal(0, n, links, breedte - rechts)
    y = _schaal(lo, hi, hoogte - onder, boven)
    d = [f'<svg viewBox="0 0 {breedte} {hoogte}" role="img" aria-labelledby="iw-titel" class="grafiek">',
         '<title id="iw-titel">Cumulatieve winst in euro per week bij vaste inzet met weekbudget, walk-forward.</title>']
    for t in _ticks(lo, hi):
        d.append(f'<line class="grid" x1="{links}" x2="{breedte - rechts}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>')
        d.append(f'<text class="as" x="{links - 6}" y="{y(t) + 4:.1f}" text-anchor="end">€{fmt(t, 0)}</text>')
    for j, lab in enumerate(reeksen[0][1]):
        d.append(f'<text class="as" x="{x(j + 1):.1f}" y="{hoogte - onder + 16}" text-anchor="middle">{e(lab[5:])}</text>')
    d.append(f'<text class="as" x="{breedte - rechts}" y="{hoogte - 4}" text-anchor="end">week (maandag)</text>')
    d.append(f'<line class="nul" x1="{links}" x2="{breedte - rechts}" y1="{y(0):.1f}" y2="{y(0):.1f}"/>')
    legenda = []
    for i, (label, labs, l) in enumerate(reeksen):
        punten = " ".join(f"{x(j):.1f},{y(v):.1f}" for j, v in enumerate([0.0] + l))
        d.append(f'<polyline class="lijn s{i + 1}" points="{punten}"><title>{e(label)}: eind €{l[-1]:+.2f}</title></polyline>')
        legenda.append(f'<li><span class="sw s{i + 1}"></span><strong>{e(label)}</strong>: eind €{l[-1]:+.2f}</li>')
    d.append("</svg>")
    return ('<ul class="legenda lijst">' + "".join(legenda) + '</ul>\n<div class="grafiek-wrap">' + "\n".join(d)
            + "</div>")


def svg_delta(exp) -> str:
    """Dot-plot: Δ log-loss vs markt per experiment en walk-forward-testjaar, foutbalk ±2 se."""
    if not exp:
        return ""
    reg = _reg(exp)
    rijen = []
    for res in exp["resultaten"]:
        if res.get("status") != "ok" or res["id"] == "E001":
            continue
        us = {u["test"][0]: u for u in _wf(res)}
        if us:
            rijen.append((_naam(reg, res["id"]), us))
    if not rijen:
        return ""
    jaren = sorted({j for _, us in rijen for j in us})
    waarden = [0.0] + [u["verschil_markt"] + s * 2 * u["verschil_se"] for _, us in rijen for u in us.values()
                       for s in (-1, 1)]
    lo, hi = min(waarden), max(waarden)
    marge = (hi - lo) * 0.05
    lo, hi = lo - marge, hi + marge
    links, rechts, rij_h, boven, breedte = 300, 20, 30, 20, 760
    hoogte = boven + rij_h * len(rijen) + 30
    x = _schaal(lo, hi, links, breedte - rechts)
    d = [f'<svg viewBox="0 0 {breedte} {hoogte}" role="img" aria-labelledby="dl-titel" class="grafiek">',
         '<title id="dl-titel">Verschil in log-loss met de markt per experiment, walk-forward, ±2 se.</title>']
    for t in _ticks(lo, hi):
        d.append(f'<line class="grid" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{boven - 8}" y2="{hoogte - 26}"/>')
        d.append(f'<text class="as" x="{x(t):.1f}" y="{hoogte - 10}" text-anchor="middle">{fmt_teken(t, 2)}</text>')
    d.append(f'<line class="nul" x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{boven - 8}" y2="{hoogte - 26}"/>')
    for i, (label, us) in enumerate(rijen):
        y0 = boven + rij_h * i + rij_h / 2
        d.append(f'<text class="label" x="{links - 10}" y="{y0 + 4:.1f}" text-anchor="end">{e(label)}</text>')
        for k, j in enumerate(jaren):
            if j not in us:
                continue
            u = us[j]
            y = y0 + (k - (len(jaren) - 1) / 2) * 9
            a, b = u["verschil_markt"] - 2 * u["verschil_se"], u["verschil_markt"] + 2 * u["verschil_se"]
            tip = (f"{label}, WK{j}: Δ {fmt_teken(u['verschil_markt'])} ± {fmt(u['verschil_se'])} (se), "
                   f"{u['ruis']}")
            d.append(f'<g class="punt"><line class="interval s{k + 1}" x1="{x(a):.1f}" x2="{x(b):.1f}" '
                     f'y1="{y:.1f}" y2="{y:.1f}"/><circle class="c{k + 1}" cx="{x(u["verschil_markt"]):.1f}" '
                     f'cy="{y:.1f}" r="5"><title>{e(tip)}</title></circle></g>')
    d.append("</svg>")
    legenda = ('<p class="legenda">' + "".join(f'<span class="sw s{k + 1}"></span>WK {j} ' for k, j in enumerate(jaren))
               + '· balk = ±2 se · <strong>links van de nullijn = beter dan de markt</strong>. Snijdt de balk de '
               'nullijn, dan valt het verschil binnen de ruis.</p>')
    return legenda + '<div class="grafiek-wrap">' + "\n".join(d) + "</div>"


def _bins_samen(us: list[dict]) -> list[dict]:
    """Kalibratiebins van meerdere testjaren samenvoegen (gewogen naar aantal)."""
    uit = []
    for bins in zip(*[u.get("kalibratie", []) for u in us]):
        n = sum(b["n"] for b in bins)
        if n:
            uit.append(dict(van=bins[0]["van"], tot=bins[0]["tot"], n=n,
                            kans=sum(b["kans"] * b["n"] for b in bins if b["n"]) / n,
                            freq=sum(b["freq"] * b["n"] for b in bins if b["n"]) / n))
    return uit


def svg_kalibratie(exp) -> str:
    if not exp:
        return ""
    reg = _reg(exp)
    res_per_id = {r["id"]: r for r in exp["resultaten"] if r.get("status") == "ok"}
    delen = []
    for id_ in KERNMODELLEN:
        if id_ not in res_per_id:
            continue
        bins = _bins_samen(_wf(res_per_id[id_]))
        if not bins:
            continue
        z, m = 220, 34
        x = _schaal(0.5, 1.0, m, z - 10)
        y = _schaal(0.0, 1.0, z - m, 10)
        d = [f'<svg viewBox="0 0 {z} {z}" role="img" class="klein" aria-label="Kalibratie {e(_naam(reg, id_))}">']
        for t in (0.5, 0.75, 1.0):
            d.append(f'<line class="grid" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="10" y2="{z - m}"/>'
                     f'<text class="as" x="{x(t):.1f}" y="{z - m + 14}" text-anchor="middle">{t:g}</text>')
        for t in (0.0, 0.5, 1.0):
            d.append(f'<line class="grid" x1="{m}" x2="{z - 10}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
                     f'<text class="as" x="{m - 4}" y="{y(t) + 4:.1f}" text-anchor="end">{t:g}</text>')
        d.append(f'<line class="nul" x1="{x(0.5):.1f}" y1="{y(0.5):.1f}" x2="{x(1):.1f}" y2="{y(1):.1f}"/>')
        pts = " ".join(f"{x(b['kans']):.1f},{y(b['freq']):.1f}" for b in bins)
        d.append(f'<polyline class="lijn s1" points="{pts}"/>')
        for b in bins:
            r = 3 + min(6, math.sqrt(b["n"]))
            d.append(f'<g class="punt"><circle class="model" cx="{x(b["kans"]):.1f}" cy="{y(b["freq"]):.1f}" '
                     f'r="{r:.1f}"><title>{b["van"]:g}–{b["tot"]:g}: voorspeld {b["kans"]:.3f}, werkelijk '
                     f'{b["freq"]:.3f}, n={b["n"]}</title></circle></g>')
        d.append("</svg>")
        delen.append(f'<figure><figcaption>{e(_naam(reg, id_))}</figcaption>{"".join(d)}</figure>')
    if not delen:
        return ""
    return ('<p class="legenda">Kans van de favoriet volgens het model (x) tegen hoe vaak die favoriet won (y), '
            'walk-forward 2025+2026 samen, 5 bins; grootte van de stip = aantal wedstrijden. Op de diagonaal = '
            'goed gekalibreerd; onder de diagonaal = te stellig.</p><div class="klein-raster">' + "".join(delen)
            + "</div>")


def svg_roi_curves(exp) -> str:
    if not exp:
        return ""
    reg = _reg(exp)
    res_per_id = {r["id"]: r for r in exp["resultaten"] if r.get("status") == "ok"}
    lijnen = []
    for id_ in ROI_MODELLEN:
        if id_ not in res_per_id:
            continue
        us = sorted(_wf(res_per_id[id_]), key=lambda u: u["test"][0])
        verloop, basis = [], 0.0
        for u in us:
            verloop += [basis + v for v in u.get("verloop", [])]
            basis = verloop[-1] if verloop else 0.0
        ci = "; ".join(f"WK{u['test'][0]}: {u['bets']} bets, ROI {pct(u.get('roi'))} {_ci_tekst(u.get('roi_90'))}"
                       for u in us)
        lijnen.append((_naam(reg, id_), verloop, ci))
    lijnen = [l for l in lijnen if l[1]]
    if not lijnen:
        return '<p class="melding">Geen bets in de walk-forward.</p>'
    alle = [0.0] + [v for _, l, _ in lijnen for v in l]
    lo, hi = min(alle), max(alle)
    marge = (hi - lo) * 0.08 or 1
    lo, hi = lo - marge, hi + marge
    n_max = max(len(l) for _, l, _ in lijnen)
    links, rechts, boven, onder, breedte, hoogte = 56, 20, 16, 36, 720, 320
    x = _schaal(0, n_max, links, breedte - rechts)
    y = _schaal(lo, hi, hoogte - onder, boven)
    d = [f'<svg viewBox="0 0 {breedte} {hoogte}" role="img" aria-labelledby="rc-titel" class="grafiek">',
         '<title id="rc-titel">Cumulatieve winst in units per bet, walk-forward 2025 en daarna 2026.</title>']
    for t in _ticks(lo, hi):
        d.append(f'<line class="grid" x1="{links}" x2="{breedte - rechts}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>')
        d.append(f'<text class="as" x="{links - 6}" y="{y(t) + 4:.1f}" text-anchor="end">{fmt(t, 0)}</text>')
    for t in _ticks(0, n_max):
        if t == int(t):
            d.append(f'<text class="as" x="{x(t):.1f}" y="{hoogte - onder + 16}" text-anchor="middle">{int(t)}</text>')
    d.append(f'<text class="as" x="{breedte - rechts}" y="{hoogte - 4}" text-anchor="end">bet nr.</text>')
    d.append(f'<line class="nul" x1="{links}" x2="{breedte - rechts}" y1="{y(0):.1f}" y2="{y(0):.1f}"/>')
    legenda = []
    for i, (label, l, ci) in enumerate(lijnen):
        punten = " ".join(f"{x(j):.1f},{y(v):.1f}" for j, v in enumerate([0.0] + l))
        d.append(f'<polyline class="lijn s{i + 1}" points="{punten}"><title>{e(label)}: {e(ci)}</title></polyline>')
        legenda.append(f'<li><span class="sw s{i + 1}"></span><strong>{e(label)}</strong> — {e(ci)}</li>')
    d.append("</svg>")
    return ('<ul class="legenda lijst">' + "".join(legenda) + '</ul>\n<div class="grafiek-wrap">' + "\n".join(d)
            + "</div><p class=\"legenda\">Inzet 1 per bet; eerst de bets op WK 2025, daarna WK 2026. Het "
            "90%-interval (bootstrap per ronde) staat per WK in de legenda.</p>")


def _inline_md(t: str) -> str:
    t = e(t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{_md_link(m.group(2))}">{m.group(1)}</a>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"<em>\1</em>", t)
    return t


def _md_link(href: str) -> str:
    """Relatieve links naar de repo laten wijzen (de site bevat alleen index.html)."""
    if re.match(r"^https?://", href) or href.startswith("#"):
        return href
    pad = href.lstrip("./").replace("../", "")
    if not pad.startswith(("docs/", "experimenten/", "resultaten/", "data/", "inhoud/")):
        pad = "docs/" + pad
    return f"{REPO_URL}/blob/main/{pad}"


def markdown_html(tekst: str) -> str:
    """Mini-markdown: koppen, lijsten (genummerd en niet), alinea's, links, vet, cursief, code."""
    uit, alinea, lijst = [], [], None

    def sluit():
        nonlocal alinea, lijst
        if alinea:
            uit.append("<p>" + _inline_md(" ".join(alinea)) + "</p>")
            alinea = []
        if lijst:
            uit.append(f"<{lijst[0]}>" + "".join(f"<li>{_inline_md(x)}</li>" for x in lijst[1]) + f"</{lijst[0]}>")
            lijst = None

    for regel in tekst.splitlines():
        s = regel.strip()
        m_kop = re.match(r"^(#{1,4})\s+(.*)$", s)
        m_ul = re.match(r"^[-*]\s+(.*)$", s)
        m_ol = re.match(r"^\d+\.\s+(.*)$", s)
        if not s:
            sluit()
        elif m_kop:
            sluit()
            n = min(len(m_kop.group(1)) + 2, 6)
            uit.append(f"<h{n}>{_inline_md(m_kop.group(2))}</h{n}>")
        elif m_ul or m_ol:
            soort = "ul" if m_ul else "ol"
            if alinea:
                uit.append("<p>" + _inline_md(" ".join(alinea)) + "</p>")
                alinea = []
            if lijst and lijst[0] != soort:
                sluit()
            lijst = lijst or (soort, [])
            lijst[1].append((m_ul or m_ol).group(1))
        elif lijst and regel.startswith(" "):
            lijst[1][-1] += " " + s
        else:
            if lijst:
                sluit()
            alinea.append(s)
    sluit()
    return "\n".join(uit)


def sectie_lijst(inh, leeg: str) -> str:
    items = inh.get("items") if isinstance(inh, dict) else None
    if not items:
        return f'<p class="melding">{e(leeg)}</p>'
    return "<ul>" + "".join(f"<li>{e(x)}</li>" for x in items) + "</ul>"


def sectie_roadmap(inh) -> str:
    items = inh.get("items") if isinstance(inh, dict) else None
    if not items:
        return '<p class="melding">Nog geen roadmap (inhoud/roadmap.json).</p>'
    return ('<ol class="tijdlijn">' + "".join(f"<li><strong>{e(x.get('datum', ''))}</strong>: {e(x.get('wat', ''))}</li>"
                                               for x in items) + "</ol>")


def sectie_sentiment(inh) -> str:
    if not isinstance(inh, dict):
        return '<p class="melding">Nog geen ontwerp (inhoud/sentiment.json).</p>'
    delen = []
    if inh.get("status"):
        delen.append(f'<p class="disclaimer">{e(inh["status"])}</p>')
    if inh.get("idee"):
        delen.append(f"<p><strong>Idee:</strong> {e(inh['idee'])}</p>")
    for veld, kop in (("aanpak", "Aanpak"), ("risicos", "Risico's")):
        if inh.get(veld):
            delen.append(f"<h3>{kop}</h3><ul>" + "".join(f"<li>{e(x)}</li>" for x in inh[veld]) + "</ul>")
    return "".join(delen)


ONDERZOEK_KOLOMMEN = [("naam", "Naam"), ("kosten", "Kosten"), ("darts_dekking", "Darts-dekking"),
                      ("nl_bruikbaar", "Bruikbaar in NL"), ("voorwaarden", "Voorwaarden"), ("oordeel", "Oordeel")]


def sectie_onderzoek(inh) -> str:
    items = inh.get("items") if isinstance(inh, dict) else None
    if not items:
        return '<p class="melding">Nog geen onderzoek (inhoud/onderzoek.json).</p>'
    rijen = []
    for x in items:
        cellen = []
        for k, _ in ONDERZOEK_KOLOMMEN:
            v = e(x.get(k, STREEP))
            if k == "naam" and str(x.get("url", "")).startswith(("http://", "https://")):
                v = f'<a href="{e(x["url"])}">{v}</a>'
            cellen.append(f"<td>{v}</td>")
        rijen.append("<tr>" + "".join(cellen) + "</tr>")
    kop = "".join(f"<th>{e(t)}</th>" for _, t in ONDERZOEK_KOLOMMEN)
    toel = f"<p><small>{e(inh['toelichting'])}</small></p>" if inh.get("toelichting") else ""
    return (f"<h3>Onderzoek naar bronnen</h3>{toel}<div class=\"tabel-wrap\"><table><thead><tr>{kop}</tr></thead>"
            f"<tbody>{''.join(rijen)}</tbody></table></div>")


SORTEER_JS = """
document.querySelectorAll('table.sorteerbaar').forEach(function(t){
  t.querySelectorAll('button.sorteer').forEach(function(b,i){
    b.addEventListener('click',function(){
      var tb=t.tBodies[0],rs=Array.prototype.slice.call(tb.rows),op=b.dataset.op!=='1';
      t.querySelectorAll('button.sorteer').forEach(function(x){x.dataset.op='';x.removeAttribute('aria-sort');});
      b.dataset.op=op?'1':'0';
      function w(r){var c=r.cells[i];if(!c)return '';var s=c.getAttribute('data-s');return s!==null?s:c.textContent.trim();}
      rs.sort(function(a,c){var x=w(a),y=w(c),nx=parseFloat(x),ny=parseFloat(y);
        if(x===''&&y!=='')return 1;if(y===''&&x!=='')return -1;
        var v=(!isNaN(nx)&&!isNaN(ny))?nx-ny:x.localeCompare(y,'nl');return op?v:-v;});
      rs.forEach(function(r){tb.appendChild(r);});
    });
  });
});
"""

VRIENDEN_HTML = """<!DOCTYPE html>
<html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Darts-WK: voor vrienden</title></head>
<body style="font:16px/1.5 system-ui,sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem">
<h1>Darts-WK 2026/27 voor vrienden</h1><p>{leeg}</p><p><strong>{disclaimer}</strong></p>
<p><a href="index.html">Terug naar het dashboard</a></p></body></html>
"""

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
nav.inhoud{display:flex;flex-wrap:wrap;gap:.3rem .8rem;font-size:.9rem;margin:.6rem 0}
tr.mislukt td{background:color-mix(in srgb,var(--slecht) 10%,transparent)}
button.sorteer{all:unset;cursor:pointer;color:var(--tekst2);font-weight:600}
button.sorteer:focus-visible{outline:2px solid var(--link)}
button.sorteer[data-op="1"]::after{content:" ▲"}button.sorteer[data-op="0"]::after{content:" ▼"}
.grafiek .interval.s1{stroke:var(--s1)}.grafiek .interval.s2{stroke:var(--s2)}
.grafiek circle.c1{fill:var(--s1)}.grafiek circle.c2{fill:var(--s2)}
.klein-raster{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:.8rem}
.klein-raster figure{margin:0}.klein-raster figcaption{font-size:.85rem;color:var(--tekst2)}
svg.klein{width:100%;height:auto}svg.klein text{font-size:11px;fill:var(--tekst2)}
svg.klein .grid{stroke:var(--grid)}svg.klein .nul{stroke:var(--as);stroke-dasharray:4 3}
svg.klein .lijn{fill:none;stroke-width:2}svg.klein circle{fill:var(--s1);stroke:var(--vlak);stroke-width:2}
ul.lijst{list-style:none;padding-left:0}ul.lijst li{margin:.2rem 0}
ol.tijdlijn li{margin:.3rem 0}
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
            f'<li><a href="{REPO_URL}/blob/main/docs/onderzoek-odds-en-toto.md">Onderzoek odds-API\'s en '
            "TOTO-voorwaarden (docs/onderzoek-odds-en-toto.md)</a></li>"
            f'<li><a href="{REPO_URL}/blob/main/docs/review-ronde2.md">Review ronde 2 (docs/review-ronde2.md)</a></li>'
            "</ul>")


def bouw_html(verzameld: dict, live, nu: dt.datetime | None = None, sha: str | None = None,
              experimenten=None, inhoud: dict | None = None, protocol: str | None = None) -> str:
    runs, totalen, extra = verzameld["runs"], verzameld["totalen"], verzameld["extra"]
    inhoud = inhoud or {}
    nu = nu or dt.datetime.now(dt.timezone.utc)
    if sha:
        commit = f'commit <a href="{REPO_URL}/commit/{e(sha)}"><code>{e(sha[:7])}</code></a>'
    else:
        commit = "commit onbekend (lokaal gebouwd)"
    extra_html = ""
    titels = {"data": "Gegevens per WK", "blind_underdog": "Vergelijking: blind op de underdog",
              "meldingen": "Meldingen"}
    if extra:
        extra_html = ("<h3>Aanvullende vergelijking</h3>"
                      + "\n".join(tabel_generiek(titels[k], v) for k, v in extra.items()))
    protocol_html = (markdown_html(protocol) if protocol else
                     '<p class="melding">docs/protocol.md niet gevonden.</p>')
    nav = "".join(f'<a href="#{i}">{t}</a>' for i, t in (
        ("samenvatting", "Samenvatting"), ("werkwijze", "Werkwijze"), ("experimenten", "Experimenten"),
        ("vergelijking", "Vergelijking"), ("kalibratie", "Kalibratie"), ("roi", "ROI"), ("inzet", "Inzet in €"), ("protocol", "Protocol"), ("ideeen", "Ideeën"),
        ("roadmap", "Roadmap"), ("live", "Live"), ("sentiment", "Sentiment"), ("bronnen", "Bronnen")))
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
<nav class="inhoud">{nav}</nav>
</header>

<section id="aanbeveling">
<h2>Huidige aanbeveling</h2>
{sectie_aanbeveling(inhoud.get("aanbeveling"))}
</section>

<section id="samenvatting">
<h2>Samenvatting: beste model tegenover de markt</h2>
{sectie_samenvatting(experimenten)}
</section>

<section id="werkwijze">
<h2>Hoe we een model verbeteren (werkwijze)</h2>
{sectie_werkwijze()}
</section>

<section id="experimenten">
<h2>Experimenten</h2>
{sectie_experimenten(experimenten)}
</section>

<section id="vergelijking">
<h2>Vergelijking per model en per WK</h2>
{svg_delta(experimenten)}
</section>

<section id="kalibratie">
<h2>Kalibratie</h2>
{svg_kalibratie(experimenten)}
</section>

<section id="roi">
<h2>Winstverloop (ROI-curves)</h2>
{svg_roi_curves(experimenten)}
</section>

<section id="inzet">
<h2>Inzetbeleid in euro's (E027)</h2>
{sectie_inzet(experimenten)}
</section>

<section id="protocol">
<h2>Protocol en waarom deze keuzes</h2>
{protocol_html}
</section>

<section id="ideeen">
<h2>Wat kunnen we nog tunen? Ideeën</h2>
{sectie_lijst(inhoud.get("ideeen"), "Nog geen ideeën (inhoud/ideeen.json).")}
</section>

<section id="roadmap">
<h2>Roadmap tot en met het WK (11-12-2026 t/m 3-1-2027)</h2>
{sectie_roadmap(inhoud.get("roadmap"))}
</section>

<section id="live">
<h2>WK 2026/27 live</h2>
{sectie_live(live)}
<h3>Voor vrienden</h3>
<p><a href="vrienden.html">Vriendenpagina</a>: {e(VRIENDEN_LEEG)}</p>
</section>

<section id="sentiment">
<h2>X-sentimentmeter (ontwerp)</h2>
{sectie_sentiment(inhoud.get("sentiment"))}
</section>

<section id="bronnen">
<h2>Bronnen en onderzoek</h2>
{sectie_bronnen()}
{sectie_onderzoek(inhoud.get("onderzoek"))}
</section>

<section id="bijlage">
<h2>Bijlage: eerdere terugtests</h2>
<details><summary>Kerncijfers, grafieken en methode van de eerdere terugtests (vorm, rating, vergelijking)</summary>
<h3>Kerncijfers per test-WK</h3>
<p>Log-loss en Brier: <strong>lager is beter</strong>. Verschil = model − markt; positief betekent dat de markt
beter voorspelt (<span class="badge slecht">markt wint</span>). Markt = slotodds met proportionele margecorrectie;
Shin klein eronder. ROI bij vaste inzet 1 met 90%-interval (bootstrap per ronde). Drempel en reden komen uit de
train-jaren.</p>
{tabel_kerncijfers(runs, totalen)}
<h3>Log-loss: model tegenover markt</h3>
{svg_logloss(runs)}
<h3>ROI met 90%-interval</h3>
{svg_roi(runs)}
<h3>Winstverloop</h3>
{svg_verloop(runs)}
{extra_html}
<h3>Methode</h3>
{sectie_methode(runs)}
</details>
</section>

<footer>
<p>{e(DISCLAIMER)}</p>
<p>Laatst bijgewerkt: {e(nu.strftime("%Y-%m-%d %H:%M %Z").strip())} · {commit} ·
<a href="data.json">data.json</a></p>
</footer>
</main>
<script>{SORTEER_JS}</script>
</body>
</html>
"""


def main(argv=None) -> int:
    basis = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--resultaten", type=Path, default=basis / "resultaten")
    parser.add_argument("--uit", type=Path, default=basis / "site")
    parser.add_argument("--inhoud", type=Path, default=basis / "inhoud")
    parser.add_argument("--protocol", type=Path, default=basis / "docs" / "protocol.md")
    args = parser.parse_args(argv)

    verzameld = verzamel(args.resultaten)
    live = lees_live(args.resultaten)
    sha = os.environ.get("GITHUB_SHA") or None
    nu = dt.datetime.now(dt.timezone.utc)
    args.uit.mkdir(parents=True, exist_ok=True)
    exp = lees_experimenten(args.resultaten)
    inhoud = lees_inhoud(args.inhoud)
    protocol = args.protocol.read_text(encoding="utf-8") if args.protocol.exists() else None
    (args.uit / "index.html").write_text(bouw_html(verzameld, live, nu, sha, exp, inhoud, protocol),
                                         encoding="utf-8")
    (args.uit / "vrienden.html").write_text(VRIENDEN_HTML.format(leeg=e(VRIENDEN_LEEG), disclaimer=e(DISCLAIMER)),
                                            encoding="utf-8")
    data = {"gegenereerd": nu.isoformat(timespec="seconds"), "commit": sha, **verzameld, "live": live,
            "inhoud": inhoud}
    (args.uit / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(verzameld['runs'])} runs → {args.uit / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
