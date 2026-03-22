# SHOKUN — Definition of Done (DoD)

## Propósito

Define el estándar **mínimo obligatorio** para considerar una pieza realmente terminada.  
No basta con que “funcione”: debe estar **completa, integrada, robusta, simple y cerrada de verdad**.

**Una tarea o entrega no está terminada si no cumple *todos* los criterios siguientes.**

---

## Principios SHOKUN

1. Máxima exigencia en resultados.
2. Cierre completo de cada pieza antes de avanzar.
3. Simplicidad y minimalismo en arquitectura.
4. Atención extrema al detalle.
5. Robustez operativa real.
6. Claridad estructural y legibilidad.
7. Evitar ingeniería barroca.
8. Lo que no aporta valor, se elimina.

---

## Criterios (todos obligatorios)

### 1. Completitud funcional

- La funcionalidad está implementada de forma completa.
- Cumple exactamente el objetivo definido.
- No quedan TODOs, placeholders ni partes simuladas.
- No depende de “ya lo arreglaremos después”.

### 2. Integración real

- Está conectada al flujo real del sistema.
- No es una demo aislada.
- Funciona dentro del contexto completo del proyecto.

### 3. Robustez

- Maneja errores esperables.
- Valida inputs cuando aplica.
- Tolera estados no ideales sin romper el sistema.
- Tiene fallback o salida controlada cuando corresponde.

### 4. Simplicidad arquitectónica

- La solución usa la menor complejidad razonable.
- No hay capas, patrones o abstracciones innecesarias.
- Cada módulo tiene una responsabilidad clara.
- La solución elegida es la más simple que resuelve bien el problema.

### 5. Minimalismo estructural

- Mínimo número razonable de archivos, pasos, dependencias y componentes.
- No hay piezas ornamentales o redundantes.
- No se introduce infraestructura antes de necesitarla de verdad.

### 6. Claridad

- Nombres claros.
- Flujo entendible.
- Responsabilidades bien separadas.
- Un experto puede entender la pieza rápidamente.

### 7. Observabilidad

- Logs o trazas suficientes para diagnosticar.
- Estados visibles o inspeccionables.
- Decisiones importantes explicables.

### 8. Validación

- Comportamiento normal probado.
- Casos límite relevantes revisados.
- No rompe piezas existentes relacionadas.

### 9. Estabilidad

- No requiere intervención manual constante.
- No introduce fragilidad evidente.
- No deja deuda técnica inmediata conocida sin registrar o resolver.

### 10. Documentación mínima operativa

- Queda explicado qué hace.
- Queda explicado cómo usarlo.
- Queda explicado cómo diagnosticarlo si falla.
- Sin documentación barroca ni relleno.

### 11. Cierre real

- No necesita una “v2 urgente”.
- No queda a medio cerrar.
- Se puede dar por terminado sin autoengaño.

---

## Antipatrones prohibidos

- “Ya funciona más o menos”.
- “Dejamos esto temporal y luego volvemos”.
- “Metemos otra capa por si acaso”.
- “Lo hacemos genérico aunque aún no haga falta”.
- “Creamos cinco archivos cuando bastan dos”.
- “No está limpio pero ya tirará”.

---

## Regla final

Si una pieza **no cumple todos** los puntos anteriores, **no está DONE** según SHOKUN.

---

## Puntuación y revisión

Para evaluar con nota sobre 20, usar [shokun_validator.md](shokun_validator.md) y la plantilla [shokun_review_template.md](shokun_review_template.md).

---

## Dominio RevMax (referencia, no sustituye el DoD)

Criterios específicos de producto (p. ej. Dojo, knowledge): ver `docs/DOJO_*` y auditorías en `docs/` cuando apliquen.
