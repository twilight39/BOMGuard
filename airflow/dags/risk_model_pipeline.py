"""Airflow DAG for weekly ML risk model retraining."""

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator


def refresh_substance_database() -> None:
    pass


def enrich_missing_features() -> None:
    pass


def train_for_regulation(regulation_id: str) -> None:
    pass


def evaluate_all_models() -> None:
    pass


def promote_if_gates_pass(min_roc_auc: float = 0.75) -> None:
    pass


def generate_evidently_report() -> None:
    pass


def invalidate_risk_cache() -> None:
    pass


with DAG(
    "risk_model_pipeline",
    schedule_interval="@weekly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:
    t1 = PythonOperator(
        task_id="refresh_substances",
        python_callable=refresh_substance_database,
    )
    t2 = PythonOperator(
        task_id="enrich_features",
        python_callable=enrich_missing_features,
    )
    t3 = PythonOperator(
        task_id="train_reach_model",
        python_callable=lambda: train_for_regulation("eu_reach_svhc"),
    )
    t4 = PythonOperator(
        task_id="train_pfas_model",
        python_callable=lambda: train_for_regulation("us_state_pfas"),
    )
    t5 = PythonOperator(
        task_id="evaluate",
        python_callable=evaluate_all_models,
    )
    t6 = PythonOperator(
        task_id="promote",
        python_callable=promote_if_gates_pass,
        op_kwargs={"min_roc_auc": 0.75},
    )
    t7 = PythonOperator(
        task_id="drift_check",
        python_callable=generate_evidently_report,
    )
    t8 = PythonOperator(
        task_id="invalidate_cache",
        python_callable=invalidate_risk_cache,
    )

    t1 >> t2 >> [t3, t4] >> t5 >> t6 >> t8
    t6 >> t7
