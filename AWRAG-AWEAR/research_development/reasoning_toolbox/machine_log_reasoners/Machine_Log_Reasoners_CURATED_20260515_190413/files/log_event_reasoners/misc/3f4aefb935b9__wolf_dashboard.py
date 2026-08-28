# ONE-SHOT BUILD ADDENDUM - FILE 15

## FILE 15: ui/wolf_dashboard.py

### COPILOT INSTRUCTIONS:
**Create the main PyQt5 dashboard window with a wolf theme.**

**PSEUDOCODE:**

```python
"""
Wolf Dashboard - Main UI Window
Displays all analysis, charts, feeds, and predictions.
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

# Import other UI components
from ui.chart_widget import ChartWidget
from ui.event_timeline import EventTimeline
from ui.social_feed import SocialFeed
from ui.prediction_panel import PredictionPanel
from ui.analog_gauges import AnalogGauges
from ui.wolf_theme import apply_wolf_theme

class WolfDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CompuCog - The Wolf Oracle")
        self.setGeometry(100, 100, 1600, 900)

        # Apply wolf theme
        apply_wolf_theme(self)

        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- Left Panel (Charts & Gauges) ---
        left_panel = QVBoxLayout()
        self.chart_widget = ChartWidget()
        self.analog_gauges = AnalogGauges()
        left_panel.addWidget(self.chart_widget)
        left_panel.addWidget(self.analog_gauges)
        main_layout.addLayout(left_panel, 70) # 70% width

        # --- Right Panel (Feeds & Predictions) ---
        right_panel = QVBoxLayout()
        self.event_timeline = EventTimeline()
        self.social_feed = SocialFeed()
        self.prediction_panel = PredictionPanel()
        right_panel.addWidget(self.event_timeline)
        right_panel.addWidget(self.social_feed)
        right_panel.addWidget(self.prediction_panel)
        main_layout.addLayout(right_panel, 30) # 30% width

        # --- Wolf Logo ---
        logo_label = QLabel(self)
        pixmap = QPixmap("assets/wolf_logo.png")
        logo_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio))
        logo_label.setAlignment(Qt.AlignTop | Qt.AlignRight)
        # Position logo in top-right corner

    def update_data(self, analysis_results):
        """
        UPDATE ALL UI WIDGETS WITH NEW DATA:

        ALGORITHM:
            1. self.chart_widget.update_chart(analysis_results["chart_data"])
            2. self.analog_gauges.update_gauges(analysis_results["metrics"])
            3. self.event_timeline.update_timeline(analysis_results["enriched_breaks"])
            4. self.social_feed.update_feed(analysis_results["social_signals"])
            5. self.prediction_panel.update_predictions(analysis_results["predictions"])
        """
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dashboard = WolfDashboard()
    dashboard.show()
    sys.exit(app.exec_())

```

**COPILOT: Implement using PyQt5. Create a placeholder for each custom widget for now. The main goal is to get the layout and theme working.**
