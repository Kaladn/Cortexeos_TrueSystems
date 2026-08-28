
from topk_sparse_resonance import assess_resonance

# Test Case 1: Dense field with obvious matches
voxel_field_1 = {
    "v1": [0.8, 0.2, 0.1, 1.0, 0.5, 0.3],
    "v2": [0.7, 0.3, 0.2, 0.9, 0.4, 0.2],
    "v3": [0.9, 0.1, 0.1, 0.95, 0.5, 0.25],
    "v4": [0.1, 0.9, 0.8, 0.2, 0.1, 0.05],
    "v5": [0.85, 0.2, 0.15, 1.0, 0.55, 0.3]
}
harmonic_vector_1 = [0.75, 0.25, 0.15, 0.95, 0.45, 0.25]
print("Test Case 1: Dense Field with Obvious Matches")
matches, log = assess_resonance(harmonic_vector_1, voxel_field_1, k=3, threshold=0.85)
print("Top-k Matches:", matches)
print("Resonance Log:", log)

# Test Case 2: Sparse field with one strong match
voxel_field_2 = {
    "v1": [0.2, 0.1, 0.3, 0.4, 0.1, 0.2],
    "v2": [0.95, 0.05, 0.0, 1.0, 0.5, 0.3],  # Strong match
    "v3": [0.0, 0.9, 0.1, 0.3, 0.2, 0.1]
}
harmonic_vector_2 = [0.9, 0.1, 0.05, 1.0, 0.48, 0.29]
print("\nTest Case 2: Sparse Field with One Strong Match")
matches, log = assess_resonance(harmonic_vector_2, voxel_field_2, k=2, threshold=0.85)
print("Top-k Matches:", matches)
print("Resonance Log:", log)

# Test Case 3: No matches above threshold
voxel_field_3 = {
    "v1": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
    "v2": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
}
harmonic_vector_3 = [0.9, 0.9, 0.9, 0.9, 0.9, 0.9]
print("\nTest Case 3: No Matches Above Threshold")
matches, log = assess_resonance(harmonic_vector_3, voxel_field_3, k=2, threshold=0.95)
print("Top-k Matches:", matches)
print("Resonance Log:", log)
