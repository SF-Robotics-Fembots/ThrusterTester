#!/usr/bin/env python3
"""
Simple thruster control program for Raspberry Pi 5.
Uses hardware PWM via sysfs on GPIO12 (PWM0 channel 0).
Requires: dtoverlay=pwm in /boot/firmware/config.txt
"""

import sys
import time
import os

# PWM Configuration
PWM_CHIP = 0        # pwmchip0
PWM_CHANNEL = 0     # channel 0 (GPIO12)
PWM_FREQ = 50       # 50Hz for ESC/servo
NEUTRAL_US = 1500
MIN_US = 1100
MAX_US = 1900


class HardwarePWM:
    """Hardware PWM control via sysfs."""

    def __init__(self, chip=0, channel=0):
        self.chip = chip
        self.channel = channel
        self.pwm_path = f"/sys/class/pwm/pwmchip{chip}"
        self.channel_path = f"{self.pwm_path}/pwm{channel}"
        self.exported = False

    def export(self):
        """Export the PWM channel."""
        if os.path.exists(self.channel_path):
            print(f"PWM channel {self.channel} already exported")
            self.exported = True
            return True

        try:
            with open(f"{self.pwm_path}/export", "w") as f:
                f.write(str(self.channel))
            # Wait for sysfs to create the channel
            time.sleep(0.1)
            self.exported = True
            print(f"Exported PWM channel {self.channel}")
            return True
        except PermissionError:
            print(f"Permission denied. Run with sudo or add user to gpio group")
            return False
        except Exception as e:
            print(f"Failed to export PWM: {e}")
            return False

    def unexport(self):
        """Unexport the PWM channel."""
        if not self.exported:
            return
        try:
            with open(f"{self.pwm_path}/unexport", "w") as f:
                f.write(str(self.channel))
        except Exception:
            pass

    def set_period_ns(self, period_ns):
        """Set PWM period in nanoseconds."""
        try:
            with open(f"{self.channel_path}/period", "w") as f:
                f.write(str(int(period_ns)))
            return True
        except Exception as e:
            print(f"Failed to set period: {e}")
            return False

    def set_duty_ns(self, duty_ns):
        """Set PWM duty cycle in nanoseconds."""
        try:
            with open(f"{self.channel_path}/duty_cycle", "w") as f:
                f.write(str(int(duty_ns)))
            return True
        except Exception as e:
            print(f"Failed to set duty cycle: {e}")
            return False

    def enable(self):
        """Enable PWM output."""
        try:
            with open(f"{self.channel_path}/enable", "w") as f:
                f.write("1")
            return True
        except Exception as e:
            print(f"Failed to enable PWM: {e}")
            return False

    def disable(self):
        """Disable PWM output."""
        try:
            with open(f"{self.channel_path}/enable", "w") as f:
                f.write("0")
            return True
        except Exception:
            return False

    def set_frequency_and_pulse(self, freq_hz, pulse_us):
        """Set frequency and pulse width."""
        period_ns = int(1e9 / freq_hz)  # Convert Hz to ns
        duty_ns = int(pulse_us * 1000)   # Convert us to ns

        # Period must be set before duty_cycle, and duty must be <= period
        self.set_period_ns(period_ns)
        self.set_duty_ns(duty_ns)

    def set_pulse_us(self, pulse_us):
        """Set pulse width in microseconds."""
        duty_ns = int(pulse_us * 1000)
        self.set_duty_ns(duty_ns)


def main():
    print("=== Thruster Control (Hardware PWM) ===")
    print(f"PWM Chip: {PWM_CHIP}, Channel: {PWM_CHANNEL} (GPIO12)")
    print(f"Frequency: {PWM_FREQ}Hz")
    print(f"Range: {MIN_US}-{MAX_US}us, Neutral: {NEUTRAL_US}us")
    print()

    # Check if pwmchip exists
    if not os.path.exists(f"/sys/class/pwm/pwmchip{PWM_CHIP}"):
        print(f"ERROR: /sys/class/pwm/pwmchip{PWM_CHIP} not found!")
        print("\nMake sure you have enabled the PWM overlay:")
        print("  Add 'dtoverlay=pwm' to /boot/firmware/config.txt")
        print("  Then reboot")
        sys.exit(1)

    # Initialize hardware PWM
    pwm = HardwarePWM(chip=PWM_CHIP, channel=PWM_CHANNEL)

    if not pwm.export():
        print("\nTry: sudo python3 thruster_control.py")
        sys.exit(1)

    # Configure PWM
    pwm.set_frequency_and_pulse(PWM_FREQ, NEUTRAL_US)
    pwm.enable()
    print(f"PWM started at neutral ({NEUTRAL_US}us)")

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
                pwm.set_pulse_us(NEUTRAL_US)
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
            pwm.set_pulse_us(pwm_us)

            time.sleep(duration)

            # Return to neutral
            pwm.set_pulse_us(NEUTRAL_US)
            print(f"Returned to neutral ({NEUTRAL_US}us)")

    except KeyboardInterrupt:
        print("\nInterrupted")

    finally:
        # Cleanup
        print("\nShutting down...")
        pwm.set_pulse_us(NEUTRAL_US)
        time.sleep(0.5)
        pwm.disable()
        print("Done")


if __name__ == "__main__":
    main()
