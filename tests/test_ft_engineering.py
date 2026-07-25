"""
tests/test_ft_engineering.py
=============================
Tests unitarios para el modulo de feature engineering.
Para correr:
    pytest tests/ -v --cov=mlops_pipeline/src --cov-report=xml --cov-report=term
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Permitir importar desde mlops_pipeline/src/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mlops_pipeline" / "src"))

from ft_engineering import (
    build_derived_features,
    build_preprocessor,
    get_feature_columns,
    COLUMNAS_LEAKAGE,
    ORDEN_TENDENCIA,
    prepare_dataset,
)


# ============================================================
# Fixture: dataframe sintetico de prueba
# ============================================================

@pytest.fixture
def df_dummy():
    """DataFrame minimo con las columnas esperadas para feature engineering."""
    n = 100
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "tipo_credito": rng.integers(1, 10, n),
        "fecha_prestamo": pd.date_range("2024-01-01", periods=n, freq="D"),
        "capital_prestado": rng.uniform(500_000, 10_000_000, n),
        "plazo_meses": rng.integers(6, 60, n),
        "edad_cliente": rng.integers(20, 70, n),
        "tipo_laboral": rng.choice(["Empleado", "Independiente"], n),
        "salario_cliente": rng.uniform(1_000_000, 8_000_000, n),
        "total_otros_prestamos": rng.uniform(0, 3_000_000, n),
        "cuota_pactada": rng.uniform(100_000, 800_000, n),
        "puntaje_datacredito": rng.uniform(400, 900, n),
        "cant_creditosvigentes": rng.integers(0, 10, n),
        "huella_consulta": rng.integers(0, 8, n),
        "creditos_sectorFinanciero": rng.integers(0, 5, n),
        "creditos_sectorCooperativo": rng.integers(0, 3, n),
        "creditos_sectorReal": rng.integers(0, 3, n),
        "promedio_ingresos_datacredito": rng.uniform(500_000, 5_000_000, n),
        "tendencia_ingresos": rng.choice(ORDEN_TENDENCIA, n),
        "Pago_atiempo": rng.choice([0, 1], n, p=[0.05, 0.95]),
    })
    df["tipo_laboral"] = df["tipo_laboral"].astype("category")
    df["tendencia_ingresos"] = pd.Categorical(df["tendencia_ingresos"],
                                               categories=ORDEN_TENDENCIA, ordered=True)
    df["tipo_credito"] = df["tipo_credito"].astype("category")
    return df


# ============================================================
# Tests: build_derived_features
# ============================================================

class TestBuildDerivedFeatures:
    def test_agrega_ratios_financieros(self, df_dummy):
        df_out = build_derived_features(df_dummy)
        assert "ratio_cuota_salario" in df_out.columns
        assert "ratio_capital_salario" in df_out.columns
        assert "ratio_otros_salario" in df_out.columns
        assert "endeudamiento_total" in df_out.columns

    def test_agrega_banderas_booleanas(self, df_dummy):
        df_out = build_derived_features(df_dummy)
        assert "tiene_historial_datacredito" in df_out.columns
        assert "multiples_sectores" in df_out.columns
        # Tipos correctos
        assert df_out["tiene_historial_datacredito"].dtype == int

    def test_agrega_variables_temporales(self, df_dummy):
        df_out = build_derived_features(df_dummy)
        assert "anio_prestamo" in df_out.columns
        assert "mes_prestamo" in df_out.columns
        assert (df_out["anio_prestamo"] == 2024).all()

    def test_no_modifica_original(self, df_dummy):
        cols_originales = df_dummy.columns.tolist()
        _ = build_derived_features(df_dummy)
        assert df_dummy.columns.tolist() == cols_originales

    def test_ratios_son_numericos(self, df_dummy):
        df_out = build_derived_features(df_dummy)
        assert pd.api.types.is_numeric_dtype(df_out["ratio_cuota_salario"])
        assert pd.api.types.is_numeric_dtype(df_out["endeudamiento_total"])


# ============================================================
# Tests: get_feature_columns
# ============================================================

class TestGetFeatureColumns:
    def test_devuelve_diccionario(self, df_dummy):
        df_out = build_derived_features(df_dummy)
        cols = get_feature_columns(df_out)
        assert isinstance(cols, dict)
        assert "numericas_continuas" in cols
        assert "numericas_discretas" in cols
        assert "categoricas_nominales" in cols
        assert "categoricas_ordinales" in cols

    def test_excluye_leakage_y_target(self, df_dummy):
        df_out = build_derived_features(df_dummy)
        cols = get_feature_columns(df_out)
        todas = (cols["numericas_continuas"] + cols["numericas_discretas"]
                 + cols["categoricas_nominales"] + cols["categoricas_ordinales"])
        # No incluye target
        assert "Pago_atiempo" not in todas
        # No incluye leakage (puntaje, saldos)
        for col_leak in COLUMNAS_LEAKAGE:
            assert col_leak not in todas
        # No incluye fecha_prestamo cruda
        assert "fecha_prestamo" not in todas

    def test_categorica_ordinal_incluye_tendencia(self, df_dummy):
        df_out = build_derived_features(df_dummy)
        cols = get_feature_columns(df_out)
        assert "tendencia_ingresos" in cols["categoricas_ordinales"]


# ============================================================
# Tests: build_preprocessor
# ============================================================

class TestBuildPreprocessor:
    def test_construye_columntransformer(self, df_dummy):
        df_out = build_derived_features(df_dummy)
        cols = get_feature_columns(df_out)
        prep = build_preprocessor(cols)
        # Debe tener 3 transformers: num, nom, ord
        assert len(prep.transformers) == 3
        nombres = [t[0] for t in prep.transformers]
        assert "num" in nombres
        assert "nom" in nombres
        assert "ord" in nombres

    def test_fit_y_transform(self, df_dummy):
        df_out = build_derived_features(df_dummy)
        cols = get_feature_columns(df_out)
        prep = build_preprocessor(cols)
        todas = (cols["numericas_continuas"] + cols["numericas_discretas"]
                 + cols["categoricas_nominales"] + cols["categoricas_ordinales"])
        X = df_out[todas]
        X_t = prep.fit_transform(X)
        # Debe producir una matriz 2D con misma cantidad de filas
        assert X_t.shape[0] == len(df_out)
        # Debe haber MAS columnas post-OHE que pre-procesamiento (por OneHotEncoder)
        assert X_t.shape[1] >= len(todas) - len(cols["categoricas_nominales"])

    def test_get_feature_names_out(self, df_dummy):
        df_out = build_derived_features(df_dummy)
        cols = get_feature_columns(df_out)
        prep = build_preprocessor(cols)
        todas = (cols["numericas_continuas"] + cols["numericas_discretas"]
                 + cols["categoricas_nominales"] + cols["categoricas_ordinales"])
        prep.fit(df_out[todas])
        names = prep.get_feature_names_out()
        assert len(names) > 0
        # Las numericas mantienen nombre
        for c in cols["numericas_continuas"][:3]:
            assert c in names


# ============================================================
# Tests: leakage exclusion (test critico de logica de negocio)
# ============================================================

def test_puntaje_es_leakage():
    """Validacion explicita: 'puntaje' debe estar en COLUMNAS_LEAKAGE."""
    assert "puntaje" in COLUMNAS_LEAKAGE, "puntaje no fue identificado como leakage"


def test_saldos_son_leakage():
    """Las 4 variables de saldo deben estar marcadas como leakage."""
    saldos = ["saldo_mora", "saldo_total", "saldo_principal", "saldo_mora_codeudor"]
    for s in saldos:
        assert s in COLUMNAS_LEAKAGE, f"{s} no fue identificado como leakage"


def test_puntaje_datacredito_no_es_leakage():
    """puntaje_datacredito (score externo del buro) SI debe usarse."""
    assert "puntaje_datacredito" not in COLUMNAS_LEAKAGE, (
        "puntaje_datacredito es legitimo y no debe excluirse"
    )
