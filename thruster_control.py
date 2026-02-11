#!/usr/bin/env python3
"""
Simple thruster control program for Raspberry Pi 5.
Uses lgpio gpio_write PWM on GPIO18 via gpiochip4.
"""

import sys
import time
import threading

try:
    import lgpio
except ImportError:
    print("Error: lgpio not installed. Run: sudo apt install python3-lgpio")
    sys.exit(1)

# PWM Configuration
PWM_GPIO = 18
PWM_FREQ = 100      # 100Hz
NEUTRAL_US = 1500
MIN_US = 1100
MAX_US = 1900

# Pi 5 uses gpiochip4
CHIP = 4


class PWMOutput:
    """PWM output using lgpio gpio_write in a thread."""

    def __init__(self, chip, gpio, freq_hz=100):
        self.chip = chip
        self.gpio = gpio
        self.period_s = 1.0 / freq_hz
        self.pulse_us = NEUTRAL_US
        self.running = False
        self.thread = None

        lgpio.gpio_claim_output(chip, gpio, 0)

    def _pwm_loop(self):
        while self.running:
            high_s = self.pulse_us / 1000000.0
            low_s = self.period_s - high_s
            lgpio.gpio_write(self.chip, self.gpio, 1)
            time.sleep(high_s)
            lgpio.gpio_write(self.chip, self.gpio, 0)
            if low_s > 0:
                time.sleep(low_s)

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._pwm_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.1)
        lgpio.gpio_write(self.chip, self.gpio, 0)

    def set_pulse_us(self, pulse_us):
        self.pulse_us = pulse_us


def main():
    print("=== Thruster Control ===")
    print(f"GPIO: {PWM_GPIO}, Frequency: {PWM_FREQ}Hz")
    print(f"Range: {MIN_US}-{MAX_US}us, Neutral: {NEUTRAL_US}us")
    print()

    try:
        chip = lgpio.gpiochip_open(CHIP)
    except Exception as e:
        print(f"Failed to open gpiochip{CHIP}: {e}")
        sys.exit(1)

    pwm = PWMOutput(chip, PWM_GPIO, PWM_FREQ)
    pwm.set_pulse_us(NEUTRAL_US)
    pwm.start()
    print(f"PWM started at neutral ({NEUTRAL_US}us)")

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
                pwm.set_pulse_us(NEUTRAL_US)
                print(f"Set to neutral ({NEUTRAL_US}us)")
                continue

            if not cmd:
                continue

            parts = cmd.split()

            try:
                pwm_us = int(parts[0])
            except ValueError:
                print("Invalid PWM value")
                continue

            if pwm_us < MIN_US or pwm_us > MAX_US:
                print(f"PWM must be between {MIN_US} and {MAX_US}us")
                continue

            duration = 1.0
            if len(parts) >= 2:
                try:
                    duration = float(parts[1])
                except ValueError:
                    print("Invalid duration")
                    continue

            print(f"Running at {pwm_us}us for {duration}s...")
            pwm.set_pulse_us(pwm_us)
            time.sleep(duration)

            pwm.set_pulse_us(NEUTRAL_US)
            print(f"Returned to neutral ({NEUTRAL_US}us)")

    except KeyboardInterrupt:
        print("\nInterrupted")

    finally:
        print("\nShutting down...")
        pwm.set_pulse_us(NEUTRAL_US)
        time.sleep(0.5)
        pwm.stop()
        lgpio.gpiochip_close(chip)
        print("Done")


if __name__ == "__main__":
    main()
