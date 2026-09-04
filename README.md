# Albert

Ein lokaler Sprach-KI-Assistent mit drei wählbaren Personas (Albert, Albertine,
Alex). Läuft als kleine Weboberfläche: Persona auswählen, Start drücken,
Leertaste halten zum Sprechen. Kann per Sprache im regionalen Ökosystem
(Airtable) nachschlagen, was es an Initiativen/Organisationen/Personen gibt,
und neue Beiträge erfassen.

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
2. "Start" drücken — die Person verbindet sich und begrüßt dich
3. Leertaste gedrückt halten, um zu sprechen; loslassen für die Antwort
4. "Stop" beendet die Verbindung wieder, der Chatverlauf bleibt sichtbar
5. Beim ersten Start fragt der Browser nach Mikrofonzugriff — ohne Freigabe
   funktioniert nur die Sprachausgabe, nicht die Spracheingabe

Der Status-Badge oben zeigt jederzeit, ob die Verbindung aktiv ist.

### Weitere Seiten

- **`/board.html`** — Themen-Board für einen zweiten Monitor: zeigt live,
  wonach gesucht wurde und was neu erfasst wurde, als verschiebbare Post-its.
  Rechtsklick auf eine Notiz zum Löschen.

## Airtable-Anbindung

Albert kann per Function-Calling auf eine Airtable-Basis zugreifen:
- **Nachschlagen** (`list_entities`): Initiativen, Organisationen, Personen
- **Neu erfassen** (`submit_contribution`): Organisation, Person, Initiative,
  Challenge oder Event — landet zur Prüfung durch das Team in der Tabelle
  `_input_pipeline`, erscheint also nicht sofort live in der Datenbank

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
