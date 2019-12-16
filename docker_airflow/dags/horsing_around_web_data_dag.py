from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
# we need to specify an exact function name here; if we tried just a class, it wouldn't work.
from etl_scripts.s3_transformations import horsing_around_web_data_transformations


default_args = {
    'owner': 'dan_friedman',
    'start_date': datetime(2019, 12, 15, 12, 56, 0),
    'depends_on_past': False, # later change this to True and delete CSV logic
    'email': ['dfriedman33@gmail.com'],
    'email_on_failure': False,
    'email_on_retry': False
}

# TODO later change None to "*/2 * * * *" to run every 2 minutes
dag = DAG(
          'horsing_around_s3_web_data_transformations_dag', 
          default_args=default_args, 
          schedule_interval="*/2 * * * *",
          )

horsing_around_s3_web_data_transformations = PythonOperator(
                                                            task_id='horsing_around_web_data_transformations',
                                                            dag=dag,
                                                            python_callable=horsing_around_web_data_transformations
                                                            )