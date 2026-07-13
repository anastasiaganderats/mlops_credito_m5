# Pipeline MLOps - Prediccion de Pago a Tiempo

**Proyecto Integrador - Modulo 5 - Henry**
**Rol simulado:** Cientifico de Datos Jr Advanced - Sector financiero
**Variable objetivo:** `Pago_atiempo` (binario: 1 = paga, 0 = impago)
**Dataset:** 10.763 registros historicos de creditos, 23 variables originales

---

## Caso de negocio

Una empresa financiera necesita anticipar el comportamiento crediticio de nuevos clientes antes de otorgar prestamos. El equipo de Datos y Analitica desarrolla un modelo predictivo que se integra en el flujo operativo: recibe la solicitud, calcula la probabilidad de pago a tiempo y devuelve un score que alimenta la decision crediticia.

El modelo opera bajo principios MLOps: estructura de carpetas estricta, versionamiento con tres ramas (developer/certification/master), pipelines automatizados de feature engineering, monitoreo de drift continuo y despliegue dockerizado de la API.

---

## Resumen de hallazgos clave

### Calidad de datos

- Dataset con 23 variables, sin nulos disfrazados ni variables irrelevantes.
- Nulos correlacionados (~14% de las filas) en `promedio_ingresos_datacredito` y `tendencia_ingresos`: clientes sin historial en el buro Datacredito. Tratamiento: no imputacion por media, sino categoria informativa (feature derivada `tiene_historial_datacredito`).
- Desbalance severo del target: 95.25% pago a tiempo / 4.75% impago. Condiciona toda la estrategia de modelado (metricas robustas, class_weight, SMOTE, threshold tuning).

### Deteccion iterativa de leakage

- **Etapa EDA (Avance 1)**: las 4 variables de saldo (`saldo_mora`, `saldo_total`, `saldo_principal`, `saldo_mora_codeudor`) presentan AUC univariada > 0.90. Representan estado post-otorgamiento del prestamo, no disponibles al momento de evaluar un nuevo cliente. Excluidas.
- **Etapa modelado (Avance 2)**: verificacion complementaria detecta que `puntaje` (score interno) presenta AUC univariada = 1.0 y capturaba 74% de la importancia del Random Forest. Hipotesis: score post-hoc calculado a partir del comportamiento observado, o output de un modelo previo entrenado sobre estos mismos datos. Se excluye.
- `puntaje_datacredito` (score externo del buro Datacredito, AUC 0.62) se mantiene: informacion disponible al momento de la solicitud.

### Modelamiento (Avance 2)

Se comparan 5 modelos baseline y 3 optimizados con SMOTE + GridSearchCV:

| Modelo | ROC-AUC | F1 clase 0 | Notas |
|--------|---------|------------|-------|
| **LGBM baseline** | 0.6482 | **0.1860** | Seleccionado como final |
| LogReg | 0.6613 | 0.1345 | Mejor recall clase 0 |
| XGBoost | 0.6578 | 0.1606 | |
| Random Forest | 0.6436 | 0.0877 | |
| KNN | 0.5855 | 0.0192 | Peor con desbalance |
| lgbm_smote (grid) | 0.6851 | 0.0545 | Mejor ROC, peor F1 clase 0 |
| xgb_smote (grid) | 0.6637 | 0.1538 | |
| logreg_smote (grid) | 0.6433 | 0.1290 | |

**Modelo final**: LightGBM baseline con `class_weight='balanced'`.
**Threshold de decision optimizado**: 0.35 (F1 macro), en lugar del 0.5 default.

### Monitoreo de drift (Avance 3)

Sobre split temporal por `fecha_prestamo` (70% mas antiguo como historico de referencia, 30% mas reciente como periodo actual):

| Periodo | Rango de fechas | Registros |
|---------|-----------------|-----------|
| Historico (referencia) | 2024-11-26 a 2025-05-26 | 7.534 |
| Actual (produccion simulada) | 2025-05-26 a 2026-04-26 | 3.229 |

**Data drift por variable** (24 variables analizadas):

| Nivel | Cantidad | Ejemplos representativos |
|-------|----------|--------------------------|
| Drift severo | 6 | total_otros_prestamos, promedio_ingresos_datacredito, ratio_otros_salario, endeudamiento_total, plazo_meses, mes_prestamo |
| Drift moderado | 10 | capital_prestado, salario_cliente, cuota_pactada, ratios varios |
| Sin drift | 8 | puntaje_datacredito, edad_cliente, otros |

Metricas aplicadas: Kolmogorov-Smirnov, Population Stability Index (PSI), Jensen-Shannon divergence, Chi-cuadrado.

**Model drift**:

| Metrica | Historico | Actual | Delta |
|---------|-----------|--------|-------|
| ROC-AUC | 0.9383 | 0.9172 | -0.0211 |
| F1 macro | 0.7936 | 0.8409 | +0.0473 |
| F1 clase 0 | 0.6181 | 0.6939 | +0.0758 |
| Tasa impago real | 5.35% | 3.34% | -2.01 pp |
| Tasa impago predicha | 9.60% | 4.24% | -5.36 pp |

Caida de ROC-AUC (0.0211) esta dentro del umbral configurado (0.05). El modelo se mantiene estable en performance pese al drift detectado en las features.

**Recomendacion automatica**: MONITOREO_REFORZADO con reentrenamiento preventivo, ya que multiples variables presentan drift severo aunque la performance se mantiene.

---

## Estructura del repositorio

```
PI/
|-- mlops_pipeline/
|   |-- set_up.bat                       # Crea venv e instala dependencias
|   |-- requirements.txt
|   `-- src/
|       |-- config.json                  # Metadatos del proyecto
|       |-- Cargar_datos.ipynb           # Avance 1 - Carga y validacion
|       |-- comprension_eda.ipynb        # Avance 1 - EDA completo
|       |-- ft_engineering.py            # Avance 2 - Feature engineering
|       |-- model_training_evaluation.py # Avance 2 - Entrenamiento y evaluacion
|       |-- modelamiento.ipynb           # Avance 2 - Analisis con visualizaciones
|       |-- model_monitoring.py          # Avance 3 - Drift detection
|       `-- model_deploy.py              # Avance 4 - FastAPI (placeholder)
|-- models/
|   |-- best_model.joblib                # Pipeline ganador (preproc + LGBM)
|   |-- preprocessor.joblib              # ColumnTransformer ajustado
|   |-- threshold_optimo.json            # Umbral 0.35
|   |-- model_metrics.json               # Metricas de todos los modelos
|   |-- comparacion_modelos.png          # Visualizacion comparativa
|   |-- curvas_roc.png
|   |-- curvas_pr.png
|   |-- matrices_confusion.png
|   |-- feature_importance.png
|   `-- threshold_tuning.png
|-- data_processed/
|   |-- dataset_limpio.parquet           # Output Cargar_datos
|   |-- reglas_validacion.json           # Contrato de datos para produccion
|   |-- X_train.parquet, X_test.parquet  # Splits
|   |-- y_train.parquet, y_test.parquet
|   |-- X_train_transformed.parquet      # Post-preprocessor
|   |-- X_test_transformed.parquet
|   |-- feature_cols.json                # Catalogo de features
|   |-- prediction_log.csv               # Log de predicciones para drift
|   |-- drift_metrics.csv                # Metricas de drift por variable
|   |-- drift_summary.json               # Resumen ejecutivo del drift
|   `-- model_performance_drift.json     # Model drift detallado
|-- streamlit_app/
|   `-- app.py                           # Dashboard de monitoreo
|-- tests/                               # Extra Credit (aun no implementado)
|-- .github/workflows/                   # Extra Credit (aun no implementado)
|-- Base_de_datos.csv                    # Dataset fuente
|-- requirements.txt
|-- .gitignore
`-- readme.md
```

---

## Setup local (Windows)

### 1. Clonar el repositorio

```cmd
git clone https://github.com/anastasiaganderats/mlops_credito_m5.git
cd mlops_credito_m5
```

### 2. Crear entorno virtual y registrar kernel Jupyter

```cmd
cd mlops_pipeline
.\set_up.bat
cd ..
```

Crea `mlops_pipeline/mlops_credito_m5-venv/` e instala las dependencias.
Requiere Python 3.10, 3.11 o 3.12 (Python 3.13 y 3.14 no tienen wheels disponibles para varias librerias del stack).

### 3. Activar el entorno

```cmd
mlops_pipeline\mlops_credito_m5-venv\Scripts\activate
```

En PowerShell:

```powershell
mlops_pipeline\mlops_credito_m5-venv\Scripts\Activate.ps1
```

El prompt debe cambiar a `(mlops_credito_m5-venv) C:\...`.

### 4. Ejecutar el pipeline en orden

```cmd
cd mlops_pipeline\src
jupyter notebook Cargar_datos.ipynb            # Avance 1 - carga
jupyter notebook comprension_eda.ipynb         # Avance 1 - EDA
python ft_engineering.py                       # Avance 2 - features
python model_training_evaluation.py            # Avance 2 - modelado end-to-end
jupyter notebook modelamiento.ipynb            # Avance 2 - analisis con visualizaciones
python model_monitoring.py                     # Avance 3 - drift
cd ..\..
streamlit run streamlit_app\app.py             # Avance 3 - dashboard
```

---

## Ramas y versionado

```
                  V1.0.0       V1.0.1       V1.1.0       V1.1.1
master:           o------------o------------o------------o
                  |            |            |            |
certification: ---o------------o------------o------------o
                  |            |            |            |
developer:    ----o------------o------------o------------o
                  estructura   carga+EDA    FE+modelado  drift+API+Docker
```

| Version | Avance | Contenido |
|---------|--------|-----------|
| V1.0.0 | - | Estructura inicial del proyecto |
| V1.0.1 | 1 | Cargar_datos + comprension_eda |
| V1.1.0 | 2 | ft_engineering + model_training_evaluation + modelamiento.ipynb |
| V1.1.1 | 3 + 4 | model_monitoring + Streamlit + FastAPI + Dockerfile |

Flujo de pull request: `developer` -> `certification` (validacion) -> `master` (produccion estable).

---

## Tech stack

- **Lenguaje**: Python 3.10-3.12
- **Datos**: pandas, numpy, pyarrow, openpyxl
- **Visualizacion**: matplotlib, seaborn
- **ML**: scikit-learn, xgboost, lightgbm, imbalanced-learn, feature-engine
- **Estadistica y drift**: scipy (KS, Jensen-Shannon, chi-cuadrado), PSI (implementacion manual)
- **API**: FastAPI, uvicorn, pydantic
- **Dashboard**: Streamlit
- **Despliegue**: Docker
- **Testing y calidad**: pytest, pytest-cov, SonarCloud

---

## Autora

**Anastasia Ganderats**
Sociologa | Data Scientist
aganderatsi@gmail.com
Henry - Modulo 5 - Cohorte 2026
