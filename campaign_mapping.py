import yaml
import json

def load_campaign(filename):
    with open(filename, 'r') as f:
        return yaml.safe_load(f)

def get_fingerprint(entry):
    test_name = entry.get("name")
    w1 = entry["Worker_1"]["name"]
    w2 = entry["Worker_2"]["name"]
    params = entry.get("parameters", {})

    base = [test_name, w1, w2, params.get("ip"), params.get("port")]

    if test_name == "https_sni":
        base.append(params.get("domain"))
    elif test_name == "http_1_conformance":
        base.append(params.get("request-data", {}).get("host"))
    elif test_name == "udp_dns_qname_prober":
        base.append(params.get("qname"))
    elif test_name == "http_simple_request":
        base.append(params.get("hostname"))
    else:
        base.append(str(params))  # fallback

    return tuple(base)

def build_id_mapping(old_campaign, new_campaign):
    old_fingerprints = {get_fingerprint(entry): entry for entry in old_campaign}
    new_fingerprints = {get_fingerprint(entry): entry["id"] for entry in new_campaign}

    id_mapping = {}
    missing_entries = []

    for fp, old_entry in old_fingerprints.items():
        new_id = new_fingerprints.get(fp)
        if new_id:
            id_mapping[old_entry["id"]] = new_id
        else:
            missing_entries.append(old_entry)

    return id_mapping, missing_entries

def update_results_file(old_results_path, id_mapping, missing_entries, output_path="results_mapped.json"):
    with open(old_results_path, 'r') as f:
        results = json.load(f)

    missing_ids = {entry["id"] for entry in missing_entries}
    cleaned_results = {}

    removed_count = 0
    remapped_count = 0
    skipped_workers = set()

    for old_id_str, result_entry in results.items():
        old_id = int(old_id_str)

        if old_id in missing_ids:
            removed_count += 1
            skipped_workers.add(result_entry["worker_1"])
            skipped_workers.add(result_entry["worker_2"])
            continue

        if old_id in id_mapping:
            new_id = id_mapping[old_id]
            cleaned_results[str(new_id)] = result_entry
            remapped_count += 1

    with open(output_path, 'w') as f:
        json.dump(cleaned_results, f, indent=2)

    print("\n✅ Result mapping complete.")
    print(f"✔️ Remapped: {remapped_count} tests")
    print(f"🗑️ Removed: {removed_count} tests")
    print(f"🧑 Skipped Workers: {', '.join(sorted(skipped_workers))}")

def main():
    old_campaign = load_campaign("old_campaign.yml") #insert campaign with the removed worker here (alyanetalyrz2)
    new_campaign = load_campaign("campaign.yml") #insert campaign without the removed worker here (alyanetalyrz2)

    id_mapping, missing_entries = build_id_mapping(old_campaign, new_campaign)
    update_results_file("run_1_http_results.json", id_mapping, missing_entries) # insert result file here

if __name__ == "__main__":
    main()
