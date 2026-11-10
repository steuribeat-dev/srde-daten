"""
EODHD-Test: prüft, ob Kurse, Fundamentaldaten, Kursziele und Zahlentermine für Schweizer und
europäische Titel vorhanden sind. Schreibt data/test_eodhd.json. Start über GitHub Actions («EODHD Test»).
"""
import os, json, datetime as dt
import srde_abruf as s

TITEL = [("NESN", "SW"), ("ZURN", "SW"), ("SRAIL", "SW"), ("BSLN", "SW"), ("BCVN", "SW"),
         ("UMI", "BR"), ("SIE", "XETRA"), ("AI", "PA"), ("ASML", "AS"), ("ENEL", "MI"), ("ISP", "MI")]
INDIZES = ["SX5E.INDX", "STOXX50E.INDX", "SXXP.INDX"]

def main():
    erg = {"lauf_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"), "titel": {}, "indizes": {}}
    for sym, b in TITEL:
        r = {}
        try:
            d = s.kurse(sym, b)
            r["kurse"] = s.kennzahlen(d) if d is not None and len(d) >= 60 else "keine Daten"
        except Exception as e:
            r["kurse"] = f"Fehler: {e}"
        try:
            j = s.hole(f"https://eodhd.com/api/fundamentals/{sym}.{b}?api_token={s.KEY}&fmt=json")
            if j:
                g = j.get("General", {}) or {}
                r["allgemein"] = {k: g.get(k) for k in ("Name", "Exchange", "CurrencyCode", "Sector", "Industry")}
                r["fundamental"] = s.fundamental_auswerten(j)
                r["analyst_rohdaten"] = j.get("AnalystRatings")
                r["abschnitte"] = sorted(j.keys())
                hist = ((j.get("Earnings", {}) or {}).get("History", {}) or {})
                r["earnings_history_neueste"] = [hist[k] for k in sorted(hist)[-3:]]
                r["highlights_auszug"] = {k: (j.get("Highlights", {}) or {}).get(k) for k in ("WallStreetTargetPrice", "MostRecentQuarter")}
            else:
                r["fundamental"] = "keine Daten"
        except Exception as e:
            r["fundamental"] = f"Fehler: {e}"
        erg["titel"][f"{sym}.{b}"] = r
    try:
        erg["zahlentermine"] = s.zahlentermine([f"{x}.{b}" for x, b in TITEL])
        heute = dt.date.today(); bis = heute + dt.timedelta(days=150)
        erg["kalender_roh_symbole"] = s.hole(f"https://eodhd.com/api/calendar/earnings?api_token={s.KEY}&fmt=json&symbols=NESN.SW,UMI.BR,SIE.XETRA")
        roh = s.hole(f"https://eodhd.com/api/calendar/earnings?api_token={s.KEY}&fmt=json&from={heute}&to={bis}")
        alle = (roh or {}).get("earnings", []) or []
        erg["kalender_ohne_symbole"] = {"anzahl": len(alle),
            "europa": [e for e in alle if str(e.get("code", "")).split(".")[-1] in ("SW", "BR", "XETRA", "PA", "AS")][:15]}
    except Exception as e:
        erg["zahlentermine"] = f"Fehler: {e}"
    for ix in INDIZES:
        try:
            j = s.hole(f"https://eodhd.com/api/fundamentals/{ix}?api_token={s.KEY}&fmt=json")
            comp = (j or {}).get("Components") or {}
            erg["indizes"][ix] = {"anzahl": len(comp), "beispiele": [v.get("Code") + "." + str(v.get("Exchange")) for v in list(comp.values())[:5]]}
        except Exception as e:
            erg["indizes"][ix] = f"Fehler: {e}"
    try:
        fx = s.hole(f"https://eodhd.com/api/eod/EURCHF.FOREX?api_token={s.KEY}&fmt=json&from={(dt.date.today()-dt.timedelta(days=10)).isoformat()}")
        erg["eurchf"] = fx[-1] if fx else None
    except Exception as e:
        erg["eurchf"] = f"Fehler: {e}"
    os.makedirs(s.OUT, exist_ok=True)
    with open(os.path.join(s.OUT, "test_eodhd.json"), "w") as fh:
        json.dump(erg, fh, ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: (v.get("fundamental", {}).get("kursziel") if isinstance(v.get("fundamental"), dict) else v.get("fundamental"))
                      for k, v in erg["titel"].items()}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
