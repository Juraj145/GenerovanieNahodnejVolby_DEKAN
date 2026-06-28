# -*- coding: utf-8 -*-
"""Vygeneruje app.ico – ikonu programu.

Ikona symbolizuje program „Voľba poradia vystúpenia kandidátov na dekana":
  - akademická čiapka (mortarboard) = dekan / akademické prostredie,
  - očíslovaný zoznam 1–2–3 = poradie vystúpenia kandidátov.

Ak v priečinku existuje vlastný obrázok `icon_source.png` (najlepšie štvorcový,
aspoň 256×256), ikona sa vytvorí z neho. Inak sa nakreslí predvolený návrh.
"""

import os
from PIL import Image, ImageDraw

SIZES = [16, 24, 32, 48, 64, 128, 256]
ZDROJ_OBRAZOK = "icon_source.png"

# farby
POZADIE = (122, 27, 51, 255)      # akademická bordová
POZADIE2 = (90, 18, 38, 255)      # tmavší okraj
BIELA = (255, 255, 255, 255)
ZLATA = (240, 190, 70, 255)
TMAVA = (60, 12, 26, 255)


def _gradient_pozadie(size: int) -> Image.Image:
    """Zvislý jemný prechod ako podklad."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(size):
        t = y / max(1, size - 1)
        r = int(POZADIE[0] * (1 - t) + POZADIE2[0] * t)
        g = int(POZADIE[1] * (1 - t) + POZADIE2[1] * t)
        b = int(POZADIE[2] * (1 - t) + POZADIE2[2] * t)
        for x in range(size):
            img.putpixel((x, y), (r, g, b, 255))
    return img


def draw(size: int) -> Image.Image:
    s = size / 256.0
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # zaoblené pozadie s prechodom
    podklad = _gradient_pozadie(size)
    maska = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(maska)
    md.rounded_rectangle(
        [int(6 * s), int(6 * s), int(250 * s), int(250 * s)],
        radius=int(46 * s),
        fill=255,
    )
    img.paste(podklad, (0, 0), maska)
    d = ImageDraw.Draw(img)

    # --- očíslovaný zoznam (poradie vystúpenia) v dolnej časti ---
    riadky = [
        (96, ZLATA, 150),   # 1. – zvýraznený (zlatý)
        (130, BIELA, 132),
        (164, BIELA, 116),
    ]
    for y, farba, sirka in riadky:
        cx = int(74 * s)
        cy = int((y + 10) * s)
        r = int(15 * s)
        # číselný "bod"
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=farba)
        # čiara zoznamu
        d.rounded_rectangle(
            [int(100 * s), int(y * s), int((100 + sirka) * s), int((y + 20) * s)],
            radius=int(10 * s),
            fill=farba,
        )

    # --- akademická čiapka (mortarboard) v hornej časti ---
    cx = int(128 * s)
    cy = int(70 * s)
    w = int(96 * s)   # polovičná šírka dosky
    h = int(34 * s)   # polovičná výška dosky
    doska = [
        (cx, cy - h),
        (cx + w, cy),
        (cx, cy + h),
        (cx - w, cy),
    ]

    # čiapka (hlava) pod doskou – lichobežník (kreslí sa pred doskou)
    d.polygon(
        [
            (cx - int(40 * s), cy + int(2 * s)),
            (cx + int(40 * s), cy + int(2 * s)),
            (cx + int(30 * s), cy + int(48 * s)),
            (cx - int(30 * s), cy + int(48 * s)),
        ],
        fill=ZLATA,
    )

    # doska navrch
    d.polygon(doska, fill=BIELA)

    # gombík v strede dosky
    d.ellipse(
        [cx - int(8 * s), cy - int(8 * s), cx + int(8 * s), cy + int(8 * s)],
        fill=ZLATA,
    )
    # strapec splývajúci z pravej strany dosky
    px = cx + int(70 * s)
    d.line(
        [(cx, cy), (px, cy - int(2 * s)), (px, cy + int(40 * s))],
        fill=ZLATA,
        width=max(1, int(5 * s)),
        joint="curve",
    )
    d.ellipse(
        [px - int(8 * s), cy + int(38 * s), px + int(8 * s), cy + int(54 * s)],
        fill=ZLATA,
    )

    return img


def z_obrazka(cesta: str) -> Image.Image:
    """Pripraví štvorcovú ikonu z dodaného obrázka."""
    obr = Image.open(cesta).convert("RGBA")
    strana = max(obr.size)
    stvorec = Image.new("RGBA", (strana, strana), (0, 0, 0, 0))
    stvorec.paste(obr, ((strana - obr.width) // 2, (strana - obr.height) // 2))
    return stvorec.resize((256, 256), Image.LANCZOS)


def main():
    if os.path.exists(ZDROJ_OBRAZOK):
        base = z_obrazka(ZDROJ_OBRAZOK)
        print(f"app.ico vytvorený z {ZDROJ_OBRAZOK}")
    else:
        base = draw(256)
        print("app.ico vytvorený (predvolený návrh)")
    base.save("app.ico", format="ICO", sizes=[(s, s) for s in SIZES])


if __name__ == "__main__":
    main()
