# Albert — die Wunschmaschine

Ein lokaler Sprach-KI-Assistent mit drei wählbaren Personas (Albert, Albertine,
Alex). Läuft als kleine Weboberfläche: Persona auswählen, Start drücken,
einfach drauflos reden. Im Gespräch führt Albert die Person vom abstrakten
Zukunftswunsch zu einer eigenen, konkreten lokalen Idee (der
"Wunsch-Trichter") oder nimmt ein Anliegen bzw. eine Beobachtung auf. Beides
wird zur Prüfung durch das Team in Airtable erfasst — Wünsche lassen sich
zusätzlich direkt ausdrucken und ans Board hängen.

## Schnellstart (empfohlen)

Einfach **`Albert-starten.bat`** doppelklicken. Das Skript:
- prüft, ob Python installiert ist (sonst kurzer Hinweis mit Download-Link)
- fragt, welche Version laufen soll (Pfeiltasten + Enter) — die aktuell
  laufende Version ist in der Liste markiert und vorausgewählt, läuft nach
  10 Sekunden ohne Eingabe automatisch damit weiter; alternativ lässt sich
  explizit eine andere Version (Update oder Downgrade auf ein Tag) wählen
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
   (`OPENAI_API_KEY`, `AIRTABLE_API_TOKEN`) -- die Airtable-Base selbst ist
   fest in `config.py` hinterlegt, nicht geheim, und ueber Git ausgerollt:

   ```bash
   copy .env.example .env
   ```

3. Server starten:

   ```bash
   python server.py
   ```

## Verwendung

`http://127.0.0.1:8000` im Browser öffnen:

1. Persona auswählen (Albert / Albertine / Alex — welche zur Auswahl stehen,
   lässt sich in den Einstellungen festlegen)
2. "Start" drücken — die Person verbindet sich und begrüsst dich
3. Je nach Einstellung entweder einfach drauflos reden (freihändig, Server
   erkennt selbst, wann jemand spricht) oder den grünen Knopf gedrückt
   halten, solange man spricht (Push-to-Talk -- der Knopf löst technisch
   die Leertaste aus)
4. Gibt es einen Zukunftswunsch, fragt Albert nach, was sich hier vor Ort
   ändern würde und was man konkret tun könnte — erst dann wird erfasst.
   Bei einem Anliegen/einer Beobachtung reicht eine kurze Bestätigung.
5. Ist Drucken aktiviert, fragt Albert nach einem erfassten Wunsch, ob er
   ausgedruckt werden soll — bei "Ja" wird sofort auf dem eingestellten
   Drucker gedruckt, kein Klick auf einen Link nötig
6. "Stop" beendet die Verbindung wieder, der Chatverlauf bleibt sichtbar
7. Beim ersten Start fragt der Browser nach Mikrofonzugriff — ohne Freigabe
   funktioniert nur die Sprachausgabe, nicht die Spracheingabe

Der Status-Badge oben zeigt jederzeit, ob die Verbindung aktiv ist. Der
Footer unten (auf jeder Seite gleich) verlinkt zum Themen-Board, zu den
Einstellungen und zeigt die laufende Version.

### Weitere Seiten

- **`/setup.html`** ("Einstellungen", auch im Footer verlinkt) — hier lässt
  sich festlegen: welche Personen angezeigt werden, welche Stimme jede
  Person hat (mit "Vorhören"-Knopf für einen Audio-Testsatz direkt in der
  Seite), freihändig vs. Push-to-Talk, ob und auf welchem Drucker gedruckt
  wird (inkl. "Testseite drucken"-Knopf, unabhängig von einem Gespräch),
  wie viele Einträge das Themen-Board je Spalte zeigt, und ob
  Debug-Informationen im Gespräch angezeigt werden.
- **`/board.html`** ("Themen-Board", auch im Footer verlinkt) — für einen
  zweiten Monitor gedacht: zeigt live und synchron aus Airtable die
  neuesten Anliegen und Zukunftswünsche als Post-its (Anzahl je Spalte
  einstellbar). Rechtsklick auf eine Notiz markiert sie in Airtable als
  "rejected" (kein echtes Löschen, sondern der normale Team-Workflow).
- **`/about.html`** ("Über diese App", auch im Footer verlinkt) —
  Transparenz-Seite für Besucherinnen und Besucher: ein Strukturbild
  zeigt, was lokal auf dem Gerät passiert, wofür die OpenAI-Realtime-API
  gebraucht wird und wo erfasste Wünsche/Anliegen landen (Airtable).
  Über den "Diese Seite drucken"-Knopf lässt sich die Seite auch
  ausdrucken und z.B. neben dem Gerät aufhängen.

### Themen-Board auf einem zweiten Rechner

Das Board holt seine Daten direkt aus Airtable (nicht aus etwas Lokalem)
und fragt alle 15 Sekunden nach — ein zweiter Rechner braucht also keine
Netzwerkverbindung zum ersten. Einfach eine eigene, unabhängige
Albert-Installation aufsetzen (Ordner kopieren oder Repo klonen,
`Albert-starten.bat` starten, `.env` ausfüllen) und dort statt der
Startseite `http://127.0.0.1:8000/board.html` öffnen. Für die reine
Board-Anzeige reicht ein Platzhalter bei `OPENAI_API_KEY` — der wird erst
für echte Gespräche gebraucht — solange `AIRTABLE_API_TOKEN` Zugriff auf
dieselbe Base hat.

## Drucken

Ist in den Einstellungen ein Drucker ausgewählt und Drucken aktiviert, kann
ein erfasster Zukunftswunsch direkt auf Papier ausgegeben werden — per
echtem Windows-Druckauftrag (direkt über GDI, ohne dass sich eine externe
Anwendung öffnet), ausgelöst entweder per Sprache im Gespräch oder über den
Button im Chat. Das Layout (Titel, Wunsch, Warum, lokale Idee, Platz für
eine Skizze) lässt sich vorab auch als PDF unter `/api/wish/{id}/pdf`
ansehen — beide Ausgaben nutzen denselben Aufbau.

## Airtable-Anbindung

Albert erfasst per Function-Calling zwei Arten von Einträgen in der Tabelle
`_input_pipeline` (zur Prüfung durch das Team, erscheint also nicht sofort
live in der Datenbank):
- **`submit_wish`**: ein Zukunftswunsch — Originalwunsch, warum er der
  Person wichtig ist, und eine selbst entwickelte lokale Idee dazu
- **`submit_challenge`**: ein Anliegen oder eine Beobachtung, die jemanden
  beschäftigt

Alle drei Personas haben feste Leitplanken (jugendfrei, kein Bezug zu
politischen/religiösen Themen, Schweizer Hochdeutsch ohne "ß") in ihren
Instruktionen (`personas.py`, `persona_behavior.md`).

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

## Changelog

Wird bei jedem Tag aktualisiert.

- **v1.2.8** — Persona-Avatare auf der Startseite ersetzt: statt der
  selbst gezeichneten Platzhalter jetzt fertige "Avataaars"-Illustrationen
  (via DiceBear), passend zu jeder Person -- Albert z.B. deutlich älter
  und mit Schnurrbart. "Über diese App" auf Wunsch technischer
  formuliert (konkrete Modell-/Protokoll-/API-Angaben).
- **v1.2.7** — Neue Transparenz-Seite `/about.html` ("Über diese App",
  im Footer verlinkt): Strukturbild zeigt Besucherinnen und Besuchern,
  was lokal passiert, wofür OpenAI gebraucht wird und wo Wünsche/
  Anliegen gespeichert werden (Airtable) -- inklusive Druckfunktion,
  um die Seite z.B. neben dem Gerät aufzuhängen.
- **v1.2.6** — Abschied vor Gesprächsende zuverlässig gemacht: statt sich
  auf das Modell zu verlassen, erzwingt der Server jetzt eine eigene,
  dedizierte Abschieds-Antwort (Dank, Hinweis dass der Chatverlauf
  gelöscht wird, freundlicher Wunsch) -- inkl. Fix einer Race Condition,
  die den Abschied manchmal übersprang. Layout-Abstand zum Footer im
  Gespräch behoben. Neues Test-Kommando ("mach schneller") für
  schnelleres manuelles Durchtesten bis zur Druckfrage.
- **v1.2.5** — Gespräch endet nach der Verabschiedung automatisch und
  springt zur Personenauswahl zurück (neues Tool `end_conversation`,
  wartet bis der Abschiedssatz zu Ende gesprochen ist). Begrüssung
  natürlicher formuliert ("Hey, schön bist du da!"), und Albert darf
  bei lockerem Reden mitgehen, statt sofort in die Wunsch/Anliegen-
  Fragen zu springen -- schlägt aber vor Gesprächsende den Bogen dahin
  zurück.
- **v1.2.4** — README dokumentiert, wie man das Themen-Board auf einem
  zweiten Rechner anzeigt (eigene, unabhaengige Albert-Installation, da
  das Board direkt aus Airtable liest -- keine Netzwerkverbindung
  zwischen den Rechnern noetig).
- **v1.2.3** — Airtable-Base auf "HSG-SSI-ecosystem (DEV_v2)" umgestellt.
  Die Base-ID ist kein Geheimnis (nur der Zugriffstoken ist einer) und
  lebt deshalb jetzt in `config.py` statt in der gitignoreten `.env` --
  ein kuenftiger Wechsel rollt damit automatisch per Tag an alle
  Geraete aus, ohne dass jedes Geraet einzeln in `.env` angepasst
  werden muss.
- **v1.2.2** — Kritischen Self-Modifying-Script-Bug im Start-Skript
  behoben: ein Versionswechsel per `git checkout` konnte die gerade
  laufende `Albert-starten.bat` mitten in der Ausfuehrung veraendern und
  dadurch kaputte Befehle erzeugen (auf einem echten Geraet beobachtet:
  `ION_ACTION` statt `VERSION_ACTION`, `%b` statt der Versionsnummer).
  Das Skript kopiert sich jetzt beim Start zuerst in einen Temp-Ordner
  und laeuft von dort aus weiter.
- **v1.2.1** — Toten Code entfernt (`static/wunschzettel.html`);
  Entwicklungs-Branches (alles ausser `main`) ueberspringen die
  Versionsauswahl komplett, statt bei jedem Testlauf auf einen Tag zu
  wechseln
- **v1.2.0** — Versions-Menue vereinfacht: nur noch Tags zur Auswahl,
  kein separater "main"-Eintrag mehr (main koennte theoretisch weiter
  sein als der letzte Tag, wenn ein Merge vergessen wird zu taggen --
  jetzt ist immer nur ein echt veroeffentlichter Stand waehlbar)
- **v1.1.8** — Fehler beim Versionswechsel (Update/Downgrade) im
  Start-Skript sichtbar gemacht statt stillschweigend zu verwerfen
- **v1.1.7** — Changelog eingefuehrt, damit jedes Tag eine echte
  Aenderung dokumentiert
- **v1.1.6** — README auf aktuellen Stand gebracht, Versions-Menue beim
  Start ueberarbeitet (laufende Version in der Liste markiert,
  10s-Fortschrittsbalken statt 5s-Countdown)
- **v1.1.5** — Footer-Links nicht mehr unterstrichen
- **v1.1.4** — Versionsauswahl-Menue beim Start (Pfeiltasten, "Bleiben"
  als Standard)
- **v1.1.3** — Standard-Stimmen auf Ash/Shimmer/Alloy gesetzt
- **v1.1.2** — Stimmen pro Person waehlbar, mit Vorhoer-Button in den
  Einstellungen; Themen-Board-Link in den Footer verschoben
- **v1.1.1** — Druck-Flow gehaertet (Druckfrage wird nicht mehr
  uebersprungen), Wunschzettel-Layout an PDF-Vorschau angeglichen
- **v1.1.0** — Wunschmaschine: Zukunftswuensche und Anliegen per Sprache
  sammeln (Wunsch-Trichter), echtes Drucken, Einstellungsseite,
  live-synchronisiertes Themen-Board
- **v1.0.0** — Erste Version: Albert Sprachassistent mit
  Airtable-Anbindung, Themen-Board und Ein-Klick-Launcher
