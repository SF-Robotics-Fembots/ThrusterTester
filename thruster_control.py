#!/usr/bin/env python3
"""
Simple thruster control program for Raspberry Pi 5.
Uses hardware PWM on GPIO18.
"""

import sys
import time

try:
    import lgpio
except ImportError:
    print("Error: lgpio not installed. Run: sudo apt install python3-lgpio")
    sys.exit(1)

# PWM Configuration
PWM_GPIO = 18
PWM_FREQ = 100  # 50Hz for ESC/servo
NEUTRAL_US = 1500
MIN_US = 1100
MAX_US = 1900

# Pi 5 uses gpiochip4
CHIP = 4


def us_to_duty(pulse_us: int) -> float:
    """Convert microseconds to duty cycle percentage."""
    # At 50Hz, period is 20ms (20000us)
    # duty = (pulse_us / 20000) * 100
    return (pulse_us / 20000.0) * 100.0


def main():
    print("=== Thruster Control ===")
    print(f"PWM GPIO: {PWM_GPIO}")
    print(f"Frequency: {PWM_FREQ}Hz")
    print(f"Range: {MIN_US}-{MAX_US}us, Neutral: {NEUTRAL_US}us")
    print()

    # Open GPIO chip
    try:
        chip = lgpio.gpiochip_open(CHIP)
    except Exception as e:
        print(f"Failed to open gpiochip{CHIP}: {e}")
        sys.exit(1)

    # Start PWM at neutral
    try:
        duty = us_to_duty(NEUTRAL_US)
        lgpio.tx_pwm(chip, PWM_GPIO, PWM_FREQ, duty)
        print(f"PWM started at neutral ({NEUTRAL_US}us)")
    except Exception as e:
        print(f"Failed to start PWM: {e}")
        lgpio.gpiochip_close(chip)
        sys.exit(1)

    # ESC initialization sequence
    print("\n--- ESC Initialization ---")
    print("Holding neutral for 3 seconds...")
    time.sleep(3)
    print("ESC should be initialized (listen for beeps)")

    print("\n--- Control Mode ---")
    print("Enter: <pwm_us> <seconds>  (e.g., '1600 2' runs 1600us for 2 seconds)")
    print("Enter: q to quit")
    print("Enter: n for neutral")
    print()

    try:
        while True:
            try:
                cmd = input("PWM> ").strip().lower()
            except EOFError:
                break

            if cmd == 'q' or cmd == 'quit':
                break

            if cmd == 'n' or cmd == 'neutral':
                duty = us_to_duty(NEUTRAL_US)
                lgpio.tx_pwm(chip, PWM_GPIO, PWM_FREQ, duty)
                print(f"Set to neutral ({NEUTRAL_US}us)")
                continue

            if not cmd:
                continue

            # Parse command
            parts = cmd.split()
            if len(parts) < 1:
                print("Usage: <pwm_us> [seconds]")
                continue

            try:
                pwm_us = int(parts[0])
            except ValueError:
                print("Invalid PWM value")
                continue

            # Validate range
            if pwm_us < MIN_US or pwm_us > MAX_US:
                print(f"PWM must be between {MIN_US} and {MAX_US}us")
                continue

            # Get duration (default 1 second)
            duration = 1.0
            if len(parts) >= 2:
                try:
                    duration = float(parts[1])
                except ValueError:
                    print("Invalid duration")
                    continue

            # Run thruster
            print(f"Running at {pwm_us}us for {duration}s...")
            duty = us_to_duty(pwm_us)
            lgpio.tx_pwm(chip, PWM_GPIO, PWM_FREQ, duty)

            time.sleep(duration)

            # Return to neutral
            duty = us_to_duty(NEUTRAL_US)
            lgpio.tx_pwm(chip, PWM_GPIO, PWM_FREQ, duty)
            print(f"Returned to neutral ({NEUTRAL_US}us)")

    except KeyboardInterrupt:
        print("\nInterrupted")

    finally:
        # Cleanup - return to neutral and stop PWM
        print("\nShutting down...")
        duty = us_to_duty(NEUTRAL_US)
        lgpio.tx_pwm(chip, PWM_GPIO, PWM_FREQ, duty)
        time.sleep(0.5)
        lgpio.tx_pwm(chip, PWM_GPIO, 0, 0)  # Stop PWM
        lgpio.gpiochip_close(chip)
        print("Done")


if __name__ == "__main__":
    main()
