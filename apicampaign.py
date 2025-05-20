import yaml
import json
import requests
import time
from datetime import datetime
from tqdm import tqdm
import os
import itertools

results_log_file = "results.json"

def load_existing_results():
    if os.path.exists(results_log_file):
        with open(results_log_file, "r") as f:
            return json.load(f)
    return {}

def save_results(results):
    sorted_results = {
        str(k): results[str(k)]
        for k in sorted((int(i) for i in results.keys() if i.isdigit()))
    }
    with open(results_log_file, "w") as f:
        json.dump(sorted_results, f, indent=2)

def log_result(results_dict, test_id, entry):
    ordered_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "worker_1": entry.pop("worker_1", None),
        "worker_2": entry.pop("worker_2", None),
        "polling_url": entry.pop("polling_url", None),
        **entry
    }
    results_dict[str(test_id)] = ordered_entry

def poll_status(status_url, progress_bar, interval=2, timeout=30):
    start_time = time.time()
    anim = itertools.cycle(["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"])
    while time.time() - start_time < timeout:
        progress_bar.set_description(f"Polling {next(anim)}")
        try:
            response = requests.get(status_url)
            response.raise_for_status()
            data = response.json()
            status = data.get("status")
            if status == "completed":
                return data.get("result")
            elif status == "failed":
                return None
        except requests.exceptions.RequestException:
            return None
        time.sleep(interval)
    return None

def extract_test_names(folder="./tests-trees"):
    names = set()
    for fname in os.listdir(folder):
        if fname.endswith(".yml") or fname.endswith(".yaml"):
            with open(os.path.join(folder, fname), "r") as f:
                try:
                    content = yaml.safe_load(f)
                    if isinstance(content, dict) and "name" in content:
                        names.add(content["name"])
                except Exception:
                    continue
    return sorted(names)

# --- Load and select tests ---
campaign_file = "./campaign.yml"
if not os.path.exists(campaign_file):
    raise FileNotFoundError("The campaign.yml file does not exist in the current directory.")

with open(campaign_file, "r") as file:
    test_campaign = yaml.safe_load(file)

existing_results = load_existing_results()

print("Test selection method:")
print("1. Run all tests")
print("2. Run by test ID range")
print("3. Run all tests with a specific name")
selection = input("Select option (1/2/3): ").strip()

while selection not in ("1", "2", "3"):
    selection = input("Please enter 1, 2, or 3: ").strip()

rerun_completed = False

if selection == "1":
    rerun_input = input("Re-run completed tests as well? (y/n): ").strip().lower()
    while rerun_input not in ("y", "n"):
        rerun_input = input("Please enter 'y' or 'n': ").strip().lower()
    rerun_completed = rerun_input == "y"

elif selection == "2":
    while True:
        try:
            start_id = int(input("Enter start test ID (inclusive): ").strip())
            end_id = int(input("Enter end test ID (inclusive): ").strip())
            selected_ids = list(range(start_id, end_id + 1))
            filtered = [t for t in test_campaign if t.get("id") in selected_ids]
            if filtered:
                test_campaign = filtered
                break
            else:
                print("No matching test IDs found in range.")
        except ValueError:
            print("Invalid input. Please enter numeric test IDs.")

elif selection == "3":
    names = extract_test_names()
    if not names:
        print("No test names found in tests-trees directory.")
        exit(1)

    print("\nAvailable test names:")
    for i, name in enumerate(names, start=1):
        print(f"{i}. {name}")

    while True:
        try:
            choice = int(input("\nEnter the number of the test to run: ").strip())
            if 1 <= choice <= len(names):
                selected_name = names[choice - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(names)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    filtered = [t for t in test_campaign if t.get("name") == selected_name]
    if not filtered:
        print(f"No tests found with the name '{selected_name}'. Exiting.")
        exit(1)
    test_campaign = filtered


# --- Configuration ---
master = "mahmoudmaster.admin.master.nopasaran.org"
task_url = "https://www.nopasaran.org/api/v1/tests-trees/task"
repository = "https://github.com/nopasaran-org/nopasaran-tests-trees"

# --- Main test loop ---
for test in test_campaign:
    test_name = test.get("name", "unknown_test")
    test_id = test.get("id", "unknown_id")

    worker_1_name = test["Worker_1"]["name"]
    worker_2_name = test["Worker_2"]["name"]

    if not rerun_completed and str(test_id) in existing_results and existing_results[str(test_id)]["status"] == "completed":
        continue

    bar_desc = f"Test {test_id}: {worker_1_name} ↔ {worker_2_name}"
    with tqdm(total=1, desc=bar_desc, unit="test", dynamic_ncols=True) as bar:
        tests_tree = f"{test_name}.png"
        worker_1 = f"{worker_1_name}.admin.worker.nopasaran.org"
        worker_2 = f"{worker_2_name}.admin.worker.nopasaran.org"

        controller_conf = test["parameters"].get("controller_conf_filename")
        shared_params = {
            k: v for k, v in test["parameters"].items()
            if k != "controller_conf_filename"
        }

        variables = {
            "Root": {
                "Worker_1": {
                    **{k: v for k, v in test["Worker_1"].items() if k != "parameters"},
                    "controller_conf_filename": controller_conf,
                    **shared_params
                },
                "Worker_2": {
                    **{k: v for k, v in test["Worker_2"].items() if k != "parameters"},
                    "controller_conf_filename": controller_conf,
                    **shared_params
                }
            }
        }

        payload = {
            "master": master,
            "first-worker": worker_1,
            "second-worker": worker_2,
            "repository": repository,
            "tests-tree": tests_tree,
            "variables": variables
        }

        try:
            tqdm.write(f"Submitting test {test_id} - {test_name}")
            response = requests.post(
                task_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()

            task_id = response.json().get("task_id")
            if task_id:
                status_url = f"{task_url}/{task_id}"
                result = poll_status(status_url, tqdm(desc=f"Polling {test_id}", total=0))
                log_result(existing_results, str(test_id), {
                    "worker_1": worker_1_name,
                    "worker_2": worker_2_name,
                    "polling_url": status_url,
                    "test_name": test_name,
                    "status": "completed" if result else "polling_failed",
                    "result": result if result else None,
                    "error": None if result else "Polling failed or timed out."
                })
            else:
                log_result(existing_results, str(test_id), {
                    "worker_1": worker_1_name,
                    "worker_2": worker_2_name,
                    "polling_url": None,
                    "test_name": test_name,
                    "status": "error",
                    "error": "No task ID in response"
                })

        except requests.exceptions.RequestException as e:
            log_result(existing_results, str(test_id), {
                "worker_1": worker_1_name,
                "worker_2": worker_2_name,
                "polling_url": None,
                "test_name": test_name,
                "status": "submission_failed",
                "error": str(e)
            })

        save_results(existing_results)
        bar.update(1)

