import os
import yaml
from itertools import permutations, product

class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

def read_worker_profiles(profiles_folder='./profiles'):
    worker_data = []
    for filename in os.listdir(profiles_folder):
        file_path = os.path.join(profiles_folder, filename)
        if filename.endswith(".yml"):
            with open(file_path, 'r') as file:
                try:
                    data = yaml.safe_load(file)
                    worker_data.append(data)
                except yaml.YAMLError as e:
                    print(f"Error reading {filename}: {e}")
                    continue

    worker_pairs = []
    for pair in permutations(worker_data, 2):
        worker_pairs.append({
            "Worker_1": pair[0],
            "Worker_2": pair[1]
        })
    return worker_pairs

def expand_parameters(params, test_name=None):
    static = {}
    dynamic = {}

    for key, value in params.items():
        if isinstance(value, str) and value.startswith("@file:"):
            file_path = value.replace("@file:", "")
            if os.path.isfile(file_path):
                with open(file_path, 'r') as f:
                    content = yaml.safe_load(f)
                    if isinstance(content, list):
                        dynamic[key] = content
                    else:
                        raise ValueError(f"File {file_path} does not contain a list.")
            else:
                raise FileNotFoundError(f"Referenced file not found: {file_path}")
        else:
            static[key] = value

    # Add controller config to all cases
    static["controller_conf_filename"] = "controller_configuration.json"

    if not dynamic:
        if test_name == "http_simple_request":
            return [dict(static, use_https="0"), dict(static, use_https="1")]
        return [static]

    keys, values = zip(*dynamic.items())

    if test_name == "http_simple_request":
        if len(set(map(len, values))) != 1:
            raise ValueError("Hostname and IP lists must be the same length for one-to-one mapping.")
        combinations_list = [dict(zip(keys, items)) for items in zip(*values)]
    else:
        combinations_list = [dict(zip(keys, combo)) for combo in product(*values)]

    expanded = []
    for combo in combinations_list:
        param_set = static.copy()
        param_set.update(combo)
        if test_name == "http_simple_request":
            # Create two versions: one with HTTPS, one without
            expanded.append(dict(param_set, use_https="0"))
            expanded.append(dict(param_set, use_https="1"))
        else:
            expanded.append(param_set)

    return expanded


def load_all_test_trees(tests_folder='./tests-trees'):
    test_trees = []
    for filename in os.listdir(tests_folder):
        if filename.endswith('.yml') or filename.endswith('.yaml'):
            path = os.path.join(tests_folder, filename)
            try:
                with open(path, 'r') as f:
                    data = yaml.safe_load(f)
                test_trees.append(data)
            except yaml.YAMLError as e:
                print(f"YAML error in {filename}: {e}")
            except FileNotFoundError as e:
                print(f"File reference error in {filename}: {e}")
    return test_trees

def main():
    campaign_output_file = "campaign.yml"
    worker_pairs = read_worker_profiles()
    test_cases = load_all_test_trees()

    campaign_entries = []
    test_id = 1

    for pair in worker_pairs:
        for test in test_cases:
            test_name = test["name"].lower()

            # Skip if Worker_2 is not accessible for server-required tests
            if test_name in ["https_sni", "dns_qname_probing"]:
                if not pair["Worker_2"].get("intranet_accessible", False):
                    continue

            parameter_sets = expand_parameters(test.get("parameters", {}), test_name=test_name)
            for params in parameter_sets:
                if test_name != "http_simple_request":
                    params["ip"] = pair["Worker_2"]["ip"]

                if test_name == "https_sni" or test_name == "dns_qname_probing":
                    params["identifier"] = params.get("ip", pair["Worker_2"]["ip"])


                campaign_entry = {
                    "id": test_id,
                    "name": test["name"],
                    "Worker_1": {**pair["Worker_1"], "role": test["worker_1_role"]},
                    "Worker_2": {**pair["Worker_2"], "role": test["worker_2_role"]},
                    "parameters": params
                }
                campaign_entries.append(campaign_entry)
                test_id += 1

# Add representer before dumping
    def custom_representer(dumper, data):
        if isinstance(data, list) and all(isinstance(i, list) and len(i) == 2 for i in data):
            return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)
        return dumper.represent_list(data)

    NoAliasDumper.add_representer(list, custom_representer)

    with open(campaign_output_file, 'w') as f:
        yaml.dump(campaign_entries, f, Dumper=NoAliasDumper, default_flow_style=False)


if __name__ == "__main__":
    main()




