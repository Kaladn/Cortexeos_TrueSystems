import pandas as pd
import matplotlib.pyplot as plt
import json

class ReportingLayer:
    def __init__(self, resonance_output):
        self.resonance_output = resonance_output
        self.df = pd.DataFrame(self.flatten_records())

    def flatten_records(self):
        flat_records = []
        for record in self.resonance_output:
            time_anchor = record.get("time_anchor")
            chain_strength = record.get("chain_strength", 0)
            for context in record.get("contextual_resonance", []):
                distance = context.get("distance", 0)
                weight = context.get("weight", 0)
                event = context.get("event", {})

                flat_records.append({
                    "time_anchor": time_anchor,
                    "chain_strength": chain_strength,
                    "distance": distance,
                    "weight": weight,
                    "uplink_mbps": event.get('uplink_mbps', 0),
                    "downlink_mbps": event.get('downlink_mbps', 0),
                    "ping_latency_ms": event.get('ping_latency_ms', 0),
                    "packet_loss_pct": event.get('packet_loss_pct', 0),
                    "mean_ping_ms": event.get('mean_ping_ms', 0),
                    "ping_jitter_ms": event.get('ping_jitter_ms', 0),
                    "obstruction_fraction": event.get('obstruction_fraction', 0),
                    "azimuth_deg": event.get('azimuth_deg', 0),
                    "elevation_deg": event.get('elevation_deg', 0),
                    "throughput_ratio": event.get('throughput_ratio', 0),
                    "latency_loss_index": event.get('latency_loss_index', 0),
                })
        return flat_records

    def plot_chain_strength(self):
        agg_df = self.df.groupby('time_anchor').mean(numeric_only=True).reset_index()
        plt.figure(figsize=(10, 5))
        plt.plot(agg_df['time_anchor'], agg_df['chain_strength'], label='Chain Strength')
        plt.title("CortexOS Resonance Chain Strength Over Time")
        plt.xlabel("Time")
        plt.ylabel("Resonance Strength")
        plt.grid()
        plt.legend()
        plt.tight_layout()
        plt.show()

    def export_to_json(self, output_path="resonance_output.json"):
        self.df.to_json(output_path, orient="records", date_format="iso")

    def summary(self):
        print("\n[CortexOS Report] Lawful Cognition Statistical Summary")
        print(self.df.describe())

    def sovereign_query_summary(self):
        print("\n[CortexOS Sovereign Cognition Summary]")
        try:
            total_frames = len(self.df)
            severe_downtime = round((self.df['packet_loss_pct'] > 99.0).mean() * 100, 4)
            degraded_pct = round((self.df['packet_loss_pct'] > 10.0).mean() * 100, 4)

            degraded_latency = self.df.loc[self.df['packet_loss_pct'] > 10.0, 'ping_latency_ms'].mean()
            degraded_latency = round(degraded_latency if not pd.isna(degraded_latency) else 0, 4)

            longest_bad_run = self._longest_bad_run()

            avg_throughput = round(self.df['throughput_ratio'].mean(), 4)
            avg_chain_strength = round(self.df['chain_strength'].mean(), 4)

            report = {
                "Total Frames": total_frames,
                "Severe Downtime %": severe_downtime,
                "Degraded Connection %": degraded_pct,
                "Avg Latency (Degraded)": degraded_latency,
                "Longest Bad Run (Frames)": longest_bad_run,
                "Avg Throughput Ratio": avg_throughput,
                "Avg Chain Strength": avg_chain_strength
            }

            for k, v in report.items():
                print(f"{k}: {v}")

        except Exception as e:
            print(f"Error in sovereign_query_summary: {e}")

    def plot_query_summary(self):
        try:
            total_frames = len(self.df)
            severe_downtime = round((self.df['packet_loss_pct'] > 99.0).mean() * 100, 4)
            degraded_pct = round((self.df['packet_loss_pct'] > 10.0).mean() * 100, 4)

            degraded_latency = self.df.loc[self.df['packet_loss_pct'] > 10.0, 'ping_latency_ms'].mean()
            degraded_latency = round(degraded_latency if not pd.isna(degraded_latency) else 0, 4)

            longest_bad_run = self._longest_bad_run()

            avg_throughput = round(self.df['throughput_ratio'].mean(), 4)
            avg_chain_strength = round(self.df['chain_strength'].mean(), 4)

            report = {
                "Total Frames": total_frames,
                "Severe Downtime %": severe_downtime,
                "Degraded Connection %": degraded_pct,
                "Avg Latency (Degraded)": degraded_latency,
                "Longest Bad Run (Frames)": longest_bad_run,
                "Avg Throughput Ratio": avg_throughput,
                "Avg Chain Strength": avg_chain_strength
            }

            plt.figure(figsize=(10, 6))
            keys = list(report.keys())
            values = list(report.values())

            plt.barh(keys, values, color='skyblue')
            plt.xlabel("Value")
            plt.title("CortexOS Sovereign Query Summary")
            plt.grid(axis='x')
            plt.tight_layout()
            plt.show()

        except Exception as e:
            print(f"Error in plot_query_summary: {e}")

    def _longest_bad_run(self, threshold=10.0):
        bad_mask = self.df['packet_loss_pct'] > threshold
        return int(bad_mask.groupby((bad_mask != bad_mask.shift()).cumsum()).sum().max())
