import yaml
import json
import requests
import time
from datetime import datetime

results_log_file = "results_log.jsonl"

def log_result(entry):
    entry["timestamp"] = datetime.utcnow().isoformat() + "Z"
    with open(results_log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def poll_status(status_url, interval=5, timeout=120):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(status_url)
            response.raise_for_status()
            data = response.json()
            status = data.get("status")
            if status == "completed":
                print("Task completed. Result:")
                print(data.get("result"))
                return data.get("result")
            elif status == "failed":
                print("Task failed. Error:")
                print(data.get("error"))
                return None
            else:
                print(f"Task status: {status}. Retrying in {interval} seconds...")
        except requests.exceptions.RequestException as e:
            print(f"Polling failed: {e}")
            return None
        time.sleep(interval)
    print("Polling timed out.")
    return None


# Configuration
master = "mahmoudmaster.admin.master.nopasaran.org"
task_url = "https://www.nopasaran.org/api/v1/tests-trees/task"
campaign_file = "/Users/alyaalshaikh/Documents/nopasaranTrees/test_campaigns_nopasaran/campaign-runner/campaign.yml"

# Load test cases from YAML file
with open(campaign_file, "r") as file:
    test_campaign = yaml.safe_load(file)

# Submit each test in the campaign
for test in test_campaign:
    test_name = test.get("name", "unknown_test")
    test_id = test.get("id", "unknown_id")

    repository = "https://github.com/nopasaran-org/nopasaran-tests-trees"
    tests_tree = f"{test_name}.png"

    print(f"\nSubmitting test ID {test_id} - {test_name}")

    worker_1 = f"{test['Worker_1']['name']}.admin.worker.nopasaran.org"
    worker_2 = f"{test['Worker_2']['name']}.admin.worker.nopasaran.org"

    # Separate out controller_conf_filename and shared parameters
    controller_conf = test["parameters"].get("controller_conf_filename")
    shared_params = {
        k: v for k, v in test["parameters"].items()
        if k != "controller_conf_filename"
    }

    # Build variable payload with duplicated parameters
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

    print(payload)

    try:
        response = requests.post(
            task_url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        print("Task submitted successfully.")

        task_id = response.json().get("task_id")
        if task_id:
            status_url = f"{task_url}/{task_id}"
            result = poll_status(status_url)
            if result:
                print("Final result retrieved successfully.")
                log_result({
                    "test_id": test_id,
                    "test_name": test_name,
                    "status": "completed",
                    "result": result
                })
            else:
                print("Failed to retrieve final result.")
                log_result({
                    "test_id": test_id,
                    "test_name": test_name,
                    "status": "polling_failed",
                    "error": "Polling failed or timed out."
                })
        else:
            print("No task ID returned in response.")
            log_result({
                "test_id": test_id,
                "test_name": test_name,
                "status": "error",
                "error": "No task ID in response"
            })

    except requests.exceptions.RequestException as e:
        print(f"Submission failed for test ID {test_id}: {e}")
        log_result({
            "test_id": test_id,
            "test_name": test_name,
            "status": "submission_failed",
            "error": str(e)
        })
