"""
SRDE-Datenabruf: lädt Tageskurse (und optional Fundamentaldaten) von EODHD für das
SRDE-Universum, berechnet Kennzahlen, prüft die Datenqualität und speichert alles in data/.

Läuft in GitHub Actions (siehe .github/workflows/srde_abruf.yml) oder lokal:
    export EODHD_API_KEY=...        # nie in den Code schreiben
    python srde_abruf.py
Optional:  FUNDAMENTALS=true  -> ruft zusätzlich /api/fundamentals ab (nur wenn im EODHD-Abo enthalten)
"""
import os, sys, json, time, datetime as dt
import urllib.request, urllib.error
import pandas as pd, numpy as np

KEY = os.environ.get("EODHD_API_KEY", "")
FUND = os.environ.get("FUNDAMENTALS", "false").lower() == "true"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HIST_DAYS = 420          # Kalendertage Historie (reicht für 200-Tage-Schnitt und 12-Monats-Rendite)

UNIVERSUM = [
    # bisherige 47 Titel
    "SREN", "ZURN", "SLHN", "NOVN", "ROP", "NESN", "ABBN", "SCMN", "GIVN", "LONN", "SIKA",
    "PGHN", "KNIN", "SOON", "SDZ", "ALC", "GEBN", "CFR", "UBSG", "HOLN", "SGSN", "LOGN",
    "SCHP", "EMSN", "VACN", "BAER", "TECN", "SRAIL", "SKAN", "BELL", "BSLN", "LUKN", "BEKN",
    "DOKA", "BOSN", "SUN", "LEHN", "DKSH", "EMMN", "BCVN", "YPSN", "SENS", "ALSN", "BRKN",
    "AMRZ", "DAE", "GALD",
    # Erweiterung auf 110 Titel (weitere SPI-Titel)
    "ADEN", "UHR", "CLN", "GF", "BARN", "LISP", "STMN", "BCHN", "BUCN", "SFZN",
    "BANB", "IFCN", "INRN", "KARN", "COTN", "ACLN", "MOVE", "CMBN", "VONN", "EFGN",
    "SQN", "VZN", "PSPN", "SPSN", "ALLN", "MOBN", "FHZN", "GALE", "MEDX", "HUBN",
    "IMPN", "ARBN", "AUTN", "BKW", "DOCM", "OERL", "SIGN", "SFSN", "FORN", "DESN",
    "TEMN", "SWON", "LAND", "AERO", "VAHN", "HBAN", "VATN", "SGKN", "ZUGN", "TKBP",
    "CLTN", "VETN", "ZEHN", "LLBN", "VPBN", "BEAN", "AVOL", "MOZN", "LEON", "RIEN",
    "BCGE", "TXGN", "GRKP"]
VERGLEICH = ["CHSPI"]     # SPI-ETF als Vergleichsmassstab

def hole(url, versuche=3):
    for i in range(versuche):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise RuntimeError(f"Zugriff verweigert ({e.code}) – API-Schlüssel oder Abo prüfen")
            if e.code == 404:
                return None
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return None

def kurse(sym, boerse="SW"):
    von = (dt.date.today() - dt.timedelta(days=HIST_DAYS)).isoformat()
    j = hole(f"https://eodhd.com/api/eod/{sym}.{boerse}?api_token={KEY}&fmt=json&from={von}")
    if not j:
        return None
    d = pd.DataFrame(j)
    d["date"] = pd.to_datetime(d["date"])
    return d.sort_values("date").reset_index(drop=True)

def kennzahlen(d):
    """Alle Kennzahlen aus der Kurshistorie. Renditen und Durchschnitte auf adjusted_close (Splits und Dividenden bereinigt)."""
    a = d["adjusted_close"].astype(float); c = d["close"].astype(float)
    h = d["high"].astype(float); l = d["low"].astype(float); v = d["volume"].astype(float)
    f = a.iloc[-1] / c.iloc[-1] if c.iloc[-1] else 1.0          # Bereinigungsfaktor heute
    ma50 = a.rolling(50).mean().iloc[-1]; ma200 = a.rolling(200).mean().iloc[-1]
    def ret(n): return (a.iloc[-1] / a.iloc[-1 - n] - 1) * 100 if len(a) > n else np.nan
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr_pct = tr.rolling(14).mean().iloc[-1] / c.iloc[-1] * 100
    hi252 = a.tail(252).max(); lo252 = a.tail(252).min()
    umsatz = (c * v).tail(60).median()
    # Datenprüfung: grosse Sprünge im unbereinigten Kurs ohne entsprechende Bereinigung deuten auf Splitfehler
    sprung_roh = (c / c.shift() - 1).abs().tail(260).max()
    sprung_ber = (a / a.shift() - 1).abs().tail(260).max()
    return {
        "datum": d["date"].iloc[-1].date().isoformat(),
        "kurs": round(c.iloc[-1], 4),
        "ma50": round(ma50 / f, 4) if pd.notna(ma50) else np.nan,
        "ma200": round(ma200 / f, 4) if pd.notna(ma200) else np.nan,
        "abstand_ma50_pct": round((a.iloc[-1] / ma50 - 1) * 100, 2) if pd.notna(ma50) else np.nan,
        "abstand_ma200_pct": round((a.iloc[-1] / ma200 - 1) * 100, 2) if pd.notna(ma200) else np.nan,
        "rendite_3m_pct": round(ret(63), 2), "rendite_6m_pct": round(ret(126), 2), "rendite_12m_pct": round(ret(252), 2),
        "rendite_12m_ohne_1m_pct": round((a.iloc[-22] / a.iloc[-253] - 1) * 100, 2) if len(a) > 253 else np.nan,
        "atr_pct": round(atr_pct, 2),
        "abstand_52w_hoch_pct": round((a.iloc[-1] / hi252 - 1) * 100, 2),
        "abstand_52w_tief_pct": round((a.iloc[-1] / lo252 - 1) * 100, 2),
        "umsatz_median_chf": round(umsatz),
        "liquiditaet": "A" if umsatz >= 1_000_000 else "B",
        # Hinweis: Split im letzten Jahr, von EODHD korrekt bereinigt (keine Massnahme nötig)
        "split_bereinigt": bool(sprung_roh > 0.35 and sprung_ber < 0.25),
        # Warnung: auch der bereinigte Kurs springt um mehr als 35 % -> Daten prüfen (Split nicht bereinigt oder Datenfehler)
        "warn_split_unbereinigt": bool(sprung_ber > 0.35),
        # Für Stop-Marken und Kaufsignal (unbereinigte Kurse der letzten 20 Tage, in CHF)
        "atr_chf": round(tr.rolling(14).mean().iloc[-1], 4),
        "tief_20t": round(l.tail(20).min(), 4),
        "hoch_20t": round(h.tail(20).max(), 4),
        "stop_technisch": round(c.iloc[-1] - 2 * tr.rolling(14).mean().iloc[-1], 4),   # Kurs minus 2 x ATR(14)
        "ma50_ueber_ma200": bool(pd.notna(ma200) and ma50 > ma200),
        "ma50_steigend": bool(len(a) > 70 and ma50 > a.rolling(50).mean().iloc[-21]),
        "tage_historie": len(d),
    }

def fundamental(sym, boerse="SW"):
    j = hole(f"https://eodhd.com/api/fundamentals/{sym}.{boerse}?api_token={KEY}&fmt=json")
    if not j:
        return {}
    return fundamental_auswerten(j)

def fundamental_auswerten(j):
    hi = j.get("Highlights", {}) or {}; va = j.get("Valuation", {}) or {}; tr = j.get("Technicals", {}) or {}
    out = {"branche": (j.get("General", {}) or {}).get("Sector"), "waehrung": (j.get("General", {}) or {}).get("CurrencyCode"),
           "roe_pct": hi.get("ReturnOnEquityTTM"), "operative_marge_pct": hi.get("OperatingMarginTTM"),
           "kgv": hi.get("PERatio"), "kgv_erwartet": va.get("ForwardPE"), "ev_ebitda": va.get("EnterpriseValueEbitda"),
           "dividendenrendite_pct": hi.get("DividendYield"), "gewinn_je_aktie_schaetzung_jahr": hi.get("EPSEstimateCurrentYear"),
           "gewinn_je_aktie_schaetzung_folgejahr": hi.get("EPSEstimateNextYear"), "beta": tr.get("Beta")}
    for k in ("roe_pct", "operative_marge_pct", "dividendenrendite_pct"):
        if isinstance(out.get(k), (int, float)): out[k] = round(out[k] * 100, 2)
    # Nettoverschuldung / EBITDA aus der letzten Bilanz
    try:
        bs = j["Financials"]["Balance_Sheet"]["quarterly"]; last = bs[sorted(bs)[-1]]
        netdebt = float(last.get("netDebt") or 0); ebitda = float(hi.get("EBITDA") or 0)
        out["nettoschuld_ebitda"] = round(netdebt / ebitda, 2) if ebitda else None
    except Exception:
        out["nettoschuld_ebitda"] = None
    try:
        cf = j["Financials"]["Cash_Flow"]["yearly"]; last = cf[sorted(cf)[-1]]
        out["free_cashflow_letztes_jahr"] = float(last.get("freeCashFlow")) if last.get("freeCashFlow") else None
    except Exception:
        out["free_cashflow_letztes_jahr"] = None
    try:
        tr_ = j.get("Earnings", {}).get("Trend", {}) or {}
        k0 = sorted(tr_)[-1] if tr_ else None
        if k0:
            t = tr_[k0]; out["schaetzung_aenderung_90t"] = t.get("epsTrend90daysAgo") and t.get("epsTrendCurrent") and \
                round((float(t["epsTrendCurrent"]) / float(t["epsTrend90daysAgo"]) - 1) * 100, 2)
    except Exception:
        pass
    # Analysten: Konsens-Kursziel und Anzahl Analysten (Stand = Abruftag)
    ar = j.get("AnalystRatings", {}) or {}
    ziel = ar.get("TargetPrice") or hi.get("WallStreetTargetPrice")
    try:
        ziel = round(float(ziel), 4) if ziel not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        ziel = None
    n = 0
    for k in ("StrongBuy", "Buy", "Hold", "Sell", "StrongSell"):
        try: n += int(float(ar.get(k) or 0))
        except (TypeError, ValueError): pass
    out["kursziel"] = ziel
    out["ziel_analysten"] = n or None
    out["analysten_rating"] = ar.get("Rating")
    out["ziel_datum"] = dt.date.today().isoformat() if ziel else None
    # Ersatz für den Kalender: nächster Termin aus Earnings.History (Einträge mit Datum in der Zukunft)
    heute = dt.date.today().isoformat(); kand = []
    for e in ((j.get("Earnings", {}) or {}).get("History", {}) or {}).values():
        for f in ("reportDate", "date"):
            v = (e or {}).get(f)
            if isinstance(v, str) and v[:10] >= heute:
                kand.append(v[:10]); break
    out["naechste_zahlen_fund"] = min(kand) if kand else None
    return out

def zahlentermine(symbole, tage=60):
    """Nächster Termin für Geschäftszahlen je Symbol (z. B. 'NESN.SW') aus dem EODHD-Kalender.
    Ein Abruf für alle Börsen ohne Symbolfilter (mit Symbolfilter liefert EODHD nur Teilmengen)."""
    heute = dt.date.today(); bis = heute + dt.timedelta(days=tage)
    j = hole(f"https://eodhd.com/api/calendar/earnings?api_token={KEY}&fmt=json"
             f"&from={heute.isoformat()}&to={bis.isoformat()}")
    gesucht = set(symbole); termine = {}
    for e in (j or {}).get("earnings", []) or []:
        code, datum = e.get("code"), e.get("report_date")
        if code in gesucht and datum and datum >= heute.isoformat():
            if code not in termine or datum < termine[code]:
                termine[code] = datum
    return termine

def main():
    if not KEY:
        sys.exit("EODHD_API_KEY fehlt (als GitHub-Secret oder Umgebungsvariable setzen).")
    os.makedirs(os.path.join(OUT, "historie"), exist_ok=True)
    zeilen, fehler = [], []
    for sym in UNIVERSUM + VERGLEICH:
        try:
            d = kurse(sym)
            if d is None or len(d) < 60:
                fehler.append(f"{sym}: keine oder zu wenig Kursdaten"); continue
            d.to_csv(os.path.join(OUT, "historie", f"{sym}.csv"), index=False)
            z = {"titel": sym, "vergleich": sym in VERGLEICH, **kennzahlen(d)}
            if FUND and sym not in VERGLEICH:
                try:
                    z.update(fundamental(sym))
                except RuntimeError as e:          # Fundamentaldaten verweigert: Kurse trotzdem speichern
                    fehler.append(f"{sym}: Fundamentaldaten – {e}")
            zeilen.append(z)
        except RuntimeError as e:
            sys.exit(str(e))
        except Exception as e:
            fehler.append(f"{sym}: {e}")
        time.sleep(0.2)
    t = pd.DataFrame(zeilen)
    if FUND:
        try:
            termine = zahlentermine([f"{x}.SW" for x in UNIVERSUM])
            t["naechste_zahlen"] = [termine.get(f"{x}.SW") for x in t["titel"]]
            if "naechste_zahlen_fund" in t.columns:
                t["naechste_zahlen"] = t["naechste_zahlen"].fillna(t["naechste_zahlen_fund"])
        except RuntimeError as e:
            fehler.append(f"Kalender: {e}")
    # Aktualität: erwarteter letzter Handelstag = häufigstes Datum
    soll = t["datum"].mode().iloc[0]
    t["veraltet"] = t["datum"] != soll
    t.to_csv(os.path.join(OUT, "kennzahlen.csv"), index=False)
    status = {"lauf_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"), "handelstag": soll,
              "titel_ok": int((~t["veraltet"]).sum()), "titel_total": len(UNIVERSUM) + len(VERGLEICH),
              "veraltet": t.loc[t["veraltet"], "titel"].tolist(), "split_bereinigt_hinweis": t.loc[t["split_bereinigt"], "titel"].tolist(),
              "warnung_split_unbereinigt": t.loc[t["warn_split_unbereinigt"], "titel"].tolist(),
              "fehler": fehler, "fundamentaldaten": FUND}
    with open(os.path.join(OUT, "status.json"), "w") as fh:
        json.dump(status, fh, ensure_ascii=False, indent=2)
    print(json.dumps(status, ensure_ascii=False, indent=2))
    if status["titel_ok"] < 0.8 * len(UNIVERSUM):
        sys.exit("Weniger als 80 % der Titel aktuell – Lauf als fehlgeschlagen markiert.")

if __name__ == "__main__":
    main()
