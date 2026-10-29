"""Opdrachtregel: dartswk fetch | fetch-events | dataset | terugtest | vergelijk."""
from __future__ import annotations

import argparse
import sys

from . import config
from .modellen import MODELLEN


def _fetch(a):
    from .bronnen import fetch
    fetch(a.jaren)


def _fetch_events(a):
    from .bronnen import fetch_orakel_events
    fetch_orakel_events(a.kalenderjaren)


def _vergelijk(a):
    from .terugtest import schrijf
    from .vergelijk import markdown, vergelijk
    v = vergelijk()
    md = markdown(v)
    fj, fm = schrijf("vergelijking", v, md)
    print(md)
    print(f"geschreven: {fj}, {fm}")


def _dataset(a):
    from .dataset import schrijf_wiki_csv
    for j in a.jaren:
        fn, meld = schrijf_wiki_csv(j)
        print(f"WK{j}: {fn}")
        for m in meld:
            print("  -", m)


def _terugtest(a):
    from .terugtest import (laad, markdown_terugtest, markdown_walk_forward, schrijf, terugtest,
                            walk_forward)
    if a.walk_forward:
        jaren = a.jaren
        data, meld = laad(jaren)
        _meld(meld)
        wf = walk_forward(a.model, jaren, data)
        md = markdown_walk_forward(wf)
        fj, fm = schrijf(f"walkforward_{a.model}", wf, md)
    else:
        if not a.train or not a.test:
            sys.exit("geef --train en --test, of --walk-forward")
        if set(a.train) & set(a.test):
            sys.exit("train en test overlappen")
        data, meld = laad(a.train + a.test)
        _meld(meld)
        t = terugtest(a.model, a.train, a.test, data)
        md = markdown_terugtest(t)
        naam = f"terugtest_{a.model}_train{'-'.join(map(str, a.train))}_test{'-'.join(map(str, a.test))}"
        fj, fm = schrijf(naam, t, md)
    print(md)
    print(f"geschreven: {fj}, {fm}")


def _meld(meld):
    for j, ms in meld.items():
        r = f"WK{j}: " + ("; ".join(ms) if ms else "geen meldingen")
        print(r)


def main(argv=None):
    alle = sorted(config.JAREN)
    p = argparse.ArgumentParser(prog="dartswk", description="Terugtest dartsmodel PDC WK (hobbyproject, geen advies)")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="haal ruwe brondata op naar data/cache/")
    f.add_argument("--jaren", type=int, nargs="+", default=alle, choices=alle)
    f.set_defaults(func=_fetch)

    e = sub.add_parser("fetch-events", help="haal Dartsorakel-evenementen en resultaatpagina's op (voor de rating)")
    e.add_argument("--kalenderjaren", type=int, nargs="+", default=[2022, 2023, 2024, 2025])
    e.set_defaults(func=_fetch_events)

    d = sub.add_parser("dataset", help="schrijf data/wedstrijden_WK<jaar>.csv (alleen Wikipedia)")
    d.add_argument("--jaren", type=int, nargs="+", default=alle, choices=alle)
    d.set_defaults(func=_dataset)

    t = sub.add_parser("terugtest", help="stem af op train, toets op test (of walk-forward)")
    t.add_argument("--model", default="vorm", choices=sorted(MODELLEN))
    t.add_argument("--train", type=int, nargs="+", choices=alle)
    t.add_argument("--test", type=int, nargs="+", choices=alle)
    t.add_argument("--walk-forward", action="store_true", help="voor elk jaar t: afstemmen op jaren < t, toetsen op t")
    t.add_argument("--jaren", type=int, nargs="+", default=alle, choices=alle, help="jaren voor walk-forward")
    t.set_defaults(func=_terugtest)

    v = sub.add_parser("vergelijk", help="alle modellen over alle splits -> resultaten/vergelijking.*")
    v.set_defaults(func=_vergelijk)

    a = p.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
