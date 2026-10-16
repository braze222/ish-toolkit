from __future__ import annotations

from dataclasses import dataclass, field


class CredentialError(Exception):
    """Credential-management failure."""


@dataclass(frozen=True)
class Credential:
    username: str
    password: str = field(repr=False)


class CredentialStore:
    """
    Boundary between ish-db and the existing ish-toolkit vault.

    This deliberately contains no encryption implementation.
    The existing vault remains the sole credential authority.
    """

    def __init__(self, vault=None):
        self._vault = vault

    @property
    def vault(self):
        if self._vault is None:
            raise CredentialError(
                "ish-db vault adapter is not configured"
            )
        return self._vault

    def get(self, profile: str) -> Credential:
        if not profile or not profile.strip():
            raise CredentialError("Credential profile is required")

        raise CredentialError(
            "Existing ish vault adapter must be connected"
        )

    def put(self, profile: str, credential: Credential) -> None:
        if not profile or not profile.strip():
            raise CredentialError("Credential profile is required")

        if not credential.username:
            raise CredentialError("Username is required")

        if not credential.password:
            raise CredentialError("Password is required")

        raise CredentialError(
            "Existing ish vault adapter must be connected"
        )

    def delete(self, profile: str) -> None:
        if not profile or not profile.strip():
            raise CredentialError("Credential profile is required")

        raise CredentialError(
            "Existing ish vault adapter must be connected"
        )
