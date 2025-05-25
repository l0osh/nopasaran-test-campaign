import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

# 1) Load the data files
data = {}
for run_idx in range(1, 5):
    path = f'run_{run_idx}_udp_dns_results.json'
    if not os.path.exists(path):
        print(f"⚠️ File not found: {path}")
        continue
    with open(path, 'r') as f:
        data[run_idx] = json.load(f)

# 2) Gather a stable, sorted list of test IDs
if data:
    test_ids = sorted(next(iter(data.values())).keys(), key=int)
else:
    test_ids = []

# 3) Classification function for DNS
def classify_dns_entry(entry):
    result = entry.get('result', {})
    w1 = result.get('Worker_1')
    if not w1:
        return 'Failure'
    
    vars1 = w1.get('Variables', {})
    dict1 = vars1.get('dict', {})

    query_sent = dict1.get('query_sent')
    received = dict1.get('received')

    # Case: query_sent true and received is literal string "false"
    if query_sent == "true" and received == "false":
        return 'No Response'

    # Case: received is a dict with DNS answers
    if isinstance(received, dict):
        answers = received.get('answers', [])
        for ans in answers:
            rdata = ans.get('rdata')
            if rdata == "127.0.0.1":
                return 'Received'
            elif rdata == "sinkhole.paloaltonetworks.com.":
                return 'Sinkhole'

    return 'Failure'

# 4) Build a classification list for each run
classifications = {
    run_idx: [classify_dns_entry(data[run_idx][tid]) for tid in test_ids]
    for run_idx in data
}

# 5) Plotting parameters
patterns = {
    'Received': '//',   # green diagonal
    'Sinkhole': '\\\\', # red backslash
    'No Response':    'xx',   # yellow cross
}
colors = {
    'Received': 'green',
    'Sinkhole': 'red',
    'No Response':    'yellow',
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
    for key in ['Received', 'Sinkhole', 'No Response']
]
ax.legend(
    handles=legend_handles,
    title="Classification",
    title_fontsize=18,
    fontsize=16,
    loc='upper center',
    bbox_to_anchor=(0.5, -0.3),
    ncol=4,
    frameon=True
)

# 8) Final formatting & save
ax.set_xlim(-6, len(test_ids))
ax.set_ylim(0, 2)  # Adjusted to fit the new y_positions range
xtick_positions = list(range(0, len(test_ids), 5))
ax.set_xticks(xtick_positions)
ax.set_xticklabels([str(i) for i in xtick_positions], fontsize=13)

# Add x-axis label
ax.set_xlabel('Domain Name ID', fontsize=14, fontweight='bold')

# Hide top, right, left spines and y-axis ticks/labels
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_visible(False)

ax.tick_params(axis='y', which='both', left=False, labelleft=False)
plt.tight_layout()
plt.savefig('udp_dns_conformance_vector.png', dpi=300, bbox_inches='tight')
print("✅ Vector chart saved as 'udp_dns_conformance_vector.png'")
