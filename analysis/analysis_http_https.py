import json

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

# Save results to a JSON file
with open("http_https_discrepancies.json", "w") as f:
    json.dump(discrepancies, f, indent=4)

print("✅ Discrepancy check complete — saved to 'http_https_discrepancies.json'")
