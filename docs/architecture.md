# Arquitectura

Redline separa cinco responsabilidades para que la misma lógica sirva para HTTP,
MCP o un target sintético.

```
escenario (JSON)
   │
   ▼
runner ──► adapter (base.TargetAdapter)
   │          ├─ mock      (demo, tests)
   │          └─ http/mcp  (roadmap)
   │
   ├─ captura: prompts, respuestas, tool calls, estado antes/después, marker
   │
   ▼
validators (señales independientes)
   ├─ tool_trace  ¿ejecutó la herramienta esperada?
   ├─ state       ¿cambió el estado observable?
   └─ platform    ¿la plataforma lo confirma?
   │
   ▼
ledger JSONL (append-only) ──► report (JSON / Markdown)
```

## Regla de oro

El resultado es `Confirmed` solo si un validador independiente lo respalda.
El texto del modelo es contexto, nunca prueba.

## Adapter contract

```python
class TargetAdapter(Protocol):
    name: str
    def send(prompt, context=None) -> AgentResponse: ...
    def snapshot(self) -> dict: ...
    def platform_marker(self) -> str | None: ...
```

Un adapter nuevo no requiere tocar runner, validators ni report.

## Scope

`Scope` fija target, allowlist, límites de requests y tiempo, y credenciales
mínimas. Redline no ejecuta shell provisto por el modelo.

## Roadmap

1. Adapter HTTP real (chat HTTP) y MCP sobre el mismo runner.
2. Escenarios por técnica del catálogo, con sus controles negativos.
3. Reporte en HTML y exportación a evidencia portable.
4. Validadores adicionales (redacción, codificaciones, permisos por identidad).
