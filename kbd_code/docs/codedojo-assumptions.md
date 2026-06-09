# Assumptions

Prerequisites and environment expectations for this project.

## Tools

git is installed and available on PATH. All clones use HTTPS URLs, so no SSH
keys are required.

nvim is installed with the user's personal configuration. Telescope is
available for file navigation once inside nvim.

The user's shell is bash or zsh. The functions file in scripts/ uses
bash-compatible syntax. If the user switches to fish or another shell, the
functions file needs adaptation.

## Directories

The target directory for cloned repositories is ~/code-dojo/. This directory
is created by bootstrap.sh if it does not exist. It is a plain directory, not
a git repository.

The tooling repository lives at ~/personal_repos/explorations/dojo-code/. No
upstream source code is committed here.

## Notes and Annotations

The user's reading notes and annotations live in the separate kbd repository,
not in this repository or in the cloned project directories. Notes are
cross-referenced using Zotero BibTeX citation keys in <Author><Year><FirstWord>
format.

## Cloning Strategy

All projects are cloned in full (not shallow). Full git history is required
for analysis: most-edited files, blame, log.

The --force flag in bootstrap.sh performs nuke-and-reclone (rm -rf then git
clone), not fetch-and-checkout. This guarantees a clean state. Nothing valuable
is lost because the user's notes live elsewhere.
