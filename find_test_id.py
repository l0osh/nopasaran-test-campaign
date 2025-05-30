import yaml

def load_campaign_file(path="campaign.yml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def extract_unique_tests(campaign):
    return sorted(set(entry["name"] for entry in campaign))

def extract_workers(campaign):
    workers = set()
    for entry in campaign:
        workers.add(entry["Worker_1"]["name"])
        workers.add(entry["Worker_2"]["name"])
    return sorted(workers)

def extract_domains(campaign, test_name_filter=None):
    domains = set()
    for entry in campaign:
        test_name = entry["name"]
        if test_name_filter and test_name != test_name_filter:
            continue
        params = entry.get("parameters", {})
        domain = None
        if test_name == "udp_dns_qname_prober":
            domain = params.get("qname")
        elif test_name == "http_simple_request":
            domain = params.get("hostname")
        elif test_name == "https_sni":
            domain = params.get("domain")
        elif test_name == "http_1_conformance":
            domain = params.get("request-data", {}).get("host")
        if domain:
            domains.add(domain)
    return sorted(domains)

def find_test_ids(campaign, test_name, w1, w2, domain):
    matched_ids = []
    for entry in campaign:
        if entry["name"] != test_name:
            continue
        if entry["Worker_1"]["name"] != w1 or entry["Worker_2"]["name"] != w2:
            continue

        params = entry.get("parameters", {})
        if test_name == "udp_dns_qname_prober" and params.get("qname") == domain:
            matched_ids.append(entry["id"])
        elif test_name == "http_simple_request" and params.get("hostname") == domain:
            matched_ids.append(entry["id"])
        elif test_name == "https_sni" and params.get("domain") == domain:
            matched_ids.append(entry["id"])
        elif test_name == "http_1_conformance" and params.get("request-data", {}).get("host") == domain:
            matched_ids.append(entry["id"])
    return matched_ids

def main():
    campaign_path = input("Enter path to campaign YAML file [default: campaign.yml]: ") or "campaign.yml"
    campaign = load_campaign_file(campaign_path)

    tests = extract_unique_tests(campaign)
    workers = extract_workers(campaign)

    print("\nAvailable Tests:")
    for i, t in enumerate(tests):
        print(f"  {i + 1}. {t}")
    test_idx = int(input("Choose test number: ")) - 1
    test_name = tests[test_idx]

    print("\nAvailable Workers:")
    for i, w in enumerate(workers):
        print(f"  {i + 1}. {w}")
    w1_idx = int(input("Choose Worker 1 number: ")) - 1
    w2_idx = int(input("Choose Worker 2 number: ")) - 1
    w1 = workers[w1_idx]
    w2 = workers[w2_idx]

    domains = extract_domains(campaign, test_name_filter=test_name)
    if not domains:
        print("\nNo domains found for the selected test.")
        return

    print("\nAvailable Domains:")
    for i, d in enumerate(domains):
        print(f"  {i + 1}. {d}")
    d_idx = int(input("Choose domain number: ")) - 1
    domain = domains[d_idx]

    ids = find_test_ids(campaign, test_name, w1, w2, domain)
    if ids:
        print("\nMatching Test ID(s):", ids)
    else:
        print("\nNo matching test found.")

if __name__ == "__main__":
    main()
