import os
import json
import yaml  # Assumes profile files are YAML

# Paths
profiles_dir = "profiles"
results_file = "run_all_workers_conformance_results.json"
output_file = "run_all_workers_conformance_results.json"  # Or overwrite: use results_file

# Collect all valid worker names from profile files
valid_names = set()

for filename in os.listdir(profiles_dir):
    if filename.endswith(".yml") or filename.endswith(".yaml") or filename.endswith(".txt") or filename.endswith(".json"):
        path = os.path.join(profiles_dir, filename)
        with open(path, "r") as f:
            try:
                profile_data = yaml.safe_load(f)
                name = profile_data.get("name")
                if name:
                    valid_names.add(name)
            except Exception as e:
                print(f"Error parsing {filename}: {e}")

# Load test results
with open(results_file, "r") as f:
    test_results = json.load(f)

# Filter entries
filtered_results = {
    test_id: data for test_id, data in test_results.items()
    if data.get("worker_1") in valid_names and data.get("worker_2") in valid_names
}

# Save filtered results
with open(output_file, "w") as f:
    json.dump(filtered_results, f, indent=2)

print(f"Filtered {len(test_results) - len(filtered_results)} entries. Saved to {output_file}")
