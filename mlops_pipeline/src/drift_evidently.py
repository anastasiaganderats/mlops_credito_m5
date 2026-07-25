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

def main() -> None:
    print("=" * 70)
    print("MONITOREO DE DATA DRIFT - EVIDENTLY")
    print("=" * 70)

    try:
        print("\n[1/4] Cargando dataset limpio...")
        df = load_clean_dataset()
        
        print("[2/4] Aplicando partición temporal...")
        X_hist, X_act = split_temporal(df)
        
        print("[3/4] Preparando features...")
        X_hist = preparar_features(X_hist)
        X_act = preparar_features(X_act)
        
        # Asegurar tipos estándar de pandas para evitar conflictos en Evidently
        X_hist = X_hist.reset_index(drop=True)
        X_act = X_act.reset_index(drop=True)

        print(f"  Dimensiones Histórico: {X_hist.shape}")
        print(f"  Dimensiones Actual:    {X_act.shape}")

        print("\n[4/4] Generando reporte Evidently...")
        from evidently.report import Report
        from evidently.metric_preset import DataDriftPreset

        report = Report(metrics=[DataDriftPreset()])
        
        # Ejecución del reporte
        print("  Ejecutando report.run()...")
        report.run(reference_data=X_hist, current_data=X_act)

        DATA_PROC_DIR.mkdir(parents=True, exist_ok=True)

        html_path = DATA_PROC_DIR / "drift_evidently_report.html"
        report.save_html(str(html_path))
        print(f"  [OK] Reporte HTML guardado en: {html_path}")

        summary_path = DATA_PROC_DIR / "drift_evidently_summary.json"
        result_dict = report.as_dict() if hasattr(report, 'as_dict') else {}
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        print(f"  [OK] Resumen JSON guardado en: {summary_path}")

    except Exception as e:
        print(f"\n[ERROR CRÍTICO DETECTADO]: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()