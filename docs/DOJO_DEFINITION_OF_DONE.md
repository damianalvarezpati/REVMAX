# Dojo — Definition of Done

Documento operativo complementario a **[DOJO_ROLE_AND_PRINCIPLES.md](./DOJO_ROLE_AND_PRINCIPLES.md)**. Lista criterios concretos para considerar cerrado un ciclo de trabajo relacionado con el Dojo.

---

## Validación humana

- [ ] Casos en `qa_runs` relevantes para el cambio tienen `human_verdict` cuando el flujo exige decisión.
- [ ] Tareas **pending** críticas del inbox (`validation_inbox`) están **done** o **dismissed** con motivo trazable, o están explícitamente aceptadas como riesgo residual documentado.

## Conocimiento promovido

- [ ] Cualquier promoción a `accepted_knowledge` cumple el contrato de API (campos obligatorios, hash, sin duplicados frívolos).

## Refresh / equilibrio

- [ ] Un run de Knowledge Refresh no deja observaciones “huérfanas” sin política: o se aceptan, o quedan como deuda en inbox según reglas.

## Scores y reporting

- [ ] Cambios en fórmulas de `area_score`, penalización por deuda o balancing están reflejados en `scoring_notes` / documentación técnica asociada.

## Reglas y motor PRO

- [ ] Ajustes a reglas que afecten decisiones PRO tienen referencia en código o ledger, alineados con [KNOWLEDGE_PRO_INTEGRATION.md](./KNOWLEDGE_PRO_INTEGRATION.md).

---

*Si un ítem no aplica a un cambio concreto, debe indicarse explícitamente en el PR o nota de release.*
