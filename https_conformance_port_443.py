import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# 1) Load the data files for HTTPS
data = {}
for run_idx in range(1, 5):
    path = f'run_{run_idx}_https_results.json'
    with open(path, 'r') as f:
        data[run_idx] = json.load(f)

# 2) Gather a stable, sorted list of test IDs
test_ids = sorted(data[1].keys(), key=int)

# 3) Classification function with new rules (Match, Null, Failure only)
def classify_entry(entry):
    result = entry.get('result', {})
    if result.get('Worker_2') is None:
        return 'Failure'

    vars1 = result.get('Worker_1', {}).get('Variables', {})
    vars2 = result.get('Worker_2', {}).get('Variables', {})

    sync1 = vars1.get('sync_dict')
    recv1 = vars1.get('received')
    sync2 = vars2.get('sync_dict')
    recv2 = vars2.get('received')

    if recv1 is None:
        return 'Null'

    if sync1 == recv2 and sync2 == recv1:
        return 'Match'

    return 'Failure'

# 4) Build a classification list for each run
classifications = {
    run_idx: [classify_entry(data[run_idx][tid]) for tid in test_ids]
    for run_idx in data
}

# 5) Plotting parameters
patterns = {
    'Match':   '//',   # green with diagonal hatch
    'Null':    'xx',   # blue with crosshatched
}
colors = {
    'Match':   'green',
    'Null':    'blue',
}

# 5.1) Modified plotting parameters
y_positions = [1.6, 1.2, 0.8, 0.4]  # Tighter spacing on y-axis
bar_height = 0.35  # Reduced height of the bars

# 6) Create the figure
fig, ax = plt.subplots(figsize=(len(test_ids)/4, 3.5))  # Slightly shorter height

for idx, run_idx in enumerate(sorted(classifications)):
    vector = classifications[run_idx]
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
        f'Run {run_idx}',
        va='center',
        ha='right',
        fontweight='bold',
        fontsize=13  # Slightly smaller font
    )

# 7) Add a legend
legend_handles = [
    mpatches.Patch(facecolor=colors[key], edgecolor='black', hatch=patterns[key], label=key)
    for key in ['Match', 'Null']
]
ax.legend(
    handles=legend_handles,
    title="Classification",
    title_fontsize=18,
    fontsize=16,
    loc='upper center',
    bbox_to_anchor=(0.5, -0.3),
    ncol=3,
    frameon=True
)

# 8) Final formatting & save
ax.set_xlim(-6, len(test_ids))
ax.set_ylim(0, 2)  # Adjusted to fit the new y_positions range
# Show only x-axis ticks every 5 indices
xtick_positions = list(range(0, len(test_ids), 5))
ax.set_xticks(xtick_positions)
ax.set_xticklabels([str(i) for i in xtick_positions], fontsize=13)

# Add x-axis label
ax.set_xlabel('Domain Name ID', fontsize=14, fontweight='bold')

# Hide top, right, left spines and y-axis ticks/labels
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_visible(False)  # Optional: keep True if you want a bottom line

ax.tick_params(axis='y', which='both', left=False, labelleft=False)
plt.tight_layout()
plt.savefig('https_1_conformance_vector.png', dpi=300, bbox_inches='tight')
print("✅ Vector chart saved as 'https_1_conformance_vector.png'")
