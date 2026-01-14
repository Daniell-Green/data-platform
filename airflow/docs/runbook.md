### Airflow DAGs not appearing
Cause: scheduler cannot write to /opt/airflow/logs (host-mounted volume)

Fix:
```
sudo chown -R 50000:0 airflow/logs
sudo chmod -R 775 airflow/logs
```