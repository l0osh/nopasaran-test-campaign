import json
import yaml

# Load JSON
with open("custom_filtered.json") as f:
    json_data = json.load(f)

# Load YAML
with open("campaign.yml") as f:
    yaml_data = yaml.safe_load(f)

# Create a lookup table from YAML by ID
yaml_lookup = {str(entry["id"]): entry for entry in yaml_data}

# Enrich JSON
for test_id, test_data in json_data.items():
    if test_id in yaml_lookup:
        campaign_entry = yaml_lookup[test_id]
        parameters = campaign_entry.get("parameters", {})

        # Determine protocol
        use_https = parameters.get("use_https", "0")
        protocol = "https" if use_https == "1" else "http"
        hostname = parameters.get("hostname", "")

        # Add to JSON
        test_data["protocol"] = protocol
        test_data["hostname"] = hostname

# Save enriched JSON
with open("enriched_filtered.json", "w") as f:
    json.dump(json_data, f, indent=2)
