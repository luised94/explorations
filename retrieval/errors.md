---
title: Errors encountered during retrieval project development
author: Luis
date: 2025-09-15
---

# Overview
Document specific errors encountered during development of project.

# Errors
### 2025-09-16
Error:
Error in questions_file_data[first_line_of_pair, last_line_of_pair] :
    incorrect number of dimensions
Solution:
Estaba accediendo a un vector object como si fuera un dataframe o matriz.
```r
questions_file_data[first_line_of_pair:last_line_of_pair]
```
---
Error:
Error in if (grep("^A:", line)) { : argument is of length zero
Solution:
Utilice la funcion grep en vez de grepl. grep devuelve el indice mientras que grepl devuelve valor booleano.
