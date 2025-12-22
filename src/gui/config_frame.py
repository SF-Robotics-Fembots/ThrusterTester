"""
Configuration frame for setting up thruster tests.
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Callable, Optional

from ..data.models import ThrusterConfig


class ConfigFrame(ttk.Frame):
    """
    Frame for configuring thruster test parameters.

    Includes:
    - Thruster type selection (with presets)
    - Thruster ID entry
    - PWM range configuration
    - Load cell calibration
    """

    def __init__(self, parent, presets_path: str = "config/thruster_presets.json"):
        super().__init__(parent)

        self.presets = self._load_presets(presets_path)
        self._on_config_change: Optional[Callable[[ThrusterConfig], None]] = None
        self._on_calibrate: Optional[Callable[[], None]] = None

        self._create_widgets()
        self._load_preset("TD1.2")  # Default

    def _load_presets(self, path: str) -> dict:
        """Load thruster presets from JSON file."""
        try:
            preset_path = Path(path)
            if not preset_path.is_absolute():
                # Try relative to script location
                script_dir = Path(__file__).parent.parent.parent
                preset_path = script_dir / path

            if preset_path.exists():
                with open(preset_path) as f:
                    data = json.load(f)
                    return data.get('presets', {})
        except Exception as e:
            print(f"Failed to load presets: {e}")

        # Default presets if file not found
        return {
            "TD1.2": {
                "name": "Diamond Dynamics TD1.2",
                "min_pwm_us": 1100,
                "max_pwm_us": 1900,
                "neutral_pwm_us": 1500,
                "pwm_frequency_hz": 50
            },
            "T100": {
                "name": "Blue Robotics T100",
                "min_pwm_us": 1100,
                "max_pwm_us": 1900,
                "neutral_pwm_us": 1500,
                "pwm_frequency_hz": 50
            },
            "T200": {
                "name": "Blue Robotics T200",
                "min_pwm_us": 1100,
                "max_pwm_us": 1900,
                "neutral_pwm_us": 1500,
                "pwm_frequency_hz": 50
            },
            "Custom": {
                "name": "Custom",
                "min_pwm_us": 1000,
                "max_pwm_us": 2000,
                "neutral_pwm_us": 1500,
                "pwm_frequency_hz": 50
            }
        }

    def _create_widgets(self):
        """Create configuration widgets."""
        # Main container with padding
        container = ttk.Frame(self, padding="10")
        container.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(container, text="Test Configuration",
                          font=('TkDefaultFont', 14, 'bold'))
        title.pack(anchor=tk.W, pady=(0, 10))

        # Thruster Type
        type_frame = ttk.LabelFrame(container, text="Thruster Type", padding="5")
        type_frame.pack(fill=tk.X, pady=5)

        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(type_frame, textvariable=self.type_var,
                                        values=list(self.presets.keys()),
                                        state='readonly', width=30)
        self.type_combo.pack(side=tk.LEFT, padx=5)
        self.type_combo.bind('<<ComboboxSelected>>', self._on_type_selected)

        # Thruster ID
        id_frame = ttk.LabelFrame(container, text="Thruster ID", padding="5")
        id_frame.pack(fill=tk.X, pady=5)

        self.id_var = tk.StringVar(value="001")
        self.id_entry = ttk.Entry(id_frame, textvariable=self.id_var, width=33)
        self.id_entry.pack(side=tk.LEFT, padx=5)

        # PWM Configuration
        pwm_frame = ttk.LabelFrame(container, text="PWM Configuration", padding="5")
        pwm_frame.pack(fill=tk.X, pady=5)

        # Min PWM
        min_row = ttk.Frame(pwm_frame)
        min_row.pack(fill=tk.X, pady=2)
        ttk.Label(min_row, text="Min PWM (us):", width=15).pack(side=tk.LEFT)
        self.min_pwm_var = tk.IntVar(value=1100)
        self.min_pwm_entry = ttk.Entry(min_row, textvariable=self.min_pwm_var, width=10)
        self.min_pwm_entry.pack(side=tk.LEFT, padx=5)

        # Max PWM
        max_row = ttk.Frame(pwm_frame)
        max_row.pack(fill=tk.X, pady=2)
        ttk.Label(max_row, text="Max PWM (us):", width=15).pack(side=tk.LEFT)
        self.max_pwm_var = tk.IntVar(value=1900)
        self.max_pwm_entry = ttk.Entry(max_row, textvariable=self.max_pwm_var, width=10)
        self.max_pwm_entry.pack(side=tk.LEFT, padx=5)

        # Neutral PWM
        neutral_row = ttk.Frame(pwm_frame)
        neutral_row.pack(fill=tk.X, pady=2)
        ttk.Label(neutral_row, text="Neutral (us):", width=15).pack(side=tk.LEFT)
        self.neutral_pwm_var = tk.IntVar(value=1500)
        self.neutral_pwm_entry = ttk.Entry(neutral_row, textvariable=self.neutral_pwm_var, width=10)
        self.neutral_pwm_entry.pack(side=tk.LEFT, padx=5)

        # PWM Frequency
        freq_row = ttk.Frame(pwm_frame)
        freq_row.pack(fill=tk.X, pady=2)
        ttk.Label(freq_row, text="Frequency (Hz):", width=15).pack(side=tk.LEFT)
        self.freq_var = tk.IntVar(value=50)
        self.freq_entry = ttk.Entry(freq_row, textvariable=self.freq_var, width=10)
        self.freq_entry.pack(side=tk.LEFT, padx=5)

        # Calibration Section
        cal_frame = ttk.LabelFrame(container, text="Load Cell Calibration", padding="5")
        cal_frame.pack(fill=tk.X, pady=5)

        self.calibrate_btn = ttk.Button(cal_frame, text="Tare Load Cell",
                                         command=self._on_calibrate_click)
        self.calibrate_btn.pack(side=tk.LEFT, padx=5)

        self.cal_status = ttk.Label(cal_frame, text="Not calibrated")
        self.cal_status.pack(side=tk.LEFT, padx=10)

        # Info label
        info_frame = ttk.Frame(container)
        info_frame.pack(fill=tk.X, pady=10)

        info_text = ("Test will sweep from Min to Max PWM in 25us increments.\n"
                     "At each step: voltage, current, power, and thrust are measured.")
        info_label = ttk.Label(info_frame, text=info_text,
                               foreground='gray', wraplength=300)
        info_label.pack(anchor=tk.W)

    def _on_type_selected(self, event=None):
        """Handle thruster type selection."""
        selected = self.type_var.get()
        self._load_preset(selected)

    def _load_preset(self, preset_name: str):
        """Load values from a preset."""
        if preset_name in self.presets:
            preset = self.presets[preset_name]
            self.type_var.set(preset_name)
            self.min_pwm_var.set(preset.get('min_pwm_us', 1100))
            self.max_pwm_var.set(preset.get('max_pwm_us', 1900))
            self.neutral_pwm_var.set(preset.get('neutral_pwm_us', 1500))
            self.freq_var.set(preset.get('pwm_frequency_hz', 50))

    def _on_calibrate_click(self):
        """Handle calibrate button click."""
        if self._on_calibrate:
            self._on_calibrate()

    def set_on_calibrate(self, callback: Callable[[], None]):
        """Set callback for calibration request."""
        self._on_calibrate = callback

    def set_calibration_status(self, status: str):
        """Update calibration status display."""
        self.cal_status.config(text=status)

    def get_config(self) -> ThrusterConfig:
        """
        Get current configuration as ThrusterConfig object.

        Returns:
            ThrusterConfig with current settings
        """
        return ThrusterConfig(
            thruster_type=self.type_var.get(),
            thruster_id=self.id_var.get(),
            min_pwm_us=self.min_pwm_var.get(),
            max_pwm_us=self.max_pwm_var.get(),
            neutral_pwm_us=self.neutral_pwm_var.get(),
            pwm_frequency_hz=self.freq_var.get()
        )

    def validate(self) -> bool:
        """
        Validate current configuration.

        Returns:
            True if configuration is valid
        """
        try:
            min_pwm = self.min_pwm_var.get()
            max_pwm = self.max_pwm_var.get()
            neutral = self.neutral_pwm_var.get()

            if min_pwm >= max_pwm:
                messagebox.showerror("Invalid Configuration",
                                    "Min PWM must be less than Max PWM")
                return False

            if not (min_pwm <= neutral <= max_pwm):
                messagebox.showerror("Invalid Configuration",
                                    "Neutral PWM must be between Min and Max")
                return False

            if min_pwm < 500 or max_pwm > 2500:
                messagebox.showerror("Invalid Configuration",
                                    "PWM values must be between 500 and 2500 us")
                return False

            if not self.id_var.get().strip():
                messagebox.showerror("Invalid Configuration",
                                    "Thruster ID cannot be empty")
                return False

            return True

        except tk.TclError:
            messagebox.showerror("Invalid Configuration",
                                "Please enter valid numeric values")
            return False

    def set_enabled(self, enabled: bool):
        """Enable or disable all configuration controls."""
        state = 'normal' if enabled else 'disabled'
        self.type_combo.config(state='readonly' if enabled else 'disabled')
        self.id_entry.config(state=state)
        self.min_pwm_entry.config(state=state)
        self.max_pwm_entry.config(state=state)
        self.neutral_pwm_entry.config(state=state)
        self.freq_entry.config(state=state)
        self.calibrate_btn.config(state=state)
