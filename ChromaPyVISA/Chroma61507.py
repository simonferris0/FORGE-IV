import pyvisa

class Chroma61507:

    VISA_ADDRESS = "USB0::0x0A69::0x0883::96150700000146::INSTR"

    def __init__(self):
        self.rm = None
        self.instrument = None

    def connect(self):
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource(self.VISA_ADDRESS)

        self.instrument.timeout = 5000

        print("Connected to Chroma 61507")

    def set_voltage(self, volts):
        self.instrument.write(f"VOLT:AC {volts}")

    def set_frequency(self, hz):
        self.instrument.write(f"FREQ {hz}")

    def output_on(self):
        self.instrument.write("OUTPUT ON")

    def output_off(self):
        self.instrument.write("OUTPUT OFF")

    def measure_voltage(self):
        return float(self.instrument.query("MEAS:VOLT:AC?"))

    def measure_current(self):
        return float(self.instrument.query("MEAS:CURR:AC?"))

    def measure_frequency(self):
        return float(self.instrument.query("MEAS:FREQ?"))

    
    def measure_real_power(self):
        response = self.instrument.query("MEAS:POW:AC?").strip()
        print(f"Raw real-power response: {response}")
        return float(response)


    
    def measure_power_factor(self):
        return float(self.instrument.query("MEAS:POW:AC:PFAC?"))


    def close(self):
        if self.instrument is not None:
            self.instrument.close()

        if self.rm is not None:
            self.rm.close()