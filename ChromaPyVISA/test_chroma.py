
from Chroma61507 import Chroma61507

chroma = Chroma61507()

try:
    chroma.connect()
    print("Power factor:", chroma.measure_power_factor())
finally:
    chroma.close()
