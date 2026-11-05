
class MockChroma:
    def __init__(self):
        self.voltage = 120.0
        self.frequency = 60.0
        self.output = False

    def connect(self):
        print("Mock Chroma connected")

    def set_voltage(self, volts):
        self.voltage = volts

    def set_frequency(self, hz):
        self.frequency = hz

    def output_on(self):
        self.output = True

    def output_off(self):
        self.output = False

    def measure_real_power(self):
        return 380.0 if self.output else 0.0

    def measure_voltage(self):
        return self.voltage if self.output else 0.0

    def measure_current(self):
        return 3.17 if self.output else 0.0

    def measure_frequency(self):
        return self.frequency if self.output else 0.0

    def measure_power_factor(self):
        return 0.99 if self.output else 0.0

    def close(self):
        print("Mock Chroma disconnected")
