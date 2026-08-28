import pandas as pd
from datetime import datetime, timedelta

# File path
CONN_CSV_PATH = r"C:\Users\Blame\Desktop\NET_SECURITY\netlog_combined_connections.csv"

# Output path
OUTPUT_PATH = "context_summary_output.csv"

# Time window for grouping logs (in seconds)
WINDOW_SIZE = 30

def parse_timestamp(ts):
    try:
        return datetime.fromisoformat(ts)
    except:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

def load_connection_data():
    df = pd.read_csv(CONN_CSV_PATH, comment='#')  # Skip comment lines
    df['timestamp'] = df['timestamp'].apply(parse_timestamp)
    return df

def build_summary(conn_df):
    start_time = conn_df['timestamp'].min()
    end_time = conn_df['timestamp'].max()

    current = start_time
    summaries = []

    while current < end_time:
        window_end = current + timedelta(seconds=WINDOW_SIZE)

        conn_window = conn_df[(conn_df['timestamp'] >= current) & (conn_df['timestamp'] < window_end)]

        summary = {
            'start_time': current.isoformat(),
            'end_time': window_end.isoformat(),
            'num_connections': len(conn_window),
            'unique_protocols': conn_window['protocol'].dropna().unique().tolist(),
            'unique_processes': conn_window['process'].dropna().unique().tolist(),
            'unique_remote_ips': list(set([ip.split(':')[0] for ip in conn_window['foreign_address'].dropna().tolist()]))
        }
        summaries.append(summary)
        current = window_end

    return pd.DataFrame(summaries)

def main():
    conn_df = load_connection_data()
    summary_df = build_summary(conn_df)
    summary_df.to_csv(OUTPUT_PATH, index=False)
    print(f"[✓] Summarized connection context saved to {OUTPUT_PATH}")

if __name__ == '__main__':
    main()
