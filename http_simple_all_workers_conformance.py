import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict

# Load classification data
with open('run_all_workers_simple_results.json', 'r') as f:
    data = json.load(f)

# Load naming map
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

# Group by worker pairs
pairwise_data = defaultdict(list)
for tid, entry in sorted(data.items(), key=lambda x: int(x[0])):  # sort by test ID
    pair = (entry['worker_1'], entry['worker_2'])
    pairwise_data[pair].append((tid, entry))

# Classify entries
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


# Apply classification
classified_by_pair = defaultdict(lambda: {'HTTP': [], 'HTTPS': []})
for pair, entries in pairwise_data.items():
    for i, (tid, entry) in enumerate(entries):
        protocol = 'HTTP' if i % 2 == 0 else 'HTTPS'
        status = classify_entry(entry)
        classified_by_pair[pair][protocol].append((int(tid), status))

# Style settings
patterns = {
    'Match':           '//',
    'Other':           '...',
    '503':             '\\\\',
    '403':             '++',
    'HandshakeTimeout':'--',
    'ConnReset':       'oo',
    'HTTPTimeout':     '++',
    'HTTPSTimeout':    '--',
    'SubmissionFailed': '',
    'PollingFailed':   '///',
    'WorkerMissing':   'xx'
}

colors = {
    'Match':           'green',
    'Other':           'dimgray',
    '503':             'red',
    '403':             'orange',
    'HandshakeTimeout':'lightblue',
    'ConnReset':       'purple',
    'HTTPTimeout':     'pink',
    'HTTPSTimeout':    'pink',
    'SubmissionFailed':'black',
    'PollingFailed':   'black',
    'WorkerMissing':   'black'
}


# Plotting function
def plot_classification_group(protocol, output_file):
    fig, ax = plt.subplots(figsize=(15, 6))
    y_spacing = 0.65
    bar_height = 0.6

    all_pairs = sorted(classified_by_pair.keys())
    y_positions = [y_spacing * (len(all_pairs) - i) for i in range(len(all_pairs))]

    present_statuses = set()

    for idx, pair in enumerate(all_pairs):
        y = y_positions[idx]
        test_vector = classified_by_pair[pair][protocol]
        test_vector.sort()
        statuses = [status for _, status in test_vector]
        present_statuses.update(statuses)

        for i, status in enumerate(statuses):
            ax.barh(
                y=y,
                width=1,
                left=i,
                height=bar_height,
                color=colors.get(status, 'gray'),
                edgecolor='black',
                hatch=patterns.get(status, '')
            )

        # Use mapped + subscripted name
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

    def legend_sort_key(status):
        if status == 'Match':
            return '0'
        if status == 'Other':
            return 'zzz'
        return status

    sorted_statuses = sorted(present_statuses, key=legend_sort_key)

    # Legend
    legend_handles = [
        mpatches.Patch(facecolor=colors[key], edgecolor='black', hatch=patterns[key], label=key)
        for key in sorted_statuses
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
    max_len = max(len(v[protocol]) for v in classified_by_pair.values())
    ax.set_xlim(-6, max(10, max_len))
    ax.set_ylim(0, y_spacing * len(all_pairs) + 0.2)
    xtick_positions = list(range(0, max_len + 1, 5))
    ax.set_xticks(xtick_positions)
    ax.set_xticklabels([str(i) for i in xtick_positions], fontsize=11)

    ax.set_xlabel('Domain Name ID', fontsize=13, fontweight='bold')

    # Hide spines and y-axis details
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis='y', which='both', left=False, labelleft=False)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Chart saved: {output_file}")

# Generate both plots
plot_classification_group('HTTP', 'http_vector_by_pair.png')
plot_classification_group('HTTPS', 'https_vector_by_pair.png')
