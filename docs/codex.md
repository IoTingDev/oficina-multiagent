# Codex (ChatGPT) como empleado de Claude

Codex viene incluido en los planes de ChatGPT, incluso Free y Go, con límites distintos. Plus tiene bastante más uso que Go.
**Estrategia:** mientras tengas Plus, Codex hace la implementación pesada de código. Claude planifica, revisa y prueba. Así el cupo Pro de Claude rinde mucho más.

## Instalación (una vez)
Lo hace todo `scripts/instalar.ps1`. Si prefieres hacerlo a mano:
```bash
npm install -g @openai/codex@0.150.0   # >=0.160 no trae "codex mcp-server"
codex login          # inicia sesión con tu cuenta de ChatGPT
```

## Conectarlo a Claude Code
Desde la carpeta de la oficina (o de cualquier proyecto):
```bash
claude mcp add codex -s user -- codex mcp-server
```
Verifica en Claude Code con `/mcp`. A partir de ahí puedes decir, por ejemplo: *"que Codex implemente el módulo X y tú revisa"*.

## Reglas para Codex
Codex lee `AGENTS.md` (en la raíz de cada repo). Ahí están las mismas reglas de la oficina.

## Cuándo usar cuál
| Tarea | Quién |
|---|---|
| Implementar mucho código, refactors, tests repetitivos | **Codex** |
| Arquitectura, decisiones, revisar el código de Codex | **Claude (Sonnet)** |
| Bugs difíciles, segunda opinión | Los dos (uno propone y el otro revisa) |
| Redes, propuestas, investigación, documentos | **Claude** |

Si vuelves al plan Go, Codex sigue funcionando pero con menos uso. Úsalo solo para revisiones de código.
