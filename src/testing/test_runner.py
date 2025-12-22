"""
Test runner for thruster characterization.

Orchestrates the test sequence: sweeping through PWM values
and collecting measurements at each point.
"""

import time
import threading
from datetime import datetime
from typing import Callable, Optional, List

from ..data.models import ThrusterConfig, TestPoint, TestResult, TestStatus, DeadbandResult
from ..hardware.pwm_controller import PWMController
from ..hardware.power_monitor import PowerMonitor
from ..hardware.load_cell import LoadCell
from .deadband_analyzer import analyze_deadband


class TestRunner:
    """
    Runs thruster characterization tests.

    Sweeps through PWM range, collecting voltage, current, power,
    and thrust measurements at each step.
    """

    def __init__(self,
                 pwm_controller: PWMController,
                 power_monitor: PowerMonitor,
                 load_cell: LoadCell,
                 config: ThrusterConfig,
                 step_us: int = 25,
                 stabilization_ms: int = 500,
                 samples_per_point: int = 5):
        """
        Initialize test runner.

        Args:
            pwm_controller: PWM controller instance
            power_monitor: Power monitor instance
            load_cell: Load cell instance
            config: Thruster configuration
            step_us: PWM step size in microseconds
            stabilization_ms: Time to wait after setting PWM before measuring
            samples_per_point: Number of samples to average per data point
        """
        self.pwm = pwm_controller
        self.power = power_monitor
        self.load_cell = load_cell
        self.config = config
        self.step_us = step_us
        self.stabilization_ms = stabilization_ms
        self.samples_per_point = samples_per_point

        self._status = TestStatus()
        self._test_points: List[TestPoint] = []
        self._stop_requested = False
        self._pause_requested = False
        self._thread: Optional[threading.Thread] = None
        self._result: Optional[TestResult] = None

        # Callbacks
        self._on_point_callback: Optional[Callable[[TestPoint], None]] = None
        self._on_progress_callback: Optional[Callable[[float], None]] = None
        self._on_complete_callback: Optional[Callable[[TestResult], None]] = None
        self._on_error_callback: Optional[Callable[[str], None]] = None

    @property
    def status(self) -> TestStatus:
        """Get current test status."""
        return self._status

    @property
    def result(self) -> Optional[TestResult]:
        """Get test result (available after test completes)."""
        return self._result

    def set_callbacks(self,
                      on_point: Optional[Callable[[TestPoint], None]] = None,
                      on_progress: Optional[Callable[[float], None]] = None,
                      on_complete: Optional[Callable[[TestResult], None]] = None,
                      on_error: Optional[Callable[[str], None]] = None):
        """
        Set callback functions for test events.

        Args:
            on_point: Called when a new data point is collected
            on_progress: Called with progress percentage (0-100)
            on_complete: Called when test completes successfully
            on_error: Called if an error occurs
        """
        self._on_point_callback = on_point
        self._on_progress_callback = on_progress
        self._on_complete_callback = on_complete
        self._on_error_callback = on_error

    def start(self):
        """Start the test in a background thread."""
        if self._status.is_running:
            return

        self._stop_requested = False
        self._pause_requested = False
        self._test_points = []
        self._result = None

        self._thread = threading.Thread(target=self._run_test)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        """Stop the test."""
        self._stop_requested = True
        if self._thread:
            self._thread.join(timeout=5.0)

    def pause(self):
        """Pause the test."""
        self._pause_requested = True
        self._status.is_paused = True

    def resume(self):
        """Resume a paused test."""
        self._pause_requested = False
        self._status.is_paused = False

    def emergency_stop(self):
        """Emergency stop - immediately halt and return to neutral."""
        self._stop_requested = True
        self.pwm.emergency_stop()
        self._status.is_running = False
        self._status.is_paused = False

    def _run_test(self):
        """Main test execution loop."""
        self._status.is_running = True
        self._status.error_message = None
        start_time = datetime.now()

        try:
            # Arm ESC
            self._update_status("Arming ESC...")
            self.pwm.arm(self.config.neutral_pwm_us)

            # Tare load cell
            self._update_status("Taring load cell...")
            self.load_cell.tare()

            # Calculate total steps
            total_steps = (self.config.max_pwm_us - self.config.min_pwm_us) // self.step_us + 1

            # Ramp to minimum PWM
            self._update_status("Ramping to start...")
            self.pwm.ramp_to(self.config.min_pwm_us)
            time.sleep(self.stabilization_ms / 1000)

            # Sweep through PWM range
            current_pwm = self.config.min_pwm_us
            step_count = 0

            while current_pwm <= self.config.max_pwm_us:
                # Check for stop/pause
                if self._stop_requested:
                    break

                while self._pause_requested:
                    time.sleep(0.1)
                    if self._stop_requested:
                        break

                if self._stop_requested:
                    break

                # Set PWM and wait for stabilization
                self.pwm.set_pwm_us(current_pwm)
                time.sleep(self.stabilization_ms / 1000)

                # Take measurements
                point = self._take_measurement(current_pwm)
                self._test_points.append(point)

                # Update status and callbacks
                self._status.current_pwm_us = current_pwm
                self._status.current_point = point
                step_count += 1
                progress = (step_count / total_steps) * 100
                self._status.progress_percent = progress

                if self._on_point_callback:
                    self._on_point_callback(point)
                if self._on_progress_callback:
                    self._on_progress_callback(progress)

                # Next step
                current_pwm += self.step_us

            # Return to neutral
            self._update_status("Returning to neutral...")
            self.pwm.ramp_to(self.config.neutral_pwm_us)
            self.pwm.disarm()

            # Analyze deadband
            deadband = analyze_deadband(
                self._test_points,
                neutral_pwm_us=self.config.neutral_pwm_us
            )

            # Create result
            end_time = datetime.now()
            self._result = TestResult(
                config=self.config,
                test_points=self._test_points,
                deadband=deadband,
                start_time=start_time,
                end_time=end_time
            )

            if self._on_complete_callback and not self._stop_requested:
                self._on_complete_callback(self._result)

        except Exception as e:
            error_msg = f"Test error: {str(e)}"
            self._status.error_message = error_msg
            self.pwm.emergency_stop()

            if self._on_error_callback:
                self._on_error_callback(error_msg)

        finally:
            self._status.is_running = False
            self._status.is_paused = False

    def _take_measurement(self, pwm_us: int) -> TestPoint:
        """
        Take averaged measurements at current PWM setting.

        Args:
            pwm_us: Current PWM value

        Returns:
            TestPoint with averaged measurements
        """
        voltages = []
        currents = []
        thrusts = []

        for _ in range(self.samples_per_point):
            v, i, _ = self.power.read_all()
            t = self.load_cell.read_kg(samples=1)

            voltages.append(v)
            currents.append(i)
            thrusts.append(t)

            time.sleep(0.02)  # Small delay between samples

        # Average measurements
        avg_voltage = sum(voltages) / len(voltages)
        avg_current = sum(currents) / len(currents)
        avg_thrust = sum(thrusts) / len(thrusts)
        avg_power = avg_voltage * avg_current

        return TestPoint(
            pwm_us=pwm_us,
            current_a=avg_current,
            voltage_v=avg_voltage,
            power_w=avg_power,
            thrust_kg=avg_thrust
        )

    def _update_status(self, message: str):
        """Update status message (for debugging/logging)."""
        print(message)


class SimulatedTestRunner(TestRunner):
    """
    Test runner with simulated hardware for development/testing.
    """

    def _take_measurement(self, pwm_us: int) -> TestPoint:
        """Generate simulated measurements based on PWM value."""
        import random

        neutral = self.config.neutral_pwm_us
        deviation = pwm_us - neutral

        # Simulate deadband
        if abs(deviation) < 30:
            thrust = random.uniform(-0.005, 0.005)
            current = random.uniform(0.1, 0.3)
        else:
            # Thrust roughly proportional to deviation from neutral
            max_thrust = 3.0  # kg at full throttle
            thrust_factor = deviation / (self.config.max_pwm_us - neutral)
            thrust = thrust_factor * max_thrust + random.uniform(-0.02, 0.02)

            # Current increases with thrust
            current = 0.5 + abs(thrust) * 3.0 + random.uniform(-0.1, 0.1)

        voltage = 12.0 + random.uniform(-0.1, 0.1)
        power = voltage * current

        return TestPoint(
            pwm_us=pwm_us,
            current_a=current,
            voltage_v=voltage,
            power_w=power,
            thrust_kg=thrust
        )
