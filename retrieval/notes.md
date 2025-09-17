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
