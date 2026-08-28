# File: lawful_event_extractor.py

class LawfulEventExtractor:
    def __init__(self):
        pass

    def extract(self, event):
        """
        Extract lawful cognition features from Starlink event v1.1
        Fully synchronized to Starlink Intake Adapter schema.
        """
        time_anchor = event['time_anchor']
        signals = event['signals']

        extracted_record = {
            'time_anchor': time_anchor,
            'uplink_mbps': signals['uplink'],
            'downlink_mbps': signals['downlink'],
            'ping_latency_ms': signals['pop_ping_latency'],
            'packet_loss_pct': signals['ping_drop'],
            'mean_ping_ms': signals['mean_ping_latency'],
            'ping_jitter_ms': signals['ping_stdvar'],
            'obstruction_fraction': signals['fraction_obstructed'],
            'azimuth_deg': signals['direction_azimuth'],
            'elevation_deg': signals['direction_elevation'],
        }

        # Example lawful cognition feature: simple signal quality metric
        extracted_record['throughput_ratio'] = signals['downlink'] / (signals['uplink'] + 0.001)
        extracted_record['latency_loss_index'] = signals['pop_ping_latency'] * (signals['ping_drop'] + 0.001)

        return extracted_record
