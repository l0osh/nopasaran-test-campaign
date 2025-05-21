import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# 1) Load the data files
data = {}
for run_idx in range(1, 5):
    path = f'run_{run_idx}_http_simple_results.json'
    with open(path, 'r') as f:
        data[run_idx] = json.load(f)

# 2) Gather sorted test IDs
test_ids = sorted(data[1].keys(), key=int)

# 3) Classification function
def classify_entry(entry):
    result = entry.get('result', {})
    if result.get('Worker_2') is None:
        return 'Failure'
    
    vars1 = result.get('Worker_1', {}).get('Variables', {})
    vars2 = result.get('Worker_2', {}).get('Variables', {})

    dict_result1 = vars1.get('dict', {}).get('result', {})
    sync_result1 = vars1.get('sync_dict', {}).get('result', {})

    dict_result2 = vars2.get('dict', {}).get('result', {})
    sync_result2 = vars2.get('sync_dict', {}).get('result', {})

    # 1. Match
    if dict_result1 == sync_result1 and dict_result2 == sync_result2:
        return 'Match'

    # 2. HTTP status codes
    status1 = dict_result1.get('results', {}).get('HTTP', {}).get('status')
    status2 = dict_result2.get('results', {}).get('HTTP', {}).get('status')

    if status1 == status2 and status1 != None:
        return 'Match'
    
    if status1 == 503 or status2 == 503:
        return '503'
    if status1 == 403 or status2 == 403:
        return '403'

    # 3. Check errors in dict results
    errors1 = dict_result1.get('errors', [])
    errors2 = dict_result2.get('errors', [])
    combined_errors = errors1 + errors2

    for err in combined_errors:
        if "handshake operation timed out" in err:
            return 'HandshakeTimeout'
        if "Connection reset by peer" in err:
            return 'ConnReset'
        if "HTTP request failed: timed out" in err:
            return 'HTTPTimeout'
        if "HTTPS request failed: timed out" in err:
            return 'HTTPSTimeout'

    # 4. Default fallback
    return 'Other'

# 4) Classify all test IDs for all runs
classifications = {run_idx: {} for run_idx in data}
for run_idx in data:
    for tid in test_ids:
        classifications[run_idx][tid] = classify_entry(data[run_idx][tid])

# 5) Plot settings
patterns = {
    'Match':           '//',   # green with diagonal hatch
    'Other':           '...',  # dark gray with dot hatch
    'Empty':           'xx',   # yellow with crosshatch (if needed)
    '503':             '\\\\', # red with backslash hatch
    '403':             '++',   # orange with plus hatch
    'HandshakeTimeout':'--',   # light blue with dash hatch
    'ConnReset':       'oo',   # purple with circle hatch
    'HTTPTimeout':     '++',   # pink with plus hatch
    'HTTPSTimeout':    '--',  # pink with dash hatch
}

colors = {
    'Match':           'green',
    'Other':           'dimgray',
    'Empty':           'yellow',
    '503':             'red',
    '403':             'orange',
    'HandshakeTimeout':'lightblue',
    'ConnReset':       'purple',
    'HTTPTimeout':     'pink',
    'HTTPSTimeout':    'pink',
}


# 6) Create subplots
fig, axes = plt.subplots(2, 2, figsize=(len(test_ids)/4, 6), sharex=True, sharey=True)

run_to_pos = {
    1: (0, 0),
    2: (0, 1),
    3: (1, 0),
    4: (1, 1),
}

for run_idx in sorted(classifications):
    row, col = run_to_pos[run_idx]
    ax = axes[row][col]
    
    http_vector = [classifications[run_idx][tid] for tid in test_ids if int(tid) % 2 == 0]
    https_vector = [classifications[run_idx][tid] for tid in test_ids if int(tid) % 2 != 0]

    # Top: HTTP (even)
    for i, status in enumerate(http_vector):
        ax.barh(y=2, width=1, left=i, height=0.8, color=colors[status], edgecolor='black', hatch=patterns[status])

    # Bottom: HTTPS (odd)
    for i, status in enumerate(https_vector):
        ax.barh(y=1, width=1, left=i, height=0.8, color=colors[status], edgecolor='black', hatch=patterns[status])

    ax.set_xlim(-2, max(len(http_vector), len(https_vector)))
    ax.set_ylim(0.5, 2.5)
    ax.set_yticks([1, 2])
    ax.set_yticklabels(['HTTPS (odd)', 'HTTP (even)'], fontsize=10)
    ax.set_xticks(range(0, max(len(http_vector), len(https_vector)), 5))
    ax.set_xticklabels([str(i) for i in range(0, max(len(http_vector), len(https_vector)), 5)], fontsize=10)
    ax.set_title(f'Run {run_idx}', fontsize=14, fontweight='bold')

    for spine in ax.spines.values():
        spine.set_visible(False)

# 7) Add legend
legend_handles = [
    mpatches.Patch(facecolor=colors[key], edgecolor='black', hatch=patterns[key], label=key)
    for key in [
        'Match', 
        '503', 
        '403', 
        'HandshakeTimeout', 
        'ConnReset',
        'HTTPTimeout',
        'HTTPSTimeout', 
        'Other'
    ]
]

fig.legend(
    handles=legend_handles,
    title="Classification",
    title_fontsize=12,
    fontsize=11,
    loc='lower center',
    ncol=5,
    frameon=True
)

# 8) Save plot
plt.tight_layout(rect=[0, 0.08, 1, 1])
plt.savefig('http_simple_matrix_vector.png', dpi=300, bbox_inches='tight')
print("✅ Updated matrix-style chart saved as 'http_simple_matrix_vector.png'")
