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

    if dict_result1 == sync_result1 and dict_result2 == sync_result2:
        return 'Match'

    status1 = dict_result1.get('results', {}).get('HTTP', {}).get('status')
    status2 = dict_result2.get('results', {}).get('HTTP', {}).get('status')

    if status1 == status2 and status1 is not None:
        return 'Match'

    if status1 == 503 or status2 == 503:
        return '503'
    if status1 == 403 or status2 == 403:
        return '403'

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

    return 'Other'

# 4) Classify
classifications = {run_idx: {} for run_idx in data}
for run_idx in data:
    for tid in test_ids:
        classifications[run_idx][tid] = classify_entry(data[run_idx][tid])

# 5) Styles
patterns = {
    'Match':           '//',
    'Other':           '...',
    'Empty':           'xx',
    '503':             '\\\\',
    '403':             '++',
    'HandshakeTimeout':'--',
    'ConnReset':       'oo',
    'HTTPTimeout':     '++',
    'HTTPSTimeout':    '--',
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

# Helper function for plotting
def plot_classification_group(protocol_name, is_https, output_file):
    fig, ax = plt.subplots(figsize=(len(test_ids)/8, 4.5))

    n_runs = len(classifications)
    y_positions = list(range(n_runs, 0, -1))

    # Collect statuses present in the plot
    present_statuses = set()

    for idx, run_idx in enumerate(sorted(classifications)):
        y = y_positions[idx]
        if is_https:
            vector = [classifications[run_idx][tid] for tid in test_ids if int(tid) % 2 != 0]
        else:
            vector = [classifications[run_idx][tid] for tid in test_ids if int(tid) % 2 == 0]

        # Track all statuses found in this vector
        present_statuses.update(vector)

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
            fontsize=16
        )

    # Create legend handles only for statuses present in data
    legend_handles = [
        mpatches.Patch(facecolor=colors[key], edgecolor='black', hatch=patterns[key], label=key)
        for key in sorted(present_statuses)
    ]

    ax.legend(
        handles=legend_handles,
        title="Classification",
        title_fontsize=18,
        fontsize=16,
        loc='lower center',
        bbox_to_anchor=(0.5, -0.5),
        ncol=4,
        frameon=True
    )

    # Axes formatting
    ax.set_xlim(-6, len(test_ids)/2)
    ax.set_ylim(0.5, n_runs + 0.5)
    xtick_positions = list(range(0, int(len(test_ids)/2), 5))
    ax.set_xticks(xtick_positions)
    ax.set_xticklabels([str(i) for i in xtick_positions], fontsize=13)

    # Hide unnecessary spines and y-axis ticks/labels
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    ax.tick_params(axis='y', which='both', left=False, labelleft=False)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Chart saved as '{output_file}'")



# 6) Save HTTP and HTTPS plots
plot_classification_group('HTTP', is_https=False, output_file='http_split_vector.png')
plot_classification_group('HTTPS', is_https=True, output_file='https_split_vector.png')
