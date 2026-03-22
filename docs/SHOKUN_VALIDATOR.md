# SHOKUN Validator

## Objetivo

Evaluar si una pieza cumple la filosofía SHOKUN y detectar desviaciones:

- complejidad innecesaria
- cierre incompleto
- fragilidad
- falta de claridad
- barroquismo técnico

**Referencia:** criterios de “done” en [`SHOKUN_DEFINITION_OF_DONE.md`](./SHOKUN_DEFINITION_OF_DONE.md).

---

## Escala

Cada bloque se puntúa de **0 a 2**.

| Puntuación | Significado |
|------------|-------------|
| 0 | no cumple |
| 1 | cumple parcialmente |
| 2 | cumple bien |

**Puntuación máxima: 20**

### Interpretación

| Rango | Significado |
|-------|-------------|
| 18–20 | SHOKUN sólido |
| 15–17 | aceptable pero con deuda |
| 11–14 | incompleto o demasiado complejo |
| 0–10 | no cumple SHOKUN |

---

## Checklist de evaluación

### 1. Completitud funcional

- ¿Hace exactamente lo que debe hacer?
- ¿No hay placeholders, hacks temporales o TODOs?

### 2. Integración real

- ¿Está conectado al sistema real?
- ¿Funciona dentro del flujo completo?

### 3. Robustez

- ¿Valida inputs?
- ¿Maneja errores razonables?
- ¿Evita roturas obvias?

### 4. Simplicidad arquitectónica

- ¿La solución tiene la menor complejidad razonable?
- ¿Se evitó meter capas o patrones innecesarios?

### 5. Minimalismo

- ¿Hay menos piezas, menos pasos y menos dependencias?
- ¿Se eliminó lo que no aporta valor?

### 6. Claridad

- ¿Nombres, flujo y responsabilidades son claros?
- ¿Puede entenderse rápido?

### 7. Observabilidad

- ¿Tiene logs, estado visible o trazabilidad suficiente?
- ¿Se puede diagnosticar?

### 8. Validación

- ¿Se probó comportamiento normal y casos importantes?
- ¿Se revisó que no rompe otras piezas?

### 9. Estabilidad

- ¿Es fiable?
- ¿No deja fragilidad evidente o necesidad inmediata de rehacer?

### 10. Documentación mínima operativa

- ¿Queda explicado qué hace, cómo usarlo y cómo diagnosticarlo?

---

## Salida esperada del validator

### Formato corto

```
SHOKUN score: X/20
Estado: sólido | aceptable | incompleto | no cumple
```

### Formato detallado

```yaml
score_total: X/20
estado: ...
fortalezas: []
violaciones: []
deuda_inmediata: []
acciones_para_cerrar: []
```

---

## Violaciones típicas

- responsabilidades mezcladas
- demasiados archivos para algo simple
- abstracción prematura
- falta de validación
- logging insuficiente
- flujo difícil de seguir
- solución temporal disfrazada de final
- dependencia innecesaria
- falta de cierre real

---

## Regla de oro

Si una solución logra el resultado pero no con **limpieza**, **simplicidad**, **robustez** y **cierre real**, no pasa SHOKUN.

---

## Ejemplo (pieza: Dojo validation debt — revisión manual)

*Solo ilustrativo; re-evaluar al cambiar código.*

**Formato corto:** SHOKUN score: **15/20** · Estado: **aceptable**

**Formato detallado:**

| # | Bloque | Score | Nota breve |
|---|--------|-------|------------|
| 1 | Completitud | 2 | Modelo dismiss/done y métricas cerrados |
| 2 | Integración | 2 | API, knowledge_inputs, inbox real |
| 3 | Robustez | 1 | Hecho sin evidencia; errores API UI básicos |
| 4 | Simplicidad | 2 | Un módulo central + config |
| 5 | Minimalismo | 2 | Sin infra extra |
| 6 | Claridad | 2 | Nombres y flujo legibles |
| 7 | Observabilidad | 1 | JSON/ métricas; pocos logs dedicados |
| 8 | Validación | 2 | Tests de negocio en `test_dojo_validation_debt.py` |
| 9 | Estabilidad | 1 | Gap “Hecho” vacío conocido |
| 10 | Documentación | 2 | `DOJO_PRACTICAL_AUDIT`, config, tests |

**Violaciones típicas tocadas:** falta de evidencia en Hecho (robustez/cierre); observabilidad mejorable con logs estructurados.

**Acciones para subir a 18+:** política mínima de evidencia o rol en Hecho; 1–2 logs en cierre de tarea (opcional, sin barroco).
