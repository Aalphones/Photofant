# Photofant — ComfyUI-Workflow-Integration (Konzept)

> Ergänzung zu *Konzept-Photofant.md*, Abschnitt „Stage 5 — Generative Features".

## Leitidee

Photofant **triggert** Workflows, ComfyUI **führt aus**. Das Ergebnis landet in
ComfyUIs eigenem `output/`-Ordner und wird **dort** reviewt. Es gibt **kein
automatisches Zurückschreiben** nach Photofant — die Übernahme als Edit ist ein
separater, bewusster Schritt (deckt sich mit dem Leitprinzip „Edits nur durch
aktives Speichern").

- **Default:** Fire-and-Forget. Photofant feuert den Workflow ab, danach läuft
  alles in ComfyUI.
- **Optional:** bewusster Import eines ausgewählten Ergebnisses als Edit.

Dadurch bleibt die Trennung sauber: Photofant ist Bibliothek + Auslöser, ComfyUI
ist die generative Werkbank.

---

## 1. Einstellungen — wo läuft ComfyUI

Im `settings`-Bereich, neben der Modell-Registry:

| Feld | Zweck | Default |
|---|---|---|
| `enabled` | ComfyUI-Integration an/aus | `false` |
| `base_url` | Host + Port der ComfyUI-Instanz | `http://127.0.0.1:8188` |
| `client_id` | Kennung für Queue-Zuordnung | `photofant` |
| `output_dir` | Pfad zu ComfyUIs `output/` (nur für Direkt-Import bei lokalem Lauf) | leer |
| `timeout` | HTTP-Timeout in Sekunden | `10` |

**„Verbindung testen"-Button** → `GET /system_stats`. Schlägt das fehl, klare
Meldung (was erwartet, was gefunden, nächster Schritt — analog Fehlerklassen aus
Abschnitt 12.2a). Generative Features bleiben gated, bis die Verbindung steht.

> Kein eingebauter Auth-Layer in ComfyUI. Lokal unkritisch; Port konfigurierbar
> halten, falls ComfyUI auf einem anderen Rechner läuft.

---

## 2. Workflow-Template-Registry

Keine Workflows im Repo-Code. Stattdessen: pro Workflow eine **Konfiguration**
plus eine **Template-Datei** im ComfyUI-**API-Format** (Export via „Save (API
Format)" — nicht das normale UI-Workflow-JSON).

Workflows werden **in den Einstellungen angelegt und verwaltet** (Template
hochladen/verweisen, Inputs/Params binden, validieren). Die Galerie-Run-Leiste
(Abschnitt 3a) konsumiert nur die dort registrierten, aktiven Workflows.

### 2.1 Konfigurationsmodell

| Feld | Beschreibung |
|---|---|
| `id` | eindeutige interne ID |
| `name` | Anzeigename in der UI |
| `category` | `upscale` / `img2img` / `inpaint` / `generic` … |
| `template_path` | Pfad zur API-Format-JSON |
| `inputs[]` | Bild-Eingänge (s.u.) |
| `params[]` | optional exponierte Parameter (s.u.) |

**inputs[]** — pro Eingangsbild:

| Feld | Beschreibung |
|---|---|
| `key` | logischer Name, z.B. `source`, `reference`, `mask` |
| `label` | UI-Beschriftung des Slots, z.B. „Quellbild", „Referenz" |
| `node_title` | bevorzugte Bindung über `_meta.title` des Nodes |
| `node_id` | Fallback-Bindung über Node-ID |
| `field` | Feld im Node, Default `image` |
| `kind` | `image` / `mask` — steuert die Slot-Bedienung (Bibliotheks-Picker vs. Masken-Editor) |
| `required` | Pflichteingang ja/nein |
| `lockable` | ob der Slot per 🔒 gegen versehentliches Re-Armen gesperrt werden kann (typisch für die Konstante) |

**params[]** — optional exponierte Felder (Skalierung, Denoise, Seed, Prompt …):

| Feld | Beschreibung |
|---|---|
| `key`, `label` | Name + UI-Beschriftung |
| `node_title` / `node_id` | Zielnode |
| `field` | Feld im Node |
| `type` | `float` / `int` / `string` / `enum` |
| `default`, `min`, `max`, `step`, `options` | Wertebereich für die UI |

### 2.2 Bindung über Titel, nicht über Reihenfolge

Eingänge werden über `_meta.title` gebunden (im ComfyUI-Workflow den
`LoadImage`-Nodes eindeutige Titel geben, z.B. „Source", „Reference"). Node-IDs
sind nur Fallback — sie ändern sich, sobald jemand den Workflow umbaut.

### 2.3 Validierung beim Registrieren

Template laden und prüfen, dass alle gebundenen `node_title`/`field` existieren.
Fehlt eine Bindung → klare Fehlermeldung, **kein stummes Scheitern** (Abschnitt
19.8). Der Workflow bleibt deaktiviert, bis die Bindung stimmt.

### 2.4 Voraussetzung am Workflow

Der Workflow muss mit einem `SaveImage`-Node enden, sonst landet nichts in
`output/`. Empfehlung: `filename_prefix` setzen (z.B. `photofant/<workflow-id>`),
damit Photofant-Runs im Output-Ordner wiederzuerkennen sind.

---

## 2a. Workflow-Verwaltung in den Einstellungen

Workflows werden ausschließlich hier angelegt, gebunden, validiert und aktiviert.
Die Galerie-Run-Leiste (Abschnitt 3a) konsumiert nur das Ergebnis.

### 2a.1 Anlegen

- Name + Kategorie wählen.
- Template (API-Format-JSON) hochladen oder referenzieren. Empfehlung: hochgeladene
  Templates in einen Photofant-verwalteten `workflows/`-Ordner kopieren, damit der
  Workflow selbst-enthalten ist. Die Bindungs-Config selbst lebt in der DB
  (konsistent mit „DB ist alleinige Wahrheit").

### 2a.2 Introspektion — Name-Hooks erkennen

Beim Laden parst Photofant das Template und listet alle Nodes mit `_meta.title` und
`class_type`. Daraus:

- erkennt es Bild-Eingänge (`LoadImage`, Mask-Loader, bekannte Custom-Loader),
- bietet die vorhandenen **Titel als Name-Hooks** zur Auswahl an — Dropdown statt
  Abtippen.

> **Name-Hook = `_meta.title`.** Der Workflow-Autor gibt in ComfyUI jedem
> Eingangs-Node einen eindeutigen, sprechenden Titel (z.B. „Reference", „Source",
> „Mask"). Über diesen Titel bindet Photofant — niemals über Reihenfolge oder
> Node-ID (die ändern sich beim Umbauen).

### 2a.3 Inputs definieren — 1 bis x

Beliebig viele Inputs. Pro Input eine Zeile, mit „Input hinzufügen" / „entfernen":

| Feld | Quelle / Bedienung |
|---|---|
| `key` | logischer Name (aus Titel vorgeschlagen) |
| `label` | UI-Beschriftung des Slots |
| `node_title` | **Name-Hook**, Dropdown aus erkannten Titeln (Freitext als Fallback) |
| `field` | Node-Feld, Default `image` |
| `kind` | `image` / `mask` |
| `required` | Pflicht ja/nein |
| `lockable` | per 🔒 gegen versehentliches Re-Armen sperrbar (typisch Konstante) |

**Auto-Vorschlag:** Photofant legt pro erkanntem Eingangs-Node automatisch einen
Input-Vorschlag an (Titel → `key`/`label`/`node_title` vorbefüllt). Der Nutzer
bestätigt oder passt an. Damit ist der Fall 1..x ohne Tipparbeit abgedeckt — egal
ob ein Upscale mit einem Input oder ein Multi-Subject-Workflow mit fünf.

### 2a.4 Parameter definieren — 0 bis x

Analog und optional: `key`, `label`, `node_title` (Hook), `field`, `type`
(`float`/`int`/`string`/`enum`), `default`, `min`/`max`/`step`/`options`.

### 2a.5 Validierung (kein stummes Scheitern)

Vor dem Aktivieren prüft Photofant:

- Jeder gebundene `node_title` **existiert** im Template und ist **eindeutig** —
  zwei Nodes mit gleichem Titel → Konflikt, blockiert, mit Hinweis, den Titel im
  Workflow eindeutig zu machen.
- Jedes gebundene `field` existiert im Zielnode.
- Mindestens ein `SaveImage` vorhanden (sonst Warnung: kein Output in `output/`).

Jeder Fehler nennt **was erwartet, was gefunden, nächster Schritt** (Abschnitt
19.8 / 12.2a). Bei Re-Import eines geänderten Templates werden Bindungen, die nicht
mehr passen, markiert statt still zu brechen.

### 2a.6 Aktivierung & Verwaltung

- Workflow erst **triggerbar**, wenn valide **und** ComfyUI-Verbindung steht (Gating).
- Liste aller Workflows mit Status (aktiv / inaktiv / invalide) und Aktionen:
  bearbeiten, duplizieren, löschen, aktiv schalten.
- Nur aktive, valide Workflows erscheinen im Dropdown der Galerie-Run-Leiste.

---

## 3. Trigger-Flow (Default, Fire-and-Forget)

1. Nutzer wählt Workflow, bindet App-Asset(s) an Input(s), setzt optional Params.
2. Job geht in die bestehende Queue (in-process, idempotent, SSE-Fortschritt).
3. Worker: für jeden Bild-Input → `POST /upload/image` → Filename ins Template
   (auf einer **Kopie** des Templates, `deepcopy`).
4. Params ins Template patchen.
5. `POST /prompt` → `prompt_id`.
6. *(optional)* `/ws` oder `/history/{prompt_id}` pollen → Status
   „läuft / fertig / Fehler" zurück an die UI.
7. **Fertig.** UI zeigt: „An ComfyUI gesendet — dort ansehen" (+ `prompt_id`).

Photofants Arbeit ist mit Schritt 5 getan. Alles Weitere passiert in ComfyUI und
ist dort einsehbar.

---

## 3a. UX — Inline in der Galerie (Run-Leiste, kein Dialog)

Statt eines eigenen Dialogs wird die **Galerie selbst zum Picker**. So bleiben die
vollen Filter-, Such- und Sortier-Funktionen der Galerie nutzbar, ohne eine zweite
Auswahl-UI zu bauen.

### Einstieg

Ein **Action-Button** (in der Filterleiste oder separat, z.B. Wand-/Funken-Icon)
aktiviert den Workflow-Modus und blendet eine schlanke, angedockte **Run-Leiste**
ein. Diese enthält:

- **Workflow-Auswahl** (Dropdown) — gespeist aus den in den Einstellungen
  angelegten Workflows (s. Abschnitt 2 / 1).
- **Einen Slot pro Input** (Beschriftung aus `label`: „Input 1 / Referenz",
  „Input 2 / Quelle"), je mit Thumbnail nach Bindung.
- **Feuer-Button** und **Reset-Button**.

### Ablauf (Armed-Slot-Prinzip)

1. Workflow wählen → die Slots erscheinen in der Run-Leiste.
2. **Slot „scharf schalten":** Klick auf einen Slot armt ihn (hervorgehoben,
   Hinweis „Klicke ein Bild für: Referenz"). Solange ein Slot scharf ist, **bindet
   der nächste Klick auf ein Galerie-Bild** dieses Bild an den Slot, statt die
   Detailansicht zu öffnen. Danach ist der Slot wieder entschärft.
3. Nächsten Slot scharf schalten → Bild anklicken → gebunden.
4. **Feuer-Button** (aktiv, sobald alle Pflicht-Slots gefüllt sind) → Job in die
   Queue, `/upload` + `/prompt`, Status „an ComfyUI gesendet".

### Wiederholen ohne Neuaufbau (Konstante bleibt, Variable wechselt)

Nach dem Feuern **bleiben alle Bindungen erhalten**. Für den typischen Fall
„eine Konstante, eine Variable":

- Nur den variablen Slot erneut scharf schalten → neues Bild anklicken → feuern.
- Die Konstante (Referenz/Stil/Identität) wird schlicht nicht angefasst und bleibt
  gebunden. Das Pinnen erübrigt sich damit — *feuern → variablen Slot neu wählen →
  feuern.* Optional kann ein Slot per 🔒 gegen versehentliches Re-Armen gesperrt
  werden.

### Batch per Multi-Select

Ein scharf geschalteter Slot nimmt statt eines einzelnen Bildes auch eine
**Mehrfachauswahl** auf und wird damit zur **Batch-Achse**:

- **Desktop:** Strg-Klick (einzeln togglen) oder Shift-Klick (Bereich) im Grid.
- **Mobile:** langes Tippen startet die Mehrfachauswahl, dann Antippen zum
  Hinzufügen/Entfernen.

Ein einfacher Klick bindet weiterhin ein Einzelbild und entschärft sofort
(Schnellpfad). Sobald Strg/Shift/Long-Press im Spiel ist, bleibt der Slot scharf und
sammelt die Auswahl; der Slot zeigt dann die Anzahl (z.B. „12 Bilder").

Beim Feuern wird der Workflow **einmal pro Bild** des Batch-Slots in die Queue
gelegt. Jeder Lauf = dieses eine Bild + die **unveränderten übrigen Inputs**. Die
Konstante (z.B. Referenz) bleibt also über den ganzen Batch gleich.

Regeln:

- **Genau ein Slot** ist die Batch-Achse; alle anderen bleiben einfach (ein Bild).
  Multi-Select in einen zweiten Slot **verschiebt** die Batch-Achse dorthin (mit
  Hinweis), statt ein Kreuzprodukt zu erzeugen.
- Der **Feuer-Button zeigt die Anzahl**: „Feuern (12×)" — keine Überraschung, wie
  viele Jobs in die Queue gehen.
- `kind = mask` ist typischerweise **nicht** batchbar (Maske gehört zum jeweiligen
  Quellbild) — solche Slots sind als Batch-Achse gesperrt.
- Reine Fire-and-Forget: N Jobs in die bestehende Queue (idempotent,
  SSE-Fortschritt), alle Ergebnisse landen in ComfyUIs `output/`.
- Nach dem Feuern bleiben Auswahl und Konstante erhalten — erneut feuern oder Reset.

### Filter voll nutzbar

Während des Modus laufen alle Galerie-Filter normal: Referenz filtern und an
„Input 1" binden, dann zur Quelle filtern und an „Input 2" binden — alles im selben
Grid. Ist kein Slot scharf, verhält sich die Galerie ganz normal (Detailansicht,
Scrollen, Filtern). Nur ein scharfer Slot leitet den Klick um; **Esc** oder erneuter
Slot-Klick entschärft.

### Ende

**Reset-Button** löst alle Bindungen, verlässt den Workflow-Modus, blendet die
Run-Leiste aus → die Galerie ist wieder im Normalbetrieb.

### Hinweise

- Slots klar als gefüllt/leer/scharf unterscheidbar; Pflicht-Slots markiert.
- `kind = mask`: Slot öffnet den Masken-Editor auf dem zuvor gebundenen Quellbild,
  statt ein Galerie-Bild zu erwarten.
- Workflow-Wechsel mitten im Modus → Bindungen verwerfen (mit kurzer Rückfrage).

---

## 4. Optionaler Import (on demand, kein Auto-Save)

Separater, bewusster Schritt — **nicht** Teil des Trigger-Flows:

- **„Aus ComfyUI-Output importieren":** Photofant listet die Ergebnisse, entweder
  - über `GET /history/{prompt_id}` → `outputs` → `GET /view`, **oder**
  - bei lokalem Lauf direkt aus `output_dir` gelesen (Backend hat FS-Zugriff).
- Nutzer wählt das gewünschte Bild → Ablage als **Edit** in `personX/edits/`,
  Versionskette + Lineage zum Quell-Asset in der DB.
- Erst hier greift „bewusstes Speichern". Vorher rührt Photofant nichts an.

---

## 5. Beispiel — Upscale (ein Input)

**Workflow-Config:**

```json
{
  "id": "upscale_4x",
  "name": "Upscale 4x",
  "category": "upscale",
  "template_path": "workflows/upscale_4x.api.json",
  "inputs": [
    { "key": "source", "node_title": "Source", "field": "image", "required": true }
  ],
  "params": [
    { "key": "scale", "label": "Skalierung", "node_title": "Upscale",
      "field": "scale_by", "type": "float", "default": 4.0, "min": 1.0, "max": 8.0 }
  ]
}
```

**Ablauf:**

1. Quellbild aus einem Person-Ordner wählen → an `source` binden.
2. Trigger → Bild wird hochgeladen, Template gepatcht, `/prompt` abgefeuert.
3. ComfyUI rechnet, schreibt `output/photofant/upscale_4x_00001.png`.
4. Ergebnis in ComfyUI ansehen.
5. Bei Bedarf in Photofant importieren → liegt als Edit im Person-Ordner.

Mehr Inputs (Inpainting-Maske, ControlNet-Referenz, zweites Subjekt) folgen exakt
demselben Muster: weitere Einträge in `inputs[]`, je über Titel gebunden.

---

## 6. Abgrenzung / Risiken

- **API ohne Auth, Port 8188 Default.** Lokal unkritisch, sonst Reverse-Proxy.
- **`SaveImage` Pflicht**, sonst kein persistentes Ergebnis im `output/`.
- **API-Format ≠ UI-Format.** Nur das API-Format-JSON ist patch- und queuebar.
- **Template als Vorlage behandeln** — bei jedem Lauf frisch laden / `deepcopy`.
- **Output-Cleanup** liegt bei ComfyUI; Photofant verwaltet diese Dateien nicht.
