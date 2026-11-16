# Redline

Evaluador de red-team para agentes de IA. CLI-first, sin dependencias, agnóstico de proveedor.

Declaras un escenario y un target autorizado; Redline ejecuta, captura la traza
(prompts, respuestas, tool calls) y **valida el impacto con señales independientes**:
no le cree al modelo, le cree a la traza de backend, al cambio de estado o al
marcador de plataforma.

## Por qué existe

Las pruebas de agentes hoy se hacen a mano y se confía en lo que el modelo dice.
Redline convierte eso en un ciclo repetible: baseline, hipótesis falsable, input
controlado, evidencia observable y verificación independiente.

## Instal

Sin dependencias. Con el repositorio clonado:

```bash
python -m redline --help
```

## Uso

```bash
# catálogo de técnicas (de las labs PortSwigger)
python -m redline catalog list
python -m redline catalog show excessive-agency

# demo de extremo a extremo (target sintético)
python -m redline selftest

# correr un escenario declarado
python -m redline run --scenario scenarios/excessive_agency.json --mode vulnerable
python -m redline run --scenario scenarios/excessive_agency.json --mode contained

# reporte
python -m redline report --run <run-id> --format markdown
```

Salida: JSON estructurado + ledger JSONL en `evidence/runs.jsonl`.

## Estatus

`Confirmed`, `Blocked`, `No breach observed`, `Inconclusive`.
Un escenario solo es `Confirmed` si un validador independiente (traza, estado o
plataforma) lo respalda. Lo que el modelo afirma no cuenta como prueba.

## Límites

- MVP: adapter sintético. El adapter HTTP/MCP viene después.
- El catálogo inicial son las técnicas verificadas en las labs, no una taxonomía universal.
- El target debe estar autorizado. Redline no ataca destinos no declarados.
