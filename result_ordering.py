import os
import json
import glob

def sort_json_by_id(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Convert keys to integers for sorting, then back to strings for JSON
    sorted_data = {
        str(k): data[str(k)]
        for k in sorted((int(key) for key in data.keys()))
    }

    # Overwrite the file with sorted content
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(sorted_data, f, indent=2)
    print(f"Sorted: {filepath}")

def main():
    json_files = glob.glob("run*.json")
    for filepath in json_files:
        try:
            sort_json_by_id(filepath)
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

if __name__ == "__main__":
    main()
