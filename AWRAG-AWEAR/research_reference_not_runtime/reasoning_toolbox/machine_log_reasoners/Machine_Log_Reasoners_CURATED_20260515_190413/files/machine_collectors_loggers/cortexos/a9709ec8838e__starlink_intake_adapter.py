# File: starlink_intake_adapter_v1_1.py

import pandas as pd
import numpy as np
from datetime import datetime

class StarlinkIntakeAdapter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None
        self.time_windows = None

    def load_data(self):
        """
        Load Starlink CSV into memory with proper datetime parsing.
        """
        self.df = pd.read_csv(self.file_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], errors='coerce')
        self.df.dropna(subset=['timestamp'], inplace=True)
        self.df.sort_values(by='timestamp', inplace=True)

    def schema_map(self):
        """
        Return lawful schema mapping of available fields.
        """
        schema = {
            'timestamp': 'Temporal Anchor',
            'uplink': 'Uplink Throughput (Mbps)',
            'downlink': 'Downlink Throughput (Mbps)',
            'pop_ping_latency': 'Ping Latency (ms)',
            'ping_drop': 'Packet Loss (%)',
            'mean_ping_latency': 'Mean Ping (ms)',
            'ping_stdvar': 'Ping Std Dev (Jitter)',
            'fraction_obstructed': 'Obstruction Fraction',
            'direction_azimuth': 'Satellite Azimuth (deg)',
            'direction_elevation': 'Satellite Elevation (deg)'
        }
        return schema

    def window_slicer(self, window_minutes=5):
        """
        Segment data into lawful time windows for resonance analysis.
        """
        self.df.set_index('timestamp', inplace=True)
        self.time_windows = self.df.resample(f'{window_minutes}min').agg({
            'uplink': 'mean',
            'downlink': 'mean',
            'pop_ping_latency': 'mean',
            'ping_drop': 'mean',
            'mean_ping_latency': 'mean',
            'ping_stdvar': 'mean',
            'fraction_obstructed': 'mean',
            'direction_azimuth': 'mean',
            'direction_elevation': 'mean'
        }).dropna().reset_index()
        return self.time_windows

    def lawful_records(self):
        """
        Output lawful ingestion records ready for resonance engine.
        """
        lawful_events = []
        for _, row in self.time_windows.iterrows():
            event = {
                'time_anchor': row['timestamp'],
                'signals': {
                    'uplink': row['uplink'],
                    'downlink': row['downlink'],
                    'pop_ping_latency': row['pop_ping_latency'],
                    'ping_drop': row['ping_drop'],
                    'mean_ping_latency': row['mean_ping_latency'],
                    'ping_stdvar': row['ping_stdvar'],
                    'fraction_obstructed': row['fraction_obstructed'],
                    'direction_azimuth': row['direction_azimuth'],
                    'direction_elevation': row['direction_elevation']
                }
            }
            lawful_events.append(event)
        return lawful_events
