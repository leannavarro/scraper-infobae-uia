# Scraper Masivo de Infobae - Búsqueda UIA

Script de Python para extraer noticias sobre UIA (Unión Industrial Argentina) desde Infobae mediante búsqueda.

## Características

- **Scraping por búsqueda**: Extrae artículos usando el buscador de Infobae
- **Paginación automática**: Navega múltiples páginas de resultados
- **Scraping concurrente** con ThreadPoolExecutor para contenido completo
- **Dos modos de operación**:
  - **Modo rápido**: Extrae títulos, links, descripciones y fechas
  - **Modo profundo**: Extrae el contenido completo (título, autor, fecha, cuerpo)
- **Rate limiting** configurable para no sobrecargar el servidor
- **Exportación**: JSON y CSV
- **Logging** detallado para seguimiento del proceso

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

### Ejecución básica
```bash
python scraper_infobae.py
```

Esto ejecutará el scraper buscando "UIA" en Infobae, navegando hasta 10 páginas de resultados y extrayendo tanto títulos como contenido completo.

### Personalización

Edita la función `main()` en el script:

```python
# Configurar el scraper
scraper = InfobaeScraper(
    max_workers=3,  # Número de hilos concurrentes
    delay=0.5       # Segundos entre requests
)

# Cambiar el término de búsqueda o número de páginas
query = "uia"  # Puedes cambiar a cualquier término
articles = scraper.scrape_search_results(query, max_pages=10)
```

### Scraping profundo

El script ahora automáticamente extrae el contenido completo de los artículos encontrados (limitado a 50 artículos en el ejemplo para no saturar).

## Estructura de datos

### Modo rápido (títulos y links)
```json
{
  "title": "Título del artículo sobre UIA",
  "url": "https://www.infobae.com/economia/...",
  "description": "Descripción breve del artículo...",
  "date": "2025-11-25",
  "search_query": "uia",
  "page": 1,
  "scraped_at": "2025-11-25T09:08:00.123456"
}
```

### Modo profundo (contenido completo)
```json
{
  "url": "https://www.infobae.com/...",
  "title": "Título del artículo",
  "author": "Nombre del autor",
  "date": "2025-11-25",
  "body": "Cuerpo completo del artículo...",
  "scraped_at": "2025-11-25T09:08:00.123456"
}
```

## Archivos generados

- `infobae_uia_titulos.json`: Todos los artículos sobre UIA en formato JSON
- `infobae_uia_titulos.csv`: Todos los artículos sobre UIA en formato CSV
- `infobae_uia_completo.json`: Artículos con contenido completo (cuerpo del artículo)

## Notas

- El scraper incluye un delay entre requests (0.5s por defecto) para ser respetuoso con el servidor
- Los selectores CSS pueden necesitar ajustes si Infobae cambia su estructura HTML
- La paginación se detiene automáticamente cuando no se encuentran más resultados
- Se limita a 50 artículos completos por defecto para evitar tiempos de ejecución largos

## Ejemplo de salida

```
============================================================
SCRAPER DE INFOBAE - BÚSQUEDA: UIA
============================================================
2025-11-25 09:08:15 - INFO - Iniciando búsqueda de 'uia' - máximo 10 páginas
2025-11-25 09:08:16 - INFO - Scrapeando página 1: https://www.infobae.com/buscador/?query=uia
2025-11-25 09:08:16 - INFO - Página 1: 20 artículos encontrados
...
2025-11-25 09:08:25 - INFO - ✓ Total de artículos extraídos: 87

✓ Se extrajeron 87 artículos sobre UIA
✓ Archivos guardados: infobae_uia_titulos.json y infobae_uia_titulos.csv
```
