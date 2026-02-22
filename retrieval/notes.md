---
title: Notes for simple retrieval practice project
author: Luis
date: 2025-09-15
---
## Notes
### 2025-09-15
Current plan:
  Have questions in simple plain text with simple "custom" format.
  Parse with R and select subset.
  Output to console or a file. Output answer to separate file for evaluation.
  Manually add questions.

Added four questions from different fields.
Used initial format:
```format
Q:
A:
---
```

Could have format in readable form and process to csv.

### 2025-09-16
Primero determiné como unir el rango de cada par de pregunta y contestación.
Seleccionar rango, e usar un for loop sencillo para convertir a dataframe.
Solo hay dos posibilidades: ser pregunta o contestación. Lo único sería manejar la presencia de "Q:" o "A:".
También tenía que añadir una linea nueva al agregar nuevo contenido a constestacion o linea.

#### Session 2
Should I figure out how to print the dataframe as an alternative to typing the name while working on the REPL?
Got the loop. Estoy seguro que algo asi de sencillo seria bastante efectivo como quiera.
Puedo facilmente añadir mas preguntas. Ahora tendria que añadir categorias y ver si es mejor generar archivos tipo texto, markdown, html o user el repl u otras formas mas interactivas.

### 2025-10-14
First time in a while. Never did the clean up.
Turns out a recent article came out in Hacker news (plain text spaced repetition) and used a similar format for the Q&A pairs. Good signs?
