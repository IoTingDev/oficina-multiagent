# Editor de video (ffmpeg + Whisper)

Todo el procesamiento corre en tu PC, sin gastar cupo de Claude. El agente `editor-video` solo lee la transcripción y escribe el archivo de cortes.

## Instalación (una vez)
1. ffmpeg: `winget install Gyan.FFmpeg` (Windows) y reinicia la terminal.
2. Python 3.10+ y: `pip install -r scripts/video/requirements.txt`
3. Pon el logo en `marca/logo.png` y los colores en `marca/marca.json`.

## Uso
```bash
# 1. Transcribir (crea crudo.mp4.transcripcion.txt / .json)
python scripts/video/editar.py transcribir redes/crudos/sensor-cacao.mp4

# 2. (opcional) Ver dónde hay voz
python scripts/video/editar.py silencios redes/crudos/sensor-cacao.mp4

# 3. Render de las versiones TikTok e Instagram
python scripts/video/editar.py render redes/crudos/sensor-cacao.corte.json
```

## Archivo de cortes (`*.corte.json`)
```json
{
  "fuente": "redes/crudos/sensor-cacao.mp4",
  "nombre": "2026-11-24_sensor-cacao",
  "segmentos": [ {"inicio": 12.4, "fin": 31.0}, {"inicio": 45.2, "fin": 58.8} ],
  "gancho": {
    "tiktok": "¿Cuánta agua necesita de verdad el cacao?",
    "instagram": "Monitoreo de humedad para cacao de exportación"
  },
  "versiones": ["tiktok", "instagram"],
  "quitar_silencios": true,
  "cierre": true
}
```

## Historias con varios videos
Cada segmento puede venir de un archivo distinto, y `velocidad` acelera un tramo (timelapse, con el audio silenciado en ese tramo):
```json
{
  "nombre": "2026-11-24_replica-3d",
  "gancho": {"tiktok": "Nos llegó esta pieza rota…", "instagram": "Réplica funcional por impresión 3D"},
  "segmentos": [
    {"fuente": "redes/crudos/05.mp4", "inicio": 3.0, "fin": 6.5},
    {"fuente": "redes/crudos/01.mp4", "inicio": 0.0, "fin": 12.0},
    {"fuente": "redes/crudos/03.mp4", "inicio": 0.0, "fin": 80.0, "velocidad": 8},
    {"fuente": "redes/crudos/05.mp4", "inicio": 6.5, "fin": 20.0}
  ]
}
```

## Ver un video sin abrirlo
`python scripts/video/editar.py fotogramas redes/crudos/01.mp4` crea `01.mp4.fotogramas.jpg`, una hoja de 8 cuadros con marcas de tiempo.

## Qué hace
- Une los segmentos y quita silencios de más de 0,6 s.
- Pasa a vertical 1080×1920. Si el video es horizontal, pone fondo desenfocado.
- Subtítulos automáticos: estilo TikTok (MAYÚSCULAS, 3 palabras, borde) o Instagram (caja con color de marca).
- Gancho en pantalla los primeros 3 s, logo y, en Instagram, cierre de 1,5 s con logo, web y usuario.
- Audio normalizado a −14 LUFS (estándar de redes).
- Salida en `redes/por-aprobar/`.
