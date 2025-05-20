import json
import matplotlib.pyplot as plt

# 1) Load the data files
data = {}
for run_idx in range(1, 5):
    path = f'run_{run_idx}_results.json'
    with open(path, 'r') as f:
        data[run_idx] = json.load(f)

# 2) Gather a stable, sorted list of test IDs
test_ids = sorted(data[1].keys(), key=int)

# 3) Classification function with your rules
def classify_entry(entry):
    result = entry.get('result', {})
    # Worker_2 null → failure (gray)
    if result.get('Worker_2') is None:
        return 'failure'
    
    vars1 = result.get('Worker_1', {}).get('Variables', {})
    vars2 = result.get('Worker_2', {}).get('Variables', {})

    sync1 = vars1.get('sync_received')
    recv1 = vars1.get('received') or ""
    sync2 = vars2.get('sync_received')
    recv2 = vars2.get('received') or ""

    # If worker_1 received is empty string → empty (yellow)
    if recv1 == "":
        return 'empty'
    
    # 503 in worker_1 received → 503 (red)
    if '503' in recv1:
        return '503'
    
    # Match condition: sync1 == recv2 and sync2 == recv1
    if sync1 == recv2 and sync2 == recv1:
        return 'match'
    
    # Default fallback: failure (gray)
    return 'failure'



# 4) Build a classification list for each run
classifications = {
    run_idx: [classify_entry(data[run_idx][tid]) for tid in test_ids]
    for run_idx in data
}

# 5) Plotting parameters
patterns = {
    'match':   '//',   # green with diagonal hatch
    'failure': '...',  # gray with dot hatch
    'empty':   'xx',   # yellow with crosshatched
    '503':     '\\\\', # red with backslash hatch
}
colors = {
    'match':  'green',
    'failure':'gray',
    'empty':  'yellow',
    '503':    'red',
}

# 6) Create the figure
fig, ax = plt.subplots(figsize=(len(test_ids)/4, 4.5))
y_positions = [4, 3, 2, 1]  # one row per run

for idx, run_idx in enumerate(sorted(classifications)):
    vector = classifications[run_idx]
    y = y_positions[idx]
    for i, status in enumerate(vector):
        ax.barh(
            y=y,
            width=1,
            left=i,
            height=0.8,
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
        fontsize=12
    )

# 7) Final formatting & save
ax.set_xlim(-6, len(test_ids))
ax.set_ylim(0.5, 4.5)
ax.axis('off')
plt.tight_layout()
plt.savefig('http_1_conformance_vector.png', dpi=300, bbox_inches='tight')
print("✅ Vector chart saved as 'http_1_conformance_vector.png'")
