"""
Erfasst Käufe und Verkäufe in data/positionen.csv.
Wird über GitHub Actions («Position erfassen») mit Formular-Eingaben gestartet.
Stop = Kaufkurs − 2 × ATR14 (aus data/kennzahlen.csv, letzter Abruf).
"""
import csv, os, sys, datetime as dt

BASIS = os.path.dirname(os.path.abspath(__file__))
POS = os.path.join(BASIS, "data", "positionen.csv")
KZ = os.path.join(BASIS, "data", "kennzahlen.csv")
SPALTEN = ["titel", "kaufdatum", "kaufkurs", "stueck", "stop", "ziel"]

def zahl(s, name, ganz=False):
    s = (s or "").strip().replace("'", "").replace(",", ".")
    if not s:
        return None
    try:
        v = float(s)
    except ValueError:
        sys.exit(f"Ungültige Zahl bei {name}: {s}")
    if v <= 0:
        sys.exit(f"{name} muss grösser als 0 sein")
    if ganz:
        if v != int(v):
            sys.exit(f"{name} muss eine ganze Zahl sein")
        return int(v)
    return v

def lesen():
    if not os.path.exists(POS):
        return []
    with open(POS, newline="", encoding="utf-8") as fh:
        zeilen = [z.strip() for z in fh.read().splitlines() if z.strip()]
    if not zeilen:
        return []
    r = csv.DictReader(zeilen)
    r.fieldnames = [f.strip() for f in r.fieldnames]
    return [{k: (row.get(k) or "").strip() for k in SPALTEN} for row in r]

def schreiben(pos):
    with open(POS, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SPALTEN, lineterminator="\n")
        w.writeheader()
        for p in sorted(pos, key=lambda x: x["titel"]):
            w.writerow(p)

KZ_EU = os.path.join(BASIS, "data", "kennzahlen_europa.csv")

def atr(titel):
    """ATR14 in Handelswährung: Schweizer Titel aus kennzahlen.csv (atr_chf),
    europäische Titel (Format KÜRZEL.BÖRSE, z. B. SIE.XETRA) aus kennzahlen_europa.csv (atr)."""
    for datei, spalte in ((KZ, "atr_chf"), (KZ_EU, "atr")):
        if not os.path.exists(datei):
            continue
        with open(datei, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row["titel"].upper() == titel:
                    try:
                        return float(row.get(spalte) or ""), True
                    except ValueError:
                        return None, True
    return None, False

def main():
    aktion = os.environ.get("AKTION", "").strip()
    titel = os.environ.get("TITEL", "").strip().upper()
    stueck = zahl(os.environ.get("STUECK"), "Anzahl", ganz=True)
    kurs = zahl(os.environ.get("KURS"), "Kurs")
    ziel = zahl(os.environ.get("ZIEL"), "Ziel")
    datum = (os.environ.get("DATUM") or "").strip() or dt.date.today().isoformat()
    try:
        dt.date.fromisoformat(datum)
    except ValueError:
        sys.exit(f"Datum im Format JJJJ-MM-TT angeben, nicht {datum}")
    if not titel:
        sys.exit("Titel (Kürzel) fehlt")

    pos = lesen()
    alt = next((p for p in pos if p["titel"] == titel), None)

    if aktion == "Kauf":
        if not stueck or not kurs:
            sys.exit("Für einen Kauf Anzahl und Kurs angeben")
        a, bekannt = atr(titel)
        if not bekannt:
            sys.exit(f"{titel} ist weder in kennzahlen.csv noch in kennzahlen_europa.csv – Kürzel prüfen "
                         f"(Schweiz z. B. NOVN, Europa z. B. SIE.XETRA). Nichts geändert.")
        if alt:  # Nachkauf: Durchschnittskurs
            n_alt, k_alt = int(alt["stueck"] or 0), float(alt["kaufkurs"] or 0)
            n = n_alt + stueck
            kurs_neu = (n_alt * k_alt + stueck * kurs) / n if n_alt and k_alt else kurs
            alt.update(kaufkurs=f"{kurs_neu:.2f}", stueck=str(n))
            if a: alt["stop"] = f"{kurs_neu - 2 * a:.2f}"
            if ziel: alt["ziel"] = f"{ziel:.2f}"
            print(f"Nachkauf {titel}: jetzt {n} Stück, Ø-Kurs {kurs_neu:.2f}, Stop {alt['stop'] or 'fehlt'}")
        else:
            p = {"titel": titel, "kaufdatum": datum, "kaufkurs": f"{kurs:.2f}", "stueck": str(stueck),
                 "stop": f"{kurs - 2 * a:.2f}" if a else "", "ziel": f"{ziel:.2f}" if ziel else ""}
            pos.append(p)
            print(f"Kauf {titel}: {stueck} Stück zu {kurs:.2f}, Stop {p['stop'] or 'fehlt'}, "
                  f"Notausgang {kurs * 0.8:.2f}, Ziel {p['ziel'] or 'fehlt'}")
    elif aktion == "Verkauf":
        if not alt:
            sys.exit(f"{titel} ist nicht in positionen.csv")
        gehalten = int(alt["stueck"] or 0)
        if stueck and gehalten and stueck < gehalten:
            alt["stueck"] = str(gehalten - stueck)
            print(f"Teilverkauf {titel}: {stueck} verkauft, {alt['stueck']} verbleiben")
        else:
            pos.remove(alt)
            print(f"Verkauf {titel}: Position entfernt")
        if kurs and alt.get("kaufkurs"):
            k = float(alt["kaufkurs"])
            print(f"Ergebnis je Aktie vor Gebühren: {kurs - k:+.2f} (Handelswährung, {(kurs / k - 1) * 100:+.1f} %)")
    else:
        sys.exit("Aktion muss «Kauf» oder «Verkauf» sein")

    schreiben(pos)
    print(f"Positionen: {len(pos)} von 8 belegt")
    with open(POS, encoding="utf-8") as fh:
        print(fh.read())

if __name__ == "__main__":
    main()
