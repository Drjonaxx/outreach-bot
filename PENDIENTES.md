# Pendientes

La rutina «Capataz» (tarea programada de Claude, lunes y jueves 9:44 am) lee este
archivo y toma el primer pendiente de **Para Claude** que no esté hecho.
En este repo **nunca** hace push a `claude/clipper` ni a
`claude/clipper-out`: esas ramas las mueven las rutinas de clips, y un
push de otra sesión les rompe el suyo. Si el clipper necesita un arreglo,
lo deja en la rama `claude/automatizar-tareas-czbut9` y lo avisa.

## Para Jonathan

- [x] Fusionar `claude/automatizar-tareas-czbut9` a `main` (17 oct 2026).
- [ ] Prender en Make «Post Threads IA Diario (a email)» si quieres el
      post de @beingvortex en tu correo cada mañana.
- [ ] TikTok: subir a mano los clips que dicen los mensajes de la noche.

## Para Claude

- [ ] Revisar cada semana `clipper-pruebas.yml`: si sale en rojo, buscar
      la causa en `claude/clipper` y dejar el arreglo listo (sin push a
      esa rama).
- [ ] Una vez por semana, comparar en YouTube (vistas por streamer) qué
      rinde más y proponer cambios a `daily.json` en el resumen del
      domingo.
