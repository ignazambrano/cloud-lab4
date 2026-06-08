# =============================================================================
# Laboratorio IV - Parte I, Actividad 1.2
# Procesamiento Paralelo de Imágenes
# Autores: Ignacio Zambrano | Luisa Guerrero
# Curso: Computación Paralela y Distribuida en la Nube
# PUCE - Carrera de Ciencia de Datos
# =============================================================================

from PIL import Image, ImageFilter
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import time
import sys
import os

# ==================== FUNCIONES DE FILTRO ====================

def convertir_a_grises(region: np.ndarray) -> np.ndarray:
    """
    Convierte una región (sub-imagen) de RGB a escala de grises
    usando la fórmula de luminancia perceptual:
        Y = 0.2989·R + 0.5870·G + 0.1140·B
    Devuelve un array 3-canal para poder recombinar la imagen final.
    """
    grises = (
        0.2989 * region[:, :, 0] +
        0.5870 * region[:, :, 1] +
        0.1140 * region[:, :, 2]
    ).astype(np.uint8)
    # Expandir a 3 canales para mantener formato consistente
    return np.stack([grises, grises, grises], axis=2)


def aplicar_sharpen(region: np.ndarray) -> np.ndarray:
    """
    Aplica un filtro de nitidez (sharpen) manual usando convolución 3x3.
    Kernel sharpen estándar:
        [ 0, -1,  0]
        [-1,  5, -1]
        [ 0, -1,  0]
    Trabaja canal por canal para mantener colores.
    """
    kernel = np.array([[ 0, -1,  0],
                       [-1,  5, -1],
                       [ 0, -1,  0]], dtype=np.float32)

    h, w, c = region.shape
    resultado = np.zeros_like(region, dtype=np.float32)

    for canal in range(c):
        capa = region[:, :, canal].astype(np.float32)
        # Padding para no perder bordes
        pad = np.pad(capa, 1, mode='edge')
        for i in range(h):
            for j in range(w):
                bloque = pad[i:i+3, j:j+3]
                resultado[i, j, canal] = np.sum(bloque * kernel)

    # Clip para mantener valores válidos [0, 255]
    return np.clip(resultado, 0, 255).astype(np.uint8)


# ==================== PROCESAMIENTO SECUENCIAL ====================

def procesar_imagen_secuencial(imagen_path: str, filtro_fn) -> np.ndarray:
    """Aplica filtro_fn a la imagen completa de forma secuencial."""
    img = Image.open(imagen_path).convert("RGB")
    arr = np.array(img)
    return filtro_fn(arr)


# ==================== PROCESAMIENTO PARALELO ====================

def procesar_imagen_paralelo(imagen_path: str, filtro_fn, num_hilos: int = 4) -> np.ndarray:
    """
    Divide la imagen en 'num_hilos' franjas horizontales,
    aplica filtro_fn a cada franja en paralelo y las recombina.
    """
    img = Image.open(imagen_path).convert("RGB")
    arr = np.array(img)
    h = arr.shape[0]
    tam_franja = h // num_hilos

    franjas = []
    for i in range(num_hilos):
        inicio = i * tam_franja
        fin = h if i == num_hilos - 1 else inicio + tam_franja
        franjas.append(arr[inicio:fin, :, :])

    with ThreadPoolExecutor(max_workers=num_hilos) as executor:
        resultados = list(executor.map(filtro_fn, franjas))

    return np.vstack(resultados)


# ==================== CREACIÓN DE IMAGEN DE PRUEBA ====================

def crear_imagen_prueba(path: str, ancho: int = 800, alto: int = 600):
    """Crea una imagen RGB sintética para pruebas si no existe una real."""
    if os.path.exists(path):
        return
    print(f"  → Creando imagen de prueba en '{path}' ({ancho}x{alto}px)...")
    arr = np.random.randint(0, 256, (alto, ancho, 3), dtype=np.uint8)
    # Añadir gradiente para hacerla más interesante
    for i in range(alto):
        arr[i, :, 0] = np.clip(arr[i, :, 0] + int(i * 255 / alto), 0, 255)
    Image.fromarray(arr).save(path)


# ==================== EJECUCIÓN PRINCIPAL ====================

IMAGEN_PATH = "imagen_prueba.jpg"
crear_imagen_prueba(IMAGEN_PATH)

print("=" * 65)
print("  PROCESAMIENTO PARALELO DE IMÁGENES")
print(f"  Imagen: {IMAGEN_PATH}")
print("=" * 65)

filtros = {
    "Grises (luminancia)": convertir_a_grises,
    "Sharpen (nitidez)":   aplicar_sharpen,
}

for nombre_filtro, fn in filtros.items():
    print(f"\n  ── Filtro: {nombre_filtro} ──")

    # Secuencial
    t0 = time.time()
    resultado_seq = procesar_imagen_secuencial(IMAGEN_PATH, fn)
    t_seq = time.time() - t0
    print(f"    [SECUENCIAL]   Tiempo: {t_seq:.4f} seg")

    # Paralelo con 2 y 4 hilos
    for num_hilos in [2, 4]:
        t0 = time.time()
        resultado_par = procesar_imagen_paralelo(IMAGEN_PATH, fn, num_hilos)
        t_par = time.time() - t0
        speedup = t_seq / t_par if t_par > 0 else float('inf')
        eficiencia = speedup / num_hilos * 100
        print(f"    [PARALELO {num_hilos}H]  Tiempo: {t_par:.4f} seg | "
              f"Speedup: {speedup:.2f}x | Eficiencia: {eficiencia:.1f}%")

    # Guardar resultado
    nombre_salida = f"resultado_{nombre_filtro.split()[0].lower()}.png"
    Image.fromarray(resultado_par).save(nombre_salida)
    print(f"    → Imagen guardada: {nombre_salida}")

print("\n" + "=" * 65)
print("  Nota sobre el GIL de Python:")
print("  El filtro Sharpen es CPU-intensivo (bucles anidados), por lo")
print("  que el GIL puede limitar la ganancia real con hilos. Para")
print("  producción se recomendaría usar NumPy vectorizado o GPU.")
print("=" * 65)
