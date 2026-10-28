"""Opdrachtregel: dartswk fetch | dataset | terugtest."""
from __future__ import annotations

import argparse
import sys

from . import config


def _fetch(a):
    from .bronnen import fetch
    fetch(a.jaren)


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

    d = sub.add_parser("dataset", help="schrijf data/wedstrijden_WK<jaar>.csv (alleen Wikipedia)")
    d.add_argument("--jaren", type=int, nargs="+", default=alle, choices=alle)
    d.set_defaults(func=_dataset)

    t = sub.add_parser("terugtest", help="stem af op train, toets op test (of walk-forward)")
    t.add_argument("--model", default="vorm", choices=["vorm"])
    t.add_argument("--train", type=int, nargs="+", choices=alle)
    t.add_argument("--test", type=int, nargs="+", choices=alle)
    t.add_argument("--walk-forward", action="store_true", help="voor elk jaar t: afstemmen op jaren < t, toetsen op t")
    t.add_argument("--jaren", type=int, nargs="+", default=alle, choices=alle, help="jaren voor walk-forward")
    t.set_defaults(func=_terugtest)

    a = p.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
