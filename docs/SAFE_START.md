# Learn slowly with dummy data

You do not need to promote the project or store important credentials now.
Complete one stage at a time. Stop if an output differs from the guide.

## 1. Confirm the version and test the device

```sh
ish --version
ish selftest --full
ish db doctor
```

Your confirmed earlier iPhone result was for v2.0. The 3.0 preview and intervening v2.1/2.1.1 code still need
its own device test. The self-test uses temporary dummy data. Do not run vault
init on your existing real vault. A GitHub update does not install itself.

## 2. Create a separate practice HOME

In the same terminal session, run:

```sh
umask 077
practice_home=$(mktemp -d "$HOME/ish-practice.XXXXXX")
printf 'Practice folder: %s\n' "$practice_home"
HOME="$practice_home" ish vault init
HOME="$practice_home" ish vault set demo-note
HOME="$practice_home" ish vault verify
HOME="$practice_home" ish vault get demo-note
```

Use a practice-only password and a value such as `learning with dummy data`.
The HOME prefix applies only to that command. It does not move or replace your
real vault. Keep the printed path; if you close the shell, set practice_home to
that exact directory before continuing. Never set it to your real /root HOME.

## 3. Practice keys and backups in that same folder

```sh
HOME="$practice_home" ish crypt keygen
HOME="$practice_home" ish crypt protect-key
HOME="$practice_home" ish backup create vault --encrypt
HOME="$practice_home" ish backup list
```

Use a different practice-only crypt-key password. Copy the returned backup ID,
then substitute it for BACKUP_ID:

```sh
HOME="$practice_home" ish backup verify BACKUP_ID
HOME="$practice_home" ish backup restore BACKUP_ID \
  --to "$practice_home/recovered"
HOME="$practice_home" ish vault \
  --directory "$practice_home/recovered" verify
```

The practice copies are intentionally retained. No cleanup command is supplied
that could accidentally delete live state. Continue with booklet chapters 14-18
only after you understand which copy and password each command uses.

## 4. Before important information

- Verify an off-device recovery copy and the separately backed-up protected
  crypt private key. Keep their passwords separately. Never rely on one copy.
- Keep iOS/iSH and dependencies supported and updated; do not blindly replace
  Alpine repositories or compile random cryptography packages from tutorials.
- Use unique passphrases. Keep service recovery codes independent of this vault.
- Use a device passcode, screen lock and account multifactor authentication.
- Do not paste terminal commands from strangers without understanding them.
- Do not use this early-stage toolkit as the only store for irreplaceable secrets.

## Screenshots and public help

Show only the practice environment. Never share private-key files, password
prompts with answers, TOTP seeds, real get output, personal backup bundles or
full terminal scrollback. Redact names, paths and account identifiers as needed.
Public issue reports should use dummy reproduction data. Secret reports belong
in a private channel described in SECURITY.md.

## If a credential is exposed

Stop sharing the affected material. Revoke/rotate the credential at its issuing
service, review active sessions and access logs, then replace dependent copies.
Deleting a GitHub file or post does not invalidate a credential or erase forks,
caches, screenshots or repository history. Do not post the credential again to
ask whether it is compromised. Preserve incident evidence privately.
