---
title: "Errors encountered during cv_in_quarto project completion"
date: 2025-06-08
---

# Overview
Erros encountered during completion of the cv_in_quarto project. Organized by date encountered. 
Each one will include the cli command or commit, the error and the solution.
To revisit the state:
git checkout <commit-hash>

## 2025-06-08
### Arial not found
- Command
```{bash}
quarto render cv_in_quarto/luis_martinez_cv.qmd
```
- Commit hash
1b83ac541932effd0bf01c4d1763372678a67c18
- Error
```{error}
ERROR:
compilation failed- no matching packages
Package fontspec Error: The font "Arial" cannot be found.
```
- Solution
```{bash}
sudo apt update
sudo apt install ttf-mscorefonts-installer
fc-cache -fv
# Confirm
fc-match Arial
# Render to confirm
quarto render cv_in_quarto/luis_martinez_cv.qmd
```

### Digraphs do not show up
- Command
```{bash}
# see the resulting pdf.
quarto render cv_in_quarto/luis_martinez_cv.qmd
```
- Commit hash
a810d19c8aba6b2d3e8830f2dabdbc6927600fa5
- Error
```{error}
Digraphs do not show in the pdf. The digraphs are the accented i present in my lastname.
```
- Solution
Tried putting it in latex but it doesnt work if it is in the yaml.
```{attempt}
title: "Luis E. Mart\'{i}nez-Rodr\'{i}guez, Ph.D."
ERROR: YAMLException: unknown escape sequence (2:22)
```
The solution was to set the enconding to utf8 in the yaml header.
```{quarto}
  pdf:
    mainfont: "Arial"
    fontenc: "T1"
    inputenc: "utf8"
    fontsize: 11pt
```

### Custom function does not run from neovim.
- Command
```{neovim}
:! view_files -t pdf cv_in_quarto
```
- Commit hash
ed339e7a1add733c75bf04945df8c7f119d9da1e
- Error
The script is executed in a non-interactive non-login shell. .bashrc is never accesible.
```{error}
/bin/bash: line 1: view_files: command not found shell returned 127
```
- Solution
Turn function into script or run terminal
Remember to exit using Ctrl+\ Ctrl+n

### Custom function does not run from neovim.
- Command
```{bash}
quarto render cv_in_quarto/luis_martinez_cv.qmd
```
- Commit hash
ae33a7c5212320d7eba18302d865cb1fc18f83d3
- Error
```{error}
ERROR:
compilation failed- error
Undefined control sequence.
<argument> \fullunderline
...
```
- Solution
Requires the definition of control sequence in the header. See the underline section in the development_log.qmd.
