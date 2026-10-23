import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock
from http.client import HTTPConnection
from http.server import HTTPServer
from elmatrix import evidence, transport
from elmatrix.cli import main
from elmatrix.engine import match_opportunities
from elmatrix.server import Handler

class AuditTests(unittest.TestCase):
    def test_init_isolated_repeat(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {'ELMATRIX_HOME':td}):
            self.assertEqual(main(['init']),0)
            self.assertEqual(main(['init']),0)
            self.assertTrue((Path(td)/'elmatrix.sqlite3').is_file())
    def test_atom_date(self):
        self.assertEqual(evidence._parse_date('2026-10-22T12:00:00Z'),'2026-10-22T12:00:00+00:00')
    def test_dtd_refused(self):
        for data in (b'<!DOCTYPE rss [<!ENTITY x "hello">]><rss/>', '<rss/>'.encode('utf-16')):
            with self.assertRaises(ValueError): evidence.parse_rss(data,'https://example.com/rss')
    def test_url_ipv6_and_control(self):
        self.assertEqual(evidence.canonicalize_url('https://[2606:4700:4700::1111]/'),'https://[2606:4700:4700::1111]/')
        for value in ('https://example.com/\nx','https://user:pass@example.com','https://[fe80::1%25eth0]/'):
            with self.assertRaises(ValueError): evidence.canonicalize_url(value)
    def test_region_case_and_invalid_profile(self):
        a=match_opportunities(region='ZA');b=match_opportunities(region='za')
        self.assertEqual(a,b)
        self.assertEqual(next(x for x in a if x['id']=='service-cleaning-leads')['score_factors']['region_fit'],5)
        with self.assertRaises(ValueError): match_opportunities(hours=-1)
    def test_database_symlink_hardlink_and_permissions(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'db'; db=evidence.open_db(p);db.close()
            self.assertEqual(p.stat().st_mode & 0o777,0o600)
            link=Path(td)/'sym';link.symlink_to(p)
            with self.assertRaises((OSError,ValueError)): evidence.open_db(link)
            os.link(p,Path(td)/'hard')
            with self.assertRaises(ValueError): evidence.open_db(p)
    def test_future_schema_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'db';db=evidence.open_db(p);db.execute('UPDATE schema_meta SET version=99');db.commit();db.close()
            before=p.read_bytes()
            with self.assertRaises(ValueError): evidence.open_db(p)
            self.assertEqual(before,p.read_bytes())
    def test_mixed_dns_refused(self):
        answers=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443)),(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))]
        with patch('socket.getaddrinfo',return_value=answers),self.assertRaises(ValueError): transport.public_addresses('example.com',443)
    def test_pinned_connect_preserves_tls_hostname(self):
        answers=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))]
        sock=MagicMock();context=MagicMock()
        with patch('socket.socket',return_value=sock),patch('ssl.create_default_context',return_value=context),patch('socket.getaddrinfo',side_effect=AssertionError('must not resolve again')):
            conn=transport.PinnedConnection('example.com',443,answers,8,True);conn.connect()
        sock.connect.assert_called_once_with(('93.184.216.34',443))
        context.wrap_socket.assert_called_once_with(sock,server_hostname='example.com')
    def test_network_error_redacted(self):
        with patch('socket.getaddrinfo',side_effect=OSError('secret-token')):
            with self.assertRaises(RuntimeError) as caught: evidence.fetch_rss('https://example.com/?key=secret-token')
        self.assertNotIn('secret-token',str(caught.exception))
    def test_private_redirect_rejected(self):
        response=MagicMock(status=302);response.getheader.return_value='http://127.0.0.1/'
        connection=MagicMock();connection.getresponse.return_value=response
        public=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',80))]
        private=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',80))]
        with patch('socket.getaddrinfo',side_effect=[public,private]),patch.object(transport,'PinnedConnection',return_value=connection) as constructor:
            with self.assertRaises(ValueError): evidence.fetch_rss('http://example.com/feed')
        self.assertEqual(constructor.call_count,1)
    def test_dashboard_host_and_origin(self):
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            for host,origin,status in [('evil.example',None,403),('127.0.0.1:'+str(server.server_port),'https://evil.example',403),('127.0.0.1:'+str(server.server_port),None,200)]:
                conn=HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                headers={'Host':host}
                if origin:headers['Origin']=origin
                conn.request('GET','/api/opportunities',headers=headers)
                response=conn.getresponse();self.assertEqual(response.status,status);response.read();conn.close()
        finally:server.shutdown();server.server_close();thread.join()
