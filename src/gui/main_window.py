"""
Main application window with tabbed interface.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from .config_frame import ConfigFrame
from .test_frame import TestFrame
from .results_frame import ResultsFrame
from ..data.models import TestPoint, TestResult, TestStatus
from ..data.database import Database
from ..hardware.pwm_controller import PWMController
from ..hardware.power_monitor import PowerMonitor
from ..hardware.load_cell import LoadCell
from ..testing.test_runner import TestRunner, SimulatedTestRunner


class MainWindow:
    """
    Main application window for Thruster Tester.

    Contains a notebook with three tabs:
    - Configuration
    - Test Execution
    - Results
    """

    def __init__(self, simulate: bool = False):
        """
        Initialize main window.

        Args:
            simulate: If True, use simulated hardware
        """
        self.simulate = simulate

        # Create main window
        self.root = tk.Tk()
        self.root.title("Thruster Tester")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)

        # Initialize hardware (or simulated)
        self._init_hardware()

        # Initialize database
        self.db = Database()

        # Test runner (created when test starts)
        self.test_runner: Optional[TestRunner] = None

        # Create UI
        self._create_widgets()
        self._setup_callbacks()
        self._load_test_history()

    def _init_hardware(self):
        """Initialize hardware interfaces."""
        self.pwm = PWMController(simulate=self.simulate)
        self.power = PowerMonitor(simulate=self.simulate)
        self.load_cell = LoadCell(simulate=self.simulate)

        if self.simulate:
            print("Running in simulation mode")

    def _create_widgets(self):
        """Create main window widgets."""
        # Menu bar
        self._create_menu()

        # Main container
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Notebook (tabbed interface)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create frames
        self.config_frame = ConfigFrame(self.notebook)
        self.test_frame = TestFrame(self.notebook)
        self.results_frame = ResultsFrame(self.notebook)

        # Add tabs
        self.notebook.add(self.config_frame, text="Configuration")
        self.notebook.add(self.test_frame, text="Test")
        self.notebook.add(self.results_frame, text="Results")

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var,
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Results...",
                              command=self._export_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Calibrate Load Cell",
                               command=self._calibrate_load_cell)
        tools_menu.add_command(label="Test PWM Output",
                               command=self._test_pwm)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _setup_callbacks(self):
        """Set up callbacks between components."""
        # Config frame callbacks
        self.config_frame.set_on_calibrate(self._calibrate_load_cell)

        # Test frame callbacks
        self.test_frame.set_callbacks(
            on_start=self._start_test,
            on_stop=self._stop_test,
            on_pause=self._pause_test,
            on_resume=self._resume_test,
            on_emergency_stop=self._emergency_stop
        )

        # Results frame callbacks
        self.results_frame.set_callbacks(
            on_load_test=self._load_test,
            on_delete_test=self._delete_test,
            on_refresh=self._load_test_history
        )

        # Window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _start_test(self):
        """Start a new test."""
        # Validate configuration
        if not self.config_frame.validate():
            return

        config = self.config_frame.get_config()

        # Confirm start
        if not messagebox.askyesno("Start Test",
                                    f"Start test for {config.thruster_type} "
                                    f"(ID: {config.thruster_id})?\n\n"
                                    "Make sure the test area is clear!"):
            return

        # Disable config during test
        self.config_frame.set_enabled(False)

        # Clear previous data
        self.test_frame.reset()

        # Create test runner
        if self.simulate:
            self.test_runner = SimulatedTestRunner(
                pwm_controller=self.pwm,
                power_monitor=self.power,
                load_cell=self.load_cell,
                config=config
            )
        else:
            self.test_runner = TestRunner(
                pwm_controller=self.pwm,
                power_monitor=self.power,
                load_cell=self.load_cell,
                config=config
            )

        # Set up callbacks
        self.test_runner.set_callbacks(
            on_point=self._on_test_point,
            on_progress=self._on_test_progress,
            on_complete=self._on_test_complete,
            on_error=self._on_test_error
        )

        # Switch to test tab
        self.notebook.select(1)

        # Start test
        self.test_runner.start()
        self.status_var.set("Test running...")

    def _stop_test(self):
        """Stop the current test."""
        if self.test_runner:
            self.test_runner.stop()
            self.status_var.set("Test stopped")
            self.config_frame.set_enabled(True)

    def _pause_test(self):
        """Pause the current test."""
        if self.test_runner:
            self.test_runner.pause()
            self.status_var.set("Test paused")

    def _resume_test(self):
        """Resume a paused test."""
        if self.test_runner:
            self.test_runner.resume()
            self.status_var.set("Test running...")

    def _emergency_stop(self):
        """Emergency stop."""
        if self.test_runner:
            self.test_runner.emergency_stop()

        self.pwm.emergency_stop()
        self.status_var.set("EMERGENCY STOP")
        self.config_frame.set_enabled(True)

        messagebox.showwarning("Emergency Stop",
                               "Emergency stop activated!\n"
                               "Thruster returned to neutral.")

    def _on_test_point(self, point: TestPoint):
        """Handle new test point."""
        # Update UI in main thread
        self.root.after(0, lambda: self._update_test_point(point))

    def _update_test_point(self, point: TestPoint):
        """Update test frame with new point (in main thread)."""
        self.test_frame.update_readings(point)
        self.test_frame.add_data_point(point)

    def _on_test_progress(self, progress: float):
        """Handle progress update."""
        self.root.after(0, lambda: self._update_progress(progress))

    def _update_progress(self, progress: float):
        """Update progress display (in main thread)."""
        if self.test_runner:
            self.test_frame.update_status(self.test_runner.status)

    def _on_test_complete(self, result: TestResult):
        """Handle test completion."""
        self.root.after(0, lambda: self._handle_test_complete(result))

    def _handle_test_complete(self, result: TestResult):
        """Handle test completion (in main thread)."""
        self.status_var.set("Test complete!")
        self.config_frame.set_enabled(True)

        # Save to database
        try:
            test_id = self.db.save_test_result(result)
            result.test_id = test_id
            self.status_var.set(f"Test saved (ID: {test_id})")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save test: {e}")

        # Display results
        self.results_frame.display_result(result)
        self._load_test_history()

        # Switch to results tab
        self.notebook.select(2)

        messagebox.showinfo("Test Complete",
                           f"Test completed successfully!\n\n"
                           f"Max thrust: {result.max_thrust_kg:.3f} kg\n"
                           f"Deadband: {result.deadband.range_us if result.deadband else 'N/A'} us")

    def _on_test_error(self, error: str):
        """Handle test error."""
        self.root.after(0, lambda: self._handle_test_error(error))

    def _handle_test_error(self, error: str):
        """Handle test error (in main thread)."""
        self.status_var.set(f"Error: {error}")
        self.config_frame.set_enabled(True)
        messagebox.showerror("Test Error", error)

    def _calibrate_load_cell(self):
        """Calibrate load cell."""
        if messagebox.askyesno("Tare Load Cell",
                               "Remove all weight from the load cell and click OK to tare."):
            try:
                self.load_cell.tare()
                self.config_frame.set_calibration_status("Tared")
                self.status_var.set("Load cell tared")
                messagebox.showinfo("Calibration", "Load cell tared successfully!")
            except Exception as e:
                messagebox.showerror("Calibration Error", str(e))

    def _test_pwm(self):
        """Test PWM output."""
        TestPWMDialog(self.root, self.pwm)

    def _export_results(self):
        """Export current results."""
        self.notebook.select(2)  # Switch to results tab
        # Export is handled in results frame

    def _load_test(self, test_id: int):
        """Load a test from database."""
        try:
            result = self.db.get_test_result(test_id)
            if result:
                self.results_frame.display_result(result)
                self.status_var.set(f"Loaded test {test_id}")
            else:
                messagebox.showerror("Load Error", "Test not found")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def _delete_test(self, test_id: int):
        """Delete a test from database."""
        try:
            self.db.delete_test(test_id)
            self._load_test_history()
            self.results_frame.clear()
            self.status_var.set(f"Deleted test {test_id}")
        except Exception as e:
            messagebox.showerror("Delete Error", str(e))

    def _load_test_history(self):
        """Load test history from database."""
        try:
            tests = self.db.get_all_tests()
            self.results_frame.update_history(tests)
        except Exception as e:
            print(f"Failed to load test history: {e}")

    def _show_about(self):
        """Show about dialog."""
        messagebox.showinfo("About Thruster Tester",
                           "Thruster Tester v1.0\n\n"
                           "Characterize thruster performance across PWM range.\n\n"
                           "Supported thrusters:\n"
                           "- Diamond Dynamics TD1.2\n"
                           "- Blue Robotics T100/T200\n\n"
                           "Hardware:\n"
                           "- Raspberry Pi 5 (Hardware PWM)\n"
                           "- INA228 power monitor\n"
                           "- HX711 load cell")

    def _on_close(self):
        """Handle window close."""
        if self.test_runner and self.test_runner.status.is_running:
            if not messagebox.askyesno("Test Running",
                                        "A test is running. Stop and exit?"):
                return
            self._emergency_stop()

        # Cleanup
        self.pwm.cleanup()
        self.load_cell.cleanup()
        self.db.close()

        self.root.destroy()

    def run(self):
        """Start the application."""
        self.root.mainloop()


class TestPWMDialog:
    """Dialog for testing PWM output manually."""

    def __init__(self, parent, pwm_controller: PWMController):
        self.pwm = pwm_controller

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("PWM Test")
        self.dialog.geometry("300x150")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # PWM slider
        ttk.Label(self.dialog, text="PWM (us):").pack(pady=5)

        self.pwm_var = tk.IntVar(value=1500)
        self.slider = ttk.Scale(self.dialog, from_=1000, to=2000,
                                 variable=self.pwm_var, orient=tk.HORIZONTAL,
                                 command=self._on_slider_change)
        self.slider.pack(fill=tk.X, padx=20)

        self.value_label = ttk.Label(self.dialog, text="1500 us")
        self.value_label.pack()

        # Warning
        ttk.Label(self.dialog, text="WARNING: Thruster will spin!",
                  foreground='red').pack(pady=10)

        # Close button
        ttk.Button(self.dialog, text="Close",
                   command=self._on_close).pack(pady=5)

        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_slider_change(self, value):
        """Handle slider change."""
        pwm_value = int(float(value))
        self.value_label.config(text=f"{pwm_value} us")
        self.pwm.set_pwm_us(pwm_value)

    def _on_close(self):
        """Handle dialog close."""
        self.pwm.set_pwm_us(1500)  # Return to neutral
        self.dialog.destroy()
