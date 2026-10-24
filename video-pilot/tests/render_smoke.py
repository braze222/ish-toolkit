"""Real FFmpeg smoke check; uses temporary synthetic test media, no network."""
from pathlib import Path
import struct
import sys
import tempfile
import wave
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import elmatrix_video as video


def chunk(kind, data):
    return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        image = root / 'cover.png'
        image.write_bytes(b'\x89PNG\r\n\x1a\n' +
            chunk(b'IHDR', struct.pack('!2I5B', 64, 64, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress((b'\0' + b'\x20\x60\x80' * 64) * 64)) +
            chunk(b'IEND', b''))
        audio = root / 'audio.wav'
        with wave.open(str(audio), 'wb') as out:
            out.setnchannels(1); out.setsampwidth(2); out.setframerate(16000)
            out.writeframes(b'\0\0' * 32000)
        project = root / 'project'
        video.init(project)
        video.render(project, image, audio)
        info = video.probe(project / 'video.mp4')
        stream = next(s for s in info['streams'] if s['codec_type'] == 'video')
        assert (stream['width'], stream['height']) == (720, 1280)
        assert 1.9 <= float(info['format']['duration']) <= 2.2
        original = video.digest(project / 'video.mp4')
        try: video.render(project, image, audio)
        except video.VideoError: pass
        else: raise AssertionError('Existing render was overwritten')
        assert video.digest(project / 'video.mp4') == original
    print('PASS: real MP4 render, dimensions, duration and no-overwrite check')


if __name__ == '__main__': main()
