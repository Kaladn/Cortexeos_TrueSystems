"""
Core module for the EventStream.

Acts as a centralized emitter for all system events, providing a single
point of entry for event publication, which is currently backed by the
structured logger.
"""

import logging

class EventStream:
    """A simple event stream that publishes events to the logger."""

    def __init__(self):
        self.logger = logging.getLogger("EventStream")

    def publish(self, event_type: str, source: str, level: str = "INFO", **details):
        """
        Publishes an event to the system's log stream.

        Args:
            event_type: The type of event (e.g., "job.start", "plugin.load").
            source: The component that generated the event (e.g., "616", "PluginManager").
            level: The logging level ("INFO", "WARN", "ERROR", "DEBUG").
            details: A dictionary of arbitrary key-value pairs for context.
        """
        log_level = getattr(logging, level.upper(), logging.INFO)
        # The message is the event_type, details are passed as 'extra'
        # We pass source and details in the 'extra' dict for the formatter
        self.logger.log(log_level, event_type, extra={"source": source, "details": details})

# Global event stream instance to be used throughout the application
event_stream = EventStream()

