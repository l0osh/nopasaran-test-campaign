import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict

# 0) Load name map
with open('paper_workers_naming.json', 'r') as f:
    name_map = json.load(f)

# Unicode subscripts
subscript_digits = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

def format_worker_name(worker_id):
    mapped = name_map.get(worker_id, worker_id)
    if any(char.isdigit() for char in mapped):
        base = ''.join([c for c in mapped if not c.isdigit()])
        digits = ''.join([c for c in mapped if c.isdigit()])
        return base + digits.translate(subscript_digits)
    return mapped

# 1) Load the single result file
with open('run_all_workers_conformance_results.json', 'r') as f:
    data = json.load(f)

# 2) Group entries by worker pair
pairwise_data = defaultdict(list)
for tid, entry in sorted(data.items(), key=lambda x: int(x[0])):  # sort by test ID
    pair = (entry['worker_1'], entry['worker_2'])
    pairwise_data[pair].append((int(tid), entry))

# 3) Classification function
def classify_entry(entry):
    if entry.get('status') == 'submission_failed':
        return 'SubmissionFailed'
    if entry.get('status') == 'polling_failed':
        return 'PollingFailed'

    result = entry.get('result', {})
    if result.get('Worker_1') is None or result.get('Worker_2') is None:
        return 'WorkerMissing'

    vars1 = result.get('Worker_1', {}).get('Variables', {})
    vars2 = result.get('Worker_2', {}).get('Variables', {})

    sync1 = vars1.get('sync_received')
    recv1 = vars1.get('received') or ""
    sync2 = vars2.get('sync_received')
    recv2 = vars2.get('received') or ""

    if recv1 == "":
        return 'Empty'
    if '503' in recv1:
        return '503'
    if sync1 == recv2 and sync2 == recv1:
        return 'Match'

    return 'Failure'

# 4) Apply classification to all pairs
classified_by_pair = defaultdict(list)
for pair, entries in pairwise_data.items():
    sorted_entries = sorted(entries, key=lambda x: x[0])
    for _, entry in sorted_entries:
        status = classify_entry(entry)
        classified_by_pair[pair].append(status)

# 5) Plotting parameters
patterns = {
    'Match':           '//',
    'Empty':           'xx',
    '503':             '\\\\',
    'Failure':         '...',
    'SubmissionFailed':'',      # solid black
    'PollingFailed':   '///',
    'WorkerMissing':   'oo',
}

colors = {
    'Match':           'green',
    'Empty':           'yellow',
    '503':             'red',
    'Failure':         'dimgray',
    'SubmissionFailed':'black',
    'PollingFailed':   'black',
    'WorkerMissing':   'black',
}

# 6) Create the plot
fig, ax = plt.subplots(figsize=(15, 6))
y_spacing = 0.65
bar_height = 0.6

all_pairs = sorted(classified_by_pair.keys(), key=lambda p: (format_worker_name(p[0]), format_worker_name(p[1])))
y_positions = [y_spacing * (len(all_pairs) - i) for i in range(len(all_pairs))]
present_statuses = set()

for idx, pair in enumerate(all_pairs):
    y = y_positions[idx]
    statuses = classified_by_pair[pair]
    present_statuses.update(statuses)

    for i, status in enumerate(statuses):
        ax.barh(
            y=y,
            width=1,
            left=i,
            height=bar_height,
            color=colors[status],
            edgecolor='black',
            hatch=patterns[status]
        )

    w1 = format_worker_name(pair[0])
    w2 = format_worker_name(pair[1])
    ax.text(
        -5, y,
        f'{w1} ↔ {w2}',
        va='center',
        ha='right',
        fontweight='bold',
        fontsize=13
    )

# 7) Legend
preferred_order = ['Match', '503', 'Empty']
remaining_statuses = sorted(present_statuses - set(preferred_order))
legend_keys = preferred_order + remaining_statuses

legend_handles = [
    mpatches.Patch(facecolor=colors[key], edgecolor='black', hatch=patterns[key], label=key)
    for key in legend_keys
]
ax.legend(
    handles=legend_handles,
    title="Classification",
    title_fontsize=16,
    fontsize=13,
    loc='upper center',
    bbox_to_anchor=(0.5, -0.1),
    ncol=4,
    frameon=True
)

# 8) Final formatting
max_len = max(len(statuses) for statuses in classified_by_pair.values())
ax.set_xlim(-6, max(10, max_len))
ax.set_ylim(0, y_spacing * len(all_pairs) + 0.2)
xtick_positions = list(range(0, max_len + 1, 5))
ax.set_xticks(xtick_positions)
ax.set_xticklabels([str(i) for i in xtick_positions], fontsize=11)

ax.set_xlabel('Domain Name ID', fontsize=13, fontweight='bold')
for spine in ['top', 'right', 'left', 'bottom']:
    ax.spines[spine].set_visible(False)
ax.tick_params(axis='y', which='both', left=False, labelleft=False)

plt.tight_layout()
plt.savefig('http_classification_by_pair.png', dpi=300, bbox_inches='tight')
print("✅ Chart saved: http_classification_by_pair.png")
