# =============================================================================
# Laboratorio IV - Parte I, Actividad 1.1
# Búsqueda Paralela en Arreglos Grandes
# Autores: Ignacio Zambrano | Luisa Guerrero
# Curso: Computación Paralela y Distribuida en la Nube
# PUCE - Carrera de Ciencia de Datos
# =============================================================================

from concurrent.futures import ThreadPoolExecutor
import time
import random
import math

# ==================== FUNCIÓN DE BLOQUE ====================
def buscar_bloque(datos, objetivo, inicio, fin):
    for i in range(inicio, fin):
        if datos[i] == objetivo:
            return i
    return -1

# ==================== CONFIGURACIÓN ====================
N = 10_000_000
datos = [random.randint(1, 1000) for _ in range(N)]
objetivo = random.choice(datos)

# ==================== VERSIÓN SECUENCIAL ====================
def busqueda_secuencial(datos, objetivo):
    for i in range(len(datos)):
        if datos[i] == objetivo:
            return i
    return -1

# ==================== VERSIÓN PARALELA ====================
def busqueda_paralela(datos, objetivo, num_hilos=4):
    n = len(datos)
    tam_bloque = math.ceil(n / num_hilos)

    resultados = []

    with ThreadPoolExecutor(max_workers=num_hilos) as executor:
        futuros = []

        for h in range(num_hilos):
            inicio = h * tam_bloque
            fin = min(inicio + tam_bloque, n)

            futuros.append(
                executor.submit(buscar_bloque, datos, objetivo, inicio, fin)
            )

        for futuro in futuros:
            resultado = futuro.result()

            if resultado != -1:
                resultados.append(resultado)

    if resultados:
        return min(resultados)

    return -1

# ==================== EJECUCIÓN SECUENCIAL ====================
print("=" * 70)
print("BÚSQUEDA PARALELA EN ARREGLOS GRANDES")
print(f"Arreglo de {N:,} elementos")
print(f"Objetivo seleccionado aleatoriamente: {objetivo}")
print("=" * 70)

inicio = time.perf_counter()
resultado_sec = busqueda_secuencial(datos, objetivo)
fin = time.perf_counter()

tiempo_secuencial = fin - inicio

print(
    f"\nSecuencial - Posición: {resultado_sec} | "
    f"Tiempo: {tiempo_secuencial:.10f} seg"
)

# ==================== EJECUCIÓN PARALELA ====================
resultados_paralelos = {}

for hilos in [2, 4, 8]:
    inicio = time.perf_counter()
    resultado_par = busqueda_paralela(datos, objetivo, hilos)
    fin = time.perf_counter()

    tiempo_paralelo = fin - inicio
    speedup = tiempo_secuencial / tiempo_paralelo if tiempo_paralelo > 0 else float("inf")
    eficiencia = speedup / hilos

    resultados_paralelos[hilos] = {
        "posicion": resultado_par,
        "tiempo": tiempo_paralelo,
        "speedup": speedup,
        "eficiencia": eficiencia
    }

    print(
        f"Paralelo {hilos} hilos - Posición: {resultado_par} | "
        f"Tiempo: {tiempo_paralelo:.10f} seg | "
        f"Speedup: {speedup:.10f} | "
        f"Eficiencia: {eficiencia:.10f}"
    )

# ==================== TABLA RESUMEN ====================
print("\n" + "=" * 70)
print(f"{'Configuración':<20} {'Tiempo (s)':<18} {'Speedup':<18} {'Eficiencia'}")
print("-" * 70)

print(
    f"{'Secuencial':<20} "
    f"{tiempo_secuencial:<18.10f} "
    f"{1.0:<18.10f} "
    f"{1.0:.10f}"
)

for hilos, r in resultados_paralelos.items():
    print(
        f"{str(hilos) + ' hilos':<20} "
        f"{r['tiempo']:<18.10f} "
        f"{r['speedup']:<18.10f} "
        f"{r['eficiencia']:.10f}"
    )

print("=" * 70)

# ==================== MEJOR CONFIGURACIÓN ====================
mejor_hilos = max(
    resultados_paralelos,
    key=lambda h: resultados_paralelos[h]["speedup"]
)

mejor = resultados_paralelos[mejor_hilos]

print(
    f"\nMejor configuración: {mejor_hilos} hilos "
    f"con Speedup = {mejor['speedup']:.10f} "
    f"y Eficiencia = {mejor['eficiencia']:.10f}"
)

print("\nNota:")
print("Como el objetivo se selecciona aleatoriamente desde el arreglo,")
print("puede aparecer muy al inicio. Por eso los tiempos y el speedup")
print("pueden variar bastante entre ejecuciones.")
print("Además, ThreadPoolExecutor usa hilos y en Python el GIL puede limitar")
print("el paralelismo real en tareas CPU-bound.")