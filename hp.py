import matplotlib.pyplot as plt
import numpy as np

# Original curve approximation
def base_hp(L):
    return 0.05 * L**2 + 5 * L + 40

# Full scaled curve to hit 99,999 at level 99
def hp_curve(L):
    base_99 = base_hp(99)
    delta = 99999 - base_99
    return base_hp(L) + delta * (L / 99)**3

# Levels
levels = np.arange(1, 100)
hp_values = [hp_curve(L) for L in levels]

# Plot
plt.figure(figsize=(10, 6))
plt.plot(levels, hp_values, label="HP Curve", color="blue")
plt.scatter([1,2,3,4,5,99], [hp_curve(L) for L in [1,2,3,4,5,99]], color="red", label="Key Levels")
plt.title("Level vs HP (Scaled to 99,999 at L99)")
plt.xlabel("Level")
plt.ylabel("HP")
plt.grid(True)
plt.legend()
plt.show()

