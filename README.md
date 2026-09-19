# Turismo y clima

Prototipo académico para Comunicación y Stakeholder Management. Recomienda actividades genéricas según el pronóstico y aplica el cambio del cliente: **viento > 50 km/h bloquea todas las actividades al aire libre y genera una alerta, incluso con cielo soleado**.

## Ejecutar

Requiere Python 3.10 o superior. No requiere instalar paquetes.

```powershell
python app.py
```

Abrir http://127.0.0.1:8000. En Windows también puedes usar `py app.py`. Para otro puerto: `python app.py --port 8001`.

La consulta real requiere internet. La demostración funciona sin internet y está identificada como simulada. El servicio escucha únicamente en el equipo local.

## Demostración para el profesor

1. Seleccionar soleado y viento de 20 km/h: aparecen planes interiores y exteriores.
2. Cambiar a 50 km/h: no se activa la alerta por viento.
3. Cambiar a 50.01 o 60 km/h: desaparecen todos los planes exteriores y aparece HIGH_WIND.
4. Probar lluvia y 20 km/h: solo planes interiores por el estado del clima.
5. Consultar el pronóstico real de Bogotá. Mostrar fuente y hora UTC.

## API HTTP

| Ruta GET | Parámetros | Respuesta |
|---|---|---|
| `/health` | Ninguno | 200, estado del servicio |
| `/api/recommendations` | `lat`, `lon`; Bogotá por defecto | Pronóstico de la próxima hora, planes y alerta |
| `/api/demo` | `wind` en km/h, `code` WMO | Misma política con datos simulados |

Ejemplo: http://127.0.0.1:8000/api/demo?wind=60&code=0

Campos principales: `activities`, `outdoor_blocked`, `safety_alert`, `wind_kmh`, `weather_code`, `forecast_time`, `source`, `simulated`. `safety_alert` es null cuando no hay alerta de viento. `outdoor_blocked` también puede ser true por lluvia u otro clima no favorable.

Errores: 400 para parámetros inválidos, 404 para rutas desconocidas, 503 si el proveedor falla o los datos meteorológicos no se pueden validar. En un 503 no se emiten recomendaciones. La interfaz elimina resultados anteriores al iniciar cada consulta.

## Diseño e impacto del cambio

`forecast()` adapta la API de Open-Meteo, pide explícitamente km/h y selecciona la primera hora futura en UTC. `recommend()` concentra las reglas y clasifica el catálogo mediante `outdoor`. `Handler` expone JSON y una interfaz HTML.

La regla previa por cielo se conserva en `outdoor_weather`: códigos 0–3 permiten exteriores; los demás códigos WMO reconocidos ofrecen interiores. La política nueva `wind > 50` tiene prioridad y se aplica en el servidor a todo el catálogo. No se cambia el proveedor ni se incorpora base de datos. El campo de alerta permite explicar el bloqueo al viajero.

El registro del cambio documenta una reconstrucción académica del antes y después; no se afirma que el profesor lo haya aprobado ni que exista historial previo de desarrollo.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Se comprueban límite exacto, prioridad del viento con varios estados del cielo, lluvia, entradas no finitas, unidades del proveedor, API HTTP y fallos del proveedor. Las pruebas usan respuestas controladas y no dependen del clima real.

## Alcance

La alerta se incluye en JSON y se muestra en pantalla al consultar. No hay vigilancia continua, SMS ni notificaciones push. Los planes son ejemplos genéricos, no un catálogo comercial. La regla de 50 km/h proviene del ejercicio y no certifica seguridad meteorológica. Prototipo local: antes de producción se requieren servidor de despliegue, límites de solicitudes y observabilidad.

## Entregables y equipo

En `entregables/`: documento de cambio de dos páginas y presentación ejecutiva con notas para exponer. Equipo: Julián Daniel Quitian Peña y Geraldine Rojas Torres.

Reparto sugerido: Geraldine explica cliente y cambio (diapositivas 1–3); Julián demuestra los escenarios y explica impacto y validación (diapositivas 4–6). Es una propuesta de reparto, no un registro de trabajo realizado.

## Publicar en GitHub

Crear un repositorio y subir `app.py`, `index.html`, `tests/`, `README.md`, `.gitignore` y `entregables/`. No subir `tmp/` ni `.build/`. También puede usarse Git:

```powershell
git add app.py index.html tests README.md .gitignore entregables
git commit -m "Agrega prototipo de turismo con bloqueo por viento"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
git push -u origin main
```

Sustituir la URL por el repositorio real. Estos comandos son instrucciones; el repositorio no se considera publicado hasta verificar el enlace remoto.

## Fuente

Datos meteorológicos: [Open-Meteo](https://open-meteo.com/). Contrato consultado: [Forecast API](https://open-meteo.com/en/docs). Se usan `hourly=weather_code,wind_speed_10m`, `wind_speed_unit=kmh` y `timezone=GMT`.
