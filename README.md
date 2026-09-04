# Albert

Ein lokaler Sprach-KI-Assistent mit drei wählbaren Personas (Albert, Albertine,
Alex) — die "Wunschmaschine". Läuft als kleine Weboberfläche: Persona
auswählen, Start drücken, einfach drauflos reden (kein Knopf zum Sprechen
nötig, Albert hört durchgehend zu). Sammelt Zukunftswünsche und Anliegen von
Besuchern und erfasst sie zur Prüfung durch das Team in Airtable.

## Schnellstart (empfohlen)

Einfach **`Albert-starten.bat`** doppelklicken. Das Skript:
- prüft, ob Python installiert ist (sonst kurzer Hinweis mit Download-Link)
- legt beim ersten Mal automatisch eine virtuelle Umgebung an
- installiert/aktualisiert alle benötigten Python-Pakete automatisch
- fragt beim allerersten Start nach den Zugangsdaten (`.env`, öffnet sich
  automatisch zum Ausfüllen)
- startet den Server und öffnet die Weboberfläche im Browser

Das funktioniert auch nach dem Kopieren des ganzen Ordners auf einen anderen
Rechner (z.B. via GitHub-Klon oder USB-Stick) — es muss nur Python 3.11+
bereits installiert sein, den Rest erledigt das Skript.

## Manuelles Setup (Alternative)

1. Virtuelle Umgebung anlegen und Abhaengigkeiten installieren:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. `.env.example` zu `.env` kopieren und die eigenen Zugangsdaten eintragen
   (`OPENAI_API_KEY`, `AIRTABLE_API_TOKEN`, `AIRTABLE_BASE_ID`):

   ```bash
   copy .env.example .env
   ```

3. Server starten:

   ```bash
   python server.py
   ```

## Verwendung

`http://127.0.0.1:8000` im Browser öffnen:

1. Persona auswählen (Albert / Albertine / Alex)
2. "Start" drücken — die Person verbindet sich und begrüsst dich
3. Einfach drauflos reden — kein Knopf nötig, Albert hört durchgehend zu
   und erkennt selbst, wann jemand spricht (Server-VAD)
4. "Stop" beendet die Verbindung wieder, der Chatverlauf bleibt sichtbar
5. Beim ersten Start fragt der Browser nach Mikrofonzugriff — ohne Freigabe
   funktioniert nur die Sprachausgabe, nicht die Spracheingabe

Der Status-Badge oben zeigt jederzeit, ob die Verbindung aktiv ist.

### Weitere Seiten

- **`/board.html`** — Themen-Board für einen zweiten Monitor: zeigt live,
  wonach gesucht wurde und was neu erfasst wurde, als verschiebbare Post-its.
  Rechtsklick auf eine Notiz zum Löschen.

## Airtable-Anbindung

Albert erfasst per Function-Calling zwei Arten von Einträgen in der Tabelle
`_input_pipeline` (zur Prüfung durch das Team, erscheint also nicht sofort
live in der Datenbank):
- **`submit_wish`**: ein Zukunftswunsch, inkl. selbst entwickelter lokaler Idee
- **`submit_challenge`**: ein Anliegen oder eine Beobachtung, die jemanden
  beschäftigt

Alle drei Personas haben feste Leitplanken (jugendfrei, kein Bezug zu
politischen/religiösen Themen) in ihren Instruktionen (`personas.py`).

## Alternative: Konsolen-Variante

Für Tests ohne Browser gibt es weiterhin ein einfaches Konsolen-Skript mit
fester Stimme/Persona (`config.py`):

```bash
python main.py
```

Leertaste gedrueckt halten, um zu sprechen; loslassen, damit Albert antwortet.
Mit Strg+C beenden. Nicht gleichzeitig mit `server.py` starten (beide
belegen Mikrofon/Lautsprecher).

Hinweis: Beide Varianten benoetigen Zugriff auf Mikrofon und Lautsprecher
(ueber `sounddevice`/PortAudio bzw. die Browser-Audio-APIs).
