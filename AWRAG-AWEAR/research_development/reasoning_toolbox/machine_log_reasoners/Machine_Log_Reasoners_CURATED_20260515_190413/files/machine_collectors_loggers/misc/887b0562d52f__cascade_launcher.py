
import yaml
from cascade_engine import CascadeEngine
from universal_loader import load_and_parse

def main(yaml_config_path):
    with open(yaml_config_path) as f:
        config = yaml.safe_load(f)

    data_result = load_and_parse(config["input_file"])

    if data_result["type"] == "fasta":
        sequence = "".join(data_result["sequences"])
        engine = CascadeEngine()
        results = engine.process(sequence, config)
        print("Results:", results)

    elif data_result["type"] == "table":
        for row in data_result["rows"]:
            data_string = "".join(str(row[field]) for field in config.get("bloom_fields", []))
            engine = CascadeEngine()
            results = engine.process(data_string, config)
            print("Row results:", results)

if __name__ == "__main__":
    import sys
    main(sys.argv[1])
