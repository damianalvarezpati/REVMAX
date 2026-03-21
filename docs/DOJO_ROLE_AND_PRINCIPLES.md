# Dojo — Rol y principios (documento rector)

Este documento fija el **papel del Dojo dentro de RevMax**. No es marketing: guía decisiones de diseño, priorización y gobernanza del conocimiento.

---

## 1. Qué es el Dojo

El **Dojo** es el **órgano de sentido y disciplina** del sistema respecto al conocimiento útil para decisiones de revenue:

- **Absorbe información** desde datasets indexados, patrones extraídos, reglas candidatas, ejecuciones de análisis, observaciones de refresh y casos de validación.
- **Clasifica y juzga** esa información: qué cuenta como evidencia, qué es hipótesis, qué está integrado al motor PRO y qué no.
- **Exige validación humana** cuando el sistema no puede honestamente tratar algo como cerrado (hipótesis, divergencias, casos sin veredicto).
- **Enseña al sistema** en el sentido operativo: promoción controlada de observaciones a conocimiento aceptado, casos gold/candidatos, ledger de validación — siempre con trazabilidad.
- **Modula confianza y madurez** mediante scores por área, deuda de validación, equilibrio de conocimiento y límites explícitos al subir de “nivel” sin trabajo real.

En una frase: **el Dojo es el sensei del conocimiento en RevMax** — no una pantalla decorativa ni un archivo más.

---

## 2. Qué no es el Dojo

- **No** es solo la UI del frontend: la UI es un **visor** de reglas, bandeja, inputs y estado; el Dojo es el **rol funcional** que atraviesa API, datos y flujos.
- **No** es un repositorio pasivo de “casos”: los casos son **material de juicio**; sin juicio y sin vínculos a reglas/áreas, no sustituyen gobernanza.
- **No** es un módulo opcional al final del pipeline: condiciona **madurez**, **prioridad de esfuerzo** y **bloqueos** cuando la deuda es inaceptable.
- **No** es el motor de pricing en sí: el **decision engine** PRO ejecuta reglas; el Dojo vigila **calidad del conocimiento** que alimenta y rodea esas reglas.

---

## 3. Papel dentro de RevMax

| Dimensión | Papel del Dojo |
|-----------|----------------|
| **Gobernanza** | Define qué se acepta como conocimiento consolidado vs observado, y bajo qué condiciones. |
| **Priorización** | Ordena esfuerzo (refresh, validación, ingestión) hacia áreas débiles vía *balancing* y deuda. |
| **Honestidad** | Evita que el sistema se califique bien solo por actividad o datos mal anclados. |
| **Enseñanza** | Conecta validación humana, ledger y aceptación explícita con mejoras medibles en inputs del modelo. |

---

## 4. Interacción con el resto del sistema

### Datasets (`MASTER_DATASET_INDEX`, flags por área)

- El Dojo **no** ingiere datos por sí mismo: **consume** qué hay indexado y cuánto aporta por área.
- Los huecos de cobertura alimentan **gaps** y, con el tiempo, **tareas** (indirectamente vía madurez y refresh).

### Scraping / fuentes externas

- Cualquier scraping o HTTP debe ser **dirigido, trazable y acotado** (p. ej. allowlist en refresh).
- El Dojo trata esas fuentes como **señales candidatas**, no como verdad hasta pasar por observación → aceptación / validación.

### Knowledge Inputs (`knowledge_inputs`, snapshot)

- Es la **radiografía por área**: cobertura, calidad, validación, readiness, `area_score`, gaps.
- Los scores están **acotados** por reglas explícitas; la **deuda de validación** puede **penalizar** y **bloquear** subidas de madurez.

### Knowledge Refresh

- Observa cambios (datasets nuevos, patrones, extract opcional) y **no auto-acepta** conocimiento.
- La selección de áreas puede ser **dinámica** (equilibrio) en lugar de uniforme.
- Las observaciones pueden generar **tareas de inbox** hasta revisión humana.

### Validation debt / Dojo inbox

- La validación humana es **deuda operativa acumulada**, no una sugerencia suave.
- Tareas pendientes **obligatorias** con prioridad, vínculos y estado; impactan métricas y madurez.

### Decision engine (PRO / reglas deterministas)

- El Dojo **no** reemplaza reglas PRO: vigila **alineación** (reglas esperadas vs integradas), hipótesis no validadas y promoción trazable.
- Cambios en reglas **críticas** exigen trazabilidad (accept-observed, ledger, revisiones), no “ajustes silenciosos”.

### Casos Dojo (training candidates, `qa_runs`)

- Son **vehículos de juicio humano** y material para mejorar consistencia; deben estar ligados a áreas y, donde aplique, a reglas/hipótesis.

### Futuro ML / modelos

- El Dojo impone **disciplina previa**: sin datos etiquetados, validación y reglas honestas, el ML no compensa autoengaño.
- Cualquier uso futuro de ML debe **respetar** la misma jerarquía: evidencia → validación → promoción.

---

## 5. Funciones principales (resumen operativo)

1. **Absorber** — Unificar señales desde índices, reglas, ledger, QA y refresh en un marco común.
2. **Clasificar y juzgar** — Distinguir hipótesis vs evidencia, integración PRO vs pendiente.
3. **Detectar huecos** — Gaps explícitos por área y por tipo (datos, patrones, motor, validación).
4. **Equilibrar conocimiento** — Reparto dinámico de esfuerzo hacia áreas débiles (*knowledge balancing*).
5. **Exigir validación humana** — Inbox con tareas obligatorias y umbrales de bloqueo.
6. **Enseñar al sistema** — Promoción de conocimiento aceptado, candidatos y ledger con criterios.
7. **Modular confianza y madurez** — Scores, penalizaciones, techos y deuda visibles.

---

## 6. Límites (anti–autoengaño)

| Límite | Implicación |
|--------|-------------|
| **No autoconvencerse** | Métricas y subidas de score deben reflejar **trabajo verificable**, no volumen de actividad vacía. |
| **No aceptar verdad débil como sólida** | Hipótesis y reglas parciales siguen etiquetadas; la aceptación manual exige campos explícitos y deduplicación. |
| **No cambiar reglas críticas sin trazabilidad** | Promoción vía APIs y artefactos auditables (`accept-observed`, ledger, notas en runs). |
| **No inflar scores por actividad vacía** | Bonus de calidad acotados; deuda de validación penaliza; refresh no sustituye validación. |

---

## 7. Principios de diseño

1. **Honestidad** — Preferir etiquetas “débil” / “hipótesis” a una falsa sensación de cobertura.
2. **Trazabilidad** — Cada promoción y cada tarea enlaza fuente, motivo y responsable cuando aplica.
3. **Disciplina** — Inbox y umbrales obligan a cerrar deuda antes de declarar éxito.
4. **Mejora progresiva** — Targets y equilibrio buscan cerrar brechas sin prometer saltos mágicos.
5. **Equilibrio del conocimiento** — Reforzar lo débil sin sobre-invertir en lo ya fuerte.
6. **Utilidad real** — Si no impacta decisiones, pricing o riesgo operativo, no merece inflar la madurez.

---

## 8. Documentos relacionados

| Documento | Contenido enlazado |
|-----------|-------------------|
| [DOJO_DEFINITION_OF_DONE.md](./DOJO_DEFINITION_OF_DONE.md) | Criterios de “hecho” para trabajo Dojo/validación. |
| [DOJO_AUDIT_VS_CHARTER.md](./DOJO_AUDIT_VS_CHARTER.md) | Auditoría del estado real del Dojo frente a charter y DoD. |
| [KNOWLEDGE_INPUTS_DOJO.md](./KNOWLEDGE_INPUTS_DOJO.md) | Modelo de datos y scoring por área. |
| [KNOWLEDGE_REFRESH.md](./KNOWLEDGE_REFRESH.md) | Refresh nocturno, observaciones, aceptación manual. |
| [KNOWLEDGE_BALANCING.md](./KNOWLEDGE_BALANCING.md) | Equilibrio activo de esfuerzo entre áreas. |
| [DOJO_VALIDATION_DEBT.md](./DOJO_VALIDATION_DEBT.md) | Inbox de deuda de validación y penalización. |
| [KNOWLEDGE_PRO_INTEGRATION.md](./KNOWLEDGE_PRO_INTEGRATION.md) | Integración con el motor PRO. |

---

## 9. Evolución

Este documento es **normativo para el diseño**. Los cambios de comportamiento en código deben poder explicarse en términos de: rol del Dojo, principios anteriores y límites — o el cambio debe actualizar explícitamente este documento.
