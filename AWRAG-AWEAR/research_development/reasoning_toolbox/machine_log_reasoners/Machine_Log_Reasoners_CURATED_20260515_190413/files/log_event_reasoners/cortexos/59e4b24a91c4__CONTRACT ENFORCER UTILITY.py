"""
CortexOS Contract Enforcer — V1
Static Interface Verifier for All Modules
"""

import os
import ast
import traceback

# Define your CortexOS codebase root directory:
CORTEX_ROOT = r"C:\Users\Blame\Desktop\cortexos_organized"

# Collect all *.py files in full directory tree
def collect_python_files(root_dir):
    python_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for file in filenames:
            if file.endswith('.py'):
                full_path = os.path.join(dirpath, file)
                python_files.append(full_path)
    return python_files

# Analyze each file
def analyze_file(file_path):
    contracts = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=file_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                methods = []
                init_args = []
                for body_item in node.body:
                    if isinstance(body_item, ast.FunctionDef):
                        method_name = body_item.name
                        arg_names = [arg.arg for arg in body_item.args.args]
                        if method_name == "__init__":
                            init_args = arg_names[1:]  # skip self
                        else:
                            methods.append((method_name, arg_names[1:]))
                contracts.append({
                    "file": file_path,
                    "class": class_name,
                    "init_args": init_args,
                    "methods": methods
                })
    except Exception as e:
        contracts.append({
            "file": file_path,
            "error": str(e)
        })
    return contracts

# Full scan and report
def run_contract_enforcer():
    all_files = collect_python_files(CORTEX_ROOT)
    full_contracts = []
    for file_path in all_files:
        result = analyze_file(file_path)
        full_contracts.extend(result)

    return full_contracts

# Pretty output printer
def print_contracts(contracts):
    for contract in contracts:
        print("\n" + "="*80)
        print(f"FILE: {contract['file']}")
        if 'error' in contract:
            print(f"ERROR parsing: {contract['error']}")
            continue
        print(f"CLASS: {contract['class']}")
        print(f"Constructor Arguments: {contract['init_args']}")
        for method, args in contract['methods']:
            print(f"  METHOD: {method}({', '.join(args)})")

# RUN
if __name__ == "__main__":
    contracts = run_contract_enforcer()
    print_contracts(contracts)
