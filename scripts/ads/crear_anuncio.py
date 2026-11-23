#!/usr/bin/env python3
"""
Generador de imágenes publicitarias con la marca IoTing Dev (Pillow, local, sin gastar cupo).

El agente decide el mensaje; este script arma la pieza con tu foto real + marca.

Uso (una pieza):
  python scripts/ads/crear_anuncio.py --foto publicidad/fotos/replica.jpg \
      --titulo "¿Se dañó una pieza descontinuada?" \
      --subtitulo "La replicamos en 3D, funcional y a tu medida" \
      --cta "Cotiza por WhatsApp" --formato feed --salida publicidad/por-aprobar/replica_feed.png

Uso (varias variantes A/B desde un JSON):
  python scripts/ads/crear_anuncio.py --lote publicidad/campanas/replica-3d.json

Formatos: feed (1080x1350, 4:5) · cuadrado (1080x1080) · story (1080x1920, también Reels/TikTok)
Sin --foto usa un fondo degradado de marca.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

RAIZ = Path(__file__).resolve().parents[2]
FORMATOS = {"feed": (1080, 1350), "cuadrado": (1080, 1080), "story": (1080, 1920)}
# Zonas seguras (px) donde las apps tapan la pieza con su interfaz
SEGURA = {"feed": (60, 60), "cuadrado": (60, 60), "story": (250, 340)}

FUENTES = [
    "/usr/share/fonts/truetype/google-fonts/ofl/montserrat/Montserrat[wght].ttf",
    r"C:\Windows\Fonts\Montserrat-Bold.ttf", r"C:\Windows\Fonts\arialbd.ttf",
    "/Library/Fonts/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def marca():
    base = {"color_primario": "#25A9E1", "color_secundario": "#2C5DA7", "logo": "marca/logo.png",
            "web": "iotingdev.com"}
    p = RAIZ / "marca" / "marca.json"
    if p.exists():
        base.update(json.loads(p.read_text(encoding="utf-8-sig")))
    return base


def fuente(tam, peso=800):
    for f in FUENTES:
        if Path(f).exists():
            ft = ImageFont.truetype(f, tam)
            try:
                ft.set_variation_by_axes([peso])  # fuentes variables (Montserrat)
            except Exception:
                pass
            return ft
    return ImageFont.load_default()


def ajustar(draw, texto, ft, ancho):
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = (actual + " " + palabra).strip()
        if draw.textlength(prueba, font=ft) <= ancho:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def fondo(foto, w, h, prim, sec):
    if foto and Path(foto).exists():
        return ImageOps.fit(Image.open(foto).convert("RGB"), (w, h), method=Image.LANCZOS, centering=(0.5, 0.45))
    img = Image.new("RGB", (w, h), sec)
    px = img.load()
    for y in range(h):
        t = y / h
        c = tuple(int(sec[i] * (1 - t) + prim[i] * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def crear(p, m):
    fmt = p.get("formato", "feed")
    w, h = FORMATOS[fmt]
    sup, inf = SEGURA[fmt]
    prim, sec = hex_rgb(m["color_primario"]), hex_rgb(m["color_secundario"])
    img = fondo(p.get("foto"), w, h, prim, sec).convert("RGBA")

    # Degradado de marca desde abajo para que el texto siempre se lea
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    alto_g = int(h * (0.62 if fmt != "story" else 0.55))
    for i in range(alto_g):
        a = int(235 * (i / alto_g) ** 1.4)
        d.line([(0, h - alto_g + i), (w, h - alto_g + i)], fill=sec + (a,))
    img = Image.alpha_composite(img, capa)
    d = ImageDraw.Draw(img)

    margen = 70
    ancho_txt = w - 2 * margen
    y_fin = h - inf - 20  # el bloque de texto crece hacia arriba desde aquí

    # Botón CTA
    cta = p.get("cta", "")
    if cta:
        f_cta = fuente(42, 700)
        tw = d.textlength(cta, font=f_cta)
        bw, bh = int(tw + 90), 96
        by = y_fin - bh
        d.rounded_rectangle([margen, by, margen + bw, by + bh], radius=48, fill=prim)
        d.text((margen + bw / 2, by + bh / 2), cta, font=f_cta, fill="white", anchor="mm")
        y_fin = by - 40

    # Subtítulo
    sub = p.get("subtitulo", "")
    if sub:
        f_sub = fuente(40, 500)
        lineas = ajustar(d, sub, f_sub, ancho_txt)
        for ln in reversed(lineas):
            d.text((margen, y_fin), ln, font=f_sub, fill=(235, 245, 255), anchor="ls")
            y_fin -= 54
        y_fin -= 20

    # Título (se reduce hasta que quepa en 4 líneas)
    tam = 84 if fmt != "story" else 92
    while True:
        f_t = fuente(tam, 800)
        lineas = ajustar(d, p["titulo"], f_t, ancho_txt)
        if len(lineas) <= 4 or tam <= 52:
            break
        tam -= 4
    for ln in reversed(lineas):
        d.text((margen, y_fin), ln, font=f_t, fill="white", anchor="ls")
        y_fin -= int(tam * 1.12)

    # Logo en tarjeta blanca (el logo azul no se lee sobre fotos oscuras)
    lg = RAIZ / m["logo"]
    if lg.exists():
        logo = Image.open(lg).convert("RGBA")
        lw = 230
        logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
        pad = 26
        x0, y0 = margen - 10, sup
        d.rounded_rectangle([x0, y0, x0 + lw + 2 * pad, y0 + logo.height + 2 * pad], radius=28, fill=(255, 255, 255, 245))
        img.alpha_composite(logo, (x0 + pad, y0 + pad))
    # Web discreta
    if m.get("web") and p.get("mostrar_web", True):
        d.text((w - margen, sup + 40), m["web"], font=fuente(34, 600), fill="white", anchor="rm")

    salida = Path(p.get("salida") or f"publicidad/por-aprobar/anuncio_{fmt}.png")
    if not salida.is_absolute():
        salida = RAIZ / salida
    salida.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(salida, quality=95)
    print(f"OK -> {salida}")
    return salida


def main():
    ap = argparse.ArgumentParser(description="Imágenes publicitarias IoTing Dev")
    ap.add_argument("--lote", help="JSON con una lista de piezas (variantes A/B, varios formatos)")
    ap.add_argument("--foto"); ap.add_argument("--titulo"); ap.add_argument("--subtitulo")
    ap.add_argument("--cta"); ap.add_argument("--formato", default="feed", choices=FORMATOS)
    ap.add_argument("--salida")
    a = ap.parse_args()
    m = marca()
    if a.lote:
        datos = json.loads(Path(a.lote).read_text(encoding="utf-8-sig"))
        piezas = datos["piezas"] if isinstance(datos, dict) else datos
        for p in piezas:
            if p.get("foto") and not Path(p["foto"]).is_absolute():
                p["foto"] = str(RAIZ / p["foto"])
            crear(p, m)
    else:
        if not a.titulo:
            sys.exit("Falta --titulo (o usa --lote)")
        if a.foto and not Path(a.foto).is_absolute():
            a.foto = str(RAIZ / a.foto)
        crear(vars(a), m)


if __name__ == "__main__":
    main()
