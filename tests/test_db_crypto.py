import pytest
from lib.db_crypto import Credential, CredentialStore, CredentialError


def test_credential_password_hidden_in_repr():
    assert 'sensitive-value' not in repr(Credential('user', 'sensitive-value'))


def test_unconfigured_adapter_fails_closed():
    store = CredentialStore()
    with pytest.raises(CredentialError):
        store.get('profile')
    with pytest.raises(CredentialError):
        store.put('profile', Credential('user', 'secret'))
