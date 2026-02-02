# kbd_code setup issues
Document issues related to kbd system setup.

## 2026-01-27
- Wanted to keep the repo simple by syncing to a usb. Syncing to usb also avoids using github or other public service. I will eventually transition to ssh.
- WSL/Windows prevented creating the repo on the usb.
    > Mount the usb from wsl and git init from powershell.
    > Confirm that you can see the contents of the usb and run git operation. Tell git that the repo is safe to work with.

```bash
sudo mount -t drvfs D: /mnt/d -o metadata
```

```powershell
cd D:\
mkdir personal_repos
cd personal_repos
git init --bare kbd.git
```

```bash
cd /mnt/d
ls # confirm contents of usb if any.
git log # any git operation that is available outside of work trees.

# After warning message
git config --global --add safe.directory /mnt/d/personal_repos/kbd.git
```

- After the usb is setup, create the local copy via wsl.

```bash
# Location is preference based. I keep repos and worktrees in one directory.
mkdir ~/personal_repos/kbd/

# Go to your working directory
cd ~/personal_repos/kbd

# Initialize git
git init

# Create the initial files
touch journal.txt notes.txt context.txt .gitignore

# Add remote pointing to USB bare repo
git remote add origin /mnt/d/personal_repos/kbd.git

# Stage, commit, push
git add -A
git commit -m "init"
git push -u origin master
git pull # Should show 'already up to date' message.
```

Used initial kbd_setup.sh functions.
ksuboff returns: 'umount: /mnt/d: target is busy.' because a the directory was opened in a tmux pane. Afterwards, kusboff worked and was able to eject. Disconneted the usb and reconnected to run kbd_find_usb.
Fixed bug where I inverted a test. '-z $VARIABLE' is true if empty.

## 2026-01-28
Tried to transfer the repo via usb to a new device. The drive was not showing up on wsl.
```error
mount: /mnt/d: mount point does not exist.
```

Had to create the directory and then mount.

```bash
sudo mkdir -p /mnt/d
kbd_find_usb # takes care of mounting the drive.
ls /mnt/d # should show contents now.
```

Once the drive's contents are visible, git clone. May get the ownership issue again. Just run the same command.

```bash
git config --global --add safe.directory /mnt/d/personal_repos/kbd.git
git clone /mnt/d/personal_repos/kbd.git ~/personal_repos/kbd
cd ~/personal_repos/kbd
git log # check the HEAD log.
```

## 2026-02-02
### WSL Permission Drift
The WSL drvfs mount with -o metadata is fragile. Windows antivirus locking files, Unicode normalization differences (NFD vs NFC in filenames), and case-sensitivity mismatches (Windows is case-preserving, Linux is case-sensitive) will corrupt your git index over time. You'll see "modified" files in git status that you haven't touched, caused by line-ending or permission-bit changes (644 vs 755).

Mitigation: Enforce a .gitattributes with * text=auto eol=lf and *.txt text. Store a git config core.filemode false in the repo's local config. Never run git gc on the USB bare repo from WSL; always from native Linux or Windows Git.

```bash
# Create .gitattributes
echo "* text=auto eol=lf" >> .gitattributes
echo "*.txt text" >> .gitattributes

# Set core.filemode for this repo
git config core.filemode false

# Commit
git add .gitattributes
git commit -m "add gitattributes for WSL compatibility"
```
