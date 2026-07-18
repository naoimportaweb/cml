#!/usr/bin/env python3
"""Transporte HTTP do rolhama contra o webapi (PHP+MySQL).

Substitui a API /v1 do bddphp. Duas pontas:
- WorkerClient  — o worker (llm/) fala com K_worker: /work/next, /job/{id}/request,
                  PUT /job/{id}/response, POST /job/{id}/error, /haswork.
- ClientAPI     — um cliente de app fala com K_auth[canal]: POST /canal/{n}/job,
                  GET /job/{id}, GET /job/{id}/response, DELETE /job/{id}.

A confidencialidade do payload continua ponta a ponta (ChaCha20-Poly1305 do bdd.py);
este módulo só cuida do transporte e do MAC de autenticação. O MAC bate byte a byte
com webapi/lib.php (mesmo canonical, mesma derivação de chave).
"""
from __future__ import annotations

import hashlib
import hmac
import http.client
import json
import os
import time
import urllib.parse


# ------------------------------------------------------------- derivação de chave
def base_secret(bdd_key: str) -> bytes:
    """base = SHA-256(ROLHAMA_BDD_KEY) — raiz das chaves de autenticação."""
    return hashlib.sha256(bdd_key.encode()).digest()


def k_auth(bdd_key: str, canal: int) -> bytes:
    """K_auth[canal] = HMAC(base, "auth|<canal>"). Igual a webapi/lib.php k_auth()."""
    return hmac.new(base_secret(bdd_key), f"auth|{canal}".encode(), hashlib.sha256).digest()


def k_worker(bdd_key: str, worker_key: str | None = None) -> bytes:
    """K_worker = HMAC(base_w, "worker"); base_w = sha256(worker_key) ou base. Igual ao PHP."""
    base_w = hashlib.sha256(worker_key.encode()).digest() if worker_key else base_secret(bdd_key)
    return hmac.new(base_w, b"worker", hashlib.sha256).digest()


# ------------------------------------------------------------- assinatura (MAC)
def sign_headers(key: bytes, method: str, route: str, body: bytes) -> dict:
    """Cabeçalhos X-Rolhama-* para a rota app-relativa `route` (sem subdir, sem query)."""
    ts = str(int(time.time()))
    nonce = os.urandom(16).hex()
    body_hash = hashlib.sha256(body).hexdigest()
    canon = f"{method}\n{route}\n{ts}\n{nonce}\n{body_hash}"
    mac = hmac.new(key, canon.encode(), hashlib.sha256).hexdigest()
    return {"X-Rolhama-MAC": mac, "X-Rolhama-Nonce": nonce, "X-Rolhama-Ts": ts}


# ------------------------------------------------------------------- transporte
class _Http:
    def __init__(self, base_url: str):
        u = urllib.parse.urlparse(base_url)
        self.scheme = u.scheme or "https"
        self.host = u.hostname
        self.port = u.port
        self.base_path = u.path.rstrip("/")   # subdir do deploy (ex.: "/rolhama"); NÃO entra no MAC

    def _conn(self, timeout: int):
        if self.scheme == "https":
            return http.client.HTTPSConnection(self.host, self.port, timeout=timeout)
        return http.client.HTTPConnection(self.host, self.port, timeout=timeout)

    def _do(self, key: bytes | None, method: str, route: str, body: bytes = b"",
            timeout: int = 30, query: str = "") -> tuple[int, bytes]:
        # `route` é o que entra no MAC; `query` (ex.: "?type=LLM") vai só na URL.
        conn = self._conn(timeout)
        try:
            headers = {}
            if key is not None:
                headers.update(sign_headers(key, method, route, body))
            if body:
                headers["content-type"] = "application/octet-stream"
            conn.request(method, self.base_path + route + query, body=body or None, headers=headers)
            resp = conn.getresponse()
            return resp.status, resp.read()
        finally:
            conn.close()


# ------------------------------------------------------------------- worker
class WorkerClient(_Http):
    def __init__(self, base_url: str, worker_key: bytes):
        super().__init__(base_url)
        self.key = worker_key

    def haswork(self) -> bool:
        _, data = self._do(None, "GET", "/haswork")
        return data.strip() == b"1"

    def work_next(self, type: str | None = None) -> dict | None:
        """Reivindica o próximo job (opcionalmente só de um mecanismo via `type`).

        Devolve {canal, job, request, type, modelo} ou None (204/erro).
        """
        q = f"?type={type}" if type else ""
        status, data = self._do(self.key, "GET", "/work/next", query=q)
        if status == 200:
            return json.loads(data)
        return None   # 204 = nada pendente

    def get_request(self, job: str) -> bytes:
        status, data = self._do(self.key, "GET", f"/job/{job}/request")
        if status != 200:
            raise RuntimeError(f"GET request {job} → {status}")
        return data

    def put_response(self, job: str, blob: bytes) -> int:
        status, _ = self._do(self.key, "PUT", f"/job/{job}/response", body=blob)
        return status   # 201 ok · 409 job não-ativo

    def post_error(self, job: str, blob: bytes) -> int:
        status, _ = self._do(self.key, "POST", f"/job/{job}/error", body=blob)
        return status


# ------------------------------------------------------------------- cliente app
class ClientAPI(_Http):
    def __init__(self, base_url: str, canal: int, auth_key: bytes):
        super().__init__(base_url)
        self.canal = canal
        self.key = auth_key

    def enqueue(self, blob: bytes) -> str:
        """POST /canal/{n}/job → devolve o UUID do job."""
        status, data = self._do(self.key, "POST", f"/canal/{self.canal}/job", body=blob)
        if status != 201:
            raise RuntimeError(f"POST job → {status}: {data.decode(errors='replace')[:200]}")
        return json.loads(data)["job"]

    def status(self, job: str) -> dict | None:
        status, data = self._do(self.key, "GET", f"/job/{job}")
        return json.loads(data) if status == 200 else None

    def response(self, job: str, wait: int = 30) -> bytes | None:
        route = f"/job/{job}/response" + (f"?wait={int(wait)}" if wait else "")
        # a query NÃO entra no MAC — assina só o path.
        sign_route = f"/job/{job}/response"
        headers = sign_headers(self.key, "GET", sign_route, b"")
        conn = self._conn(wait + 10 if wait else 30)
        try:
            conn.request("GET", self.base_path + route, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            return data if resp.status == 200 else None
        finally:
            conn.close()

    def delete(self, job: str) -> bool:
        status, _ = self._do(self.key, "DELETE", f"/job/{job}")
        return status == 204
