# =============================================================================
# Laboratorio IV - Actividad 3.2
# API REST Serverless desplegada en Vercel
# Autores: Ignacio Zambrano | Luisa
# Curso: Computación Paralela y Distribuida en la Nube
# PUCE - Carrera de Ciencia de Datos
# =============================================================================
# Este archivo se ubica en api/tareas.py del repositorio.
# Vercel lo detecta automáticamente como función serverless.
# =============================================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
import uuid
from mangum import Mangum   # Adaptador ASGI → AWS Lambda / Vercel

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="TaskFlow API — Serverless (Vercel)",
    description="API de gestión de tareas desplegada como función serverless. "
                "Autores: Ignacio Zambrano y Luisa. PUCE - Lab IV.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Modelos ───────────────────────────────────────────────────────────────────
class TareaCreate(BaseModel):
    titulo: str      = Field(..., min_length=1, max_length=120)
    descripcion: str = Field(..., min_length=1, max_length=500)
    prioridad: Optional[str] = "media"
    etiquetas: Optional[List[str]] = []

    @validator("prioridad")
    def prioridad_valida(cls, v):
        if v not in {"baja", "media", "alta"}:
            raise ValueError("Prioridad debe ser: baja, media o alta")
        return v

class TareaUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    completada: Optional[bool] = None
    prioridad: Optional[str] = None
    etiquetas: Optional[List[str]] = None

class Tarea(BaseModel):
    id: str
    titulo: str
    descripcion: str
    prioridad: str
    etiquetas: List[str]
    completada: bool
    creada_en: str
    actualizada_en: str

# ── "Base de datos" en memoria ────────────────────────────────────────────────
# Nota: en Serverless la memoria se reinicia por invocación.
# Para persistencia real se usaría Vercel KV, Supabase o PlanetScale.
_db: dict[str, dict] = {}

def _ts(): return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/")
def raiz():
    return {
        "api": "TaskFlow Serverless",
        "autores": ["Ignacio Zambrano", "Luisa"],
        "version": "1.0.0",
        "nota": "Función serverless — memoria efímera entre invocaciones frías.",
    }

@app.get("/tareas", response_model=List[Tarea])
def listar_tareas(
    completada: Optional[bool] = None,
    prioridad: Optional[str] = None,
):
    resultado = list(_db.values())
    if completada is not None:
        resultado = [t for t in resultado if t["completada"] == completada]
    if prioridad:
        resultado = [t for t in resultado if t["prioridad"] == prioridad]
    return resultado

@app.post("/tareas", response_model=Tarea, status_code=201)
def crear_tarea(tarea: TareaCreate):
    ahora = _ts()
    nueva = {
        "id": str(uuid.uuid4()),
        "titulo": tarea.titulo,
        "descripcion": tarea.descripcion,
        "prioridad": tarea.prioridad,
        "etiquetas": tarea.etiquetas,
        "completada": False,
        "creada_en": ahora,
        "actualizada_en": ahora,
    }
    _db[nueva["id"]] = nueva
    return nueva

@app.get("/tareas/{tarea_id}", response_model=Tarea)
def obtener_tarea(tarea_id: str):
    if tarea_id not in _db:
        raise HTTPException(404, detail="Tarea no encontrada")
    return _db[tarea_id]

@app.put("/tareas/{tarea_id}", response_model=Tarea)
def actualizar_tarea(tarea_id: str, cambios: TareaUpdate):
    if tarea_id not in _db:
        raise HTTPException(404, detail="Tarea no encontrada")
    t = _db[tarea_id]
    for campo, valor in cambios.dict(exclude_unset=True).items():
        t[campo] = valor
    t["actualizada_en"] = _ts()
    return t

@app.delete("/tareas/{tarea_id}")
def eliminar_tarea(tarea_id: str):
    if tarea_id not in _db:
        raise HTTPException(404, detail="Tarea no encontrada")
    eliminada = _db.pop(tarea_id)
    return {"mensaje": "Tarea eliminada exitosamente", "tarea": eliminada}

@app.get("/tareas/estadisticas/resumen")
def estadisticas():
    todas = list(_db.values())
    total = len(todas)
    completadas = sum(1 for t in todas if t["completada"])
    return {
        "total": total,
        "completadas": completadas,
        "pendientes": total - completadas,
        "porcentaje_completado": round(completadas / total * 100, 1) if total else 0,
        "por_prioridad": {
            "baja":  sum(1 for t in todas if t["prioridad"] == "baja"),
            "media": sum(1 for t in todas if t["prioridad"] == "media"),
            "alta":  sum(1 for t in todas if t["prioridad"] == "alta"),
        }
    }

# ── Handler para Vercel ───────────────────────────────────────────────────────
handler = Mangum(app)
