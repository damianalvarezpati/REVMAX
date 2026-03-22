# Contribuir a RevMax

## SHOKUN

El estándar de calidad y de “terminado” es **SHOKUN**. Antes de fusionar cambios sustanciales:

1. Revisar [docs/shokun/shokun_dod.md](docs/shokun/shokun_dod.md) (todos los criterios).
2. Opcional pero recomendable: puntuar con [docs/shokun/shokun_validator.md](docs/shokun/shokun_validator.md) o usar [docs/shokun/shokun_review_template.md](docs/shokun/shokun_review_template.md).

Índice: [docs/shokun/README.md](docs/shokun/README.md)

## Pruebas

Ejecutar la suite de tests del proyecto antes de abrir un PR (ajusta el comando si usas otro entorno):

```bash
python3 -m pytest tests/ -q
```

## Estilo

- Preferir soluciones simples y legibles.
- Evitar dependencias nuevas salvo necesidad clara.
- Documentación mínima: qué cambia, cómo probarlo, cómo detectar fallos.
