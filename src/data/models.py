"""
Data models for thruster testing application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import json


@dataclass
class ThrusterConfig:
    """Configuration for a thruster test."""
    thruster_type: str  # e.g., "TD1.2", "T100", "T200"
    thruster_id: str    # User-defined identifier
    min_pwm_us: int     # Minimum PWM pulse width in microseconds
    max_pwm_us: int     # Maximum PWM pulse width in microseconds
    neutral_pwm_us: int = 1500  # Neutral/off PWM value
    pwm_frequency_hz: int = 50  # PWM frequency for ESC

    def to_dict(self) -> dict:
        return {
            'thruster_type': self.thruster_type,
            'thruster_id': self.thruster_id,
            'min_pwm_us': self.min_pwm_us,
            'max_pwm_us': self.max_pwm_us,
            'neutral_pwm_us': self.neutral_pwm_us,
            'pwm_frequency_hz': self.pwm_frequency_hz
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ThrusterConfig':
        return cls(**data)


@dataclass
class TestPoint:
    """Single measurement point during a thruster test."""
    pwm_us: int         # PWM pulse width in microseconds
    current_a: float    # Current in Amps
    voltage_v: float    # Voltage in Volts
    power_w: float      # Power in Watts (V * I)
    thrust_kg: float    # Thrust force in kg
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            'pwm_us': self.pwm_us,
            'current_a': self.current_a,
            'voltage_v': self.voltage_v,
            'power_w': self.power_w,
            'thrust_kg': self.thrust_kg,
            'timestamp': self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TestPoint':
        data = data.copy()
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class DeadbandResult:
    """Analysis results for the thruster deadband (off zone)."""
    min_off_pwm_us: int      # Lower bound of deadband (nearest 5us)
    max_off_pwm_us: int      # Upper bound of deadband (nearest 5us)
    midpoint_pwm_us: float   # Calculated midpoint
    range_us: int            # Total deadband range

    def to_dict(self) -> dict:
        return {
            'min_off_pwm_us': self.min_off_pwm_us,
            'max_off_pwm_us': self.max_off_pwm_us,
            'midpoint_pwm_us': self.midpoint_pwm_us,
            'range_us': self.range_us
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DeadbandResult':
        return cls(**data)


@dataclass
class TestResult:
    """Complete results from a thruster characterization test."""
    config: ThrusterConfig
    test_points: List[TestPoint]
    deadband: Optional[DeadbandResult]
    start_time: datetime
    end_time: Optional[datetime] = None
    notes: str = ""
    test_id: Optional[int] = None  # Database ID

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def max_thrust_kg(self) -> float:
        if not self.test_points:
            return 0.0
        return max(abs(p.thrust_kg) for p in self.test_points)

    @property
    def max_power_w(self) -> float:
        if not self.test_points:
            return 0.0
        return max(p.power_w for p in self.test_points)

    @property
    def max_current_a(self) -> float:
        if not self.test_points:
            return 0.0
        return max(p.current_a for p in self.test_points)

    def to_dict(self) -> dict:
        return {
            'test_id': self.test_id,
            'config': self.config.to_dict(),
            'test_points': [p.to_dict() for p in self.test_points],
            'deadband': self.deadband.to_dict() if self.deadband else None,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TestResult':
        return cls(
            test_id=data.get('test_id'),
            config=ThrusterConfig.from_dict(data['config']),
            test_points=[TestPoint.from_dict(p) for p in data['test_points']],
            deadband=DeadbandResult.from_dict(data['deadband']) if data.get('deadband') else None,
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
            notes=data.get('notes', '')
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'TestResult':
        return cls.from_dict(json.loads(json_str))


@dataclass
class TestStatus:
    """Current status during test execution."""
    is_running: bool = False
    is_paused: bool = False
    current_pwm_us: int = 1500
    progress_percent: float = 0.0
    current_point: Optional[TestPoint] = None
    error_message: Optional[str] = None
