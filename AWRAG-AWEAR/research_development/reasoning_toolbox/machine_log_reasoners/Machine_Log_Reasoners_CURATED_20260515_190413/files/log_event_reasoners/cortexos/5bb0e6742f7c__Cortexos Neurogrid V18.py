import uuid
import random
import json
import time

# Parameters
CUBE_SIZE = 99
CORE_RADIUS = 10  # reserved inner core
SNAPSHOT_DIR = "snapshots_v18"

# Initialize occupancy grid
occupancy = {}
for x in range(CUBE_SIZE):
    for y in range(CUBE_SIZE):
        for z in range(CUBE_SIZE):
            occupancy[(x, y, z)] = None

# Center of the cube
CENTER = (CUBE_SIZE // 2, CUBE_SIZE // 2, CUBE_SIZE // 2)

# Snapshot ID counter
snapshot_counter = 1

# Function to calculate Manhattan distance to center
def distance_to_center(pos):
    return sum(abs(a - b) for a, b in zip(pos, CENTER))

# Generate valid slots outside the reserved core
def generate_valid_slots():
    valid_slots = []
    for pos in occupancy:
        if occupancy[pos] is None and distance_to_center(pos) >= CORE_RADIUS:
            valid_slots.append(pos)
    return valid_slots

# Auto allocation based on sparsity
def allocate_neuron():
    global snapshot_counter
    valid_slots = generate_valid_slots()
    if not valid_slots:
        print("[ALLOCATOR] No available slots remaining!")
        return None
    
    # Sort slots by lowest neighboring occupancy (primitive heatmap balancing)
    scored_slots = []
    for pos in valid_slots:
        neighbors = get_neighbor_count(pos)
        scored_slots.append((neighbors, pos))
    scored_slots.sort()
    
    _, chosen_pos = scored_slots[0]
    neuron_id = str(uuid.uuid4())
    occupancy[chosen_pos] = neuron_id

    print(f"[ALLOC] Neuron {neuron_id} -> {chosen_pos}")
    save_snapshot(neuron_id, chosen_pos)
    snapshot_counter += 1
    return neuron_id

# Count occupied neighbors (heatmap primitive)
def get_neighbor_count(pos):
    x, y, z = pos
    count = 0
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            for dz in [-1, 0, 1]:
                if dx == dy == dz == 0:
                    continue
                nx, ny, nz = x + dx, y + dy, z + dz
                if 0 <= nx < CUBE_SIZE and 0 <= ny < CUBE_SIZE and 0 <= nz < CUBE_SIZE:
                    if occupancy[(nx, ny, nz)] is not None:
                        count += 1
    return count

# Save full RBMT snapshot after each allocation
def save_snapshot(neuron_id, pos):
    snapshot = {
        "snapshot": snapshot_counter,
        "last_neuron": neuron_id,
        "position": pos,
        "full_rbmt": {str(k): v for k, v in occupancy.items() if v is not None}
    }
    with open(f"{SNAPSHOT_DIR}/snapshot_{snapshot_counter}.json", "w") as f:
        json.dump(snapshot, f, indent=2)
    
# Export heatmap

def export_heatmap():
    heatmap = {}
    for pos in occupancy:
        heatmap[str(pos)] = 1 if occupancy[pos] else 0
    with open("heatmap_v18.json", "w") as f:
        json.dump(heatmap, f, indent=2)
    print("[EXPORT] Heatmap saved.")

# Main boot sequence
if __name__ == '__main__':
    import os
    if not os.path.exists(SNAPSHOT_DIR):
        os.makedirs(SNAPSHOT_DIR)

    start = time.time()
    
    # Allocate example neurons
    for _ in range(30):
        allocate_neuron()
        time.sleep(0.05)  # small pause to simulate time

    export_heatmap()
    
    uptime = time.time() - start
    print(f"[HEALTH] Uptime: {uptime:.2f}s | Total Neurons: {len([v for v in occupancy.values() if v is not None])}")
