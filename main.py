#!/usr/bin/env python3
"""
Thruster Tester Application

A GUI application for characterizing thruster performance across PWM ranges.
Supports Diamond Dynamics TD1.2, Blue Robotics T100/T200, and similar thrusters.

Hardware:
- Raspberry Pi Zero
- PCA9685 PWM controller (I2C)
- INA228 power monitor (I2C)
- HX711 load cell (GPIO)

Usage:
    python main.py              # Normal mode (requires hardware)
    python main.py --simulate   # Simulation mode (no hardware required)
"""

import sys
import argparse


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Thruster Tester - Characterize thruster performance'
    )
    parser.add_argument(
        '--simulate', '-s',
        action='store_true',
        help='Run in simulation mode (no hardware required)'
    )
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='Thruster Tester v1.0'
    )

    args = parser.parse_args()

    # Import here to avoid GUI issues before argument parsing
    from src.gui.main_window import MainWindow

    # Create and run application
    app = MainWindow(simulate=args.simulate)

    print("Starting Thruster Tester...")
    if args.simulate:
        print("Running in SIMULATION mode")
    else:
        print("Running in HARDWARE mode")

    app.run()


if __name__ == '__main__':
    main()
