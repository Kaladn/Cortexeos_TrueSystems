import itertools
import json

def generate_dot_patterns_3_stationary_1_variable_8x8():
    """Generates unique 8x8 grid symbols using 3 stationary and 1 variable dot method."""
    grid_size = 8
    num_positions = grid_size * grid_size
    positions = list(range(num_positions))  # 64 positions in an 8x8 grid
    dot_patterns = set()

    # Generate all possible placements of 3 stationary dots
    stationary_dot_combinations = itertools.combinations(positions, 3)

    for stationary_dots in stationary_dot_combinations:
        remaining_positions = [pos for pos in positions if pos not in stationary_dots]

        # Place the 1 variable dot in all remaining positions
        for variable_dot_pos in remaining_positions:
            pattern = 0  # Binary representation of the 8x8 grid
            for pos in stationary_dots:
                pattern |= (1 << pos)  # Set the bit for each stationary dot
            pattern |= (1 << variable_dot_pos)  # Set the bit for the variable dot
            dot_patterns.add(pattern)

    return list(dot_patterns)

def save_symbols_to_json(symbols, filename="symbolis_symbols.json"):
    """Saves generated symbols to a JSON file."""
    with open(filename, "w") as f:
        json.dump(symbols, f, indent=4)
    print(f"✅ {len(symbols)} symbols saved to {filename}")

# Generate and save symbols
symbols = generate_dot_patterns_3_stationary_1_variable_8x8()
save_symbols_to_json(symbols)
