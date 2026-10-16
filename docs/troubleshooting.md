# Troubleshooting 2.1

- Missing archive: `ls -lh /mnt/export`; iOS often appends `.tar`. Use BusyBox
  gzip/tar and the exact filename. Do not continue after failed extraction.
- Unknown command: check `ish --version`, `command -v ish`, export
  `$HOME/.local/bin` into PATH, run `hash -r`, and reinstall from the new folder.
- EPERM during competing flock: the iSH compatibility fix is included. A failed
  first lock acquisition is still a failure. Never delete lock files to force entry.
- Self-test fails: stop live mutations and preserve output. Full self-test uses
  temporary HOME; live data is not used. Storage semantics still depend on iSH.
- Wrong crypt password: this is separate from the vault password. The matching
  id.key must also be present. Protect-key changes its encoding, not key identity.
- Import rejected: use a bundle created by backup export, not a source archive
  or a manually compressed directory. Symlinks, extra members, duplicates,
  checksum mismatch and unknown manifests are refused. Duplicate IDs are refused.
- Disk full: encrypted backup workflows use multiple private copies. Free space
  needs can be several times the source size. Failed operations should not be
  treated as successful snapshots. Hard termination can leave hidden staging.
- Recovery interrupted: the current vault has either its old transaction or the
  restored transaction. Verify with the relevant old/snapshot password. A retained
  verified old vault is stored under ~/.ish-toolkit/recovery/before-... when an
  existing active vault was replaced. Do not delete SQLite journals manually.
- Large CRYPTv1 file: the compatibility reader is bounded at 32 MiB. Keep its raw
  key and old client until a separate conversion is planned; do not protect that
  key first if you still need an old client. New CRYPTv2 uses streaming instead.
- Protected key changed then command failed during fsync: inspect key-status and
  try the new key password; atomic replacement may already have completed.
- Lost password/key: no recovery bypass. A crypt key password cannot substitute
  for a vault password, and a vault password cannot recreate a lost crypt key.

The booklet contains complete recovery drills and expected outputs.
