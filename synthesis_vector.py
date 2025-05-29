import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# 1) Load synthesis.json
with open('synthesis.json', 'r') as f:
    synthesis = json.load(f)

# 2) Standardize test ordering per vector
vectors = {}
for vector_name, test_map in synthesis.items():
    test_ids = list(test_map.keys())
    statuses = [test_map[tid] for tid in test_ids]
    vectors[vector_name] = statuses

# 3) Plotting setup
patterns = {
    'Passed': '//',
    'Blocked': 'xx'
}
colors = {
    'Passed': 'green',
    'Blocked': 'red'
}
bar_height = 0.35

num_vectors = len(vectors)
spacing = 0.4
top_y = (num_vectors - 1) * spacing + 0.4
y_positions = [top_y - i * spacing for i in range(num_vectors)]

# 4) Create the plot
max_len = max(len(v) for v in vectors.values())
fig_height = 1 + num_vectors  # dynamic height
fig, ax = plt.subplots(figsize=(max_len / 4, fig_height))

for idx, (vector_name, vector) in enumerate(vectors.items()):
    y = y_positions[idx]
    for i, status in enumerate(vector):
        ax.barh(
            y=y,
            width=1,
            left=i,
            height=bar_height,
            color=colors[status],
            edgecolor='black',
            hatch=patterns[status]
        )
    ax.text(
        -5, y,
        vector_name,
        va='center',
        ha='right',
        fontweight='bold',
        fontsize=13
    )

# 5) Legend
legend_handles = [
    mpatches.Patch(facecolor=colors[key], edgecolor='black', hatch=patterns[key], label=key)
    for key in ['Passed', 'Blocked']
]
ax.legend(
    handles=legend_handles,
    title="Synthesis",
    title_fontsize=18,
    fontsize=16,
    loc='upper center',
    bbox_to_anchor=(0.5, -0.3),
    ncol=2,
    frameon=True
)

# 6) Formatting
ax.set_xlim(-6, max_len)
ax.set_ylim(0, top_y + 0.6)
xtick_positions = list(range(0, max_len, 5))
ax.set_xticks(xtick_positions)
ax.set_xticklabels([str(i) for i in xtick_positions], fontsize=13)

ax.set_xlabel('Domain Name ID', fontsize=14, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.tick_params(axis='y', which='both', left=False, labelleft=False)

plt.tight_layout()
plt.savefig('synthesis_vector.png', dpi=300, bbox_inches='tight')
print("✅ Vector chart saved as 'synthesis_vector.png'")
