from scripts.check_secrets import findings


def test_scanner_detects_common_credentials_without_values():
    value = ('gh' + 'p_' + 'a'*40).encode()
    assert findings(value) == ['github-token']
    assert findings(b'-----BEGIN ' + b'PRIVATE KEY-----\nbytes') == ['private-key-block']
    assert findings(b'SQLite format 3\x00data') == ['sqlite-database']
    assert findings(b'ordinary documentation') == []
