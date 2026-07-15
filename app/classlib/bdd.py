#!/usr/bin/env python3
"""Cliente Blind Dead Drop (bddphp) — protocolo reimplementado em stdlib.

HKDF-SHA256 (RFC 5869, salt zero) e ChaCha20-Poly1305 AEAD (RFC 8439, AAD vazio),
mais o transporte HTTP /v1. O contrato é byte a byte com o servidor bddphp e os
clientes de referência. Educacional: não é constant-time nem auditado.

Rode `python3 bdd.py` para autoverificar contra os vetores da spec/RFC.
"""
from __future__ import annotations

import hashlib
import hmac
import http.client
import os
import struct
import urllib.parse

MAX_WAIT = 60          # o servidor limita o long-poll a 60 s
MAX_BLOB = 1048576     # 1 MiB


# ----------------------------------------------------------------- HKDF
def hkdf(ikm: bytes, info: bytes, length: int) -> bytes:
    """HKDF-SHA256 com o salt zero da RFC 5869 §2.2, igual ao servidor."""
    salt = b"\x00" * 32
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    okm, t, counter = b"", b"", 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
        counter += 1
    return okm[:length]


# ------------------------------------------------------------- ChaCha20
def _rotl(v: int, c: int) -> int:
    v &= 0xFFFFFFFF
    return ((v << c) | (v >> (32 - c))) & 0xFFFFFFFF


def _quarter(s: list, a: int, b: int, c: int, d: int) -> None:
    s[a] = (s[a] + s[b]) & 0xFFFFFFFF; s[d] = _rotl(s[d] ^ s[a], 16)
    s[c] = (s[c] + s[d]) & 0xFFFFFFFF; s[b] = _rotl(s[b] ^ s[c], 12)
    s[a] = (s[a] + s[b]) & 0xFFFFFFFF; s[d] = _rotl(s[d] ^ s[a], 8)
    s[c] = (s[c] + s[d]) & 0xFFFFFFFF; s[b] = _rotl(s[b] ^ s[c], 7)


def _chacha_block(key: bytes, counter: int, nonce: bytes) -> bytes:
    s = [0x61707865, 0x3320646E, 0x79622D32, 0x6B206574]
    s += list(struct.unpack("<8I", key))
    s.append(counter & 0xFFFFFFFF)
    s += list(struct.unpack("<3I", nonce))
    w = list(s)
    for _ in range(10):
        _quarter(w, 0, 4, 8, 12); _quarter(w, 1, 5, 9, 13)
        _quarter(w, 2, 6, 10, 14); _quarter(w, 3, 7, 11, 15)
        _quarter(w, 0, 5, 10, 15); _quarter(w, 1, 6, 11, 12)
        _quarter(w, 2, 7, 8, 13); _quarter(w, 3, 4, 9, 14)
    return struct.pack("<16I", *[(w[i] + s[i]) & 0xFFFFFFFF for i in range(16)])


def chacha20_xor(key: bytes, counter: int, nonce: bytes, data: bytes) -> bytes:
    out, off = bytearray(), 0
    while off < len(data):
        ks = _chacha_block(key, counter, nonce)
        counter += 1
        out += bytes(b ^ ks[i] for i, b in enumerate(data[off:off + 64]))
        off += 64
    return bytes(out)


# ------------------------------------------------------------- Poly1305
def poly1305(msg: bytes, key: bytes) -> bytes:
    r = int.from_bytes(key[:16], "little") & 0x0FFFFFFC0FFFFFFC0FFFFFFC0FFFFFFF
    s = int.from_bytes(key[16:32], "little")
    p = (1 << 130) - 5
    acc = 0
    for i in range(0, len(msg), 16):
        n = int.from_bytes(msg[i:i + 16] + b"\x01", "little")
        acc = ((acc + n) * r) % p
    return ((acc + s) & ((1 << 128) - 1)).to_bytes(16, "little")


# ----------------------------------------------- ChaCha20-Poly1305 AEAD
def _mac_data(ciphertext: bytes) -> bytes:
    pad = b"\x00" * ((16 - len(ciphertext) % 16) % 16)  # AAD vazio
    return ciphertext + pad + struct.pack("<QQ", 0, len(ciphertext))


def aead_seal(key: bytes, nonce: bytes, plaintext: bytes) -> bytes:
    ct = chacha20_xor(key, 1, nonce, plaintext)
    otk = _chacha_block(key, 0, nonce)[:32]
    return nonce + poly1305(_mac_data(ct), otk) + ct  # nonce(12)‖tag(16)‖ct


def aead_open(key: bytes, blob: bytes) -> bytes:
    if len(blob) < 28:
        raise ValueError("blob curto demais")
    nonce, tag, ct = blob[:12], blob[12:28], blob[28:]
    otk = _chacha_block(key, 0, nonce)[:32]
    if not hmac.compare_digest(poly1305(_mac_data(ct), otk), tag):
        raise ValueError("falha de autenticação (mensagem adulterada ou segredo errado)")
    return chacha20_xor(key, 1, nonce, ct)


# ------------------------------------------------------------- protocolo
def _info(kind: str, part: str, channel: int) -> bytes:
    return f"bdd-{kind}|{part}|{channel}".encode()


def slot_address(secret: bytes, part: str, channel: int) -> str:
    return hkdf(secret, _info("addr", part, channel), 32).hex()


def message_key(secret: bytes, part: str, channel: int) -> bytes:
    return hkdf(secret, _info("key", part, channel), 32)


def seal(secret: bytes, part: str, channel: int, plaintext: bytes) -> bytes:
    return aead_seal(message_key(secret, part, channel), os.urandom(12), plaintext)


def open_blob(secret: bytes, part: str, channel: int, blob: bytes) -> bytes:
    return aead_open(message_key(secret, part, channel), blob)


# ------------------------------------------------------------- transporte
class Client:
    """Fala a API /v1 do bddphp. base_url ex.: https://host (sem /v1)."""

    def __init__(self, base_url: str, secret: bytes):
        if len(secret) != 32:
            raise ValueError("o segredo deve ter 32 bytes")
        u = urllib.parse.urlparse(base_url)
        self.scheme = u.scheme or "https"
        self.host = u.hostname
        self.port = u.port
        # prefixo quando o servidor está sob subdiretório (ex.: "/bddphp"); "" na raiz
        self.base_path = u.path.rstrip("/")
        self.secret = secret

    def _conn(self, timeout: int):
        if self.scheme == "https":
            return http.client.HTTPSConnection(self.host, self.port, timeout=timeout)
        return http.client.HTTPConnection(self.host, self.port, timeout=timeout)

    def _request(self, method: str, path: str, body=None, timeout=30):
        conn = self._conn(timeout)
        try:
            headers = {"content-type": "application/octet-stream"} if body else {}
            conn.request(method, self.base_path + path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            return resp.status, data
        finally:
            conn.close()

    def health(self) -> dict:
        import json
        _, data = self._request("GET", "/v1/health")
        return json.loads(data)

    def send(self, part: str, channel: int, plaintext: bytes, ttl: int | None = None) -> int:
        blob = seal(self.secret, part, channel, plaintext)
        if not (1 <= len(blob) <= MAX_BLOB):
            raise ValueError(f"blob fora de 1..1MiB ({len(blob)} bytes)")
        addr = slot_address(self.secret, part, channel)
        path = f"/v1/slot/{addr}"
        if ttl is not None:
            path += f"?ttl={int(ttl)}"
        status, _ = self._request("PUT", path, body=blob)
        return status  # 201 criado · 409 ocupado · 413 tamanho

    def receive(self, part: str, channel: int, wait: int = 0) -> bytes | None:
        addr = slot_address(self.secret, part, channel)
        path = f"/v1/slot/{addr}"
        timeout = 30
        if wait > 0:
            w = min(int(wait), MAX_WAIT)
            path += f"?wait={w}"
            timeout = w + 10
        status, data = self._request("GET", path, timeout=timeout)
        if status != 200:
            return None
        return open_blob(self.secret, part, channel, data)

    def remove(self, part: str, channel: int) -> bool:
        addr = slot_address(self.secret, part, channel)
        status, _ = self._request("DELETE", f"/v1/slot/{addr}")
        return status == 204


# ------------------------------------------------------------- autoteste
def _selftest() -> int:
    fails = 0

    def check(name, got, want):
        nonlocal fails
        ok = got == want
        print(f"{'ok   ' if ok else 'FAIL '} {name}")
        if not ok:
            print(f"        got  {got}\n        want {want}")
            fails += 1

    # HKDF RFC 5869 caso 3 (salt zero, info vazio, L=42)
    check("hkdf rfc5869#3", hkdf(b"\x0b" * 22, b"", 42).hex(),
          "8da4e775a563c18f715f802a063c5a31b8a11f5c5ee1879ec3454e5f3c738d2d"
          "9d201395faa4b61a96c8")
    # Vetor de referência da spec: addr(request, 0)
    secret = bytes.fromhex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")
    check("spec addr request/0", slot_address(secret, "request", 0),
          "59050b4ec15597c9f30cb39a5ddab76b17de9fb50120cba7e67b904579d98ffe")
    # Ciphertext AEAD RFC 8439 2.8.2 (keystream independe do AAD), 16 primeiros bytes
    akey = bytes.fromhex("808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f")
    anonce = bytes.fromhex("070000004041424344454647")
    pt = (b"Ladies and Gentlemen of the class of '99: If I could offer you "
          b"only one tip for the future, sunscreen would be it.")
    check("aead ct rfc8439 2.8.2", aead_seal(akey, anonce, pt)[28:44].hex(),
          "d31a8d34648e60db7b86afbc53ef7ec2")
    # Round-trip + detecção de adulteração
    k, n = b"\x07" * 32, b"\x09" * 12
    b = aead_seal(k, n, b"deadbeef payload")
    check("aead roundtrip", aead_open(k, b).decode(), "deadbeef payload")
    tampered = bytearray(b); tampered[28] ^= 1
    threw = False
    try:
        aead_open(k, bytes(tampered))
    except Exception:
        threw = True
    check("aead tamper detected", threw, True)

    print("\ntodos os vetores passam" if not fails else f"\n{fails} FALHA(S)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
