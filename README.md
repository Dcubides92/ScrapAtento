# Proyecto de Web Scraping y ETL – books.toscrape.com

## Documentación

Este archivo corresponde a la documentación solicitada en la prueba técnica.
Incluye instrucciones de instalación, ejecución y decisiones técnicas tomadas
durante el desarrollo.

---

## Requisitos del Sistema

- Python 3.10 o superior
- Acceso a Internet

---

## Instalación de Dependencias

Se recomienda el uso de un entorno virtual.

```bash
python -m venv .venv
```

### Activar entorno virtual

Windows (PowerShell):
```bash
.venv\Scripts\Activate.ps1
```

Windows (CMD):
```bash
.venv\Scripts\activate
```

### Instalar dependencias

```bash
pip install -r requirements.txt
```

Contenido de `requirements.txt`:

```txt
requests
beautifulsoup4
```

---

## Ejecución del Scraper

El script principal de scraping es `scrape_books.py`.

Ejecutar todo el proceso (modo por defecto):

```bash
python scrape_books.py
```

---

## Ejecución del Proceso ETL

El script ETL es `etl_books.py`.

```bash
python etl_books.py
```

Entrada:
- `books.txt`

Salidas:
- `productos.csv`
- `productos.json`

---

## ¿Por qué requests + BeautifulSoup y no Selenium?

Se eligió `requests + BeautifulSoup` porque el sitio
`books.toscrape.com` renderiza todo su contenido directamente en HTML
y no requiere la ejecución de JavaScript.

Esta solución es:
- Más ligera
- Más rápida
- Más fácil de mantener
- Menos costosa en recursos

Selenium se reserva para escenarios donde el contenido se genera de forma
dinámica mediante JavaScript o se requieren interacciones complejas con
la interfaz.

---

## Suposiciones y Decisiones de Diseño

Durante el desarrollo se tomaron las siguientes decisiones:

- Análisis de la página web para determinar la distribución del contemido dentro del html
- Análisis de estructura de textos para definir delimitadores de los archivos, en este cado ";"
- Separación entre scraping y ETL para mejorar la modularidad.
- Implementación de scraping "polite" mediante pausas entre peticiones.
- Manejo robusto de errores sin detener la ejecución.
- Almacenamiento de datos sin transformación en la fase de scraping.
- Transformación y normalización de datos exclusivamente en la fase ETL.
- Uso de codificación UTF-8 para soportar caracteres especiales.

---
## ¿Cómo adaptarías este script para que se ejecute automáticamente todos los días en un entorno de producción?

Considerando factores como frecuencia de ejecución,criticidad del dato, volumen, costos operativos y complejidad de mantenimiento, se pueden elegir difrentes herramientas de automatización.

Teniendo en cuenta que se indica la periodicidad diaria y una necesidad simple se optaría por:

### Cron en un servidor o VM

- Desplegar el proyecto en una VM Linux.
- Crear un entorno virtual con Python.
- Configurar una tarea cron que ejecute diariamente
- Los logs se almacenan en archivos locales.

---

## Si tuvieras que escalar este proceso para 100 sitios web diferentes, ¿cuáles serían los principales componentes de tu arquitectura?

Para escalar el proceso, es necesario evaluar la diversidad de los sitios, el volumen de datos y los requisitos de disponibilidad. A partir de esto, la arquitectura debe desacoplar responsabilidades y permitir crecimiento progresivo.

a parti de los  siguientes componentes generaria una arquitectra que cumpla con los criterios del problema planteado

-  Orquestador
-  Configuración por sitio
-  Motor de Scraping Común
-  Adaptadores por sitio (plugins)
-  Cola de Mensajes
-  Workers Escalables
-  Almacenamiento de Datos
-  ETL / Normalización
-  Observabilidad

---

## Conclusión

Este proyecto demuestra una implementación completa de Web Scraping y ETL
en Python, aplicando buenas prácticas de desarrollo, modularidad,
robustez y documentación clara.

