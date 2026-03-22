# SHOKUN Validator

## Objetivo

Evaluar si una pieza cumple la filosofía SHOKUN y detectar desviaciones:

- complejidad innecesaria
- cierre incompleto
- fragilidad
- falta de claridad
- barroquismo técnico

**Referencia:** criterios de “done” en [shokun_dod.md](shokun_dod.md).

---

## Escala

Cada bloque se puntúa de **0 a 2**.

| Puntuación | Significado |
|------------|-------------|
| 0 | no cumple |
| 1 | cumple parcialmente |
| 2 | cumple bien |

**Puntuación máxima: 20** (suma de los 10 bloques).

### Interpretación del score total

| Rango | Estado |
|-------|--------|
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

## Formato de salida recomendado

### Corto

```
SHOKUN score: X/20
Estado: sólido | aceptable | incompleto | no cumple
```

### Detallado

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

- Responsabilidades mezcladas
- Demasiados archivos para algo simple
- Abstracción prematura
- Falta de validación
- Logging insuficiente
- Flujo difícil de seguir
- Solución temporal disfrazada de final
- Dependencia innecesaria
- Falta de cierre real

---

## Regla de oro

Si una solución logra el resultado pero no con **limpieza**, **simplicidad**, **robustez** y **cierre real**, no pasa SHOKUN.

---

## Ejemplo (ilustrativo)

Pieza hipotética “módulo X”: **15/20** — **aceptable**. Re-evaluar al cambiar código.

| # | Bloque | Score | Nota |
|---|--------|-------|------|
| 1 | Completitud | 2 | |
| 2 | Integración | 2 | |
| 3 | Robustez | 1 | |
| 4 | Simplicidad | 2 | |
| 5 | Minimalismo | 2 | |
| 6 | Claridad | 2 | |
| 7 | Observabilidad | 1 | |
| 8 | Validación | 2 | |
| 9 | Estabilidad | 1 | |
| 10 | Documentación | 2 | |

Usar [shokun_review_template.md](shokun_review_template.md) para registrar una revisión real.
