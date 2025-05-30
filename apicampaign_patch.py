import os
import json
import yaml
import requests

# Config
campaign_file = "./campaign.yml"
image_scripts = {
    "http_simple_request": "http_simple_all_workers_conformance.py",
    "http_1_conformance": "http_conformance_all_workers_conformance.py",
    "udp_dns_qname_prober": "dns_all_workers.py"

}
result_files = {
    "http_simple_request": "run_all_workers_simple_results.json",
    "http_1_conformance": "run_all_workers_conformance_results.json",
    "udp_dns_qname_prober": "run_all_workers_udp_dns_qname_prober_results.json"
}
task_url = "https://www.nopasaran.org/api/v1/tests-trees/task"
master = "mahmoudmaster.admin.master.nopasaran.org"
repository = "https://github.com/nopasaran-org/nopasaran-tests-trees"

# Prompt for test ID
test_id = input("Enter the test ID to run: ").strip()

# Load campaign
with open(campaign_file, "r") as f:
    campaign = yaml.safe_load(f)

test = next((t for t in campaign if str(t.get("id")) == test_id), None)

if not test:
    print(f"No test found with ID {test_id}")
else:
    test_name = test.get("name")
    if test_name not in image_scripts or test_name not in result_files:
        print(f"No image script or result file defined for test '{test_name}'")
    else:
        # Prepare payload
        worker_1 = f"{test['Worker_1']['name']}.admin.worker.nopasaran.org"
        worker_2 = f"{test['Worker_2']['name']}.admin.worker.nopasaran.org"
        tests_tree = f"{test_name}.png"
        controller_conf = test["parameters"].get("controller_conf_filename")
        shared_params = {k: v for k, v in test["parameters"].items() if k != "controller_conf_filename"}
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

        # Submit test
        print(f"Submitting test ID {test_id} ({test_name}) to NoPASARAN...")
        try:
            response = requests.post(task_url, json=payload)
            response.raise_for_status()
            task_id = response.json().get("task_id")
            print(f"Task submitted. Task ID: {task_id}")
        except requests.RequestException as e:
            print(f"Error submitting task: {e}")
            task_id = None

        # Save status
        results_file = result_files[test_name]
        if os.path.exists(results_file):
            with open(results_file, "r") as f:
                results = json.load(f)
        else:
            results = {}

        results[test_id] = {
            "worker_1": test["Worker_1"]["name"],
            "worker_2": test["Worker_2"]["name"],
            "status": "submitted" if task_id else "submission_failed",
            "test_name": test_name,
            "task_id": task_id
        }

        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        # Run image script
        if task_id:
            print(f"Running image script: {image_scripts[test_name]}")
            os.system(f"python {image_scripts[test_name]}")

