"""
SRDE-Europa: Tageskurse, Kennzahlen und Fundamentaldaten (EODHD) für den STOXX Europe 600
ohne Schweiz, Grossbritannien und Italien. Schreibt in eigene Dateien, damit der Schweizer Teil
unberührt bleibt:
    data/kennzahlen_europa.csv    eine Zeile je Titel (Kurse in Handelswährung, Liquidität in CHF)
    data/status_europa.json       Handelstag, Anzahl Titel, Fehler
    data/universum_europa.csv     aktuelle Indexzusammensetzung (Rückfall, wenn der Index nicht abrufbar ist)
    data/historie_europa/<TITEL>.csv   letzte 30 Handelstage (für Stops und das Signaldepot)
Titelbezeichnung: <KÜRZEL>.<BÖRSE>, z. B. SIE.XETRA, UMI.BR, AI.PA.
Läuft in GitHub Actions (.github/workflows/srde_europa.yml).
"""
import os, sys, json, time, datetime as dt
import pandas as pd
import srde_abruf as s

INDEX = "SXXP.INDX"
AUSGESCHLOSSEN = {"SW", "LSE", "MI", "IL"}      # Schweiz (eigener Teil), UK, Italien (keine Daten im Abo)
OUT = s.OUT
UNI = os.path.join(OUT, "universum_europa.csv")
HIST = os.path.join(OUT, "historie_europa")
HIST_ZEILEN = 30
WAEHRUNG_BOERSE = {"ST": "SEK", "CO": "DKK", "OL": "NOK", "WAR": "PLN"}   # Rückfall ohne Fundamentaldaten

def universum():
    """Indexzusammensetzung von EODHD; bei Ausfall die zuletzt gespeicherte Liste."""
    try:
        j = s.hole(f"https://eodhd.com/api/fundamentals/{INDEX}?api_token={s.KEY}&fmt=json")
        comp = (j or {}).get("Components") or {}
        rows = [{"code": v.get("Code"), "boerse": v.get("Exchange"), "name": v.get("Name"),
                 "sektor": v.get("Sector"), "industrie": v.get("Industry")} for v in comp.values()]
        rows = [r for r in rows if r["code"] and r["boerse"] and r["boerse"] not in AUSGESCHLOSSEN]
        if len(rows) >= 200:
            u = pd.DataFrame(rows).drop_duplicates(["code", "boerse"]).sort_values(["boerse", "code"])
            u.to_csv(UNI, index=False)
            return u, "index"
    except RuntimeError:
        raise
    except Exception:
        pass
    if os.path.exists(UNI):
        return pd.read_csv(UNI), "gespeichert"
    sys.exit(f"Indexzusammensetzung {INDEX} nicht abrufbar und keine gespeicherte Liste vorhanden.")

_fx = {"CHF": 1.0}
def fx_chf(waehrung):
    """Letzter Schlusskurs <WÄHRUNG>/CHF (EODHD FOREX)."""
    w = (waehrung or "").upper()
    if w in _fx:
        return _fx[w]
    von = (dt.date.today() - dt.timedelta(days=10)).isoformat()
    j = s.hole(f"https://eodhd.com/api/eod/{w}CHF.FOREX?api_token={s.KEY}&fmt=json&from={von}")
    _fx[w] = float(j[-1]["close"]) if j else None
    return _fx[w]

def main():
    if not s.KEY:
        sys.exit("EODHD_API_KEY fehlt (als GitHub-Secret oder Umgebungsvariable setzen).")
    os.makedirs(HIST, exist_ok=True)
    u, quelle = universum()
    zeilen, fehler = [], []
    for _, r in u.iterrows():
        titel = f"{r['code']}.{r['boerse']}"
        try:
            d = s.kurse(r["code"], r["boerse"])
            if d is None or len(d) < 60:
                fehler.append(f"{titel}: keine oder zu wenig Kursdaten"); continue
            k = s.kennzahlen(d)
            f = {}
            if s.FUND:
                try:
                    f = s.fundamental(r["code"], r["boerse"])
                except RuntimeError as e:
                    fehler.append(f"{titel}: Fundamentaldaten – {e}")
            w = (f.get("waehrung") if f else None) or WAEHRUNG_BOERSE.get(r["boerse"], "EUR")
            f["waehrung"] = w
            fx = fx_chf(w)
            umsatz_lokal = k.pop("umsatz_median_chf")
            umsatz_chf = round(umsatz_lokal * fx) if fx else None
            z = {"titel": titel, "name": r.get("name"), "boerse": r["boerse"], "waehrung": w, "fx_chf": fx,
                 "sektor_index": r.get("sektor"), **k}
            # Kurs-, ATR- und Stopwerte sind in Handelswährung; Spalten entsprechend benennen
            z["atr"] = z.pop("atr_chf")
            z["umsatz_median_lokal"] = round(umsatz_lokal)
            z["umsatz_median_chf"] = umsatz_chf
            z["liquiditaet"] = "A" if (umsatz_chf or 0) >= 1_000_000 else "B"
            z.update(f)
            zeilen.append(z)
            d.tail(HIST_ZEILEN).to_csv(os.path.join(HIST, f"{titel}.csv"), index=False)
        except RuntimeError as e:
            if "Zugriff verweigert" in str(e):
                sys.exit(str(e))
            fehler.append(f"{titel}: {e}")
        except Exception as e:
            fehler.append(f"{titel}: {e}")
        time.sleep(0.1)
    if not zeilen:
        sys.exit("Keine Europa-Titel geladen.")
    t = pd.DataFrame(zeilen)
    if s.FUND:
        try:
            termine = s.zahlentermine(t["titel"].tolist())
            t["naechste_zahlen"] = [termine.get(x) for x in t["titel"]]
            if "naechste_zahlen_fund" in t.columns:
                t["naechste_zahlen"] = t["naechste_zahlen"].fillna(t["naechste_zahlen_fund"])
        except RuntimeError as e:
            fehler.append(f"Kalender: {e}")
    soll = t["datum"].mode().iloc[0]
    t["veraltet"] = t["datum"] != soll
    t.to_csv(os.path.join(OUT, "kennzahlen_europa.csv"), index=False)
    print("Titel je Börse:", t["boerse"].value_counts().to_dict())
    print("Datum je Börse:", t.groupby("boerse")["datum"].max().to_dict())
    status = {"lauf_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"), "handelstag": soll,
              "universum": f"{INDEX} ohne {', '.join(sorted(AUSGESCHLOSSEN))} ({quelle})",
              "titel_total": int(len(u)), "titel_geladen": int(len(t)), "titel_ok": int((~t["veraltet"]).sum()),
              "veraltet": t.loc[t["veraltet"], "titel"].tolist(),
              "warnung_split_unbereinigt": t.loc[t["warn_split_unbereinigt"], "titel"].tolist(),
              "waehrungen": {w: _fx.get(w) for w in sorted(t["waehrung"].dropna().unique())},
              "fehler": fehler, "fundamentaldaten": s.FUND}
    with open(os.path.join(OUT, "status_europa.json"), "w") as fh:
        json.dump(status, fh, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in status.items() if k != "fehler"}, ensure_ascii=False, indent=2))
    print(f"Fehler: {len(fehler)}")
    # Daten immer speichern; veraltete Titel sind in status_europa.json markiert und werden nicht signalisiert.
    if status["titel_geladen"] < 0.5 * len(u):
        sys.exit("Weniger als die Hälfte der Europa-Titel geladen – Lauf als fehlgeschlagen markiert (Daten trotzdem gespeichert).")

if __name__ == "__main__":
    main()
