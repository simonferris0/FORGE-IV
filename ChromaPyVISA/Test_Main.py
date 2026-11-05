
import time

from MockChroma import MockChroma
from GeneratorEmulator import GeneratorEmulator
from EthernetServer import EthernetServer


def main():
    chroma = MockChroma()
    server = None

    try:
        chroma.connect()

        generator = GeneratorEmulator(chroma)

        server = EthernetServer(host="0.0.0.0", port=5000)
        server.start()

        generator.start()

        last_status_time = time.monotonic()

        while True:
            generator.update()

            # Process commands from Type V.
            server.process_commands(generator)

            # Print status once per second.
            now = time.monotonic()

            if now - last_status_time >= 1.0:
                if generator.state == "RUNNING":
                    status = generator.get_status()
                    print(
                        f"Load: {status['load_percent']:.1f}% | "
                        f"Power: {status['real_power_kw'] * 1000:.3f} W | "
                        f"Frequency: {status['frequency']:.2f} Hz | "
                        f"Fuel: {status['fuel_gal']:.6f} gal"
                    )
                else:
                    print("Generator is OFF")

                last_status_time = now

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopping server")

    except Exception as error:
        print(f"Error: {error}")

    finally:
        if generator.state == "RUNNING":
            generator.stop()

        if server is not None:
            server.stop()

        chroma.close()


if __name__ == "__main__":
    main()
