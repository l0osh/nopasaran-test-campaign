import os
import yaml
from itertools import permutations, product

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

def expand_parameters(params):
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

    if not dynamic:
        return [static]

    # Cartesian product of all dynamic fields
    keys, values = zip(*dynamic.items())
    combinations_list = product(*values)

    expanded = []
    for combo in combinations_list:
        param_set = static.copy()
        param_set.update(dict(zip(keys, combo)))
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

    test_id = 1  # Start ID count

    for pair in worker_pairs:
        for test in test_cases:
            parameter_sets = expand_parameters(test.get("parameters", {}))
            for params in parameter_sets:
                campaign_entry = {
                    "id": test_id,
                    "name": test["name"],
                    "Worker_1": {**pair["Worker_1"], "role": test["worker_1_role"]},
                    "Worker_2": {**pair["Worker_2"], "role": test["worker_2_role"]},
                    "parameters": params
                }
                campaign_entries.append(campaign_entry)
                test_id += 1  # Increment ID for next test

    with open(campaign_output_file, 'w') as f:
        yaml.dump(campaign_entries, f)

if __name__ == "__main__":
    main()
