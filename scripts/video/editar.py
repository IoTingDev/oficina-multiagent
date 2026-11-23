#!/usr/bin/env python3
"""
Editor de video de IoTing Dev (ffmpeg + faster-whisper).

El modelo de IA solo decide QUÉ cortar y QUÉ texto poner; este script hace
todo el trabajo pesado localmente, sin gastar cupo de Claude.

Comandos:
  python editar.py transcribir <video> [--modelo small]
      -> <video>.transcripcion.json  (palabras con tiempos)
      -> <video>.transcripcion.txt   (versión corta para que el agente la lea)

  python editar.py silencios <video>
      -> imprime los tramos con voz (JSON)

  python editar.py render <corte.json>
      -> un .mp4 vertical 1080x1920 por cada versión pedida (tiktok / instagram)

Requisitos: ffmpeg en el PATH. Para transcribir: pip install faster-whisper
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
MARCA_JSON = RAIZ / "marca" / "marca.json"
W, H, FPS = 1080, 1920, 30
CIERRE_SEG = 1.5


# ---------------------------------------------------------------- utilidades
def cargar_marca():
    base = {
        "color_primario": "#00A86B",
        "color_secundario": "#0B1F33",
        "color_texto": "#FFFFFF",
        "fuente": "Montserrat",
        "logo": "marca/logo.png",
        "web": "iotingdev.com",
        "instagram": "@iotingdev",
        "tiktok": "@ing_cjuan",
    }
    if MARCA_JSON.exists():
        base.update(json.loads(MARCA_JSON.read_text(encoding="utf-8-sig")))
    base.setdefault("color_fondo_cierre", base["color_secundario"])
    base.setdefault("color_texto_cierre", base["color_texto"])
    base.setdefault("logo_marca_agua", base["logo"])
    for clave, destino in (("logo", "logo_path"), ("logo_marca_agua", "agua_path")):
        p = Path(base[clave])
        base[destino] = p if p.is_absolute() else RAIZ / p
    return base


def ass_color(hex_color, alpha="00"):
    """#RRGGBB -> &HAABBGGRR (formato ASS)."""
    h = hex_color.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha}{b}{g}{r}".upper()


def ass_tiempo(t):
    t = max(0.0, t)
    hrs = int(t // 3600)
    mins = int((t % 3600) // 60)
    secs = t % 60
    return f"{hrs}:{mins:02d}:{secs:05.2f}"


def ass_texto(s):
    return s.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def duracion(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(video)],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def tiene_audio(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=index", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True).stdout.strip()
    return bool(out)


# -------------------------------------------------------------- transcribir
def transcribir(video, modelo="small"):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("Falta faster-whisper:  pip install faster-whisper")
    print(f"Transcribiendo {video} con Whisper '{modelo}' (la primera vez descarga el modelo)...")
    m = WhisperModel(modelo, device="auto", compute_type="int8")
    segs, _ = m.transcribe(str(video), language="es", word_timestamps=True, vad_filter=True)
    datos = {"video": str(video), "segmentos": []}
    lineas = []
    for s in segs:
        palabras = [{"inicio": round(w.start, 2), "fin": round(w.end, 2), "palabra": w.word.strip()}
                    for w in (s.words or [])]
        datos["segmentos"].append({"inicio": round(s.start, 2), "fin": round(s.end, 2),
                                   "texto": s.text.strip(), "palabras": palabras})
        lineas.append(f"[{s.start:7.1f} - {s.end:7.1f}] {s.text.strip()}")
    base = Path(video)
    Path(f"{base}.transcripcion.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    Path(f"{base}.transcripcion.txt").write_text("\n".join(lineas), encoding="utf-8")
    print(f"Listo: {base}.transcripcion.txt")


# --------------------------------------------------------------- silencios
def detectar_silencios(video, umbral_db=-35, min_seg=0.6):
    if not tiene_audio(video):
        return []
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(video), "-af",
         f"silencedetect=noise={umbral_db}dB:d={min_seg}", "-f", "null", "-"],
        capture_output=True, text=True)
    inicios = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    fines = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    total = duracion(video)
    while len(fines) < len(inicios):
        fines.append(total)
    return list(zip(inicios, fines))


def tramos_con_voz(a, b, silencios, margen=0.12):
    """Divide [a,b] quitando silencios; deja un pequeño margen para no cortar palabras."""
    tramos, cursor = [], a
    for s, e in silencios:
        s2, e2 = s + margen, e - margen
        if e2 <= cursor or s2 >= b or e2 - s2 <= 0:
            continue
        if s2 > cursor:
            tramos.append((cursor, min(s2, b)))
        cursor = max(cursor, e2)
    if cursor < b:
        tramos.append((cursor, b))
    return [(x, y) for x, y in tramos if y - x >= 0.25]


# --------------------------------------------------------------- subtítulos
def palabras_en_linea(transcripcion, tramos):
    """Pasa los tiempos de las palabras del video original a la línea de tiempo editada."""
    salida, offsets, t = [], [], 0.0
    for a, b in tramos:
        offsets.append((a, b, t))
        t += b - a
    for seg in transcripcion.get("segmentos", []):
        for w in seg.get("palabras", []):
            centro = (w["inicio"] + w["fin"]) / 2
            for a, b, off in offsets:
                if a <= centro <= b:
                    salida.append({"inicio": max(a, w["inicio"]) - a + off,
                                   "fin": min(b, w["fin"]) - a + off,
                                   "palabra": w["palabra"]})
                    break
    return salida


def agrupar(palabras, max_palabras, max_dur=2.2, max_hueco=0.5):
    grupos, actual = [], []
    for w in palabras:
        if actual and (len(actual) >= max_palabras or w["inicio"] - actual[-1]["fin"] > max_hueco
                       or w["fin"] - actual[0]["inicio"] > max_dur):
            grupos.append(actual)
            actual = []
        actual.append(w)
    if actual:
        grupos.append(actual)
    return [{"inicio": g[0]["inicio"], "fin": g[-1]["fin"] + 0.05,
             "texto": " ".join(x["palabra"] for x in g)} for g in grupos]


def crear_ass(ruta, version, marca, subtitulos, gancho, dur_contenido, con_cierre):
    f = marca["fuente"]
    blanco = ass_color(marca["color_texto"])
    negro = ass_color("#000000")
    prim = ass_color(marca["color_primario"])
    sec = ass_color(marca["color_secundario"])
    if version == "tiktok":
        estilo_sub = f"Style: Sub,{f},84,{blanco},{blanco},{negro},{negro},-1,0,0,0,100,100,0,0,1,6,2,2,60,60,560,1"
        estilo_gancho = f"Style: Gancho,{f},80,{blanco},{blanco},{negro},{prim},-1,0,0,0,100,100,0,0,3,18,0,8,70,70,260,1"
    else:  # instagram: caja con color de marca, más sobrio
        estilo_sub = f"Style: Sub,{f},64,{blanco},{blanco},{sec},{sec},-1,0,0,0,100,100,0,0,3,14,0,2,80,80,560,1"
        estilo_gancho = f"Style: Gancho,{f},74,{blanco},{blanco},{sec},{sec},-1,0,0,0,100,100,0,0,3,20,0,8,80,80,260,1"
    txt_cierre = ass_color(marca["color_texto_cierre"])
    estilo_cierre = f"Style: Cierre,{f},64,{txt_cierre},{txt_cierre},{txt_cierre},{txt_cierre},-1,0,0,0,100,100,0,0,1,0,0,5,60,60,0,1"
    ev = []
    for s in subtitulos:
        txt = s["texto"].upper() if version == "tiktok" else s["texto"]
        ev.append(f"Dialogue: 0,{ass_tiempo(s['inicio'])},{ass_tiempo(s['fin'])},Sub,,0,0,0,,{ass_texto(txt)}")
    if gancho:
        ev.append(f"Dialogue: 1,{ass_tiempo(0)},{ass_tiempo(min(3.0, dur_contenido))},Gancho,,0,0,0,,{ass_texto(gancho)}")
    if con_cierre:
        red = marca["instagram"] if version == "instagram" else marca["tiktok"]
        ev.append(f"Dialogue: 1,{ass_tiempo(dur_contenido)},{ass_tiempo(dur_contenido + CIERRE_SEG)},Cierre,,0,0,0,,"
                  f"{{\\pos(540,1480)}}{ass_texto(marca['web'])}\\N{ass_texto(red)}")
    contenido = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {W}\nPlayResY: {H}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"{estilo_sub}\n{estilo_gancho}\n{estilo_cierre}\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        + "\n".join(ev) + "\n")
    Path(ruta).write_text(contenido, encoding="utf-8")


# ------------------------------------------------------------------- render
def render(config_path):
    cfg_path = Path(config_path).resolve()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    marca = cargar_marca()
    fuente = Path(cfg["fuente"])
    if not fuente.is_absolute():
        fuente = (cfg_path.parent / fuente) if (cfg_path.parent / fuente).exists() else RAIZ / fuente
    if not fuente.exists():
        sys.exit(f"No encuentro el video fuente: {fuente}")
    salida_dir = Path(cfg.get("carpeta_salida", RAIZ / "redes" / "por-aprobar"))
    if not salida_dir.is_absolute():
        salida_dir = RAIZ / salida_dir
    salida_dir.mkdir(parents=True, exist_ok=True)
    nombre = cfg.get("nombre", fuente.stem)
    audio = tiene_audio(fuente)

    # 1) Tramos finales (quitando silencios si se pide)
    segmentos = cfg.get("segmentos") or [{"inicio": 0, "fin": duracion(fuente)}]
    silencios = detectar_silencios(fuente) if (cfg.get("quitar_silencios", True) and audio) else []
    tramos = []
    for s in segmentos:
        tramos += tramos_con_voz(float(s["inicio"]), float(s["fin"]), silencios) if silencios \
            else [(float(s["inicio"]), float(s["fin"]))]
    if not tramos:
        sys.exit("No quedó ningún tramo con voz; revisa los segmentos o pon \"quitar_silencios\": false")
    dur = sum(b - a for a, b in tramos)

    # 2) Subtítulos desde la transcripción (si existe)
    tr_path = Path(f"{fuente}.transcripcion.json")
    transcripcion = json.loads(tr_path.read_text(encoding="utf-8-sig")) if tr_path.exists() else {}
    if not transcripcion:
        print("Aviso: no hay transcripción; el video sale sin subtítulos. Corre primero 'transcribir'.")
    palabras = palabras_en_linea(transcripcion, tramos)

    for version in cfg.get("versiones", ["tiktok", "instagram"]):
        con_cierre = version == "instagram" and cfg.get("cierre", True)
        subs = agrupar(palabras, 3 if version == "tiktok" else 6)
        out = salida_dir / f"{nombre}_{version}.mp4"
        with tempfile.TemporaryDirectory() as tmp:
            crear_ass(Path(tmp) / "subs.ass", version, marca, subs,
                      cfg.get("gancho", {}).get(version) if isinstance(cfg.get("gancho"), dict) else cfg.get("gancho"),
                      dur, con_cierre)
            entradas = ["-i", str(fuente)]
            logo_ok = marca["logo_path"].exists() and marca["agua_path"].exists()
            if logo_ok:
                # entrada 1 = isotipo (marca de agua), entrada 2 = logo completo (cierre)
                entradas += ["-i", str(marca["agua_path"]), "-i", str(marca["logo_path"])]
            fc = []
            for i, (a, b) in enumerate(tramos):
                fc.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}]")
                if audio:
                    fc.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[a{i}]")
                else:
                    fc.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={b - a:.3f}[a{i}]")
            n = len(tramos)
            fc.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]")
            # Vertical 9:16: fondo desenfocado + video centrado
            fc.append(f"[vc]fps={FPS},split[bg][fg]")
            fc.append(f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=25:5[bgb]")
            fc.append(f"[fg]scale={W}:{H}:force_original_aspect_ratio=decrease[fgs]")
            fc.append("[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p[vv]")
            ultimo_v, ultimo_a = "vv", "ac"
            if con_cierre:
                fc.append(f"color=c={marca['color_fondo_cierre']}:s={W}x{H}:r={FPS}:d={CIERRE_SEG},setsar=1,format=yuv420p[cv]")
                fc.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={CIERRE_SEG}[ca]")
                fc.append("[ac]aresample=48000,aformat=channel_layouts=stereo[acs]")
                fc.append("[vv][acs][cv][ca]concat=n=2:v=1:a=1[vcat][acat]")
                ultimo_v, ultimo_a = "vcat", "acat"
            fc.append(f"[{ultimo_v}]ass=subs.ass[vs]")
            ultimo_v = "vs"
            if logo_ok:
                if version == "tiktok":
                    fc.append("[1:v]scale=130:-1,format=rgba,colorchannelmixer=aa=0.85[lg]")
                    fc.append(f"[{ultimo_v}][lg]overlay=W-w-40:110[vl]")
                else:
                    fc.append("[1:v]scale=170:-1,format=rgba[lg]")
                    fc.append("[2:v]scale=560:-1,format=rgba[lgbig]")
                    fc.append(f"[{ultimo_v}][lg]overlay=W-w-40:110:enable='lt(t,{dur:.2f})'[vl0]")
                    fc.append(f"[vl0][lgbig]overlay=(W-w)/2:(H-h)/2-200:enable='gte(t,{dur:.2f})'[vl]")
                ultimo_v = "vl"
            fc.append(f"[{ultimo_a}]loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
            cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *entradas,
                   "-filter_complex", ";".join(fc), "-map", f"[{ultimo_v}]", "-map", "[aout]",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", str(out.resolve())]
            print(f"Renderizando {version}: {out.name} ({dur:.1f} s de contenido, {n} tramos)...")
            subprocess.run(cmd, check=True, cwd=tmp)
        print(f"  OK -> {out}")


def main():
    p = argparse.ArgumentParser(description="Editor de video IoTing Dev")
    sp = p.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("transcribir"); t.add_argument("video"); t.add_argument("--modelo", default="small")
    s = sp.add_parser("silencios"); s.add_argument("video")
    r = sp.add_parser("render"); r.add_argument("config")
    a = p.parse_args()
    if a.cmd == "transcribir":
        transcribir(a.video, a.modelo)
    elif a.cmd == "silencios":
        total = duracion(a.video)
        print(json.dumps([{"inicio": round(x, 2), "fin": round(y, 2)}
                          for x, y in tramos_con_voz(0, total, detectar_silencios(a.video))], indent=1))
    else:
        render(a.config)


if __name__ == "__main__":
    main()
