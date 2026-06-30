v# Konzept: Modulare Metadaten-Pipeline für Bildklassifizierung

## Ziel

Entwicklung einer modularen Bildanalyse-Pipeline für eine Python-Anwendung, die automatisch strukturierte Metadaten für Bilder erzeugt.

Die Pipeline soll:

* verschiedene KI-Modelle kombinieren
* vollständig konfigurierbar sein
* ohne Codeänderungen erweitert werden können
* mehrere Klassifizierungen gleichzeitig unterstützen
* strukturierte Metadaten (JSON) erzeugen
* neue Kategorien ausschließlich über Konfigurationsdateien hinzufügen können

Der Schwerpunkt liegt auf einer flexiblen Architektur, nicht auf einem einzelnen KI-Modell.

---

# Gesamtarchitektur

```text
                     Bild
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   WD14 Tagger     CLIP ViT-L/14   weitere Modelle
        │              │
        └──────┬───────┘
               ▼
        Feature Extraction
               ▼
         Regel-Engine
               ▼
      Metadaten-Generator
               ▼
         JSON / Datenbank
```

---

# Komponenten

## 1. Bildanalyse

Die Bildanalyse erzeugt ausschließlich Rohdaten.

Es erfolgt **keine Entscheidung**.

### WD14 liefert

* allgemeine Tags
* Charaktere
* Stilmerkmale
* Motiv
* Farben
* Kleidung
* Objekte
* Hintergründe

Beispiel

```text
anime               0.99
girl                0.98
smile               0.96
blue hair           0.95
one piece           0.92
nami                0.90
```

---

### CLIP liefert

CLIP bewertet frei definierbare Text-Prompts.

Beispiel

```text
Photo               0.08
Illustration        0.77
Anime               0.94
One Piece           0.96
Nami                0.98
```

Dadurch muss nichts trainiert werden.

---

# 2. Feature Layer

Alle Ergebnisse werden gesammelt.

Beispiel

```json
{
  "wd14": {
    "anime": 0.99,
    "illustration": 0.96,
    "one_piece": 0.91,
    "nami": 0.90
  },
  "clip": {
    "Anime": 0.95,
    "Illustration": 0.88,
    "One Piece": 0.97,
    "Nami": 0.99
  }
}
```

Die eigentliche Klassifizierung erfolgt erst anschließend.

---

# 3. Regel-Engine

Die Regel-Engine kombiniert alle Ergebnisse.

Beispiel

```
WD14 Anime        0.99
CLIP Anime        0.95

↓

Anime
Confidence 0.97
```

Oder

```
WD14 Photo        0.54
CLIP CGI          0.81

↓

CGI
Confidence 0.73
```

---

# Metadaten-Kategorien

## Medium

Ein Bild besitzt genau **eine Hauptklasse**.

```
Photo
AI Photo
Illustration
Painting
Sketch
CGI
Vector
Pixel Art
Screenshot
Document
Diagram
```

---

## Stil

Mehrere gleichzeitig möglich.

```
Anime
Manga
Cartoon
Comic
Western Comic
Disney Style
Pixar Style
Ghibli Style
Digital Painting
Oil Painting
Watercolor
Ink
Pencil
Pastel
Pixel Art
Low Poly
Voxel
Clay
Minimal
Flat Design
```

---

## Realismus

```
Photorealistic
Semi Realistic
Stylized
Abstract
Hyperrealistic
```

---

## Motiv

```
Person
Animal
Vehicle
Landscape
Building
Architecture
Nature
Plant
Food
Weapon
Object
Logo
Text
```

---

## Szene

```
Indoor
Outdoor
Day
Night
Macro
Portrait
Landscape
Close Up
Action
Aerial
Underwater
```

---

## Eigenschaften

```
Transparent Background
White Background
Monochrome
HDR
Blurry
Noisy
High Resolution
Low Resolution
JPEG Artifacts
```

---

## Technik

```
Photo
Drawing
Painting
3D Render
Vector
Scan
Screenshot
```

---

## Franchise

Beispiele

```
One Piece
Naruto
Bleach
Dragon Ball
Pokémon
Harry Potter
Marvel
DC
Star Wars
Disney
Pixar
Lord of the Rings
Game of Thrones
The Witcher
```

Diese Liste ist vollständig konfigurierbar.

---

## Charakter

```
Monkey D. Luffy
Nami
Roronoa Zoro
Harry Potter
Hermione Granger
Batman
Spider-Man
Elsa
Darth Vader
Pikachu
```

---

## Künstler (optional)

```
Eiichiro Oda
Akira Toriyama
Makoto Shinkai
Hayao Miyazaki
Van Gogh
Picasso
```

---

## AI-Modell (optional)

```
Stable Diffusion
FLUX
Midjourney
DALL·E
Ideogram
```

---

# Konfigurierbares CLIP

Der wichtigste Bestandteil ist eine frei editierbare Konfiguration.

Beispiel

```yaml
clip:

  medium:

    labels:
      - Photo
      - AI Photo
      - Illustration
      - CGI
      - Sketch
      - Screenshot

  style:

    labels:
      - Anime
      - Manga
      - Cartoon
      - Comic
      - Watercolor
      - Oil Painting
      - Digital Painting
      - Pixar Style

  realism:

    labels:
      - Photorealistic
      - Stylized
      - Semi Realistic

  franchise:

    labels:
      - One Piece
      - Naruto
      - Bleach
      - Dragon Ball
      - Pokémon
      - Harry Potter
      - Star Wars
      - Marvel
      - Disney

  character:

    labels:
      - Monkey D. Luffy
      - Nami
      - Zoro
      - Pikachu
      - Harry Potter
      - Darth Vader
```

Neue Kategorien benötigen keinerlei Codeänderung.

---

# Erweiterte Promptdefinition

Nicht jeder Begriff liefert optimale Ergebnisse.

Deshalb sollte jeder Eintrag mehrere Prompts besitzen.

Beispiel

```yaml
franchise:

  One Piece:

    prompts:
      - One Piece
      - Character from One Piece
      - Artwork from One Piece
      - Anime from One Piece

  Harry Potter:

    prompts:
      - Harry Potter
      - Wizarding World
      - Hogwarts student

  Star Wars:

    prompts:
      - Star Wars
      - Jedi
      - Sith
```

Die Regel-Engine bildet daraus automatisch einen Gesamtscore.

---

# Benutzerdefinierte Kategorien

Benutzer können beliebige Kategorien definieren.

Beispiel

```yaml
categories:

  Fahrzeuge:

    labels:
      - Car
      - Motorcycle
      - Airplane
      - Bicycle

  Tiere:

    labels:
      - Dog
      - Cat
      - Horse
      - Bird

  Pflanzen:

    labels:
      - Tree
      - Flower
      - Rose
      - Sunflower
```

Dadurch wird CLIP universell.

---

# Verarbeitungsschritte

## Schritt 1

Bild laden

↓

## Schritt 2

WD14 ausführen

↓

## Schritt 3

CLIP mit allen aktivierten Kategorien ausführen

↓

## Schritt 4

Alle Scores sammeln

↓

## Schritt 5

Regel-Engine

↓

## Schritt 6

Metadaten erzeugen

↓

## Schritt 7

JSON speichern

---

# JSON-Ausgabe

```json
{
  "medium": {
    "value": "Illustration",
    "confidence": 0.96
  },

  "styles": [
    {
      "value": "Anime",
      "confidence": 0.98
    },
    {
      "value": "Digital Painting",
      "confidence": 0.82
    }
  ],

  "realism": {
    "value": "Stylized",
    "confidence": 0.94
  },

  "franchise": {
    "value": "One Piece",
    "confidence": 0.97
  },

  "character": {
    "value": "Nami",
    "confidence": 0.99
  },

  "properties": [
    "Portrait",
    "Color",
    "High Resolution"
  ],

  "tags": [
    "girl",
    "blue hair",
    "smile"
  ]
}
```

---

# Erweiterbarkeit

Die Architektur ist vollständig modular.

Neue Funktionen benötigen lediglich:

* neue CLIP-Prompts
* neue WD14-Regeln
* optionale zusätzliche Modelle

Der Kern der Anwendung bleibt unverändert.

Beispiele zukünftiger Module:

* Gesichtserkennung
* OCR
* NSFW-Erkennung
* Logo-Erkennung
* Marken-Erkennung
* Landmarken-Erkennung
* Kunststil-Erkennung
* Bildqualität
* Duplikaterkennung
* Reverse Image Search
* AI-Generator-Erkennung
* Farbpalettenanalyse
* Dominante Farben
* Personenanzahl
* Emotionserkennung
* Objektlokalisierung

---

# Vorteile dieser Architektur

* Strikte Trennung zwischen Analyse, Entscheidungslogik und Ausgabe.
* Keine fest verdrahteten Kategorien im Quellcode.
* Frei konfigurierbare CLIP-Prompts und Kategorien.
* Kombination mehrerer KI-Modelle erhöht die Robustheit.
* Neue Franchises, Charaktere oder Stile können jederzeit per Konfigurationsdatei ergänzt werden.
* Strukturierte JSON-Metadaten erleichtern Suche, Filterung, Verschlagwortung und Datenbankintegration.
* Zukunftssicher: Zusätzliche Modelle können als weitere Feature-Lieferanten eingebunden werden, ohne bestehende Komponenten zu ändern.

## Langfristige Vision

Die Pipeline entwickelt sich zu einer allgemeinen **Metadaten-Engine** für Bilder. KI-Modelle liefern lediglich Merkmale und Wahrscheinlichkeiten. Welche Kategorien erkannt, wie Scores kombiniert und welche Metadaten gespeichert werden, entscheidet ausschließlich die Konfiguration. Dadurch bleibt das System flexibel, wartbar und an neue Anwendungsfälle anpassbar, ohne dass der Anwendungscode ständig erweitert werden muss.
