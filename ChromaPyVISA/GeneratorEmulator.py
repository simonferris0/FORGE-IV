import time
import math


class GeneratorEmulator:
    def __init__(self, chroma):
        self.chroma = chroma

        # MEP-804B nominal rating
        self.rated_power_kw = 15.0
        self.fuel_capacity_gal = 14.0
        self.fuel_level_gal = 14.0

        # Electrical output
        self.voltage = 120.0
        self.nominal_frequency = 60.0
        self.frequency = 60.0

        # Generator state
        self.state = "OFF"
        self.last_update = None
        self.last_fuel_update = None

        # Fuel consumption: load fraction -> gallons/hour.
        # These are the supplied project data, not validated
        # manufacturer values for every operating condition.
        self.fuel_curve = {
            0.00: 0.15,
            0.25: 0.3,
            0.50: 0.5,
            0.75: 0.8,
            1.00: 1.1,
        }

        # Simplified engine/governor parameters.
        # Tune these against measured generator response.
        self.droop = 0.03
        self.governor_tau = 1.0
        self.max_frequency_slew = 2.0  # Hz/second

        # Four-pole generator: 1800 RPM at 60 Hz.
        self.pole_pairs = 2
        self.generator_efficiency = 0.90

        # Simulated mechanical state
        self.engine_rpm = 1800.0
        self.mechanical_power_kw = 0.0
        self.electrical_torque_nm = 0.0
        self.mechanical_torque_nm = 0.0

    def start(self):
        if self.state == "RUNNING":
            return

        if self.fuel_level_gal <= 0:
            print("Cannot start: fuel empty")
            return

        self.frequency = self.nominal_frequency
        self.engine_rpm = 1800.0

        self.chroma.set_voltage(self.voltage)
        self.chroma.set_frequency(self.frequency)
        self.chroma.output_on()

        now = time.monotonic()
        self.last_update = now
        self.last_fuel_update = now
        self.state = "RUNNING"

        print("Generator started")

    def stop(self):
        if self.state == "OFF":
            return

        try:
            self.chroma.output_off()
        finally:
            self.state = "OFF"
            self.last_update = None
            self.last_fuel_update = None
            self.mechanical_power_kw = 0.0
            self.mechanical_torque_nm = 0.0
            self.electrical_torque_nm = 0.0

        print("Generator stopped")

    def interpolate(self, x, x1, y1, x2, y2):
        if x2 == x1:
            return y1

        return y1 + (x - x1) * (y2 - y1) / (x2 - x1)

    def calculate_fuel_rate(self, load_fraction):
        load = max(0.0, min(load_fraction, 1.0))
        points = sorted(self.fuel_curve.items())

        for index in range(1, len(points)):
            x1, y1 = points[index - 1]
            x2, y2 = points[index]

            if load <= x2:
                return self.interpolate(load, x1, y1, x2, y2)

        return points[-1][1]

    def update(self):
        if self.state != "RUNNING":
            return

        now = time.monotonic()

        if self.last_update is None:
            self.last_update = now
            self.last_fuel_update = now
            return

        dt = now - self.last_update

        # Avoid unstable calculations after a long pause.
        self.last_update = now

        if dt <= 0:
            return

        dt = min(dt, 0.25)

        # Read actual electrical output from the CHROMA.
        power_w = max(0.0, self.chroma.measure_real_power())
        power_kw = min(power_w / 1000.0, self.rated_power_kw)
        load = power_kw / self.rated_power_kw

        # Electrical torque:
        # T = P / angular velocity.
        # Frequency is used as the simulated generator speed.
        omega = 2.0 * math.pi * max(self.frequency, 1.0) / self.pole_pairs

        self.electrical_torque_nm = (
            power_kw * 1000.0 / omega
        )

        # Estimate mechanical input power and torque.
        self.mechanical_power_kw = (
            power_kw / self.generator_efficiency
        )

        self.mechanical_torque_nm = (
            self.mechanical_power_kw * 1000.0 / omega
        )

        # Steady-state governor droop.
        # At full load and 3% droop, target frequency is 58.2 Hz.
        target_frequency = (
            self.nominal_frequency * (1.0 - self.droop * load)
        )

        # First-order governor response.
        # Frequency approaches the target instead of changing
        # instantaneously when electrical load changes.
        alpha = 1.0 - math.exp(-dt / self.governor_tau)
        desired_change = alpha * (target_frequency - self.frequency)

        # Limit the rate of frequency change.
        max_change = self.max_frequency_slew * dt
        frequency_change = max(
            -max_change,
            min(desired_change, max_change)
        )

        self.frequency += frequency_change
        self.engine_rpm = (
            self.frequency * 60.0 / self.pole_pairs
        )

        # Command the simulated electrical output frequency.
        self.chroma.set_frequency(self.frequency)

        # Consume fuel using elapsed wall-clock time.
        if self.last_fuel_update is None:
            self.last_fuel_update = now

        elapsed_hours = (
            now - self.last_fuel_update
        ) / 3600.0

        self.last_fuel_update = now

        fuel_rate = self.calculate_fuel_rate(load)
        fuel_used = fuel_rate * elapsed_hours

        self.fuel_level_gal = max(
            0.0, self.fuel_level_gal - fuel_used
        )

        if self.fuel_level_gal <= 0.0:
            print("Fuel exhausted")
            self.stop()

        
    
    def get_status(self):
        print("Reading real power...")
        power_w = max(0.0, self.chroma.measure_real_power())
        power_kw = min(power_w / 1000.0, self.rated_power_kw)
        load = power_kw / self.rated_power_kw

        print("Reading voltage...")
        voltage = self.chroma.measure_voltage()
        print("Voltage:", voltage)

        print("Reading current...")
        current = self.chroma.measure_current()
        print("Current:", current)

        print("Reading frequency...")
        measured_frequency = self.chroma.measure_frequency()
        print("Frequency:", measured_frequency)

        print("Reading Power Factor...")
        power_factor = self.chroma.measure_power_factor()

        return {
            "state": self.state,
            "fuel_gal": self.fuel_level_gal,
            "fuel_percent": (
                self.fuel_level_gal / self.fuel_capacity_gal
            ) * 100.0,
            "load_percent": load * 100.0,
            "fuel_rate_gph": self.calculate_fuel_rate(load),
            "voltage": voltage,
            "current": current,
            "frequency": measured_frequency,
            "simulated_frequency": self.frequency,
            "engine_rpm": self.engine_rpm,
            "real_power_kw": power_kw,
            "mechanical_power_kw": self.mechanical_power_kw,
            "electrical_torque_nm": self.electrical_torque_nm,
            "mechanical_torque_nm": self.mechanical_torque_nm,
            "power_factor": power_factor,
        }
