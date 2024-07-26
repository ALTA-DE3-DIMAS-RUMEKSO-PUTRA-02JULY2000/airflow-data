from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.utils.dates import days_ago
import json


dag = DAG(
        'dimas_alltask2_airflow',
        description='Hello, Ini DAG Tugas 2 Dimas',
        schedule_interval='0 */5 * * *',
        start_date=datetime(2022, 10, 21),
        catchup=False
)
predict_names_task = SimpleHttpOperator(
    task_id='profile_from_gender',
    method='POST',
    http_conn_id='gender_api_dimas',
    endpoint='/gender/by-first-name-multiple',
    headers={"Content-Type": "application/json"},
    data=json.dumps([
  {
    "first_name": "eca",
    "country": "ID"
  },
  {
    "first_name": "dimas",
    "country": "ID"
  }
]),
    response_filter=lambda response: json.loads(response.text),
    log_response=True,
    dag=dag,
)
create_table_task = PostgresOperator(
    task_id='create_table_to_postgres',
    postgres_conn_id='pg_conn_dimas',
    sql="""
    CREATE TABLE IF NOT EXISTS dimas_gender_name_prediction_task2 (
        input JSONB,
        details JSONB,
        result_found BOOLEAN,
        first_name VARCHAR(50),
        probability FLOAT,
        gender VARCHAR(10),
        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    """,
    retries=3,
    retry_delay=timedelta(minutes=5),
    dag=dag,
    autocommit=True,
)
def load_predictions_to_postgres(**kwargs):
    ti = kwargs['ti']
    predictions = ti.xcom_pull(task_ids='profile_from_gender')
    pg_hook = PostgresHook(postgres_conn_id='pg_conn_dimas')
    for prediction in predictions:
        input_data = json.dumps(prediction['input'])
        details_data = json.dumps(prediction['details'])
        result_found = prediction['result_found']
        first_name = prediction['first_name']
        probability = prediction['probability']
        gender = prediction['gender']
        pg_hook.run("""
            INSERT INTO dimas_gender_name_prediction_task2 (input, details, result_found, first_name, probability, gender)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, parameters=(input_data, details_data, result_found, first_name, probability, gender))
load_predictions_task = PythonOperator(
    task_id='profile_gender_to_postgres',
    python_callable=load_predictions_to_postgres,
    provide_context=True,
    dag=dag,
)
predict_names_task >> create_table_task >> load_predictions_task