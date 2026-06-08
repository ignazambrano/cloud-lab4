# =============================================================================
# Laboratorio IV - Parte I, Actividad 1.3
# Cálculo de Estadísticas Paralelas
# Autores: Ignacio Zambrano | Luisa Guerrero
# Curso: Computación Paralela y Distribuida en la Nube
# PUCE - Carrera de Ciencia de Datos
# =============================================================================

import random
import time
import math
from concurrent.futures import ThreadPoolExecutor

# ==================== CONFIGURACIÓN ====================
datos = [random.randint(1, 10000) for _ in range(5_000_000)]

# ==================== FUNCIÓN POR BLOQUE ====================
def estadisticas_bloque(bloque):
    """
    Calcula estadísticas locales de un bloque de datos.
    Retorna dict con min, max, suma y count del bloque.
    """
    return {
        "min":   min(bloque),
        "max":   max(bloque),
        "suma":  sum(bloque),
        "count": len(bloque)
    }

# ==================== VERSIÓN SECUENCIAL ====================
def calcular_estadisticas_secuencial(datos):
    return {
        "min":      min(datos),
        "max":      max(datos),
        "suma":     sum(datos),
        "promedio": sum(datos) / len(datos),
        "count":    len(datos)
    }

# ==================== VERSIÓN PARALELA ====================
def calcular_estadisticas_paralelo(datos, num_hilos=4):
    """
    Divide los datos en bloques iguales, calcula estadísticas
    locales en paralelo y combina los resultados globalmente.
    
    La combinación es O(num_hilos) — trivialmente rápida.
    """
    n = len(datos)
    tam_bloque = math.ceil(n / num_hilos)
    bloques = [datos[i * tam_bloque : (i + 1) * tam_bloque] for i in range(num_hilos)]

    with ThreadPoolExecutor(max_workers=num_hilos) as executor:
        parciales = list(executor.map(estadisticas_bloque, bloques))

    # Combinar resultados de todos los bloques
    global_min   = min(p["min"]  for p in parciales)
    global_max   = max(p["max"]  for p in parciales)
    global_suma  = sum(p["suma"] for p in parciales)
    global_count = sum(p["count"] for p in parciales)

    return {
        "min":      global_min,
        "max":      global_max,
        "suma":     global_suma,
        "promedio": global_suma / global_count,
        "count":    global_count
    }

# ==================== EJECUCIÓN Y MEDICIÓN ====================
print("=" * 65)
print("  CÁLCULO DE ESTADÍSTICAS PARALELAS")
print(f"  Dataset: {len(datos):,} elementos enteros aleatorios [1, 10000]")
print("=" * 65)

# Secuencial
t0 = time.time()
stats_seq = calcular_estadisticas_secuencial(datos)
t_seq = time.time() - t0
print(f"\n[SECUENCIAL]")
print(f"  Min: {stats_seq['min']} | Max: {stats_seq['max']} | "
      f"Suma: {stats_seq['suma']:,} | Promedio: {stats_seq['promedio']:.4f}")
print(f"  Tiempo: {t_seq:.4f} seg")

# Paralelo
print()
for num_hilos in [2, 4, 8]:
    t0 = time.time()
    stats_par = calcular_estadisticas_paralelo(datos, num_hilos)
    t_par = time.time() - t0
    speedup    = t_seq / t_par if t_par > 0 else float('inf')
    eficiencia = speedup / num_hilos * 100

    # Verificar corrección
    correcto = (stats_par["min"] == stats_seq["min"] and
                stats_par["max"] == stats_seq["max"] and
                abs(stats_par["promedio"] - stats_seq["promedio"]) < 1e-6)

    print(f"[PARALELO {num_hilos}H]  Tiempo: {t_par:.4f} seg | "
          f"Speedup: {speedup:.2f}x | Eficiencia: {eficiencia:.1f}% | "
          f"Correcto: {'✓' if correcto else '✗'}")

# Tabla resumen
print("\n" + "=" * 65)
print(f"  Resultados verificados ✓")
print(f"  Min global: {stats_seq['min']} | Max global: {stats_seq['max']}")
print(f"  Promedio: {stats_seq['promedio']:.4f} | Total elementos: {stats_seq['count']:,}")
print("=" * 65)

print("""
Análisis:
  - La combinación de resultados parciales es O(num_hilos), por lo
    que el overhead de merge es despreciable frente al cómputo.
  - min/max/suma son operaciones "embarrassingly parallel": no hay
    dependencia entre bloques, lo que maximiza el speedup teórico.
  - El GIL de Python sigue siendo un factor limitante para hilos
    CPU-bound; en producción se usaría multiprocessing o numpy.
""")
