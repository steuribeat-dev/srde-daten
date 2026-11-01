# SRDE-Datenabruf mit GitHub Actions – Einrichtung

Dauer: ca. 30–60 Minuten. Kosten: für ein privates Repository mit dieser Nutzung in der Regel kostenlos.
Ihr EODHD-API-Schlüssel wird nur in GitHub als verschlüsseltes «Secret» hinterlegt – nie im Code, nie im Chat.

## 1. GitHub-Konto
Falls noch nicht vorhanden: auf https://github.com ein Konto eröffnen (Zwei-Faktor-Anmeldung einschalten).

## 2. Privates Repository anlegen
1. Oben rechts «+» → «New repository».
2. Name: `srde-daten`. Sichtbarkeit: **Private**. «Add a README» nicht anhaken.
3. «Create repository».

## 3. Dateien hochladen
1. Im neuen Repository auf «uploading an existing file» klicken.
2. Den **Inhalt** des entpackten Ordners `srde-daten` hineinziehen: `srde_abruf.py`, `ANLEITUNG.md`, den Ordner `data` und den Ordner `.github`.
   Hinweis: Der Ordner `.github` ist auf dem Mac versteckt. Im Finder mit **Cmd + Shift + .** sichtbar machen.
   Falls der Upload den Ordner `.github` nicht übernimmt: «Add file» → «Create new file», als Namen
   `.github/workflows/srde_abruf.yml` eintippen und den Inhalt der gleichnamigen Datei hineinkopieren.
3. «Commit changes».

## 4. API-Schlüssel als Secret hinterlegen
1. Im Repository: «Settings» → «Secrets and variables» → «Actions».
2. Reiter «Secrets» → «New repository secret».
3. Name: `EODHD_API_KEY`, Wert: Ihr EODHD-Schlüssel → «Add secret».

## 5. Optional: Fundamentaldaten
Nur wenn Ihr EODHD-Abo Fundamentaldaten enthält (im EODHD-Konto unter Ihrem Plan ersichtlich):
«Settings» → «Secrets and variables» → «Actions» → Reiter «Variables» → «New repository variable»:
Name `FUNDAMENTALS`, Wert `true`. Ohne diese Variable werden nur Kursdaten geladen.

## 6. Erster Testlauf
1. Reiter «Actions». Falls GitHub fragt, Workflows aktivieren.
2. Links «SRDE Datenabruf» → rechts «Run workflow» → «Run workflow».
3. Nach 1–3 Minuten erscheint ein grüner Haken. Im Ordner `data` liegen dann:
   - `kennzahlen.csv` – eine Zeile pro Titel mit Kurs, 50/200-Tage-Schnitt, Abständen, Renditen 3/6/12 Monate, Schwankung, Liquidität, Warnungen
   - `status.json` – Handelstag, Anzahl aktueller Titel, veraltete Titel, Split-Warnungen, Fehler
   - `historie/` – Kurshistorie pro Titel (ca. 14 Monate)
4. Roter Fehler? Auf den Lauf klicken, die Meldung kopieren und im Chat schicken (der Schlüssel erscheint dort nicht).

## 7. Danach läuft es automatisch
Werktags um 17:45 UTC (18:45 Uhr Zürich im Winter, 19:45 Uhr im Sommer). Bei einem Fehler schickt GitHub
eine E-Mail an Ihre GitHub-Adresse (Einstellung unter «Settings» → «Notifications» → «Actions»).

## 8. Verbindung zur Montags-Rangliste
Schicken Sie im Chat Ihren GitHub-Benutzernamen und den Repository-Namen (z. B. `ihrname/srde-daten`).
Die wöchentliche Rangliste liest dann die Kursdaten aus `data/kennzahlen.csv` statt aus Webquellen.
