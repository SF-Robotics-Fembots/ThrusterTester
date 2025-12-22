"""
Results display frame for viewing and exporting test data.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Callable, Optional, List

try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from ..data.models import TestResult
from ..data.csv_export import export_to_csv, export_data_only_csv


class ResultsFrame(ttk.Frame):
    """
    Frame for displaying test results.

    Includes:
    - Summary statistics
    - Deadband analysis results
    - Result graph
    - Export options
    - Historical test list
    """

    def __init__(self, parent):
        super().__init__(parent)

        self._current_result: Optional[TestResult] = None
        self._on_load_test: Optional[Callable[[int], None]] = None
        self._on_delete_test: Optional[Callable[[int], None]] = None

        self._create_widgets()

    def _create_widgets(self):
        """Create results display widgets."""
        # Main container with two columns
        container = ttk.Frame(self, padding="10")
        container.pack(fill=tk.BOTH, expand=True)

        # Left column - current result
        left_frame = ttk.Frame(container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Title
        title = ttk.Label(left_frame, text="Test Results",
                          font=('TkDefaultFont', 14, 'bold'))
        title.pack(anchor=tk.W, pady=(0, 10))

        # Summary section
        summary_frame = ttk.LabelFrame(left_frame, text="Summary", padding="5")
        summary_frame.pack(fill=tk.X, pady=5)

        self.summary_text = tk.Text(summary_frame, height=8, width=40,
                                     state='disabled', wrap=tk.WORD)
        self.summary_text.pack(fill=tk.X, padx=5, pady=5)

        # Deadband section
        deadband_frame = ttk.LabelFrame(left_frame, text="Deadband Analysis", padding="5")
        deadband_frame.pack(fill=tk.X, pady=5)

        self.deadband_text = tk.Text(deadband_frame, height=5, width=40,
                                      state='disabled', wrap=tk.WORD)
        self.deadband_text.pack(fill=tk.X, padx=5, pady=5)

        # Export buttons
        export_frame = ttk.LabelFrame(left_frame, text="Export", padding="5")
        export_frame.pack(fill=tk.X, pady=5)

        btn_row = ttk.Frame(export_frame)
        btn_row.pack(fill=tk.X, pady=5)

        self.export_full_btn = ttk.Button(btn_row, text="Export Full Report",
                                           command=self._export_full)
        self.export_full_btn.pack(side=tk.LEFT, padx=5)

        self.export_data_btn = ttk.Button(btn_row, text="Export Data Only",
                                           command=self._export_data)
        self.export_data_btn.pack(side=tk.LEFT, padx=5)

        # Graph
        if MATPLOTLIB_AVAILABLE:
            self._create_graph(left_frame)

        # Right column - historical tests
        right_frame = ttk.Frame(container, width=200)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        right_frame.pack_propagate(False)

        history_label = ttk.Label(right_frame, text="Test History",
                                   font=('TkDefaultFont', 12, 'bold'))
        history_label.pack(anchor=tk.W, pady=(0, 5))

        # Test list with scrollbar
        list_frame = ttk.Frame(right_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.test_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.test_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.test_listbox.yview)

        self.test_listbox.bind('<<ListboxSelect>>', self._on_test_selected)

        # History buttons
        hist_btn_frame = ttk.Frame(right_frame)
        hist_btn_frame.pack(fill=tk.X, pady=5)

        self.load_btn = ttk.Button(hist_btn_frame, text="Load",
                                    command=self._load_selected)
        self.load_btn.pack(side=tk.LEFT, padx=2)

        self.delete_btn = ttk.Button(hist_btn_frame, text="Delete",
                                      command=self._delete_selected)
        self.delete_btn.pack(side=tk.LEFT, padx=2)

        self.refresh_btn = ttk.Button(hist_btn_frame, text="Refresh",
                                       command=self._refresh_history)
        self.refresh_btn.pack(side=tk.LEFT, padx=2)

        # Store test IDs for listbox
        self._test_ids: List[int] = []

    def _create_graph(self, parent):
        """Create matplotlib graph for results visualization."""
        graph_frame = ttk.LabelFrame(parent, text="Thrust Curve", padding="5")
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.fig = Figure(figsize=(5, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('PWM (us)')
        self.ax.set_ylabel('Thrust (kg)')
        self.ax.grid(True, alpha=0.3)

        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def display_result(self, result: TestResult):
        """Display a test result."""
        self._current_result = result

        # Update summary
        self._update_summary(result)

        # Update deadband
        self._update_deadband(result)

        # Update graph
        self._update_graph(result)

    def _update_summary(self, result: TestResult):
        """Update summary text display."""
        self.summary_text.config(state='normal')
        self.summary_text.delete(1.0, tk.END)

        summary = f"""Thruster: {result.config.thruster_type}
ID: {result.config.thruster_id}
PWM Range: {result.config.min_pwm_us} - {result.config.max_pwm_us} us
Test Date: {result.start_time.strftime('%Y-%m-%d %H:%M')}
Duration: {result.duration_seconds:.1f}s

Data Points: {len(result.test_points)}
Max Thrust: {result.max_thrust_kg:.3f} kg
Max Power: {result.max_power_w:.1f} W
Max Current: {result.max_current_a:.2f} A"""

        self.summary_text.insert(tk.END, summary)
        self.summary_text.config(state='disabled')

    def _update_deadband(self, result: TestResult):
        """Update deadband analysis display."""
        self.deadband_text.config(state='normal')
        self.deadband_text.delete(1.0, tk.END)

        if result.deadband:
            db = result.deadband
            deadband_info = f"""Min "Off" PWM: {db.min_off_pwm_us} us
Max "Off" PWM: {db.max_off_pwm_us} us
Midpoint: {db.midpoint_pwm_us:.1f} us
Deadband Range: {db.range_us} us

Thruster is "off" from {db.min_off_pwm_us} to {db.max_off_pwm_us} us"""
        else:
            deadband_info = "No deadband analysis available"

        self.deadband_text.insert(tk.END, deadband_info)
        self.deadband_text.config(state='disabled')

    def _update_graph(self, result: TestResult):
        """Update graph with result data."""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.ax.clear()
        self.ax.set_xlabel('PWM (us)')
        self.ax.set_ylabel('Thrust (kg)')
        self.ax.grid(True, alpha=0.3)
        self.ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)

        if result.test_points:
            pwm_values = [p.pwm_us for p in result.test_points]
            thrust_values = [p.thrust_kg for p in result.test_points]

            self.ax.plot(pwm_values, thrust_values, 'b-', linewidth=1.5)

            # Mark deadband region
            if result.deadband:
                self.ax.axvspan(result.deadband.min_off_pwm_us,
                               result.deadband.max_off_pwm_us,
                               alpha=0.2, color='green', label='Deadband')
                self.ax.axvline(x=result.deadband.midpoint_pwm_us,
                               color='green', linestyle='--', linewidth=1,
                               label=f'Midpoint ({result.deadband.midpoint_pwm_us:.0f})')
                self.ax.legend(loc='upper left', fontsize='small')

        self.canvas.draw()

    def _export_full(self):
        """Export full report to CSV."""
        if not self._current_result:
            messagebox.showwarning("No Data", "No test result to export")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Full Report"
        )

        if filepath:
            try:
                export_to_csv(self._current_result, filepath)
                messagebox.showinfo("Export Complete",
                                   f"Report exported to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def _export_data(self):
        """Export data only to CSV."""
        if not self._current_result:
            messagebox.showwarning("No Data", "No test result to export")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Data Only"
        )

        if filepath:
            try:
                export_data_only_csv(self._current_result, filepath)
                messagebox.showinfo("Export Complete",
                                   f"Data exported to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def update_history(self, tests: List[dict]):
        """Update the test history list."""
        self.test_listbox.delete(0, tk.END)
        self._test_ids = []

        for test in tests:
            display = f"{test['thruster_type']} #{test['thruster_id']} - {test['start_time'][:16]}"
            self.test_listbox.insert(tk.END, display)
            self._test_ids.append(test['id'])

    def _on_test_selected(self, event):
        """Handle test selection in listbox."""
        pass  # Selection handled by load button

    def _load_selected(self):
        """Load the selected test."""
        selection = self.test_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a test to load")
            return

        test_id = self._test_ids[selection[0]]
        if self._on_load_test:
            self._on_load_test(test_id)

    def _delete_selected(self):
        """Delete the selected test."""
        selection = self.test_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a test to delete")
            return

        if not messagebox.askyesno("Confirm Delete",
                                    "Are you sure you want to delete this test?"):
            return

        test_id = self._test_ids[selection[0]]
        if self._on_delete_test:
            self._on_delete_test(test_id)

    def _refresh_history(self):
        """Request history refresh (triggers callback in main window)."""
        # This is handled by the main window
        pass

    def set_callbacks(self,
                      on_load_test: Optional[Callable[[int], None]] = None,
                      on_delete_test: Optional[Callable[[int], None]] = None,
                      on_refresh: Optional[Callable[[], None]] = None):
        """Set callback functions."""
        self._on_load_test = on_load_test
        self._on_delete_test = on_delete_test
        if on_refresh:
            self.refresh_btn.config(command=on_refresh)

    def clear(self):
        """Clear the results display."""
        self._current_result = None

        self.summary_text.config(state='normal')
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, "No test results to display")
        self.summary_text.config(state='disabled')

        self.deadband_text.config(state='normal')
        self.deadband_text.delete(1.0, tk.END)
        self.deadband_text.config(state='disabled')

        if MATPLOTLIB_AVAILABLE:
            self.ax.clear()
            self.ax.set_xlabel('PWM (us)')
            self.ax.set_ylabel('Thrust (kg)')
            self.ax.grid(True, alpha=0.3)
            self.canvas.draw()
