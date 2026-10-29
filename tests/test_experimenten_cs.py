import numpy as np

from dartswk import experimenten as x


def _rijen(jaar, n=40, seed=0):
    rng = np.random.default_rng(seed + jaar)
    uit = []
    for i in range(n):
        p = rng.uniform(0.3, 0.9)
        sn = 3 if i % 3 else 4
        verliezer = int(rng.integers(0, sn))
        s1, s2 = (sn, verliezer) if rng.random() < p else (verliezer, sn)
        a1, a2 = rng.normal(92, 4, 2)
        uit.append(dict(jaar=jaar, ronde=str(1 + i % 4), datum=f"{jaar - 1}-12-{10 + i % 15}", wedstrijd=i + 1,
                        setsnodig=sn, odd1=round(1.04 / p, 2), odd2=round(1.04 / (1 - p), 2), sets1=s1, sets2=s2,
                        winnaar=1 if s1 == sn else 2, walkover=0, avg1_12m=a1, avg2_12m=a2,
                        avg1_3m=a1 + rng.normal(0, 1), avg2_3m=None if i == 0 else a2 + rng.normal(0, 1),
                        avg1_achteraf=a1 + rng.normal(0, 3), avg2_achteraf=a2 + rng.normal(0, 3)))
    return uit


DATA = {j: _rijen(j) for j in (2024, 2025)}


def _exp(model, grid, regel="geen"):
    return dict(id="E900", model=model, grid=grid, criterium={"tekst": "c", "regel": regel, "factor_se": 1.0})


def test_cs_tune_schema_en_beoordeling():
    grid = dict(basis=dict(hold=0.6, sigma=0.3), hold=[0.6], sigma0=[0.2, 0.3], beta_niveau=[0.0, 0.2],
                beta_vol=[0.0], gamma=[0.0, 0.2], kappa=[0.0, 0.2])
    u = x.draai_cs_tune(_exp("cs-tune", grid, "verschil_lt_naief"), [2024], [2025], "walk-forward", DATA)
    assert u["n_combinaties"] == 16 and len(u["train_logloss"]) == 10
    assert set(u["gekozen"]) == {"hold", "sigma0", "beta_niveau", "beta_vol", "gamma", "kappa"}
    assert u["basis"] == "hold 0,60, σ 0,3" and set(u["per_format"]) == {"3", "4"}
    assert sum(f["n_wedstrijden"] for f in u["per_format"].values()) == u["n"] == 40
    assert x.beoordeel(_exp("cs-tune", grid, "verschil_lt_naief"), [u])["succes"] in (True, False)


def test_cs_tune_basis_gekozen_geeft_verschil_nul():
    grid = dict(basis=dict(hold=0.6, sigma=0.3), hold=[0.6], sigma3=[0.3], sigma4=[0.3])
    u = x.draai_cs_tune(_exp("cs-tune", grid), [2024], [2025], "walk-forward", DATA)
    assert u["verschil_naief"] == 0 and u["logloss_dp"] == u["logloss_naief"]


def test_cs_selectie():
    grid = dict(hold=0.6, sigma=0.3, sigma_boek=[0.0, 0.3], marge_methode=["proportioneel", "macht"],
                marges=[0.2], regels=["kans", "ev", "ev110"])
    u = x.draai_cs_selectie(_exp("cs-selectie", grid), [2024], [2025], "walk-forward", DATA)
    c = {(k["sigma_boek"], k["methode"], k["regel"]): k for k in u["combinaties"]}
    assert len(c) == 12
    for k in c.values():
        assert {"bets", "raak", "trefkans", "roi", "gem_odd", "keuzes", "roi_90"} <= set(k)
    kans, ev = c[(0.3, "proportioneel", "kans")], c[(0.3, "proportioneel", "ev")]
    assert kans["bets"] == 40 and (kans["raak"], kans["keuzes"], kans["roi"]) == (ev["raak"], ev["keuzes"], ev["roi"])
    assert c[(0.3, "proportioneel", "ev110")]["bets"] == 0     # EV is overal 1/(1+marge)
    assert c[(0.0, "proportioneel", "ev")]["gem_odd"] > kans["gem_odd"]


def test_macht_odds_marge():
    q = np.array([0.5, 0.3, 0.15, 0.05])
    o = x._macht_odds(q, 0.2)
    assert abs((1 / o).sum() - 1.2) < 1e-9
    assert o[-1] * q[-1] < o[0] * q[0]                          # longshot relatief meer marge


def test_cs_diagnose(monkeypatch, tmp_path):
    monkeypatch.setattr(x.config, "cache_map", lambda: tmp_path)   # geen Dartsorakel-cache: achteraf None
    grid = dict(hold=0.6, configs=[dict(sigma=0.0), dict(sigma=0.3), dict(sigma=0.0, kappa=0.3)])
    u = x.draai_cs_diagnose(_exp("cs-diagnose", grid), [2024], [2025], "walk-forward", DATA)
    assert u["achteraf"] is None and len(u["configs"]) == 3
    c0, c1 = u["configs"][0], u["configs"][1]
    assert set(c0["per_format"]) == {"3", "4"} and c0["totaal"]["n"] == 40
    assert sum(b["n"] for b in c0["per_favoriet"].values()) == 40
    assert c1["totaal"]["verwacht"] < c0["totaal"]["verwacht"]   # dagvorm: minder beslissende sets verwacht


def test_cs_achteraf_met_alleen_csv(monkeypatch, tmp_path):
    (tmp_path / "orakel_events" / "pages").mkdir(parents=True)
    monkeypatch.setattr(x.config, "cache_map", lambda: tmp_path)
    monkeypatch.setattr("dartswk.events.laad_wedstrijden", lambda *a: ([], {}, {}))
    a = x._achteraf_diagnose(DATA, 0.6)
    assert a["n"] == 80 and 0 <= a["c"] <= 1 and set(a["per_jaar"]) == {"2024", "2025"}


def test_markdown_cs_secties():
    grid_t = dict(basis=dict(hold=0.6, sigma=0.3), hold=[0.6], sigma=[0.0, 0.3])
    grid_s = dict(hold=0.6, sigma=0.3, sigma_boek=[0.0], marge_methode=["proportioneel"], marges=[0.2], regels=["kans"])
    grid_d = dict(hold=0.6, configs=[dict(sigma=0.0)])
    reg, res = [], []
    for i, (m, g, f) in enumerate((("cs-tune", grid_t, x.draai_cs_tune), ("cs-selectie", grid_s, x.draai_cs_selectie),
                                   ("cs-diagnose", grid_d, x.draai_cs_diagnose))):
        e = dict(_exp(m, g), id=f"E90{i}", datum="2026-10-29", hypothese="h", naam=m,
                 na_test_aangepast={"waarde": False, "toelichting": ""})
        reg.append(e)
        res.append(dict(id=e["id"], model=m, status="ok", uitkomsten=[f(e, [2024], [2025], "walk-forward", DATA)]))
    md = x.markdown(dict(register=reg, resultaten=res))
    assert "## E900" in md and "## E901" in md and "## E902" in md and "first to 3" in md
