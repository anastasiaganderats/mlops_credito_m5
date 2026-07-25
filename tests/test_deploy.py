"""
tests/test_deploy.py
=====================
Tests para el endpoint FastAPI de prediccion.
Usa fastapi.testclient para invocar los endpoints sin levantar servidor real.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mlops_pipeline" / "src"))

import model_deploy
model_deploy.cargar_modelo()
client = TestClient(model_deploy.app)


CLIENTE_EJEMPLO = {
    "tipo_credito": 4,
    "fecha_prestamo": "2026-05-15",
    "capital_prestado": 5_000_000.0,
    "plazo_meses": 24,
    "edad_cliente": 35,
    "tipo_laboral": "Empleado",
    "salario_cliente": 3_500_000.0,
    "total_otros_prestamos": 1_500_000.0,
    "cuota_pactada": 250_000.0,
    "puntaje_datacredito": 780.0,
    "cant_creditosvigentes": 3,
    "huella_consulta": 2,
    "creditos_sectorFinanciero": 2,
    "creditos_sectorCooperativo": 0,
    "creditos_sectorReal": 1,
    "promedio_ingresos_datacredito": 3_200_000.0,
    "tendencia_ingresos": "Estable",
}


class TestEndpointBasicos:
    def test_root_ok(self):
        r = client.get("/")
        assert r.status_code == 200
        body = r.json()
        assert "app" in body
        assert "endpoints" in body

    def test_health_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"
        assert r.json()["modelo_cargado"] is True

    def test_model_info(self):
        r = client.get("/model_info")
        assert r.status_code == 200
        body = r.json()
        assert "modelo_tipo" in body
        assert "n_features_esperadas" in body
        assert "threshold_decision" in body
        assert body["n_features_esperadas"] > 0


class TestPredict:
    def test_predict_devuelve_estructura_correcta(self):
        r = client.post("/predict", json=CLIENTE_EJEMPLO)
        assert r.status_code == 200
        body = r.json()
        assert "prediccion" in body
        assert "probabilidad_pago" in body
        assert "probabilidad_impago" in body
        assert "threshold_aplicado" in body
        assert "interpretacion" in body
        assert body["prediccion"] in [0, 1]
        assert 0 <= body["probabilidad_pago"] <= 1
        assert abs(body["probabilidad_pago"] + body["probabilidad_impago"] - 1) < 0.01

    def test_predict_rechaza_edad_invalida(self):
        invalido = dict(CLIENTE_EJEMPLO)
        invalido["edad_cliente"] = 15  # menor de 18
        r = client.post("/predict", json=invalido)
        assert r.status_code == 422  # validation error de Pydantic

    def test_predict_rechaza_tipo_laboral_invalido(self):
        invalido = dict(CLIENTE_EJEMPLO)
        invalido["tipo_laboral"] = "Estudiante"  # no permitido
        r = client.post("/predict", json=invalido)
        assert r.status_code == 422

    def test_predict_rechaza_salario_negativo(self):
        invalido = dict(CLIENTE_EJEMPLO)
        invalido["salario_cliente"] = -1000  # negativo
        r = client.post("/predict", json=invalido)
        assert r.status_code == 422


class TestPredictBatch:
    def test_batch_3_clientes(self):
        payload = {"clientes": [CLIENTE_EJEMPLO, CLIENTE_EJEMPLO, CLIENTE_EJEMPLO]}
        r = client.post("/predict_batch", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["n_predicciones"] == 3
        assert len(body["predicciones"]) == 3
        assert "resumen" in body
        assert body["resumen"]["total"] == 3

    def test_batch_vacio_rechazado(self):
        r = client.post("/predict_batch", json={"clientes": []})
        assert r.status_code == 422
