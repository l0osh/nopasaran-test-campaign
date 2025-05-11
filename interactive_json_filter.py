import json
import os
from datetime import datetime

def load_json(filename="results.json"):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: File '{filename}' is not valid JSON.")
        exit(1)

def get_unique_values(data, field):
    return sorted({entry.get(field) for entry in data.values() if entry.get(field) is not None})

def prompt_for_field_choice(fields):
    while True:
        print("\nAvailable filter fields:")
        for i, field in enumerate(fields):
            print(f"{i + 1}. {field}")
        choice = input("Select field to filter by (number): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(fields):
            return fields[int(choice) - 1]
        print("Invalid selection. Try again.")

def prompt_for_value_choice(field, values):
    while True:
        print(f"\nAvailable values for '{field}':")
        for i, value in enumerate(values):
            print(f"{i + 1}. {value}")
        choice = input(f"Select value for '{field}' (number): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(values):
            return values[int(choice) - 1]
        print("Invalid selection. Try again.")

def interactive_filter_menu(data):
    filters = {}
    flat_entries = {
        k: {
            'worker_1': v.get('worker_1'),
            'worker_2': v.get('worker_2'),
            'status': v.get('status'),
            'test_name': v.get('test_name'),
        }
        for k, v in data.items()
    }

    while True:
        print("\nCurrent filters:")
        if filters:
            for k, v in filters.items():
                print(f"- {k}: {v}")
        else:
            print("None")

        action = input("\nActions: [A]dd filter, [R]emove filter, [F]inish filtering: ").strip().lower()

        if action == 'f':
            break
        elif action == 'a':
            field = prompt_for_field_choice(['worker_1', 'worker_2', 'status', 'test_name'])
            values = get_unique_values(flat_entries, field)
            if not values:
                print(f"No values found for '{field}'.")
                continue
            value = prompt_for_value_choice(field, values)
            filters[field] = value
        elif action == 'r':
            if not filters:
                print("No filters to remove.")
                continue
            for i, k in enumerate(filters):
                print(f"{i + 1}. {k}")
            choice = input("Select filter to remove (number): ")
            if choice.isdigit() and 1 <= int(choice) <= len(filters):
                key = list(filters.keys())[int(choice) - 1]
                del filters[key]
        else:
            print("Invalid action.")

    # Filter entries
    filtered = {
        k: data[k] for k, flat in flat_entries.items()
        if all(flat.get(fk) == fv for fk, fv in filters.items())
    }

    return filtered, filters

def generate_filename(filters):
    if not filters:
        return "filtered_results.json"
    filter_part = "_".join(f"{k}={v}" for k, v in filters.items())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"filtered_{filter_part}_{timestamp}.json".replace(" ", "_")

def save_json(data, filters):
    filename = generate_filename(filters)
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n✅ Saved filtered results to '{filename}'.")

def main():
    print("📦 Loading 'results.json'...")
    data = load_json("results.json")
    filtered, filters = interactive_filter_menu(data)
    if not filtered:
        print("\n⚠️ No entries matched your filters.")
    else:
        save_json(filtered, filters)

if __name__ == "__main__":
    main()
