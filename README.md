# Albert

Ein lokaler Sprach-KI-Assistent mit drei wählbaren Personas (Albert, Albertine,
Alex). Läuft als kleine Weboberfläche: Persona auswählen, Start drücken,
Leertaste halten zum Sprechen.

## Setup

1. Virtuelle Umgebung anlegen und Abhaengigkeiten installieren:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. `.env.example` zu `.env` kopieren und den eigenen OpenAI API-Key eintragen:

   ```bash
   copy .env.example .env
   ```

## Starten (Weboberfläche, empfohlen)

```bash
python server.py
```

Dann `http://127.0.0.1:8000` im Browser öffnen:

1. Persona auswählen (Albert / Albertine / Alex)
2. "Start" drücken — die Person verbindet sich und begrüßt dich
3. Leertaste gedrückt halten, um zu sprechen; loslassen für die Antwort
4. "Stop" beendet die Verbindung wieder, der Chatverlauf bleibt sichtbar
5. Beim ersten Start fragt der Browser nach Mikrofonzugriff — ohne Freigabe
   funktioniert nur die Sprachausgabe, nicht die Spracheingabe

Der Status-Badge oben zeigt jederzeit, ob die Verbindung aktiv ist.

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

## Naechste Ausbaustufe (noch nicht implementiert)

Albert soll spaeter per Function Calling auf eine Airtable-Basis ("R-Table")
zugreifen koennen: bestehende Initiativen inkl. ihres "Dock"-Felds abrufen
und neue Initiativen anlegen, falls sie dort noch fehlen. Dafuer ist bereits
das leere Paket `tools/` vorgesehen, in dem die entsprechenden Tool-Definitionen
ergaenzt werden koennen, ohne den Rest der App anzufassen.
