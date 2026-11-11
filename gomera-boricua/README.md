# Gomera Boricua

Juego de gomera con física, en una sola página. Las iguanas se metieron en el
patio y hay que sacarlas tirándoles frutas con la gomera: estructuras de
madera, zinc y bloques que se caen de verdad.

**Jugar:** https://claude.ai/artifact/Ea8orVGCgJBaNP6UNJeYa7 (mejor con el celular de lado).

## Cómo se juega

- Arrastra hacia atrás desde cualquier parte de la pantalla y suelta. Mientras más estiras, más lejos va.
- Con la fruta en el aire, toca la pantalla para usar su poder.
- Ganas cuando no queda ninguna iguana. Cada fruta que te sobra vale 10,000 puntos.

| Fruta | Poder | Buena contra |
|---|---|---|
| Mangó | Ninguno: pesa y empuja | Madera |
| Quenepas | Se abren en tres | Zinc |
| Coco | Cae en picada | Bloques |
| Ají caballero | Explota | Todo lo que esté cerca |

El cilindro de gas explota cuando le pegan. La iguana jefa (nivel 8) aguanta
más golpes que las demás.

## Niveles

1. El patio · 2. La marquesina · 3. Bloque y cemento · 4. La casita ·
5. El monte · 6. El cilindro de gas · 7. Noche de coquíes · 8. La iguana jefa

Pasar un nivel abre el siguiente. Las estrellas y la mejor puntuación se
guardan en el navegador de quien juega.

## Técnico

- Todo está en `index.html`: el dibujo es en canvas, sin imágenes, y los sonidos se generan con Web Audio (el coquí incluido).
- La física es [Matter.js](https://brm.io/matter-js/) 0.19.0, que se baja de cdnjs.
- Para cambiar o añadir niveles, edita `LEVELS`. Las piezas se apilan con `frame()`, `post()`, `slab()`, `box()`, `igu()`, `jefa()`, `tank()` y `hill()`, midiendo desde el suelo (`G = 800`).
- Se probó con Playwright que las 8 estructuras se quedan quietas solas (se mueven menos de 3 px en 5 segundos) y que cada nivel se puede ganar: una búsqueda automática de tiros pasó los 8, a veces con frutas de sobra.
- Para publicar cambios en el mismo link: Artifact con `action: "read"` y el `url` de arriba, y después publicar con ese mismo `url`.
