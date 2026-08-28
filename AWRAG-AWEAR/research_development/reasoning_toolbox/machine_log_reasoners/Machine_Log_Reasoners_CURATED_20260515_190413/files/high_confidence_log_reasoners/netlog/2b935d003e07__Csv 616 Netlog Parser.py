import pandas as pd
import ipaddress
from pathlib import Path
from datetime import datetime

CSV_FILE_PATH = 'netstat_logs/netstat_log.csv'

KNOWN_GOOD_IPV6_PREFIXES = [
    "2603:", "2607:", "2606:", "2600:", "2a04:"
]
COMMON_PORTS = {'80', '443'}

def is_known_good_ip(ip_str):
    try:
        ip_obj = ipaddress.ip_address(ip_str.strip("[]"))
        if ip_obj.is_loopback or ip_obj.is_private:
            return True
        return any(ip_str.startswith(prefix) for prefix in KNOWN_GOOD_IPV6_PREFIXES)
    except ValueError:
        return False

def is_common_port(addr):
    try:
        port = addr.split(':')[-1]
        return port in COMMON_PORTS
    except:
        return False

def is_anomalous(row):
    local_ip = row['local_address'].split(':')[0]
    foreign_ip = row['foreign_address'].split(':')[0]
    if is_known_good_ip(local_ip) and is_known_good_ip(foreign_ip):
        return False
    if is_known_good_ip(foreign_ip) and is_common_port(row['foreign_address']):
        return False
    return True

def load_netstat_csv(path):
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def analyze_netstat_df(df):
    df['anomalous'] = df.apply(is_anomalous, axis=1)
    return df

def save_anomalies(df):
    anomalies = df[df['anomalous']]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"anomalies/anomalies_{timestamp}.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    anomalies.to_csv(output_path, index=False)
    print(f"[✓] Anomalies found: {len(anomalies)} saved to {output_path}")

def run_cascade_netstat_analysis():
    df = load_netstat_csv(CSV_FILE_PATH)
    df = analyze_netstat_df(df)
    save_anomalies(df)

if __name__ == '__main__':
    run_cascade_netstat_analysis()
