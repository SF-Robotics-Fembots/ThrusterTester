#!/usr/bin/env python3
"""
4-thruster test program for Raspberry Pi 5.
Select thrusters to test - each runs backward 1s, pause 1s, forward 1s.
Uses lgpio software PWM on GPIO 12, 13, 18, 19 via gpiochip4.
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
THRUSTER_GPIOS = {1: 12, 2: 13, 3: 18, 4: 19}
PWM_FREQ = 100       # 100Hz
NEUTRAL_US = 1445
REVERSE_US = 1400    # Backward (below neutral)
FORWARD_US = 1600    # Forward (above neutral)

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


def run_test(pwm_outputs, thruster_nums, reverse_us, neutral_us, forward_us):
    """Run backward/pause/forward test on selected thrusters simultaneously."""
    names = ", ".join(f"T{n} (GPIO {THRUSTER_GPIOS[n]})" for n in thruster_nums)

    print(f"\n--- Testing: {names} ---")

    # Backward
    print(f"  REVERSE ({reverse_us}us) for 1 second...")
    for n in thruster_nums:
        pwm_outputs[n].set_pulse_us(reverse_us)
    time.sleep(1.0)

    # Pause
    print(f"  NEUTRAL ({neutral_us}us) for 1 second...")
    for n in thruster_nums:
        pwm_outputs[n].set_pulse_us(neutral_us)
    time.sleep(1.0)

    # Forward
    print(f"  FORWARD ({forward_us}us) for 1 second...")
    for n in thruster_nums:
        pwm_outputs[n].set_pulse_us(forward_us)
    time.sleep(1.0)

    # Return to neutral
    for n in thruster_nums:
        pwm_outputs[n].set_pulse_us(neutral_us)
    print("  Done - returned to neutral")


def get_input(prompt, default):
    """Prompt for an integer value with a default."""
    val = input(f"{prompt} [{default}]: ").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        print(f"Invalid value, using default {default}")
        return default


def main():
    print("=== 4-Thruster Test ===")
    print()
    for num, gpio in THRUSTER_GPIOS.items():
        print(f"  Thruster {num} -> GPIO {gpio}")
    print()

    neutral_us = get_input("Neutral PWM us", NEUTRAL_US)
    reverse_us = get_input("Reverse PWM us", REVERSE_US)
    forward_us = get_input("Forward PWM us", FORWARD_US)
    freq = get_input("PWM Frequency Hz", PWM_FREQ)

    print(f"\nFrequency: {freq}Hz, Neutral: {neutral_us}us")
    print(f"Reverse: {reverse_us}us, Forward: {forward_us}us")
    print()

    try:
        chip = lgpio.gpiochip_open(CHIP)
    except Exception as e:
        print(f"Failed to open gpiochip{CHIP}: {e}")
        sys.exit(1)

    # Create PWM outputs for all 4 thrusters
    pwm_outputs = {}
    for num, gpio in THRUSTER_GPIOS.items():
        pwm_outputs[num] = PWMOutput(chip, gpio, freq)
        pwm_outputs[num].set_pulse_us(neutral_us)
        pwm_outputs[num].start()

    print("All PWM outputs started at neutral")
    print("\n--- ESC Initialization ---")
    print("Holding neutral for 3 seconds...")
    time.sleep(3)
    print("ESCs should be initialized (listen for beeps)")

    print("\n--- Test Mode ---")
    print("Enter thruster numbers to test (e.g., '1 3' or '1 2 3 4' or 'all')")
    print("Enter: q to quit")
    print()

    try:
        while True:
            try:
                cmd = input("Test> ").strip().lower()
            except EOFError:
                break

            if cmd == 'q' or cmd == 'quit':
                break

            if not cmd:
                continue

            if cmd == 'all':
                thruster_nums = [1, 2, 3, 4]
            else:
                try:
                    thruster_nums = [int(x) for x in cmd.split()]
                except ValueError:
                    print("Invalid input. Enter thruster numbers (1-4) separated by spaces.")
                    continue

                invalid = [n for n in thruster_nums if n not in THRUSTER_GPIOS]
                if invalid:
                    print(f"Invalid thruster number(s): {invalid}. Use 1-4.")
                    continue

                if not thruster_nums:
                    continue

            run_test(pwm_outputs, thruster_nums, reverse_us, neutral_us, forward_us)

    except KeyboardInterrupt:
        print("\nInterrupted")

    finally:
        print("\nShutting down...")
        for pwm in pwm_outputs.values():
            pwm.set_pulse_us(neutral_us)
        time.sleep(0.5)
        for pwm in pwm_outputs.values():
            pwm.stop()
        lgpio.gpiochip_close(chip)
        print("Done")


if __name__ == "__main__":
    main()
