"""
tests/test_models.py
=====================
Tests para model_training_evaluation y model_monitoring.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mlops_pipeline" / "src"))

from model_training_evaluation import (
    build_model,
    summarize_classification,
    tune_decision_threshold,
    seleccionar_mejor_modelo,
)
from model_monitoring import (
    calcular_ks,
    calcular_psi,
    calcular_js_divergence,
    calcular_chi2,
    clasificar_alerta_psi,
    split_temporal,
)


# ============================================================
# Tests: build_model
# ============================================================

class TestBuildModel:
    @pytest.mark.parametrize("name", ["logreg", "rf", "xgb", "knn", "lgbm"])
    def test_construye_los_cinco_modelos(self, name):
        modelo = build_model(name)
        assert modelo is not None
        assert hasattr(modelo, "fit")
        assert hasattr(modelo, "predict")

    def test_lanza_error_si_nombre_desconocido(self):
        with pytest.raises(ValueError):
            build_model("modelo_inexistente")


# ============================================================
# Tests: summarize_classification
# ============================================================

class TestSummarizeClassification:
    def test_retorna_diccionario_completo(self):
        y_true = np.array([0, 0, 1, 1, 0, 1, 1, 0])
        y_pred = np.array([0, 1, 1, 1, 0, 0, 1, 0])
        y_proba = np.array([0.2, 0.6, 0.7, 0.8, 0.1, 0.4, 0.9, 0.3])
        metrics = summarize_classification("test_modelo", y_true, y_pred, y_proba)
        assert metrics["modelo"] == "test_modelo"
        assert "roc_auc" in metrics
        assert "f1_clase_0_impago" in metrics
        assert "matriz_confusion" in metrics
        assert 0 <= metrics["roc_auc"] <= 1
        assert 0 <= metrics["accuracy"] <= 1


# ============================================================
# Tests: tune_decision_threshold
# ============================================================

class TestThresholdTuning:
    def test_devuelve_threshold_entre_0_y_1(self):
        rng = np.random.default_rng(0)
        y_true = rng.integers(0, 2, 100)
        y_proba = rng.random(100)
        resultado = tune_decision_threshold(y_true, y_proba, metric="f1_macro")
        assert "threshold" in resultado
        assert 0 <= resultado["threshold"] <= 1


# ============================================================
# Tests: seleccionar_mejor_modelo
# ============================================================

class TestSeleccionarMejorModelo:
    def test_selecciona_por_score_compuesto(self):
        resultados = [
            {"metrics": {"modelo": "a", "roc_auc": 0.7, "f1_clase_0_impago": 0.3, "pr_auc": 0.5}},
            {"metrics": {"modelo": "b", "roc_auc": 0.6, "f1_clase_0_impago": 0.5, "pr_auc": 0.8}},
        ]
        mejor = seleccionar_mejor_modelo(resultados)
        # Score a: 0.5*0.7 + 0.3*0.3 + 0.2*0.5 = 0.54
        # Score b: 0.5*0.6 + 0.3*0.5 + 0.2*0.8 = 0.61
        assert mejor["metrics"]["modelo"] == "b"


# ============================================================
# Tests: drift metrics
# ============================================================

class TestDriftMetrics:
    def test_ks_distribuciones_iguales(self):
        rng = np.random.default_rng(0)
        s = pd.Series(rng.normal(0, 1, 1000))
        stat, pval = calcular_ks(s, s)
        assert pval > 0.9  # son la misma serie, no debe haber drift

    def test_ks_distribuciones_distintas(self):
        rng = np.random.default_rng(0)
        s1 = pd.Series(rng.normal(0, 1, 1000))
        s2 = pd.Series(rng.normal(5, 1, 1000))  # media muy distinta
        stat, pval = calcular_ks(s1, s2)
        assert pval < 0.01  # drift detectado

    def test_psi_sin_drift(self):
        rng = np.random.default_rng(0)
        s = pd.Series(rng.normal(0, 1, 1000))
        psi = calcular_psi(s, s, n_bins=10)
        assert psi is not None
        assert psi < 0.1

    def test_psi_con_drift_severo(self):
        rng = np.random.default_rng(0)
        s1 = pd.Series(rng.normal(0, 1, 1000))
        s2 = pd.Series(rng.normal(3, 0.5, 1000))
        psi = calcular_psi(s1, s2, n_bins=10)
        assert psi is not None
        assert psi > 0.25  # PSI alto

    def test_js_divergence_simetrica(self):
        rng = np.random.default_rng(0)
        s1 = pd.Series(rng.normal(0, 1, 500))
        s2 = pd.Series(rng.normal(1, 1, 500))
        js_ab = calcular_js_divergence(s1, s2)
        js_ba = calcular_js_divergence(s2, s1)
        assert js_ab is not None
        # JS divergence ES simetrica
        assert abs(js_ab - js_ba) < 0.001

    def test_chi2_categoricas(self):
        s1 = pd.Series(["A"] * 50 + ["B"] * 50)
        s2 = pd.Series(["A"] * 50 + ["B"] * 50)
        chi2, pval = calcular_chi2(s1, s2)
        assert pval > 0.5  # mismas distribuciones, sin drift


# ============================================================
# Tests: clasificar_alerta_psi
# ============================================================

class TestClasificarAlerta:
    def test_psi_bajo_sin_drift(self):
        assert clasificar_alerta_psi(0.05) == "SIN_DRIFT"

    def test_psi_medio_moderado(self):
        assert clasificar_alerta_psi(0.15) == "DRIFT_MODERADO"

    def test_psi_alto_severo(self):
        assert clasificar_alerta_psi(0.30) == "DRIFT_SEVERO"

    def test_psi_none_devuelve_na(self):
        assert clasificar_alerta_psi(None) == "N/A"


# ============================================================
# Tests: split_temporal
# ============================================================

class TestSplitTemporal:
    def test_split_70_30(self):
        df = pd.DataFrame({
            "fecha_prestamo": pd.date_range("2024-01-01", periods=100, freq="D"),
            "valor": range(100),
        })
        hist, act = split_temporal(df, proporcion_historica=0.7)
        assert len(hist) == 70
        assert len(act) == 30
        # historico debe tener fechas mas antiguas
        assert hist["fecha_prestamo"].max() < act["fecha_prestamo"].min()
