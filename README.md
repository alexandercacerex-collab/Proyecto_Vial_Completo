# Dashboard Ejecutivo de Planificación y Control – Proyecto Vial

Versión mejorada del dashboard Streamlit, construida con los datos del archivo
`Proyecto_Vial_Completo_Actualizado(1).xlsx`.

## Mejoras incluidas

- Panel ejecutivo con KPIs.
- Curva S programada por Horas-Hombre.
- Análisis mensual de recursos.
- Identificación y visualización de ruta crítica.
- Línea de tiempo mensual de actividades críticas.
- Matriz de rendimientos y cuadrillas.
- Simulador interactivo para excavación en roca fija.
- Comparación de escenarios de eficiencia.
- Filtros por grupo de partidas y criticidad.
- Descarga de datos en CSV.
- Diseño optimizado para exposición y Streamlit Cloud.

## Despliegue

1. Subir todos los archivos a la raíz de un repositorio GitHub.
2. En Streamlit Community Cloud:
   - Branch: `main`
   - Main file path: `app.py`
3. Presionar Deploy.

## Dependencias

`requirements.txt`:
- streamlit
- pandas
- plotly
