import matplotlib.pyplot as plt

levels = list(range(1, 100))
xp = []

for L in levels:
    if L < 20:
        # smooth cubic growth from level 1 to 20
        xp_val = 10000 * (L / 20)**3
        xp.append(int(xp_val))
    else:
        # scaled cubic growth from level 20 to 99
        xp_val = 10000 + 2.008 * (L - 20)**3
        xp.append(int(xp_val))

plt.plot(levels, xp, marker='o')
plt.title("XP Curve: Level 1 → 99")
plt.xlabel("Level")
plt.ylabel("XP")
plt.grid(True)
plt.show()
