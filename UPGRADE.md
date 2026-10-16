# Upgrade from the working v2 installation to 2.1

Your existing v2 vault is compatible. Do not run vault init or vault migrate
again. Installation changes launchers, not stored data.

1. Save `ish-toolkit-v2.1.tar.gz` into the iOS Files folder mounted at
   `/mnt/export`. Run `ls -lh /mnt/export` and use the exact filename; iOS may
   append `.tar`.
2. Extract using BusyBox, as confirmed working on your device:

```sh
cd ~
busybox gzip -dc /mnt/export/ish-toolkit-v2.1.tar.gz | busybox tar -xvf -
cd ~/ish-toolkit-v2.1
sh install.sh
export PATH="$HOME/.local/bin:$PATH"
hash -r
ish --version
ish selftest --full
```

Expected version: `ish-toolkit 2.1.0-local`. If the file ends in `.tar.gz.tar`,
append `.tar` in the extraction command. If extraction or installation fails,
stop; later commands may still invoke the old version.

3. After the full self-test passes:

```sh
ish vault verify
ish db doctor
```

4. Optional key protection (only after you have a crypt key):

```sh
ish crypt key-status
ish crypt protect-key
```

If there is no key yet, first run `ish crypt keygen`. Protect-key preserves the
key identity, replaces the file atomically, and does not retain an unencrypted
copy. Back up the resulting protected `~/.crypt/id.key` and keep its password
separately. Old copies of the raw key are still able to decrypt older and newer
ciphertext addressed to that identity; protection does not revoke those copies.
Old crypt clients cannot read the protected key or CRYPTv2 files.

5. Create a portable vault backup:

```sh
ish backup create vault --encrypt
ish backup list
```

Use the actual returned ID in place of BACKUP_ID:

```sh
ish backup verify BACKUP_ID
ish backup export BACKUP_ID --to /mnt/export/vault-backup.ishbackup
```

Choose a new destination filename for each export. Export does not add
another encryption layer. The snapshot must already be encrypted if that is
required. Never put passwords or TOTP seeds into shell arguments.

## Restoring versus activating

`ish backup restore ID --to ~/recovered-vault` creates a separate inspected copy.
`ish backup recover-vault ID --preview` displays a plan only.
`ish backup recover-vault ID` asks you to type RECOVER, requests the snapshot
password and current active vault password, and replaces the active contents
transactionally after retaining a verified old vault under
`~/.ish-toolkit/recovery/before-...`. It does not merge entries. The snapshot
password becomes the active password. Stop all old clients before activation.

On a fresh installation, import the exported `.ishbackup` file first:

```sh
ish backup import /mnt/export/vault-backup.ishbackup
```

Encrypted imports require the matching crypt private key (and its password if
protected), plus the snapshot vault password. A duplicate ID is refused without
changing the existing entry. Vault recovery refuses retained legacy-format
files; preserve or migrate those before attempting activation.

See BOOKLET.md / the PDF for detailed workflows, validation and troubleshooting.
