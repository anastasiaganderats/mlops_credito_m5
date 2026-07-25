"""
drift_evidently.py
===================
Genera reporte de data drift usando la libreria Evidently.

Complementa a model_monitoring.py (que implementa las 4 metricas KS/PSI/JS/Chi2
de forma manual con scipy). Este script agrega un reporte HTML profesional
generado automaticamente por Evidently, alineado con el estandar de la
industria para monitoreo de modelos en produccion.

Estrategia:
  - Usa el mismo split temporal por fecha_prestamo (70% historico / 30% actual)
    que model_monitoring.py, para que ambos reportes sean comparables.
  - Genera un archivo HTML interactivo en data_processed/drift_evidently_report.html
  - Persistir estadisticas en JSON para consumo programatico.

Uso:
    python drift_evidently.py

Salidas:
    data_processed/drift_evidently_report.html   (reporte interactivo)
    data_processed/drift_evidently_summary.json  (resumen programatico)

Estado: V1.1.1 - Avance 3 (extension).
"""

import json
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings('ignore')

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ft_engineering import (
    load_clean_dataset,
    build_derived_features,
    get_feature_columns,
    COLUMNAS_LEAKAGE,
    DATA_PROC_DIR,
)


PROPORCION_HISTORICA = 0.70


def split_temporal(df, proporcion_historica=PROPORCION_HISTORICA):
    """Mismo split temporal que model_monitoring.py."""
    df = df.sort_values('fecha_prestamo').reset_index(drop=True)
    n_hist = int(len(df) * proporcion_historica)
    return df.iloc[:n_hist].copy(), df.iloc[n_hist:].copy()


def preparar_features(df):
    """Aplica feature engineering y devuelve solo las columnas del modelo (sin target ni leakage)."""
    df = build_derived_features(df)
    fc = get_feature_columns(df)
    columnas = (fc['numericas_continuas'] + fc['numericas_discretas']
                + fc['categoricas_nominales'] + fc['categoricas_ordinales'])
    return df[columnas].copy()


def main():
    print("=" * 70)
    print("DRIFT REPORT CON EVIDENTLY - V1.1.1 (Avance 3 extension)")
    print("=" * 70)

    # 1. Cargar dataset
    print("\n[1/4] Cargando dataset limpio...")
    df = load_clean_dataset()
    print(f"  Dataset: {len(df):,} filas x {df.shape[1]} columnas")

    # 2. Split temporal
    print(f"\n[2/4] Split temporal {int(PROPORCION_HISTORICA*100)}/{int((1-PROPORCION_HISTORICA)*100)}...")
    df_hist, df_act = split_temporal(df)
    print(f"  Historico:  n={len(df_hist):,}")
    print(f"  Actual:     n={len(df_act):,}")

    # 3. Preparar features (mismas que se usan en el modelo)
    print("\n[3/4] Preparando features (excluyendo leakage)...")
    X_hist = preparar_features(df_hist)
    X_act = preparar_features(df_act)
    print(f"  Columnas a comparar: {X_hist.shape[1]}")
    print(f"  Leakage excluido: {COLUMNAS_LEAKAGE}")

    # 4. Generar reporte Evidently
    print("\n[4/4] Generando reporte Evidently...")
    try:
        from evidently import Report
        from evidently.presets import DataDriftPreset
    except ImportError as e:
        print(f"\n[ERROR] Evidently no esta instalado. Ejecuta:")
        print(f"    pip install evidently")
        print(f"\nDetalle: {e}")
        return

    report = Report(metrics=[DataDriftPreset()])
    result = report.run(reference_data=X_hist, current_data=X_act)

    # Guardar HTML
    html_path = DATA_PROC_DIR / "drift_evidently_report.html"
    result.save_html(str(html_path))
    print(f"  Reporte HTML: {html_path}")

    # Extraer resumen programatico
    try:
        result_dict = result.as_dict() if hasattr(result, 'as_dict') else {}
        summary_path = DATA_PROC_DIR / "drift_evidently_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump({
                "engine": "evidently",
                "metric": "DataDriftPreset",
                "n_reference": len(X_hist),
                "n_current": len(X_act),
                "n_features_compared": X_hist.shape[1],
                "columnas_leakage_excluidas": COLUMNAS_LEAKAGE,
                "html_report": str(html_path.name),
                "result_dict_sample": result_dict if isinstance(result_dict, dict) else str(result_dict)[:500],
            }, f, indent=2, ensure_ascii=False, default=str)
        print(f"  Resumen JSON: {summary_path}")
    except Exception as e:
        print(f"  [WARN] No se pudo extraer summary programatico: {e}")

    print("\n" + "=" * 70)
    print("Reporte Evidently generado. Abrir en navegador:")
    print(f"  file:///{html_path.as_posix()}")
    print("=" * 70)


if __name__ == "__main__":
    main()
