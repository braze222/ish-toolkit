"""Public feed transport: resolve once, pin peer, retain TLS hostname checks."""
import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urlsplit, urljoin


def public_addresses(host, port):
    answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not answers or any(not ipaddress.ip_address(a[4][0]).is_global for a in answers):
        raise ValueError('Feed destination must contain only public IP addresses.')
    return answers


class PinnedConnection(http.client.HTTPConnection):
    def __init__(self, host, port, addresses, timeout, secure):
        super().__init__(host, port, timeout=timeout)
        self.addresses = addresses
        self.secure = secure

    def connect(self):
        family, kind, protocol, _, address = self.addresses[0]
        peer = socket.socket(family, kind, protocol)
        try:
            peer.settimeout(self.timeout)
            peer.connect(address)
            if self.secure:
                peer = ssl.create_default_context().wrap_socket(peer, server_hostname=self.host)
            self.sock = peer
        except BaseException:
            peer.close()
            raise


def fetch(url, canonicalize, *, timeout, max_bytes, user_agent):
    current = canonicalize(url)
    try:
        for hop in range(6):
            parsed = urlsplit(current)
            secure = parsed.scheme == 'https'
            port = parsed.port or (443 if secure else 80)
            addresses = public_addresses(parsed.hostname, port)
            connection = PinnedConnection(parsed.hostname, port, addresses, timeout, secure)
            try:
                target = parsed.path or '/'
                if parsed.query:
                    target += '?' + parsed.query
                connection.request('GET', target, headers={'User-Agent':user_agent,'Accept':'application/rss+xml, application/atom+xml, application/xml','Accept-Encoding':'identity'})
                response = connection.getresponse()
                if response.status in (301,302,303,307,308):
                    location = response.getheader('Location')
                    if not location or hop == 5:
                        raise ValueError('Missing redirect destination or redirect limit exceeded.')
                    next_url = canonicalize(urljoin(current, location))
                    if secure and urlsplit(next_url).scheme != 'https':
                        raise ValueError('HTTPS downgrade redirect refused.')
                    current = next_url
                    continue
                if response.status != 200:
                    raise RuntimeError('Feed returned an unsuccessful HTTP status.')
                if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
                    raise ValueError('Compressed feed responses are not accepted.')
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise ValueError('Feed exceeds response byte limit.')
                return data, current
            finally:
                connection.close()
    except (OSError, http.client.HTTPException):
        raise RuntimeError('Feed network request failed; check public endpoint and connectivity.') from None
