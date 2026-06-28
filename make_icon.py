# -*- coding: utf-8 -*-
"""Vygeneruje app.ico – jednoduchá ikona (urna s lístkom a fajkou)."""

from PIL import Image, ImageDraw


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 256.0

    # pozadie – zaoblený štvorec
    d.rounded_rectangle(
        [int(8 * s), int(8 * s), int(248 * s), int(248 * s)],
        radius=int(40 * s),
        fill=(31, 119, 180, 255),
    )

    # biely "lístok"
    d.rounded_rectangle(
        [int(64 * s), int(56 * s), int(192 * s), int(176 * s)],
        radius=int(10 * s),
        fill=(255, 255, 255, 255),
    )
    # riadky na lístku
    for i, y in enumerate((84, 108, 132)):
        d.rounded_rectangle(
            [int(80 * s), int(y * s), int(176 * s), int((y + 8) * s)],
            radius=int(4 * s),
            fill=(150, 170, 190, 255),
        )

    # zelená fajka
    d.line(
        [(int(96 * s), int(196 * s)), (int(128 * s), int(224 * s)), (int(184 * s), int(150 * s))],
        fill=(40, 170, 70, 255),
        width=int(20 * s),
        joint="curve",
    )
    return img


sizes = [16, 24, 32, 48, 64, 128, 256]
base = draw(256)
base.save("app.ico", format="ICO", sizes=[(s, s) for s in sizes])
print("app.ico vytvorený")
