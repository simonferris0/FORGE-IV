
import time

from Chroma61507 import Chroma61507
from GeneratorEmulator import GeneratorEmulator
from EthernetServer import EthernetServer


def main():
    chroma = Chroma61507()
    server = None

    try:
        chroma.connect()

        generator = GeneratorEmulator(chroma)

        # Start Ethernet server.
        server = EthernetServer(host="0.0.0.0", port=5000)
        server.start()

        generator.start()

        last_status_time = time.monotonic()

        while generator.state == "RUNNING":
            generator.update()

            # Process incoming commands from Type V.
            server.process_commands(generator)

            # Print status once per second.
            now = time.monotonic()

            if now - last_status_time >= 1.0:
                status = generator.get_status()

                print(
                    f"Load: {status['load_percent']:.1f}% | "
                    f"Power: {status['real_power_kw'] * 1000:.3f} W | "
                    f"Frequency: {status['frequency']:.2f} Hz | "
                    f"Fuel: {status['fuel_gal']:.6f} gal"
                )

                last_status_time = now

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopping generator")

    except Exception as error:
        print(f"Error: {error}")

    finally:
        if server is not None:
            server.stop()

        try:
            if chroma.instrument is not None:
                chroma.output_off()
        finally:
            chroma.close()


if __name__ == "__main__":
    main()
