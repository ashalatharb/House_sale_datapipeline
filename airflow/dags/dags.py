from datetime import datetime, timedelta
import json

from airflow import DAG
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.python import PythonOperator

from utils import _local_to_s3, run_redshift_external_query , extract_places

# Config
BUCKET_NAME = Variable.get("BUCKET")


# DAG definition
default_args = {
    "owner": "airflow",
    "depends_on_past": True,
    "wait_for_downstream": True,
    "start_date": datetime(2021, 8, 27),
    "email": ["dummy@bigdummy.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

dag = DAG(
    "house_sales",
    default_args=default_args,
    schedule_interval="@daily",
    max_active_runs=1,
)

load_sales_data_to_stage = PythonOperator(
    dag=dag,
    task_id="load_sales_data",
    python_callable=_local_to_s3,
    op_kwargs={
        }
)

create_new_zipcode_list = PythonOperator(
    dag=dag,
    task_id="create_newzipcode_list",
    python_callable=_local_to_s3,
    op_kwargs={
    },
)


extract_neighbourhood_info = PythonOperator(
    dag=dag,
    task_id="extract_neighbourhood_info",
    python_callable=extract_places,
    op_kwargs={
    },
)


load_to_target = PostgresOperator(
    dag=dag,
    task_id="load_to_target",
    sql="redshift_setup.sql",
    postgres_conn_id="redshift",
)

end_of_data_pipeline = DummyOperator(task_id="end_of_data_pipeline", dag=dag)

load_sales_data_to_stage >> create_new_zipcode_list >> \
    extract_neighbourhood_info >> load_to_target >> end_of_data_pipeline
