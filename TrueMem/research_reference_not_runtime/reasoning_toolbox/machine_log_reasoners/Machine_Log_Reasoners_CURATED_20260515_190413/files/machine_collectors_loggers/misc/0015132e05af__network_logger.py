import psutil
import socket
import csv
import time
import os
from datetime import datetime
from scapy.all import sniff, IP, TCP, UDP
import threading
from rich.live import Live
from rich.table import Table
from rich.console import Console

# Settings
LOG_INTERVAL = 10  # seconds
CSV_CONN_FILE = 'netlog_combined_connections.csv'
CSV_PKT_FILE = 'netlog_combined_packets.csv'
console = Console()


def get_process_name(pid):
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return 'Unknown'


def get_netstat_snapshot():
    snapshot = []
    for conn in psutil.net_connections(kind='inet'):
        if conn.status != psutil.CONN_NONE and conn.raddr:
            local_ip = f"{conn.laddr.ip}:{conn.laddr.port}"
            remote_ip = f"{conn.raddr.ip}:{conn.raddr.port}"
            protocol = 'TCP' if conn.type == socket.SOCK_STREAM else 'UDP'
            snapshot.append({
                'timestamp': datetime.utcnow().isoformat(),
                'protocol': protocol,
                'local_address': local_ip,
                'foreign_address': remote_ip,
                'state': conn.status,
                'pid': conn.pid,
                'process': get_process_name(conn.pid)
            })
    return snapshot


def write_snapshot_to_csv(snapshot):
    file_exists = os.path.exists(CSV_CONN_FILE)

    with open(CSV_CONN_FILE, mode='a', newline='', encoding='utf-8') as file:
        fieldnames = ['timestamp', 'protocol', 'local_address', 'foreign_address', 'state', 'pid', 'process']
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({'timestamp': f"# --- New Run: {datetime.utcnow().isoformat()} ---"})
        for entry in snapshot:
            writer.writerow(entry)


def packet_callback(pkt):
    try:
        timestamp = datetime.utcnow().isoformat()
        proto = 'TCP' if TCP in pkt else 'UDP' if UDP in pkt else 'OTHER'
        src_ip = pkt[IP].src if IP in pkt else 'N/A'
        dst_ip = pkt[IP].dst if IP in pkt else 'N/A'
        src_port = pkt.sport if hasattr(pkt, 'sport') else 'N/A'
        dst_port = pkt.dport if hasattr(pkt, 'dport') else 'N/A'
        pkt_len = len(pkt)

        file_exists = os.path.exists(CSV_PKT_FILE)
        with open(CSV_PKT_FILE, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['timestamp', 'protocol', 'src_ip', 'src_port', 'dst_ip', 'dst_port', 'packet_length'])
            writer.writerow([timestamp, proto, src_ip, src_port, dst_ip, dst_port, pkt_len])
    except Exception:
        pass


def initialize_packet_logger():
    sniff(prn=packet_callback, store=False)


def main():
    console.print("[*] Starting hybrid logger: connections + packet sniffing...", style="bold green")
    threading.Thread(target=initialize_packet_logger, daemon=True).start()

    total_logs = 0
    with Live(refresh_per_second=2) as live:
        while True:
            snapshot = get_netstat_snapshot()
            total_logs += len(snapshot)
            write_snapshot_to_csv(snapshot)

            table = Table(title="Live Connection Logger", expand=True)
            table.add_column("Metric", style="cyan", no_wrap=True)
            table.add_column("Value", style="magenta")
            table.add_row("This Interval", str(len(snapshot)))
            table.add_row("Total Logs", str(total_logs))
            table.add_row("Time", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
            live.update(table)

            time.sleep(LOG_INTERVAL)


if __name__ == '__main__':
    main()
