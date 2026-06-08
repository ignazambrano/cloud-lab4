# =============================================================================
# Laboratorio IV - Actividad 3.2
# API REST Serverless — Handler nativo de Vercel (sin FastAPI)
# Autores: Ignacio Zambrano | Luisa Guerrero
# Curso: Computación Paralela y Distribuida en la Nube
# PUCE - Carrera de Ciencia de Datos

# =============================================================================

import json
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ── "Base de datos" en memoria ────────────────────────────────────────────────
# En serverless la memoria es efímera entre cold starts.
_db: dict = {}

def _ts():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _json(data, status=200):
    return status, json.dumps(data, ensure_ascii=False)

def _cors_headers():
    return {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

# ══════════════════════════════════════════════════════════════════════════════
#  LÓGICA DE NEGOCIO
# ══════════════════════════════════════════════════════════════════════════════

def listar_tareas(query: dict) -> tuple:
    resultado = list(_db.values())

    completada = query.get("completada", [None])[0]
    if completada == "true":
        resultado = [t for t in resultado if t["completada"]]
    elif completada == "false":
        resultado = [t for t in resultado if not t["completada"]]

    prioridad = query.get("prioridad", [None])[0]
    if prioridad in ("baja", "media", "alta"):
        resultado = [t for t in resultado if t["prioridad"] == prioridad]

    buscar = query.get("buscar", [None])[0]
    if buscar:
        q = buscar.lower()
        resultado = [
            t for t in resultado
            if q in t["titulo"].lower() or q in t["descripcion"].lower()
        ]

    return _json(resultado)


def obtener_tarea(tarea_id: str) -> tuple:
    if tarea_id not in _db:
        return _json({"detail": f"Tarea '{tarea_id}' no encontrada"}, 404)
    return _json(_db[tarea_id])


def crear_tarea(body: dict) -> tuple:
    titulo = (body.get("titulo") or "").strip()
    descripcion = (body.get("descripcion") or "").strip()
    prioridad = body.get("prioridad", "media")
    etiquetas = body.get("etiquetas", [])

    if not titulo or not descripcion:
        return _json({"detail": "titulo y descripcion son obligatorios"}, 422)
    if prioridad not in ("baja", "media", "alta"):
        return _json({"detail": "prioridad debe ser: baja, media o alta"}, 422)

    ahora = _ts()
    nueva = {
        "id":             str(uuid.uuid4()),
        "titulo":         titulo,
        "descripcion":    descripcion,
        "prioridad":      prioridad,
        "etiquetas":      etiquetas if isinstance(etiquetas, list) else [],
        "completada":     False,
        "creada_en":      ahora,
        "actualizada_en": ahora,
    }
    _db[nueva["id"]] = nueva
    return _json(nueva, 201)


def actualizar_tarea(tarea_id: str, body: dict) -> tuple:
    if tarea_id not in _db:
        return _json({"detail": f"Tarea '{tarea_id}' no encontrada"}, 404)

    t = _db[tarea_id]
    campos = ("titulo", "descripcion", "prioridad", "etiquetas", "completada")
    for campo in campos:
        if campo in body:
            t[campo] = body[campo]
    t["actualizada_en"] = _ts()
    return _json(t)


def eliminar_tarea(tarea_id: str) -> tuple:
    if tarea_id not in _db:
        return _json({"detail": f"Tarea '{tarea_id}' no encontrada"}, 404)
    eliminada = _db.pop(tarea_id)
    return _json({"mensaje": "Tarea eliminada exitosamente", "tarea": eliminada})


def estadisticas() -> tuple:
    todas = list(_db.values())
    total = len(todas)
    completadas = sum(1 for t in todas if t["completada"])
    return _json({
        "total":                 total,
        "completadas":           completadas,
        "pendientes":            total - completadas,
        "porcentaje_completado": round(completadas / total * 100, 1) if total else 0,
        "por_prioridad": {
            "baja":  sum(1 for t in todas if t["prioridad"] == "baja"),
            "media": sum(1 for t in todas if t["prioridad"] == "media"),
            "alta":  sum(1 for t in todas if t["prioridad"] == "alta"),
        },
    })


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTER — mapea método + path a la función correcta
# ══════════════════════════════════════════════════════════════════════════════

def _route(method: str, path: str, query: dict, body: dict) -> tuple:
    # Normalizar path
    p = path.rstrip("/")

    # GET /api  o  GET /api/tareas
    if method == "GET" and p in ("/api", "/api/tareas", ""):
        return listar_tareas(query)

    # GET /api/tareas/estadisticas/resumen
    if method == "GET" and p == "/api/tareas/estadisticas/resumen":
        return estadisticas()

    # GET /api/tareas/{id}
    if method == "GET" and p.startswith("/api/tareas/"):
        tarea_id = p.split("/api/tareas/")[1]
        return obtener_tarea(tarea_id)

    # POST /api/tareas
    if method == "POST" and p in ("/api/tareas", ""):
        return crear_tarea(body)

    # PUT /api/tareas/{id}
    if method == "PUT" and p.startswith("/api/tareas/"):
        tarea_id = p.split("/api/tareas/")[1]
        return actualizar_tarea(tarea_id, body)

    # DELETE /api/tareas/{id}
    if method == "DELETE" and p.startswith("/api/tareas/"):
        tarea_id = p.split("/api/tareas/")[1]
        return eliminar_tarea(tarea_id)

    # Raíz informativa
    if method == "GET":
        return _json({
            "api":     "TaskFlow Serverless",
            "autores": ["Ignacio Zambrano", "Luisa Guerrero"],
            "version": "1.0.0",
            "endpoints": [
                "GET    /api/tareas",
                "POST   /api/tareas",
                "GET    /api/tareas/{id}",
                "PUT    /api/tareas/{id}",
                "DELETE /api/tareas/{id}",
                "GET    /api/tareas/estadisticas/resumen",
            ],
        })

    return _json({"detail": "Endpoint no encontrado"}, 404)


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER DE VERCEL
# ══════════════════════════════════════════════════════════════════════════════

class handler(BaseHTTPRequestHandler):

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except Exception:
            return {}

    def _send(self, status: int, body: str):
        self.send_response(status)
        for k, v in _cors_headers().items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_OPTIONS(self):
        self._send(204, "")

    def _handle(self):
        parsed = urlparse(self.path)
        query  = parse_qs(parsed.query)
        body   = self._read_body()
        status, response = _route(self.command, parsed.path, query, body)
        self._send(status, response)

    def do_GET(self):    self._handle()
    def do_POST(self):   self._handle()
    def do_PUT(self):    self._handle()
    def do_DELETE(self): self._handle()

    # Silenciar logs internos de BaseHTTPRequestHandler
    def log_message(self, format, *args): pass
