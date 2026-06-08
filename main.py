# =============================================================================
# Laboratorio IV - Parte II, Actividad 2.1 / 2.3
# API REST con FastAPI — CRUD completo de Tareas
# Autores: Ignacio Zambrano | Luisa Guerrero
# Curso: Computación Paralela y Distribuida en la Nube
# PUCE - Carrera de Ciencia de Datos
# =============================================================================
# Instalación requerida:
#   pip install fastapi uvicorn pydantic
# Ejecución local:
#   uvicorn main:app --reload --port 8000
# Documentación automática:
#   http://127.0.0.1:8000/docs
# =============================================================================

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
import uuid

# ==================== APP ====================
app = FastAPI(
    title="API de Gestión de Tareas — Lab IV",
    description=(
        "API REST distribuida para gestión de tareas. "
        "Desarrollada por Ignacio Zambrano y Luisa Guerrero. "
        "PUCE — Computación Paralela y Distribuida en la Nube."
    ),
    version="1.0.0",
)

# CORS: permite que el frontend (cualquier origen en desarrollo) consuma la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== MODELOS ====================

class TareaBase(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=120, example="Estudiar FastAPI")
    descripcion: str = Field(..., min_length=1, max_length=500, example="Revisar documentación oficial")
    prioridad: Optional[str] = Field("media", example="alta")
    etiquetas: Optional[List[str]] = Field(default_factory=list, example=["backend", "api"])

    @validator("prioridad")
    def prioridad_valida(cls, v):
        opciones = {"baja", "media", "alta"}
        if v not in opciones:
            raise ValueError(f"Prioridad debe ser una de: {opciones}")
        return v


class TareaCreate(TareaBase):
    pass


class TareaUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=120)
    descripcion: Optional[str] = Field(None, min_length=1, max_length=500)
    completada: Optional[bool] = None
    prioridad: Optional[str] = None
    etiquetas: Optional[List[str]] = None

    @validator("prioridad")
    def prioridad_valida(cls, v):
        if v is not None and v not in {"baja", "media", "alta"}:
            raise ValueError("Prioridad debe ser: baja, media o alta")
        return v


class Tarea(TareaBase):
    id: str
    completada: bool = False
    creada_en: str
    actualizada_en: str

    class Config:
        orm_mode = True


# ==================== ALMACENAMIENTO EN MEMORIA ====================
# (Simulación de base de datos para el lab)
tareas_db: dict[str, Tarea] = {}


def _ahora() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


# ==================== ENDPOINTS ====================

@app.get("/", tags=["Info"])
def raiz():
    """Endpoint de bienvenida con información de la API."""
    return {
        "api": "Gestión de Tareas - Lab IV",
        "version": "1.0.0",
        "autores": ["Ignacio Zambrano", "Luisa"],
        "docs": "/docs",
        "endpoints": ["/tareas", "/tareas/{id}", "/tareas/estadisticas/resumen"]
    }


@app.get("/tareas", response_model=List[Tarea], tags=["Tareas"])
def listar_tareas(
    completada: Optional[bool] = Query(None, description="Filtrar por estado"),
    prioridad: Optional[str] = Query(None, description="Filtrar por prioridad: baja|media|alta"),
    buscar: Optional[str] = Query(None, description="Buscar en título o descripción"),
):
    """
    Lista todas las tareas. Admite filtros opcionales por estado,
    prioridad y búsqueda de texto libre.
    """
    resultado = list(tareas_db.values())

    if completada is not None:
        resultado = [t for t in resultado if t.completada == completada]
    if prioridad:
        resultado = [t for t in resultado if t.prioridad == prioridad]
    if buscar:
        q = buscar.lower()
        resultado = [
            t for t in resultado
            if q in t.titulo.lower() or q in t.descripcion.lower()
        ]

    return resultado


@app.post("/tareas", response_model=Tarea, status_code=201, tags=["Tareas"])
def crear_tarea(tarea: TareaCreate):
    """
    Crea una nueva tarea. Genera ID único (UUID) y timestamps automáticamente.
    """
    ahora = _ahora()
    nueva = Tarea(
        id=str(uuid.uuid4()),
        titulo=tarea.titulo,
        descripcion=tarea.descripcion,
        prioridad=tarea.prioridad,
        etiquetas=tarea.etiquetas,
        completada=False,
        creada_en=ahora,
        actualizada_en=ahora,
    )
    tareas_db[nueva.id] = nueva
    return nueva


@app.get("/tareas/{tarea_id}", response_model=Tarea, tags=["Tareas"])
def obtener_tarea(tarea_id: str):
    """Obtiene una tarea por su ID. Retorna 404 si no existe."""
    if tarea_id not in tareas_db:
        raise HTTPException(status_code=404, detail=f"Tarea '{tarea_id}' no encontrada")
    return tareas_db[tarea_id]


@app.put("/tareas/{tarea_id}", response_model=Tarea, tags=["Tareas"])
def actualizar_tarea(tarea_id: str, cambios: TareaUpdate):
    """
    Actualiza parcialmente una tarea (PATCH semántico sobre PUT).
    Solo modifica los campos enviados; los demás se conservan.
    """
    if tarea_id not in tareas_db:
        raise HTTPException(status_code=404, detail=f"Tarea '{tarea_id}' no encontrada")

    tarea_actual = tareas_db[tarea_id]
    datos_actualizados = tarea_actual.dict()

    for campo, valor in cambios.dict(exclude_unset=True).items():
        datos_actualizados[campo] = valor

    datos_actualizados["actualizada_en"] = _ahora()
    tareas_db[tarea_id] = Tarea(**datos_actualizados)
    return tareas_db[tarea_id]


@app.delete("/tareas/{tarea_id}", tags=["Tareas"])
def eliminar_tarea(tarea_id: str):
    """Elimina una tarea por su ID. Retorna 404 si no existe."""
    if tarea_id not in tareas_db:
        raise HTTPException(status_code=404, detail=f"Tarea '{tarea_id}' no encontrada")
    eliminada = tareas_db.pop(tarea_id)
    return {"mensaje": "Tarea eliminada exitosamente", "tarea": eliminada}


@app.get("/tareas/estadisticas/resumen", tags=["Estadísticas"])
def estadisticas():
    """
    Devuelve un resumen estadístico del estado actual de las tareas.
    Útil para el dashboard del frontend.
    """
    todas = list(tareas_db.values())
    total = len(todas)
    completadas = sum(1 for t in todas if t.completada)
    pendientes = total - completadas

    por_prioridad = {"baja": 0, "media": 0, "alta": 0}
    for t in todas:
        por_prioridad[t.prioridad] += 1

    return {
        "total": total,
        "completadas": completadas,
        "pendientes": pendientes,
        "porcentaje_completado": round(completadas / total * 100, 1) if total > 0 else 0,
        "por_prioridad": por_prioridad,
    }
