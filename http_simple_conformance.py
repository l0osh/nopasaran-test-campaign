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

def update_synthesis_file(classifications, test_ids, filename='synthesis.json'):
    synthesis = {}
    # Try to load existing synthesis file if it exists
    try:
        with open(filename, 'r') as f:
            synthesis = json.load(f)
    except FileNotFoundError:
        synthesis = {}

    synthesis['S1_HTTP'] = {}
    synthesis['S1_HTTPS'] = {}

    for tid in test_ids:
        tid_str = str(tid)
        # Collect classification results for this tid across runs
        run_results = [classifications[run_idx][tid_str] for run_idx in sorted(classifications)]

        non_matches = sum(1 for r in run_results if r != 'Match')
        status = 'Blocked' if non_matches >= 3 else 'Passed'

        if int(tid) % 2 == 0:
            synthesis['S1_HTTP'][tid_str] = status
        else:
            synthesis['S1_HTTPS'][tid_str] = status

    # Save the updated synthesis file
    with open(filename, 'w') as f:
        json.dump(synthesis, f, indent=2)
    print(f"✅ Synthesis file '{filename}' updated")


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

# Helper function for plotting (compact layout)
def plot_classification_group(protocol_name, is_https, output_file):
    fig, ax = plt.subplots(figsize=(len(test_ids)/8, 3.5))  # Reduced height for compactness

    n_runs = len(classifications)
    y_spacing = 0.4  # Distance between runs on y-axis
    bar_height = 0.35

    # New y_positions with tighter spacing
    y_positions = [y_spacing * (n_runs - i) for i in range(n_runs)]

    # Collect statuses present in the plot
    present_statuses = set()

    for idx, run_idx in enumerate(sorted(classifications)):
        y = y_positions[idx]
        if is_https:
            vector = [classifications[run_idx][tid] for tid in test_ids if int(tid) % 2 != 0]
        else:
            vector = [classifications[run_idx][tid] for tid in test_ids if int(tid) % 2 == 0]

        present_statuses.update(vector)

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

    # Legend only for statuses in current data
    legend_handles = [
        mpatches.Patch(facecolor=colors[key], edgecolor='black', hatch=patterns[key], label=key)
        for key in sorted(present_statuses)
    ]

    ax.legend(
        handles=legend_handles,
        title="Classification",
        title_fontsize=16,
        fontsize=13,
        loc='upper center',
        bbox_to_anchor=(0.5, -0.3),
        ncol=4,
        frameon=True
    )

    # Axes formatting
    ax.set_xlim(-6, len(test_ids) / 2)
    ax.set_ylim(0, y_spacing * n_runs + 0.2)  # Adjusted for tighter layout
    xtick_positions = list(range(0, int(len(test_ids) / 2), 5))
    ax.set_xticks(xtick_positions)
    ax.set_xticklabels([str(i) for i in xtick_positions], fontsize=11)

    # Add x-axis label
    ax.set_xlabel('Domain Name ID', fontsize=13, fontweight='bold')

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

update_synthesis_file(classifications, test_ids)
