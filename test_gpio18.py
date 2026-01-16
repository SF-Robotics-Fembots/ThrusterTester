#!/usr/bin/env python3
"""Test GPIO18 toggle on Pi 5."""

import lgpio
import time

CHIP = 4  # Pi 5 uses gpiochip4
GPIO = 18

chip = lgpio.gpiochip_open(CHIP)
lgpio.gpio_claim_output(chip, GPIO, 0)

print(f"Toggling GPIO{GPIO} - watch with scope or LED")
print("Ctrl+C to stop")

try:
    while True:
        lgpio.gpio_write(chip, GPIO, 1)
        print("HIGH")
        time.sleep(0.5)
        lgpio.gpio_write(chip, GPIO, 0)
        print("LOW")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nStopped")
finally:
    lgpio.gpio_write(chip, GPIO, 0)
    lgpio.gpiochip_close(chip)
