import yaml
import json
import os

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
        base.append(params.get("use_https"))
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

def update_results_file(results_path, id_mapping, missing_entries):
    with open(results_path, 'r') as f:
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

    with open(results_path, 'w') as f:  # overwrite original file
        json.dump(cleaned_results, f, indent=2)

    print(f"\n📄 Updated: {results_path}")
    print(f"✔️ Remapped: {remapped_count} tests")
    print(f"🗑️ Removed: {removed_count} tests")
    print(f"🧑 Skipped Workers: {', '.join(sorted(skipped_workers)) if skipped_workers else 'None'}")

def main():
    old_campaign = load_campaign("old_campaign.yml")
    new_campaign = load_campaign("campaign.yml")

    id_mapping, missing_entries = build_id_mapping(old_campaign, new_campaign)

    for filename in os.listdir():
        if filename.endswith(".json") and "run" in filename:
            update_results_file(filename, id_mapping, missing_entries)

if __name__ == "__main__":
    main()
