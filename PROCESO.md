# Proceso diario – Short de Boquiabierto

Canal: Boquiabierto (@boquiabierto.datoss), YouTube Shorts de curiosidades en español neutro.
Objetivo: 1 Short al día, todo animado con IA, publicado a las 19:30 (Europe/Madrid) vía Metricool.

## Datos fijos
- Metricool: marca con blogId **7795733** (su YouTube es UC3UI6XLCfcVYhm1_b1c885g = boquiabierto.datoss). Comprobar con
  `getBrandSettings` que el blogId sigue teniendo ese canal. NUNCA publicar en otra marca (la 7440516 es AquaPet).
- Voz ElevenLabs: voice_id **18GZPpJvaVG53Nt3H52N** (SAM ADAM, latino neutro), modelo `eleven_v4`, `generations_count: 1`.
- Vídeo IA: ElevenLabs `ltx-v2-fast` (clips de 6 s, 1920x1080, unos 1.454 créditos cada uno). 4 clips por Short.
- Transcripción con tiempos por palabra: ElevenLabs `creative_transcribe_audio` (`eleven_scribe_v1`, gratis) conectado al nodo de la voz.
- Montaje: `python3 tools/montaje.py config.json` (ver cabecera del script). Necesita ffmpeg y la fuente Inter Display Black.

## Pasos
1. **Idea**: primera idea sin marcar de `ideas.md` (respetando la regla de categorías).
2. **Verificar** el dato con 1–3 búsquedas web y abrir al menos una fuente fiable. Si no se confirma → marcarla `[~]` con el motivo y pasar a la siguiente.
3. **Guion** (55–65 palabras, 20–27 s): gancho en la primera frase (sin saludo), dato, giro con «Pero lo más loco es esto:»
   y cierre «Sígueme para más datos que no te enseñaron en el colegio.» Etiquetas de emoción de eleven_v4 al inicio de
   frases clave: `[intrigued]`, `[curious]`, `[excited]`. Nada que no esté verificado.
4. **Flow** de ElevenLabs nuevo (`creative_create_flow`, nombre «Short NN - tema») y, en paralelo: la voz y 4 clips.
   Prompts de vídeo en inglés, cinematográficos, con el sujeto centrado («subject centered in frame»), un clip por momento
   del guion (gancho, explicación, giro, cierre). Sondear con `creative_get_flow_run_status`.
5. **Revisar los clips**: sacar 3 fotogramas de cada uno y mirarlos. Si alguno sale deforme o no se entiende,
   repetir SOLO ese clip una vez con un prompt mejor.
6. **Transcribir** la voz para tener los tiempos por palabra. Guardar la lista `words` en `words.json`.
7. **Montar**: escribir `config.json` con escenas cortadas en los cambios de frase (escenas de 2,5–6 s; se pueden
   reutilizar clips con otro `src`, `reverse`, `zoom` o encuadre). Gancho de pantalla en 2 líneas cortas, en mayúsculas,
   con curiosidad (no repetir la primera frase literal). `keywords` = 6–10 palabras clave tal como salen en la transcripción.
   Opcional: escena `freeze` + `beep_at` en el momento de impacto. `ambience`: `underwater` para mar, `soft` para el resto.
8. **Revisar el vídeo final**: 6–7 fotogramas en una tira; comprobar encuadre, subtítulos y duración. Corregir y volver a montar si hace falta.
9. **Subir** el mp4 a este repositorio en `videos/AAAA-MM-DD_tema.mp4`, commit y push a `main`.
   Enlace público: `https://raw.githubusercontent.com/javiersikkoo/boquiabierto-videos/main/videos/<archivo>`
   (comprobar con `curl -I` que da 200).
10. **Programar** en Metricool (`createScheduledPost`, blogId 7795733) para hoy a las **19:30 Europe/Madrid**
    (si ya pasó, mañana a las 19:30), red `youtube`, con
    `youtubeData: {title, type: "short", privacy: "public", tags, category: "EDUCATION", madeForKids: false, isAiGeneratedContent: true}`.
    Título < 70 caracteres con emoji y `#shorts`; descripción con el dato, la llamada a seguir y 5–6 hashtags.
    **TikTok** (misma marca, misma hora, publicación aparte con `providers: [{"network":"tiktok"}]`): mismo vídeo,
    `text` = gancho corto + emoji + «¿Lo sabías?» + 5–6 hashtags (incluido #aprendeentiktok), y
    `tiktokData: {title (OBLIGATORIO, corto, con emoji), privacyOption: "PUBLIC_TO_EVERYONE", isAigc: true, autoAddMusic: false}`.
    Comprobar antes con `getBrandSettings` que la marca tiene `tiktokData: boquiabierto.datoss`; si no, publicar solo en YouTube y avisar.
11. **Marcar** la idea en `ideas.md` como `[x] … · publicado AAAA-MM-DD`, y añadir una línea a `publicados.md`
    (fecha, nº de idea, título, archivo, id de Metricool, fuente). Commit y push.
12. **Limpieza**: borrar de `videos/` los mp4 de más de 5 días (Metricool guarda su propia copia). Commit y push.
13. **Aviso al usuario** con `SendUserMessage`, en español y breve: qué se ha programado, a qué hora y el enlace del planificador de Metricool.
    Si algo falló (créditos, conexión, Metricool), decir qué falló y qué falta, sin inventar que se publicó.

## Límites
- Máximo 5 clips de vídeo por Short (4 + 1 repetición). Si no hay créditos suficientes, no publicar a medias: avisar.
- No reproducir contenido con derechos de autor ni personajes conocidos; nada de personas reales identificables.
