# SHOKUN — Filosofía operativa del proyecto

**SHOKUN es obligatorio en RevMax:** define cómo se define “terminado”, cómo se revisa el trabajo y qué se considera aceptable. No es un framework ni una herramienta: es criterio compartido.

## Qué es

- **Máxima exigencia** en resultados y en funciones entregadas.
- **Cierre real** de cada pieza antes de abrir la siguiente.
- **Simplicidad y minimalismo** en arquitectura, procesos y estructuras.
- **Sin ingeniería barroca:** lo que no aporta valor se elimina.
- **Detalle, robustez operativa, claridad estructural y observabilidad.**
- **Documentación mínima operativa:** qué es, cómo usarlo, cómo diagnosticarlo.

## Principios (resumen)

1. Resultados y funciones al nivel exigido, no “casi”.
2. Una pieza cerrada de verdad antes de acumular más superficie.
3. La solución más simple que funcione bien.
4. Legibilidad y responsabilidades claras.
5. Trazabilidad suficiente para diagnosticar sin adivinar.

## Documentos

| Documento | Uso |
|-----------|-----|
| [**shokun_dod.md**](shokun_dod.md) | Definition of Done: una tarea no está terminada si no cumple **todos** los criterios. |
| [**shokun_validator.md**](shokun_validator.md) | Checklist puntuable (0–2 × 10 → **/20**) para evaluar features, módulos o refactors. |
| [**shokun_review_template.md**](shokun_review_template.md) | Plantilla reutilizable para una revisión escrita. |

## Día a día

1. Antes de dar por cerrada una pieza: recorrer el **DoD** ([shokun_dod.md](shokun_dod.md)).
2. En revisión de código o de diseño: puntuar con el **Validator** ([shokun_validator.md](shokun_validator.md)).
3. En PRs o decisiones importantes: opcionalmente rellenar [shokun_review_template.md](shokun_review_template.md) y enlazarlo.

**Regla:** si no cumple SHOKUN, no está done — aunque “funcione”.
