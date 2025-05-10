# Worker Test Campaign Generator

This project generates test campaign configurations by pairing worker profiles and combining them with test templates. It reads worker data from YAML files, expands parameter combinations, and outputs a comprehensive test campaign file.

## Features

- Loads worker profiles from a directory
- Loads test trees with parameters from another directory
- Supports dynamic parameter expansion via file references
- Generates all possible worker pairings (permutations)
- Outputs a single YAML file (`campaign.yml`) containing test cases

## Dependencies

- Python 3.x

Install dependencies:

```bash
pip install -r requirements.txt
```

## File Structure

```
project/
│
├── profiles/              # Directory containing worker profile YAML files
│   └── \*.yml             # Individual worker profile files
│
├── tests-trees/           # Directory containing test tree YAML files
│   └── \*.yml             # Test tree definitions with parameter specs
│
├── campaign.yml           # Output file containing all test combinations
├── generator.py           # Main script (the one shown above)
└── README.md              # This file
```

## Usage

1. **Prepare Worker Profiles**  
   Place worker YAML files in the `./profiles/` folder. Each file should contain a dictionary representing a worker.

2. **Prepare Test Trees**  
   Place test tree YAML files in the `./tests-trees/` folder. Each file should define:

   - `name`: Name of the test
   - `worker_1_role`, `worker_2_role`: Roles assigned to workers
   - `parameters`: (Optional) Dictionary of static values and/or dynamic references to lists (e.g. `@file:params.yml`)

3. **Run the Script**

   ```bash
   python generator.py
   ```

   This generates `campaign.yml` containing all permutations of workers and parameter combinations.

## Example `parameters` Field

```yaml
parameters:
  dst_port: 443
  config: "@file:configs.yml"
```

Where `configs.yml` is a YAML file containing a list of possible values for `config`.

## Output

Each entry in `campaign.yml` will look like:

```yaml
- id: 1
  name: Example Test
  Worker_1:
    name: VPS_1
    role: client
    ...
  Worker_2:
    name: VPS_2
    role: server
    ...
  parameters:
    dst_port: 443
    server_ip: 10.78.89.43
```
