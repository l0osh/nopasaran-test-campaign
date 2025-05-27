import os
import yaml
from itertools import permutations, product
import copy

class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def read_worker_profiles(profiles_folder='./profiles'):
    worker_data = []
    for filename in sorted(os.listdir(profiles_folder)):
        file_path = os.path.join(profiles_folder, filename)
        if filename.endswith(".yml"):
            with open(file_path, 'r') as file:
                try:
                    data = yaml.safe_load(file)
                    worker_data.append(data)
                except yaml.YAMLError as e:
                    print(f"Error reading {filename}: {e}")
                    continue

    worker_data.sort(key=lambda x: x.get("name", ""))

    worker_pairs = []
    for pair in permutations(worker_data, 2):
        worker_pairs.append({
            "Worker_1": pair[0],
            "Worker_2": pair[1]
        })
    return worker_pairs


def resolve_file_references(data):
    if isinstance(data, dict):
        return {k: resolve_file_references(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [resolve_file_references(i) for i in data]
    elif isinstance(data, str) and data.startswith("@file:"):
        file_path = data.replace("@file:", "")
        if os.path.isfile(file_path):
            with open(file_path, 'r') as f:
                content = yaml.safe_load(f)
                return content
        else:
            raise FileNotFoundError(f"Referenced file not found: {file_path}")
    else:
        return data



def expand_parameters(params, test_name=None):
    def collect_dynamic_parameters(obj, path_prefix=""):
        static = {}
        dynamic = {}

        for key, value in obj.items():
            full_key = f"{path_prefix}{key}" if path_prefix else key

            if isinstance(value, dict):
                nested_static, nested_dynamic = collect_dynamic_parameters(value, f"{full_key}.")
                static[key] = nested_static
                dynamic.update(nested_dynamic)
            elif isinstance(value, str) and value.startswith("@file:"):
                file_path = value.replace("@file:", "")
                if os.path.isfile(file_path):
                    with open(file_path, 'r') as f:
                        content = yaml.safe_load(f)
                        if isinstance(content, list):
                            dynamic[full_key] = content
                        else:
                            raise ValueError(f"File {file_path} does not contain a list.")
                else:
                    raise FileNotFoundError(f"Referenced file not found: {file_path}")
            else:
                static[key] = value

        return static, dynamic

    static, dynamic = collect_dynamic_parameters(params)

    static["controller_conf_filename"] = "controller_configuration.json"

    if not dynamic:
        if test_name == "http_simple_request":
            return [dict(static, use_https="0"), dict(static, use_https="1")]
        return [static]

    keys, values = zip(*sorted(dynamic.items()))

    if len(set(map(len, values))) == 1:
        combinations_list = [dict(zip(keys, items)) for items in zip(*values)]
    else:
        combinations_list = [dict(zip(keys, combo)) for combo in product(*values)]

    expanded = []
    for combo in combinations_list:
        param_set = copy.deepcopy(static)

        for full_key, value in combo.items():
            keys_path = full_key.split(".")
            target = param_set
            for k in keys_path[:-1]:
                target = target.setdefault(k, {})
            target[keys_path[-1]] = value

        param_set = resolve_file_references(param_set)

        domain = param_set.get("domain")
        request_data = param_set.get("request-data", {})
        if isinstance(request_data, dict) and domain:
            request_data["host"] = domain
            param_set["request-data"] = request_data

        if test_name == "http_simple_request":
            expanded.append(dict(param_set, use_https="0"))
            expanded.append(dict(param_set, use_https="1"))
        else:
            expanded.append(param_set)

    return expanded




def load_all_test_trees(tests_folder='./tests-trees'):
    test_trees = []
    for filename in sorted(os.listdir(tests_folder)):
        if filename.endswith('.yml') or filename.endswith('.yaml'):
            path = os.path.join(tests_folder, filename)
            try:
                with open(path, 'r') as f:
                    data = yaml.safe_load(f)

                # PATCH: Ensure qname in response_spec matches top-level qname
                if (
                    isinstance(data, dict)
                    and data.get("name") == "udp_dns_qname_probing"
                    and isinstance(data.get("parameters"), dict)
                ):
                    qname_value = data["parameters"].get("qname")
                    if isinstance(data["parameters"].get("response_spec"), dict):
                        data["parameters"]["response_spec"]["qname"] = qname_value

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

            # Rule 1: Skip mirrored roles for http_simple_request (keep one direction only)
            if test_name == "http_simple_request":
                if pair["Worker_1"]["name"] > pair["Worker_2"]["name"]:
                    continue

            # Rule 2: Server (Worker_2) must be internet accessible for all tests
            if not pair["Worker_2"].get("internet_accessible", False):
                continue

            # Additional skip for intranet-restricted tests
            if test_name in ["https_sni", "udp_dns_qname_probing", "http_1_conformance"]:
                if not pair["Worker_2"].get("intranet_accessible", False):
                    continue

            parameter_sets = expand_parameters(test.get("parameters", {}), test_name=test_name)
            for params in parameter_sets:
                # Inject target IP if not http_simple_request
                if test_name != "http_simple_request":
                    params["ip"] = pair["Worker_2"]["ip"]

                # Add identifier for https_sni
                if test_name in ["https_sni"]:
                    params["identifier"] = params.get("ip", pair["Worker_2"]["ip"])

                campaign_entry = {
                    "id": test_id,
                    "name": test["name"],
                    "Worker_1": {**pair["Worker_1"], "role": test["worker_1_role"]},
                    "Worker_2": {**pair["Worker_2"], "role": test["worker_2_role"]},
                    "parameters": params
                }

                # Apply special filters for dns_qname_prober
                if test_name == "udp_dns_qname_probing":
                    w1_ip = pair["Worker_1"]["ip"]
                    w2_ip = pair["Worker_2"]["ip"]


                campaign_entries.append(campaign_entry)
                test_id += 1

    def custom_representer(dumper, data):
        if isinstance(data, list) and all(isinstance(i, list) and len(i) == 2 for i in data):
            return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)
        return dumper.represent_list(data)

    NoAliasDumper.add_representer(list, custom_representer)

    with open(campaign_output_file, 'w') as f:
        yaml.dump(campaign_entries, f, Dumper=NoAliasDumper, default_flow_style=False)

if __name__ == "__main__":
    main()
