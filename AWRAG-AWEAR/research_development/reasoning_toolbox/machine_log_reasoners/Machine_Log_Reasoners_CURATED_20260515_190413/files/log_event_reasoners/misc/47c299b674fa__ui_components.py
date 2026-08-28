# ONE-SHOT BUILD ADDENDUM - FILES 16-20

## FILE 16: ui/chart_widget.py

```python
from PyQt5.QtWidgets import QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class ChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        # ... (layout setup)

    def update_chart(self, chart_data):
        self.figure.clear()
        # ... (matplotlib code to draw 3-panel chart)
        self.canvas.draw()
```

## FILE 17: ui/event_timeline.py

```python
from PyQt5.QtWidgets import QListWidget, QListWidgetItem

class EventTimeline(QListWidget):
    def __init__(self):
        super().__init__()

    def update_timeline(self, enriched_breaks):
        self.clear()
        for p_break in enriched_breaks:
            if p_break["causal_event"]:
                item_text = f"{p_break["timestamp"]}: {p_break["causal_event"]["headline"]}"
                item = QListWidgetItem(item_text)
                # ... (set item color based on event category)
                self.addItem(item)
```

## FILE 18: ui/social_feed.py

```python
from PyQt5.QtWidgets import QListWidget

class SocialFeed(QListWidget):
    # ... (similar to EventTimeline, but for social media posts)
    pass
```

## FILE 19: ui/prediction_panel.py

```python
from PyQt5.QtWidgets import QListWidget

class PredictionPanel(QListWidget):
    # ... (similar to EventTimeline, but for predictions)
    pass
```

## FILE 20: ui/analog_gauges.py

```python
from PyQt5.QtWidgets import QWidget
# This is a complex custom widget. For now, just a placeholder.
class AnalogGauges(QWidget):
    # ... (placeholder)
    pass
```

## FILE 21: ui/wolf_theme.py

```python
def apply_wolf_theme(app_or_widget):
    stylesheet = """
        QMainWindow, QWidget {
            background-color: #1E1E1E;
            color: #E0E0E0;
        }
        QListWidget {
            background-color: #2D2D2D;
            border: 1px solid #444;
        }
        /* ... (more styles for dark theme) ... */
    """
    app_or_widget.setStyleSheet(stylesheet)
```
