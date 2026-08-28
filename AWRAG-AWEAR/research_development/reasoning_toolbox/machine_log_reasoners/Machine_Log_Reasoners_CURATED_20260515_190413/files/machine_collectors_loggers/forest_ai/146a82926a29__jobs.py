'''
Jobs command group for monitoring and managing asynchronous tasks.
'''

import logging
import json
from pathlib import Path

# This is a placeholder implementation. In a real system, this would
# interact with a proper job queue (e.g., Redis, RabbitMQ, or a database).

def get_job_log_path(config_loader):
    return config_loader.base_path / "logs" / "jobs.jsonl"

def list_jobs(args):
    logger = logging.getLogger("jobs_cmd")
    job_log_file = get_job_log_path(args.config_loader)

    if not job_log_file.exists():
        print("No job history found.")
        return

    with open(job_log_file, "r") as f:
        lines = f.readlines()

    print(f"{'ID':<15} {'TYPE':<15} {'STATUS':<12} {'NOTE'}")
    # Display last 10 jobs for brevity
    for line in lines[-10:]:
        job = json.loads(line)
        print(f"{job['job_id']:<15} {job['type']:<15} {job['status']:<12} {job.get('note', 'N/A')}")

def register(subparsers, config_loader, plugin_manager):
    '''Registers the jobs command group.'''
    parser = subparsers.add_parser("jobs", help="Monitor and manage asynchronous tasks.")
    jobs_subparsers = parser.add_subparsers(dest="action", help="Job actions")

    # List command
    list_parser = jobs_subparsers.add_parser("list", help="List recent jobs.")
    list_parser.set_defaults(func=list_jobs, config_loader=config_loader)

