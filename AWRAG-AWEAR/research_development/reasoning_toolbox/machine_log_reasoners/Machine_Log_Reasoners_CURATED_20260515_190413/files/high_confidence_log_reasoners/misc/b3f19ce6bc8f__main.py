"""
main.py
Rotational Encryption Fortress: Main script for logging metrics, anomaly detection, and Slack alerts.
- Logs encryption metrics to InfluxDB in real time.
- Queries InfluxDB for metrics analysis.
- Sends alerts for anomalies via Slack.
- Simulates synthetic anomalies for testing.
"""

from influxdb_client import InfluxDBClient, Point
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from datetime import datetime
import os
import logging
import time
import threading

# Load environment variables
# Ensure .env contains InfluxDB and Slack credentials
load_dotenv()

# Configuration and initialization
"""
INFLUXDB CONFIGURATION:
- URL: Your InfluxDB server URL.
- TOKEN: Authentication token for secure access.
- ORG: Organization name configured in InfluxDB.
- BUCKET: Default bucket for metrics storage.
"""
INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

"""
SLACK CONFIGURATION:
- API_TOKEN: Your Slack bot token for sending alerts.
"""
SLACK_API_TOKEN = os.getenv("SLACK_API_TOKEN")

# Initialize InfluxDB and Slack clients
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api()
query_api = client.query_api()
slack_client = WebClient(token=SLACK_API_TOKEN)

# Logging configuration
"""
LOGGING:
- Logs all system activity and errors to system_logs.log.
- Levels: INFO (normal activity), ERROR (failures).
"""
logging.basicConfig(filename='system_logs.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function: log_metrics
"""
Logs encryption metrics to InfluxDB.
- requests: Number of encryption requests processed.
- algorithm: Encryption algorithm used (e.g., AES, ChaCha20).
- cpu_usage: CPU usage during the process (%).
- memory_usage: Memory usage during the process (GB).
- failures: Number of encryption failures.
"""
def log_metrics(requests, algorithm, cpu_usage, memory_usage, failures):
    try:
        point = Point("encryption_metrics") \
            .tag("algorithm", algorithm) \
            .field("requests", requests) \
            .field("cpu_usage", cpu_usage) \
            .field("memory_usage", memory_usage) \
            .field("failures", failures) \
            .time(datetime.utcnow())
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
        logging.info(f"Logged metrics: {algorithm} - {requests} requests.")
    except Exception as e:
        logging.error(f"Error logging metrics: {str(e)}")

# Function: query_metrics
"""
Queries and retrieves metrics from InfluxDB.
- Focus: CPU and memory usage over time.
- Aggregation: Averages data every 5 minutes for better insights.
"""
def query_metrics():
    query = '''
    from(bucket: "metrics_bucket")
      |> range(start: -1h)
      |> filter(fn: (r) => r["_measurement"] == "encryption_metrics")
      |> filter(fn: (r) => r["_field"] == "cpu_usage" or r["_field"] == "memory_usage")
      |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
    '''
    try:
        results = query_api.query(query)
        for table in results:
            for record in table.records:
                print(f"Time: {record.get_time()}, Field: {record.get_field()}, Value: {record.get_value()}")
    except Exception as e:
        logging.error(f"Error querying metrics: {str(e)}")

# Function: send_alert_to_slack
"""
Sends alerts to Slack for critical anomalies.
- level: Severity of the alert (e.g., CRITICAL, WARNING).
- message: Alert message.
"""
def send_alert_to_slack(level, message):
    try:
        response = slack_client.chat_postMessage(channel="#alerts", text=f"{level}: {message}")
        logging.info(f"Slack alert sent: {response['ts']}")
    except SlackApiError as e:
        logging.error(f"Error sending Slack alert: {e.response['error']}")

# Function: simulate_anomalies
"""
Simulates synthetic anomalies for testing.
- Gradually increases CPU usage and failures.
- Triggers Slack alerts for critical anomalies.
"""
def simulate_anomalies():
    for i in range(20):
        requests = 50 + i * 5
        algorithm = "AES" if i % 2 == 0 else "ChaCha20"
        cpu_usage = 70 + (i % 10) * 2
        memory_usage = 2.5 + (i % 3) * 0.5
        failures = 3 if i % 7 == 0 else 0
        log_metrics(requests, algorithm, cpu_usage, memory_usage, failures)

        if failures > 2:
            send_alert_to_slack("CRITICAL", f"High failure rate detected: {failures} failures.")
        time.sleep(2)

# Function: monitor_metrics
"""
Periodically queries InfluxDB for real-time metrics monitoring.
- Interval: Queries every 60 seconds.
"""
def monitor_metrics():
    while True:
        query_metrics()
        time.sleep(60)

# Main Execution
"""
Starts anomaly simulation and monitoring in parallel.
- Threads: Ensures both tasks run without blocking.
"""
if __name__ == "__main__":
    anomaly_thread = threading.Thread(target=simulate_anomalies)
    monitoring_thread = threading.Thread(target=monitor_metrics)

    anomaly_thread.start()
    monitoring_thread.start()

    anomaly_thread.join()
    monitoring_thread.join()
