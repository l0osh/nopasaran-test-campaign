import json
import yaml

file_paths = [
    "run_1_udp_dns_results.json",
    "run_2_udp_dns_results.json",
    "run_3_udp_dns_results.json",
    "run_4_udp_dns_results.json"
]
def load_json_file(path):
    with open(path, "r") as f:
        return json.load(f)
# Load the domain list from hostnames.yml
with open("inputs/hostnames.yml", "r") as f:
    expected_domains = set(d.strip().lower() for d in yaml.safe_load(f))

# Collect all domains seen in VPS3 queries
vps_domains = set()

for path in file_paths:
    data = load_json_file(path)
    for test_data in data.values():
        try:
            w2_received = test_data["result"]["Worker_2"]["Variables"]["dict"].get("received", {})
            if isinstance(w2_received, dict) and "questions" in w2_received:
                qname = w2_received["questions"][0].get("qname", "").strip().lower().rstrip(".")
                if qname:
                    vps_domains.add(qname)
        except Exception:
            continue

# Compare domains
missing_in_vps = expected_domains - vps_domains
unexpected_in_vps = vps_domains - expected_domains

missing_in_vps, unexpected_in_vps, len(missing_in_vps)

# --- Compare ---
missing_in_vps = expected_domains - vps_domains
unexpected_in_vps = vps_domains - expected_domains

# --- Report ---
print(f"\nExpected domains in hostnames.yml: {len(expected_domains)}")
print(f"Domains seen in VPS test runs: {len(vps_domains)}")
print(f"Missing from VPS: {len(missing_in_vps)}")
print(f"Unexpected in VPS: {len(unexpected_in_vps)}")

if missing_in_vps:
    print("\nDomains missing from VPS queries:")
    for d in sorted(missing_in_vps):
        print(f" - {d}")
