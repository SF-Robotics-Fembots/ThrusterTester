"""
Test execution frame with live monitoring and graphs.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, List

try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from ..data.models import TestPoint, TestStatus


class TestFrame(ttk.Frame):
    """
    Frame for test execution and live monitoring.

    Includes:
    - Start/Stop/Pause controls
    - Progress bar
    - Live sensor readings
    - Real-time thrust vs PWM graph
    """

    def __init__(self, parent):
        super().__init__(parent)

        self._on_start: Optional[Callable[[], None]] = None
        self._on_stop: Optional[Callable[[], None]] = None
        self._on_pause: Optional[Callable[[], None]] = None
        self._on_resume: Optional[Callable[[], None]] = None
        self._on_emergency_stop: Optional[Callable[[], None]] = None

        self._test_points: List[TestPoint] = []
        self._is_running = False
        self._is_paused = False

        self._create_widgets()

    def _create_widgets(self):
        """Create test execution widgets."""
        # Main container
        container = ttk.Frame(self, padding="10")
        container.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(container, text="Test Execution",
                          font=('TkDefaultFont', 14, 'bold'))
        title.pack(anchor=tk.W, pady=(0, 10))

        # Control buttons
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill=tk.X, pady=5)

        self.start_btn = ttk.Button(btn_frame, text="Start Test",
                                     command=self._on_start_click)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.pause_btn = ttk.Button(btn_frame, text="Pause",
                                     command=self._on_pause_click, state='disabled')
        self.pause_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="Stop",
                                    command=self._on_stop_click, state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.emergency_btn = ttk.Button(btn_frame, text="EMERGENCY STOP",
                                         command=self._on_emergency_click,
                                         style='Emergency.TButton')
        self.emergency_btn.pack(side=tk.RIGHT, padx=5)

        # Style for emergency button
        style = ttk.Style()
        style.configure('Emergency.TButton', foreground='red')

        # Progress bar
        progress_frame = ttk.LabelFrame(container, text="Progress", padding="5")
        progress_frame.pack(fill=tk.X, pady=5)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame,
                                             variable=self.progress_var,
                                             maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)

        self.progress_label = ttk.Label(progress_frame, text="Ready")
        self.progress_label.pack(anchor=tk.W, padx=5)

        # Live readings
        readings_frame = ttk.LabelFrame(container, text="Live Readings", padding="5")
        readings_frame.pack(fill=tk.X, pady=5)

        # Create reading displays in grid
        readings_grid = ttk.Frame(readings_frame)
        readings_grid.pack(fill=tk.X, padx=5, pady=5)

        # PWM
        ttk.Label(readings_grid, text="PWM:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.pwm_label = ttk.Label(readings_grid, text="---- us",
                                    font=('TkFixedFont', 12))
        self.pwm_label.grid(row=0, column=1, sticky=tk.W, padx=5)

        # Voltage
        ttk.Label(readings_grid, text="Voltage:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.voltage_label = ttk.Label(readings_grid, text="--.- V",
                                        font=('TkFixedFont', 12))
        self.voltage_label.grid(row=0, column=3, sticky=tk.W, padx=5)

        # Current
        ttk.Label(readings_grid, text="Current:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.current_label = ttk.Label(readings_grid, text="--.- A",
                                        font=('TkFixedFont', 12))
        self.current_label.grid(row=1, column=1, sticky=tk.W, padx=5)

        # Power
        ttk.Label(readings_grid, text="Power:").grid(row=1, column=2, sticky=tk.W, padx=5)
        self.power_label = ttk.Label(readings_grid, text="--.- W",
                                      font=('TkFixedFont', 12))
        self.power_label.grid(row=1, column=3, sticky=tk.W, padx=5)

        # Thrust
        ttk.Label(readings_grid, text="Thrust:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.thrust_label = ttk.Label(readings_grid, text="-.--- kg",
                                       font=('TkFixedFont', 12, 'bold'))
        self.thrust_label.grid(row=2, column=1, columnspan=3, sticky=tk.W, padx=5)

        # Graph
        if MATPLOTLIB_AVAILABLE:
            self._create_graph(container)
        else:
            graph_placeholder = ttk.LabelFrame(container, text="Graph", padding="5")
            graph_placeholder.pack(fill=tk.BOTH, expand=True, pady=5)
            ttk.Label(graph_placeholder,
                      text="Matplotlib not available - graph disabled").pack()

    def _create_graph(self, parent):
        """Create matplotlib graph for thrust vs PWM."""
        graph_frame = ttk.LabelFrame(parent, text="Thrust vs PWM", padding="5")
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Create figure
        self.fig = Figure(figsize=(5, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('PWM (us)')
        self.ax.set_ylabel('Thrust (kg)')
        self.ax.grid(True, alpha=0.3)
        self.ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)

        # Create line for data
        self.line, = self.ax.plot([], [], 'b-', linewidth=1.5)

        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _on_start_click(self):
        """Handle start button click."""
        if self._on_start:
            self._on_start()

    def _on_stop_click(self):
        """Handle stop button click."""
        if self._on_stop:
            self._on_stop()

    def _on_pause_click(self):
        """Handle pause/resume button click."""
        if self._is_paused:
            if self._on_resume:
                self._on_resume()
        else:
            if self._on_pause:
                self._on_pause()

    def _on_emergency_click(self):
        """Handle emergency stop button click."""
        if self._on_emergency_stop:
            self._on_emergency_stop()

    def set_callbacks(self,
                      on_start: Optional[Callable[[], None]] = None,
                      on_stop: Optional[Callable[[], None]] = None,
                      on_pause: Optional[Callable[[], None]] = None,
                      on_resume: Optional[Callable[[], None]] = None,
                      on_emergency_stop: Optional[Callable[[], None]] = None):
        """Set callback functions for button actions."""
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_pause = on_pause
        self._on_resume = on_resume
        self._on_emergency_stop = on_emergency_stop

    def update_status(self, status: TestStatus):
        """Update display with current test status."""
        self._is_running = status.is_running
        self._is_paused = status.is_paused

        # Update progress
        self.progress_var.set(status.progress_percent)

        if status.error_message:
            self.progress_label.config(text=f"Error: {status.error_message}")
        elif status.is_paused:
            self.progress_label.config(text=f"Paused at {status.current_pwm_us} us")
        elif status.is_running:
            self.progress_label.config(
                text=f"Testing: {status.current_pwm_us} us ({status.progress_percent:.1f}%)")
        else:
            self.progress_label.config(text="Ready")

        # Update readings
        self.pwm_label.config(text=f"{status.current_pwm_us} us")

        if status.current_point:
            self.update_readings(status.current_point)

        # Update buttons
        self._update_buttons()

    def update_readings(self, point: TestPoint):
        """Update live reading displays."""
        self.pwm_label.config(text=f"{point.pwm_us} us")
        self.voltage_label.config(text=f"{point.voltage_v:.2f} V")
        self.current_label.config(text=f"{point.current_a:.2f} A")
        self.power_label.config(text=f"{point.power_w:.1f} W")
        self.thrust_label.config(text=f"{point.thrust_kg:.3f} kg")

    def add_data_point(self, point: TestPoint):
        """Add a data point to the graph."""
        self._test_points.append(point)
        self._update_graph()

    def _update_graph(self):
        """Update the graph with current data."""
        if not MATPLOTLIB_AVAILABLE:
            return

        if not self._test_points:
            return

        pwm_values = [p.pwm_us for p in self._test_points]
        thrust_values = [p.thrust_kg for p in self._test_points]

        self.line.set_data(pwm_values, thrust_values)

        # Auto-scale axes
        self.ax.relim()
        self.ax.autoscale_view()

        self.canvas.draw_idle()

    def clear_graph(self):
        """Clear graph data."""
        self._test_points = []
        if MATPLOTLIB_AVAILABLE:
            self.line.set_data([], [])
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw_idle()

    def _update_buttons(self):
        """Update button states based on test status."""
        if self._is_running:
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            self.pause_btn.config(state='normal')

            if self._is_paused:
                self.pause_btn.config(text='Resume')
            else:
                self.pause_btn.config(text='Pause')
        else:
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            self.pause_btn.config(state='disabled')
            self.pause_btn.config(text='Pause')

    def reset(self):
        """Reset frame to initial state."""
        self._test_points = []
        self._is_running = False
        self._is_paused = False

        self.progress_var.set(0)
        self.progress_label.config(text="Ready")

        self.pwm_label.config(text="---- us")
        self.voltage_label.config(text="--.- V")
        self.current_label.config(text="--.- A")
        self.power_label.config(text="--.- W")
        self.thrust_label.config(text="-.--- kg")

        self.clear_graph()
        self._update_buttons()
