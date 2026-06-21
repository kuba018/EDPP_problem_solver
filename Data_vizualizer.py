import matplotlib.pyplot as plt

# --- dane ---
p = list(range(1, 31))

same = [97, 96, 90, 89, 83, 89, 74, 72, 71, 69,
        71, 68, 57, 46, 54, 39, 50, 47, 37, 37,
        29, 19, 23, 22, 19, 16, 16, 10, 15, 18]

cplex_acc = [100] * 30

heur_acc = [100, 100, 100, 100, 100, 100, 99, 97, 100, 98,
            98, 99, 93, 90, 98, 89, 92, 84, 84, 81,
            70, 74, 70, 71, 52, 56, 52, 56, 52, 59]

# --- wykres ---
plt.figure(figsize=(9, 5))

plt.plot(p, heur_acc, '-o', linewidth=1.5, markersize=4,
         label='Heurystyka – skuteczność')
plt.plot(p, cplex_acc, '-s', linewidth=1.5, markersize=4,
         label='CPLEX – skuteczność')
plt.plot(p, same, '-^', linewidth=1.5, markersize=4,
         label='% zgodnych rozwiązań')

plt.xlabel('p')
plt.ylabel('[%]')
plt.xticks(p)
plt.ylim(0, 110)
plt.grid(True, linestyle='--', alpha=0.4)
plt.legend(loc='lower left')
plt.tight_layout()

plt.show()
# ewentualnie:
# plt.savefig('skutecznosc_wykres.png', dpi=300)