"""Vergelijking van alle modellen over alle splits (beide richtingen, 2024 als testjaar, walk-forward)."""
from __future__ import annotations

from .rating import beschrijf_data
from .terugtest import _ci, _jr, _pct, laad, prm_tekst, samenvatting, terugtest

MODELNAMEN = ["vorm", "rating", "rating-platt", "rating+markt", "rating+avg", "markt-krimp"]
SPLITS = [  # (train, test, soort)
    ([2026], [2025], "richting"),
    ([2025], [2026], "richting"),
    ([2025], [2024], "richting"),
    ([2025, 2026], [2024], "richting"),
    ([2024], [2025], "walk-forward"),
    ([2024, 2025], [2026], "walk-forward"),
]


def vergelijk(modellen=None, splits=None) -> dict:
    modellen = modellen or MODELNAMEN
    splits = splits or SPLITS
    jaren = sorted({j for tr, te, _ in splits for j in tr + te})
    data, meld = laad(jaren)
    runs = []
    for tr, te, soort in splits:
        for m in modellen:
            t = terugtest(m, tr, te, data)
            runs.append(dict(model=m, train=tr, test=te, soort=soort, parameters=t["parameters"],
                             drempel_reden=t["drempel_reden"], train_resultaat=t["train_resultaat"],
                             test_resultaat=t["test_resultaat"], _t=t))
    totaal = {}
    for m in modellen:
        wf = [r["_t"] for r in runs if r["model"] == m and r["soort"] == "walk-forward"]
        if wf:
            rows = [x for t in wf for x in t["_rows_test"]]
            ps = [p for t in wf for p in t["_p_test"]]
            totaal[m] = samenvatting(rows, ps, "per stap", [b for t in wf for b in t["_bets_test"]])
    for r in runs:
        r.pop("_t")
    return dict(data=beschrijf_data(jaren), blind_underdog=blind_underdog(data, jaren), meldingen=meld, runs=runs,
                walk_forward_totaal=totaal)


def blind_underdog(data: dict, jaren: list[int]) -> dict:
    """Nulvergelijking: inzet 1 op de underdog volgens de odds in elke wedstrijd (gelijke odds overgeslagen)."""
    uit = {}
    for j in jaren:
        res = [(r["odd2"] - 1 if r["winnaar"] == 2 else -1.0) if r["odd1"] < r["odd2"] else
               (r["odd1"] - 1 if r["winnaar"] == 1 else -1.0)
               for r in data[j] if r["odd1"] is not None and r["odd1"] != r["odd2"]]
        uit[j] = dict(bets=len(res), roi=round(sum(res) / len(res), 4))
    return uit


KOP = ("| Model | n | Log-loss | Brier | Verschil log-loss vs markt (se) | Helling | Bets | Underdog | ROI | "
       "90%-int. (geclusterd) | Drempelkeuze (train) |\n|---|---|---|---|---|---|---|---|---|---|---|")


def _regel(m, s, reden=""):
    return (f"| {m} | {s['n']} | {s['logloss_model']:.4f} | {s['brier_model']:.4f} | "
            f"{s['logloss_verschil_vs_markt']:+.4f} ({s['logloss_verschil_se']:.4f}) | {s['helling_model']:.2f} | "
            f"{s['bets']} | {s['underdog_bets']} | {_pct(s['roi'])} | {_ci(s['roi_90_geclusterd'])} | {reden} |")


def _markt(s):
    return (f"| markt (prop.) | {s['n']} | {s['logloss_markt_proportioneel']:.4f} | {s['brier_markt_proportioneel']:.4f} "
            f"| 0 | {s['helling_markt_proportioneel']:.2f} | – | – | – | – | – |\n"
            f"| markt (Shin) | {s['n']} | {s['logloss_markt_shin']:.4f} | {s['brier_markt_shin']:.4f} | | | – | – | – | – | – |")


def markdown(v: dict) -> str:
    L = ["# Vergelijking modellen: vorm, rating, rating-platt, rating+markt, rating+avg, markt-krimp", "",
         "Alle cijfers op de testjaren; parameters en drempel afgestemd op train. Log-loss en Brier: lager is beter. "
         "Verschil = gemiddelde log-loss model − markt (proportioneel) per wedstrijd, met standaardfout; < 0 = model "
         "beter. Helling = c in logit P(winst) = c·logit(p) op de testdata (1 = goed gekalibreerd, < 1 = te stellig, "
         "> 1 = te vlak). ROI bij inzet 1 met de stopregel uit de README; interval: bootstrap per (jaar, ronde).", "",
         "## Data voor de rating (events strikt vóór de WK-start)", "",
         "| WK | Cutoff (< start) | Events in lijst | Met uitslagen | Paywall | Wedstrijden | Waarvan sets | Laatste event "
         "| WK-spelers zonder data |", "|---|---|---|---|---|---|---|---|---|"]
    for j, d in v["data"].items():
        L.append(f"| {j} | {d['cutoff_voor']} | {d['events']} | {d['gebruikt']} | {d['paywall']} | {d['wedstrijden']} | "
                 f"{d['sets_wedstrijden']} | {d['laatste_event']} | {d['wk_spelers_zonder_data']} van {d['wk_spelers']} |")
    L += ["", "Nulvergelijking blind op de underdog (alle wedstrijden met ongelijke odds): " + ", ".join(
        f"{j}: {_pct(d['roi'])} over {d['bets']}" for j, d in v["blind_underdog"].items()) + ".", ""]
    for soort, titel in (("richting", "Train → test (vaste richting)"), ("walk-forward", "Walk-forward")):
        L += ["", f"## {titel}", ""]
        splits = []
        for r in v["runs"]:
            if r["soort"] == soort and (r["train"], r["test"]) not in splits:
                splits.append((r["train"], r["test"]))
        for tr, te in splits:
            rs = [r for r in v["runs"] if (r["train"], r["test"]) == (tr, te)]
            L += [f"### Train {_jr(tr)} → test {_jr(te)}", "", KOP]
            L += [_regel(r["model"], r["test_resultaat"], r["drempel_reden"]) for r in rs]
            L += [_markt(rs[0]["test_resultaat"]), "", "Parameters:", ""]
            L += [f"- `{r['model']}`: {prm_tekst(r['parameters'])}" for r in rs]
            L.append("")
    if v["walk_forward_totaal"]:
        L += ["## Walk-forward totaal (testjaren samen)", "", KOP]
        L += [_regel(m, s) for m, s in v["walk_forward_totaal"].items()]
        L += [_markt(next(iter(v["walk_forward_totaal"].values())))]
    return "\n".join(L) + "\n"

