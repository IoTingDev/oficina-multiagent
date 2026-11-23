# Oficina Virtual — IoTing Dev

Equipo de agentes de IA para DEV INGENION SAS, gerenciado por Claude.

## Cómo se usa
1. Clona este repo en tu PC y ábrelo con **Claude Code** (app de escritorio).
2. Háblale al gerente en lenguaje natural:
   - *"Edita los videos que dejé en redes/crudos y prepárame las versiones de TikTok e Instagram."*
   - *"Arma la propuesta para la startup del invernadero con lo que tenemos."*
   - *"Que dev-software revise el bug del panel admin."*
3. El gerente delega en los agentes (`.claude/agents/`) y te deja todo en **POR APROBAR** en `tareas/tablero.md`.

## Estructura
| Carpeta | Qué hay |
|---|---|
| `CLAUDE.md` | Reglas del gerente y ahorro de cupo |
| `AGENTS.md` | Reglas para Codex |
| `.claude/agents/` | Los 8 agentes (dev, I+D, comercial, finanzas, estratega, guionista, editor, analista) |
| `marca/` | Brand kit, colores y logo |
| `redes/` | Estrategia, crudos, por aprobar, publicado, métricas, guiones, calendario |
| `scripts/video/` | Editor automático (ffmpeg + Whisper) |
| `tareas/tablero.md` | Estado de todo |
| `docs/` | Configuración de Codex y otros |

## Para tus otros repos
Copia `.claude/agents/dev-software.md` y `AGENTS.md` a cada proyecto (panel_admin_ingenion, app_finanzas, etc.) para que trabajen con las mismas reglas.
