"""
CSV export functionality for thruster test results.
"""

import csv
from pathlib import Path
from typing import Optional

from .models import TestResult


def export_to_csv(result: TestResult, filepath: Optional[str] = None) -> str:
    """
    Export test result to CSV file.

    Args:
        result: TestResult to export
        filepath: Output file path (auto-generated if None)

    Returns:
        Path to created CSV file
    """
    if filepath is None:
        timestamp = result.start_time.strftime("%Y%m%d_%H%M%S")
        filepath = f"thruster_test_{result.config.thruster_type}_{result.config.thruster_id}_{timestamp}.csv"

    filepath = Path(filepath)

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)

        # Write header section with test info
        writer.writerow(['Thruster Test Results'])
        writer.writerow([])
        writer.writerow(['Configuration'])
        writer.writerow(['Thruster Type', result.config.thruster_type])
        writer.writerow(['Thruster ID', result.config.thruster_id])
        writer.writerow(['Min PWM (us)', result.config.min_pwm_us])
        writer.writerow(['Max PWM (us)', result.config.max_pwm_us])
        writer.writerow(['Neutral PWM (us)', result.config.neutral_pwm_us])
        writer.writerow(['PWM Frequency (Hz)', result.config.pwm_frequency_hz])
        writer.writerow([])
        writer.writerow(['Test Info'])
        writer.writerow(['Start Time', result.start_time.isoformat()])
        writer.writerow(['End Time', result.end_time.isoformat() if result.end_time else 'N/A'])
        writer.writerow(['Duration (s)', f"{result.duration_seconds:.1f}" if result.duration_seconds else 'N/A'])
        writer.writerow(['Notes', result.notes])
        writer.writerow([])

        # Write deadband analysis if available
        if result.deadband:
            writer.writerow(['Deadband Analysis'])
            writer.writerow(['Min Off PWM (us)', result.deadband.min_off_pwm_us])
            writer.writerow(['Max Off PWM (us)', result.deadband.max_off_pwm_us])
            writer.writerow(['Midpoint (us)', f"{result.deadband.midpoint_pwm_us:.1f}"])
            writer.writerow(['Range (us)', result.deadband.range_us])
            writer.writerow([])

        # Write summary statistics
        writer.writerow(['Summary Statistics'])
        writer.writerow(['Max Thrust (kg)', f"{result.max_thrust_kg:.3f}"])
        writer.writerow(['Max Power (W)', f"{result.max_power_w:.2f}"])
        writer.writerow(['Max Current (A)', f"{result.max_current_a:.2f}"])
        writer.writerow([])

        # Write data points
        writer.writerow(['Test Data Points'])
        writer.writerow(['PWM (us)', 'Current (A)', 'Voltage (V)', 'Power (W)', 'Thrust (kg)', 'Timestamp'])

        for point in result.test_points:
            writer.writerow([
                point.pwm_us,
                f"{point.current_a:.4f}",
                f"{point.voltage_v:.3f}",
                f"{point.power_w:.3f}",
                f"{point.thrust_kg:.4f}",
                point.timestamp.isoformat()
            ])

    return str(filepath)


def export_data_only_csv(result: TestResult, filepath: Optional[str] = None) -> str:
    """
    Export only the data points to CSV (for easy import into other tools).

    Args:
        result: TestResult to export
        filepath: Output file path (auto-generated if None)

    Returns:
        Path to created CSV file
    """
    if filepath is None:
        timestamp = result.start_time.strftime("%Y%m%d_%H%M%S")
        filepath = f"thruster_data_{result.config.thruster_type}_{result.config.thruster_id}_{timestamp}.csv"

    filepath = Path(filepath)

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)

        # Simple header
        writer.writerow(['pwm_us', 'current_a', 'voltage_v', 'power_w', 'thrust_kg'])

        for point in result.test_points:
            writer.writerow([
                point.pwm_us,
                point.current_a,
                point.voltage_v,
                point.power_w,
                point.thrust_kg
            ])

    return str(filepath)
