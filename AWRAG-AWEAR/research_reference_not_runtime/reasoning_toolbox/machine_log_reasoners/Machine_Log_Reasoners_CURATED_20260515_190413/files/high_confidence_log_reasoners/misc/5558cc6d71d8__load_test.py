#!/usr/bin/env python3
"""
Wolf Engine Cluster - Load Test
Tests throughput and compound intelligence
"""

import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load config
with open('../configs/cluster_config.json') as f:
    config = json.load(f)

API_IP = config['nodes']['node3']['ip']
API_PORT = config['services']['api']['port']
API_URL = f"http://{API_IP}:{API_PORT}"

# Test queries
TEST_QUERIES = [
    "data agnostic architecture",
    "6-1-6 is N-N-N adjustable",
    "cpu clusters beat gpu farms",
    "build today not tomorrow",
    "ephemeral interface persistent memory",
    "compound intelligence grows over time",
    "distributed over centralized",
    "practical over theoretical",
    "cheap and working beats expensive",
    "evidence first not explanation"
]

def send_query(query, query_id):
    """Send single query to Wolf Engine"""
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_URL}/think",
            json={"input": query, "type": "question"},
            timeout=5
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            return {
                "query_id": query_id,
                "query": query,
                "status": "success",
                "response": result.get("response"),
                "elapsed_ms": elapsed * 1000,
                "anchors_created": result.get("anchors_created", 0)
            }
        else:
            return {
                "query_id": query_id,
                "query": query,
                "status": "error",
                "error": f"HTTP {response.status_code}",
                "elapsed_ms": elapsed * 1000
            }
    
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "query_id": query_id,
            "query": query,
            "status": "error",
            "error": str(e),
            "elapsed_ms": elapsed * 1000
        }

def run_load_test(num_queries=100, num_threads=10):
    """Run load test with multiple concurrent queries"""
    
    print("=== Wolf Engine Load Test ===")
    print(f"Target: {API_URL}")
    print(f"Queries: {num_queries}")
    print(f"Threads: {num_threads}")
    print("")
    
    # Get initial stats
    print("Getting initial stats...")
    initial_stats = requests.get(f"{API_URL}/stats").json()
    print(f"Initial anchors: {initial_stats.get('total_anchors', 0)}")
    print("")
    
    # Run load test
    print("Starting load test...")
    start_time = time.time()
    
    results = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        
        for i in range(num_queries):
            query = TEST_QUERIES[i % len(TEST_QUERIES)]
            future = executor.submit(send_query, query, i)
            futures.append(future)
        
        # Collect results
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            
            if len(results) % 10 == 0:
                print(f"Completed: {len(results)}/{num_queries}")
    
    total_time = time.time() - start_time
    
    # Get final stats
    print("")
    print("Getting final stats...")
    final_stats = requests.get(f"{API_URL}/stats").json()
    print(f"Final anchors: {final_stats.get('total_anchors', 0)}")
    print("")
    
    # Analyze results
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")
    
    latencies = [r["elapsed_ms"] for r in results if r["status"] == "success"]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    
    throughput = num_queries / total_time
    
    anchors_created = final_stats.get('total_anchors', 0) - initial_stats.get('total_anchors', 0)
    
    # Print results
    print("=== Load Test Results ===")
    print("")
    print(f"Total Queries:     {num_queries}")
    print(f"Successful:        {success_count}")
    print(f"Errors:            {error_count}")
    print(f"Success Rate:      {success_count/num_queries*100:.1f}%")
    print("")
    print(f"Total Time:        {total_time:.2f}s")
    print(f"Throughput:        {throughput:.2f} queries/sec")
    print("")
    print(f"Avg Latency:       {avg_latency:.2f}ms")
    print(f"Min Latency:       {min_latency:.2f}ms")
    print(f"Max Latency:       {max_latency:.2f}ms")
    print("")
    print(f"Anchors Created:   {anchors_created}")
    print(f"Total Anchors:     {final_stats.get('total_anchors', 0)}")
    print(f"Total Chains:      {final_stats.get('total_chains', 0)}")
    print(f"Patterns:          {final_stats.get('patterns', 0)}")
    print(f"Avg Resonance:     {final_stats.get('avg_resonance', 0):.2f}")
    print("")
    
    # Check if we hit performance targets
    target_latency = config['performance_targets']['latency_ms']
    
    if avg_latency < target_latency:
        print(f"✓ Latency target met ({avg_latency:.2f}ms < {target_latency}ms)")
    else:
        print(f"✗ Latency target missed ({avg_latency:.2f}ms > {target_latency}ms)")
    
    if success_count == num_queries:
        print("✓ 100% success rate")
    else:
        print(f"✗ {error_count} errors occurred")
    
    print("")
    print("=== Load Test Complete ===")

if __name__ == "__main__":
    import sys
    
    num_queries = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    num_threads = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    run_load_test(num_queries, num_threads)
