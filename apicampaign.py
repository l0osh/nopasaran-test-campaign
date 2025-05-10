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
        for k in sorted((int(i) for i in results.keys()))
    }
    with open(results_log_file, "w") as f:
        json.dump(sorted_results, f, indent=2)

def log_result(results_dict, test_id, entry):
    # Move timestamp and worker info to top
    ordered_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "worker_1": entry.pop("worker_1", None),
        "worker_2": entry.pop("worker_2", None),
        "polling_url": entry.pop("polling_url", None),
        **entry  # rest of the fields
    }
    results_dict[str(test_id)] = ordered_entry

def poll_status(status_url, progress_bar, interval=5, timeout=30):
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

# --- Load and select tests ---
campaign_file = "./campaign.yml"
with open(campaign_file, "r") as file:
    test_campaign = yaml.safe_load(file)

existing_results = load_existing_results()

# Ask whether to run all tests
run_all = input("Run all tests? (y/n): ").strip().lower()
while run_all not in ("y", "n"):
    run_all = input("Please enter 'y' or 'n': ").strip().lower()

rerun_completed = False
if run_all == "y":
    rerun_input = input("Re-run completed tests as well? (y/n): ").strip().lower()
    while rerun_input not in ("y", "n"):
        rerun_input = input("Please enter 'y' or 'n': ").strip().lower()
    rerun_completed = rerun_input == "y"
else:
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
                    "ip": test["Worker_1"]["ip"],
                    "controller_conf_filename": controller_conf,
                    **shared_params
                },
                "Worker_2": {
                    "ip": test["Worker_2"]["ip"],
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
                if result:
                    log_result(existing_results, test_id, {
                        "worker_1": worker_1_name,
                        "worker_2": worker_2_name,
                        "polling_url": status_url,
                        "test_name": test_name,
                        "status": "completed",
                        "result": result
                    })
                else:
                    log_result(existing_results, test_id, {
                        "worker_1": worker_1_name,
                        "worker_2": worker_2_name,
                        "polling_url": status_url,
                        "test_name": test_name,
                        "status": "polling_failed",
                        "error": "Polling failed or timed out."
                    })
            else:
                log_result(existing_results, test_id, {
                    "worker_1": worker_1_name,
                    "worker_2": worker_2_name,
                    "polling_url": None,
                    "test_name": test_name,
                    "status": "error",
                    "error": "No task ID in response"
                })

        except requests.exceptions.RequestException as e:
            log_result(existing_results, test_id, {
                "worker_1": worker_1_name,
                "worker_2": worker_2_name,
                "polling_url": None,
                "test_name": test_name,
                "status": "submission_failed",
                "error": str(e)
            })

        save_results(existing_results)
        bar.update(1)
