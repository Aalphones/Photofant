"""Seed-Katalog für Klassifizierungs-Kategorien/-Labels (Konzept: „Metadaten-Kategorien").

`SEED_CATALOG` ist reine Daten (keine DB-Kopplung) — damit für sich testbar. Die
tatsächliche Einspielung (`insert_seed_catalog`) arbeitet auf einer rohen `Connection`
per Text-SQL (analog zu den bestehenden Daten-Migrationen im Projekt), damit sie
unverändert sowohl aus der Migration (`op.get_bind()`) als auch aus Tests (frisch
angelegte SQLite-Engine) aufgerufen werden kann — eine Insert-Logik, zwei Aufrufer.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import sqlalchemy as sa


@dataclass(frozen=True)
class SeedLabel:
    name: str
    wd14_tags: list[str] | None = None


@dataclass(frozen=True)
class SeedCategory:
    name: str
    mode: str  # single | multi
    labels: list[SeedLabel] = field(default_factory=list)


SEED_CATALOG: list[SeedCategory] = [
    SeedCategory(
        "Medium",
        "single",
        [
            SeedLabel("Photo"),
            SeedLabel("AI Photo"),
            SeedLabel("Illustration"),
            SeedLabel("Painting"),
            SeedLabel("Sketch", ["sketch"]),
            SeedLabel("CGI"),
            SeedLabel("Vector"),
            SeedLabel("Pixel Art", ["pixel_art"]),
            SeedLabel("Screenshot", ["screenshot"]),
            SeedLabel("Document"),
            SeedLabel("Diagram"),
        ],
    ),
    SeedCategory(
        "Stil",
        "multi",
        [
            SeedLabel("Anime", ["anime"]),
            SeedLabel("Manga", ["manga"]),
            SeedLabel("Cartoon"),
            SeedLabel("Comic", ["comic"]),
            SeedLabel("Western Comic"),
            SeedLabel("Disney Style"),
            SeedLabel("Pixar Style"),
            SeedLabel("Ghibli Style"),
            SeedLabel("Digital Painting"),
            SeedLabel("Oil Painting", ["oil_painting_(medium)"]),
            SeedLabel("Watercolor", ["watercolor_(medium)"]),
            SeedLabel("Ink"),
            SeedLabel("Pencil"),
            SeedLabel("Pastel"),
            SeedLabel("Pixel Art", ["pixel_art"]),
            SeedLabel("Low Poly"),
            SeedLabel("Voxel"),
            SeedLabel("Clay"),
            SeedLabel("Minimal"),
            SeedLabel("Flat Design"),
        ],
    ),
    SeedCategory(
        "Realismus",
        "single",
        [
            SeedLabel("Photorealistic", ["photorealistic"]),
            SeedLabel("Semi Realistic"),
            SeedLabel("Stylized"),
            SeedLabel("Abstract"),
            SeedLabel("Hyperrealistic", ["hyperrealistic"]),
        ],
    ),
    SeedCategory(
        "Motiv",
        "multi",
        [
            SeedLabel("Person"),
            SeedLabel("Animal"),
            SeedLabel("Vehicle"),
            SeedLabel("Landscape"),
            SeedLabel("Building"),
            SeedLabel("Architecture"),
            SeedLabel("Nature"),
            SeedLabel("Plant"),
            SeedLabel("Food"),
            SeedLabel("Weapon"),
            SeedLabel("Object"),
            SeedLabel("Logo"),
            SeedLabel("Text", ["text"]),
        ],
    ),
    SeedCategory(
        "Szene",
        "multi",
        [
            SeedLabel("Indoor", ["indoors"]),
            SeedLabel("Outdoor", ["outdoors"]),
            SeedLabel("Day", ["day"]),
            SeedLabel("Night", ["night"]),
            SeedLabel("Macro"),
            SeedLabel("Portrait", ["portrait"]),
            SeedLabel("Landscape"),
            SeedLabel("Close Up", ["close-up"]),
            SeedLabel("Action"),
            SeedLabel("Aerial", ["aerial_view"]),
            SeedLabel("Underwater", ["underwater"]),
        ],
    ),
    SeedCategory(
        "Eigenschaften",
        "multi",
        [
            SeedLabel("Transparent Background", ["transparent_background"]),
            SeedLabel("White Background", ["white_background"]),
            SeedLabel("Monochrome", ["monochrome", "greyscale"]),
            SeedLabel("HDR"),
            SeedLabel("Blurry", ["blurry"]),
            SeedLabel("Noisy"),
            SeedLabel("High Resolution", ["highres"]),
            SeedLabel("Low Resolution", ["lowres"]),
            SeedLabel("JPEG Artifacts", ["jpeg_artifacts"]),
        ],
    ),
    SeedCategory(
        "Technik",
        "multi",
        [
            SeedLabel("Photo"),
            SeedLabel("Drawing"),
            SeedLabel("Painting"),
            SeedLabel("3D Render", ["3d"]),
            SeedLabel("Vector"),
            SeedLabel("Scan"),
            SeedLabel("Screenshot", ["screenshot"]),
        ],
    ),
    SeedCategory(
        "Franchise",
        "single",
        [
            SeedLabel("One Piece", ["one_piece"]),
            SeedLabel("Naruto", ["naruto"]),
            SeedLabel("Bleach", ["bleach"]),
            SeedLabel("Dragon Ball", ["dragon_ball"]),
            SeedLabel("Pokémon", ["pokemon"]),
            SeedLabel("Harry Potter", ["harry_potter"]),
            SeedLabel("Marvel"),
            SeedLabel("DC"),
            SeedLabel("Star Wars", ["star_wars"]),
            SeedLabel("Disney"),
            SeedLabel("Pixar"),
            SeedLabel("Lord of the Rings", ["lord_of_the_rings"]),
            SeedLabel("Game of Thrones", ["game_of_thrones"]),
            SeedLabel("The Witcher", ["the_witcher"]),
        ],
    ),
    SeedCategory(
        "Charakter",
        "single",
        [
            SeedLabel("Monkey D. Luffy", ["monkey_d._luffy"]),
            SeedLabel("Nami", ["nami"]),
            SeedLabel("Roronoa Zoro", ["roronoa_zoro"]),
            SeedLabel("Harry Potter", ["harry_potter"]),
            SeedLabel("Hermione Granger", ["hermione_granger"]),
            SeedLabel("Batman", ["batman"]),
            SeedLabel("Spider-Man", ["spider-man"]),
            SeedLabel("Elsa", ["elsa"]),
            SeedLabel("Darth Vader", ["darth_vader"]),
            SeedLabel("Pikachu", ["pikachu"]),
        ],
    ),
    SeedCategory(
        "Künstler",
        "single",
        [
            SeedLabel("Eiichiro Oda", ["eiichiro_oda"]),
            SeedLabel("Akira Toriyama", ["akira_toriyama"]),
            SeedLabel("Makoto Shinkai", ["makoto_shinkai"]),
            SeedLabel("Hayao Miyazaki", ["hayao_miyazaki"]),
            SeedLabel("Van Gogh", ["vincent_van_gogh"]),
            SeedLabel("Picasso", ["pablo_picasso"]),
        ],
    ),
    SeedCategory(
        "AI-Modell",
        "single",
        [
            SeedLabel("Stable Diffusion"),
            SeedLabel("FLUX"),
            SeedLabel("Midjourney"),
            SeedLabel("DALL·E"),
            SeedLabel("Ideogram"),
        ],
    ),
]

def insert_seed_catalog(conn: sa.engine.Connection) -> None:
    """Seedet `SEED_CATALOG` in eine bereits angelegte `classification_*`-Schema-DB.

    Aufrufbar sowohl aus der Alembic-Migration (`op.get_bind()`) als auch aus Tests
    (Engine nach `Base.metadata.create_all`) — reine SQLAlchemy-Core-Operation über
    Text-SQL (kein ORM), analog zu den Daten-Migrationen im Projekt.
    """
    for category_position, category in enumerate(SEED_CATALOG):
        conn.execute(
            sa.text(
                "INSERT INTO classification_category (name, mode, position, enabled, builtin) "
                "VALUES (:name, :mode, :position, 1, 1)"
            ),
            {"name": category.name, "mode": category.mode, "position": category_position},
        )
        category_id = conn.execute(
            sa.text("SELECT id FROM classification_category WHERE name = :name"),
            {"name": category.name},
        ).scalar_one()

        for label_position, label in enumerate(category.labels):
            conn.execute(
                sa.text(
                    "INSERT INTO classification_label "
                    "(category_id, name, position, clip_prompts, wd14_tags) "
                    "VALUES (:category_id, :name, :position, NULL, :wd14_tags)"
                ),
                {
                    "category_id": category_id,
                    "name": label.name,
                    "position": label_position,
                    "wd14_tags": json.dumps(label.wd14_tags) if label.wd14_tags else None,
                },
            )
