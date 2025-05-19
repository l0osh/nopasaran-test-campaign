import json
import matplotlib.pyplot as plt

# Load input data
with open("enriched_filtered.json", "r") as f:
    data = json.load(f)

discrepancies = {}

for test_id, test_data in data.items():
    hostname = test_data.get("hostname")
    protocol = test_data.get("protocol")
    key = f"{hostname}_{protocol}"

    discrepancy_found = False
    result = test_data.get("result")

    if not result:
        discrepancies[key] = "no"
        continue

    for worker_key in ["Worker_1", "Worker_2"]:
        worker_data = result.get(worker_key, {}).get("Variables", {})

        dict_section = worker_data.get("dict", {}).get("result", {})
        sync_section = worker_data.get("sync_dict", {}).get("result", {})

        dict_results = dict_section.get("results")
        sync_results = sync_section.get("results")

        dict_errors = dict_section.get("errors")
        sync_errors = sync_section.get("errors")

        if dict_results != sync_results or dict_errors != sync_errors:
            discrepancy_found = True
            break

    discrepancies[key] = "yes" if discrepancy_found else "no"

# Save discrepancies JSON
with open("http_https_discrepancies.json", "w") as f:
    json.dump(discrepancies, f, indent=4)

print("✅ Discrepancy check complete — saved to 'http_https_discrepancies.json'")

# ------------------------
# Prepare data for vector chart

# Separate by protocol
http_results = []
https_results = []

for key, value in discrepancies.items():
    if key.endswith("_http"):
        http_results.append(value)
    elif key.endswith("_https"):
        https_results.append(value)

def create_bar_vector(results):
    """
    Create a list of 0/1 values for visualization:
    0 = match (no discrepancy)
    1 = discrepancy
    """
    return [1 if x == "yes" else 0 for x in results]

http_vector = create_bar_vector(http_results)
https_vector = create_bar_vector(https_results)

# Bar length (max length of either list)
max_len = max(len(http_vector), len(https_vector))

# Pad shorter list with zeros (assume no discrepancy for missing)
http_vector += [0] * (max_len - len(http_vector))
https_vector += [0] * (max_len - len(https_vector))

# ------------------------
# Plot vector chart

fig, ax = plt.subplots(figsize=(max_len/2, 2))

# Function to draw a horizontal bar with colored blocks
def draw_bar(y_pos, vector, label):
    for i, val in enumerate(vector):
        if val == 1:
            # Discrepancy = solid red block
            ax.barh(y=y_pos, width=1, left=i, height=0.8, color="red", edgecolor="black")
        else:
            # Match = hashed green block
            # We'll use hatching on a green block
            ax.barh(y=y_pos, width=1, left=i, height=0.8, color="green", edgecolor="black", hatch='//')
    ax.text(-1, y_pos, label, va="center", ha="right", fontsize=12, fontweight='bold')

draw_bar(1, http_vector, "HTTP")
draw_bar(0, https_vector, "HTTPS")

# Formatting
ax.set_xlim(-1, max_len)
ax.set_ylim(-0.5, 1.5)
ax.axis("off")
plt.title("Discrepancy Vector Chart: HTTP (top) vs HTTPS (bottom)")

plt.tight_layout()

# Save the vector chart as PNG image
plt.savefig("http_https_discrepancy_vector.png", dpi=150)
print("✅ Vector chart saved as 'http_https_discrepancy_vector.png'")

plt.show()
