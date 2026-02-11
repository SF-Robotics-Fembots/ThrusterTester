#!/usr/bin/env python3
"""Test tx_pwm on GPIO18 with gpiochip4 for Pi 5."""

import lgpio
import time

chip = lgpio.gpiochip_open(4)  # Pi 5 uses gpiochip4

print("Testing tx_pwm on GPIO18 with gpiochip4...")
# 50Hz, 7.5% duty = 1500us pulse
result = lgpio.tx_pwm(chip, 18, 50, 7.5)
print(f"tx_pwm returned: {result}")

print("Check scope on GPIO18 for 5 seconds...")
time.sleep(5)

lgpio.tx_pwm(chip, 18, 0, 0)
lgpio.gpiochip_close(chip)
print("Done")
