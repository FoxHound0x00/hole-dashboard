"""
Generate Persistent Homology Data for Dashboard

This script:
1. Creates blob clusters using sklearn
2. Performs persistent homology using the HOLE library
3. Generates cluster labels at different filtration thresholds
4. Computes pairwise distance matrices (structured based on clusters)
5. Saves all data as JSON for the frontend dashboard
"""

import json
import sys
import os

# Add the hole library to the path
sys.path.insert(0, '/home/sud/Documents/repos/hole-dashboard/services/backend/hole')

import numpy as np
from sklearn.datasets import make_blobs
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE, MDS
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
import hole
from hole.core import distance_metrics
from hole.visualization.cluster_flow import ClusterFlowAnalyzer

print("=" * 70)
print("PERSISTENT HOMOLOGY DATA GENERATION FOR DASHBOARD")
print("=" * 70)

# Output directory - data folder for better organization
output_dir = "/home/sud/Documents/repos/hole-dashboard/services/backend/data"

# ============================================================================
# 1. GENERATE BLOB CLUSTERS
# ============================================================================
print("\n[1/5] Generating blob clusters...")

# Create well-separated clusters
centers = np.array([
    [-8, -8, -8],
    [8, -8, 8],
    [-8, 8, 8],
    [8, 8, -8],
    [0, 0, 0]
])

n_samples = 250
points, true_labels = make_blobs(
    n_samples=n_samples,
    centers=centers,
    n_features=3,
    cluster_std=1.2,
    random_state=42
)

print(f"   ✓ Generated {n_samples} points in {len(centers)} clusters")
print(f"   ✓ Dimensionality: {points.shape[1]}D")
print(f"   ✓ Cluster distribution: {np.bincount(true_labels)}")

# Create outliers by swapping class labels
outlier_percentage = 0.10  # 10% of points become outliers
num_outliers = int(n_samples * outlier_percentage / 2)  # Divide by 2 since we swap pairs

print(f"\n   Creating outliers by swapping {num_outliers} pairs of labels...")

np.random.seed(42)
outlier_indices = []

for _ in range(num_outliers):
    # Pick two random points from DIFFERENT clusters
    attempts = 0
    while attempts < 100:
        idx1, idx2 = np.random.choice(n_samples, 2, replace=False)
        if true_labels[idx1] != true_labels[idx2]:
            # Swap their labels
            true_labels[idx1], true_labels[idx2] = true_labels[idx2], true_labels[idx1]
            outlier_indices.extend([idx1, idx2])
            break
        attempts += 1

print(f"   ✓ Created {len(outlier_indices)} outliers by label swapping")
print(f"   ✓ Outlier percentage: {len(outlier_indices)/n_samples*100:.1f}%")

# ============================================================================
# 2. COMPUTE DISTANCE MATRICES
# ============================================================================
print("\n[2/5] Computing distance matrices...")

distance_matrix_configs = {
    "euclid_dist": ("Euclidean", distance_metrics.euclidean_distance),
    "maha_dist": ("Mahalanobis", distance_metrics.mahalanobis_distance),
    "density_euclid": ("Density Euclidean", lambda pts: distance_metrics.density_normalized_distance(
        pts, distance_metrics.euclidean_distance(pts)
    )),
    "density_maha": ("Density Mahalanobis", lambda pts: distance_metrics.density_normalized_distance(
        pts, distance_metrics.mahalanobis_distance(pts)
    )),
}

computed_distance_matrices = {}
for key, (name, func) in distance_matrix_configs.items():
    print(f"   Computing {name}...")
    dist_matrix = func(points)
    computed_distance_matrices[key] = dist_matrix
    print(f"   ✓ {name}: {dist_matrix.shape}")

# ============================================================================
# 3. PERFORM PERSISTENT HOMOLOGY & EXTRACT CLUSTER LABELS
# ============================================================================
print("\n[3/5] Performing persistent homology analysis...")

# Store cluster labels at different thresholds for each metric
ph_data_all = {}

for metric_key, dist_matrix in computed_distance_matrices.items():
    print(f"\n   Processing {metric_key}...")
    
    # Create cluster flow analyzer
    analyzer = ClusterFlowAnalyzer(dist_matrix, max_thresholds=10)
    cluster_evolution = analyzer.compute_cluster_evolution(true_labels)
    
    # Extract labels at different thresholds
    # The ClusterFlowAnalyzer always uses "Euclidean" as the key regardless of input metric
    available_keys = list(cluster_evolution["labels_"].keys())
    labels_dict = cluster_evolution["labels_"][available_keys[0]]
    
    # Store the original labels
    ph_data_all[metric_key] = {
        "Original Labels": true_labels.tolist()
    }
    
    # Store labels at each threshold
    for threshold_key, ph_labels in labels_dict.items():
        ph_data_all[metric_key][threshold_key] = ph_labels.tolist()
    
    threshold_keys = list(labels_dict.keys())
    print(f"   ✓ Extracted {len(threshold_keys)} threshold stages")
    print(f"   ✓ Thresholds: {threshold_keys}")

# ============================================================================
# 4. SAVE DISTANCE MATRICES AS .NPY FILES
# ============================================================================
print("\n[4/6] Saving distance matrices as .npy files...")

for metric_key, dist_matrix in computed_distance_matrices.items():
    npy_filename = f"dist_{metric_key}.npy"
    npy_path = os.path.join(output_dir, npy_filename)
    np.save(npy_path, dist_matrix)
    print(f"   ✓ Saved {npy_filename}: {dist_matrix.shape}")

# ============================================================================
# 5. COMPUTE AND SAVE DIMENSIONALITY REDUCTION PROJECTIONS
# ============================================================================
print("\n[5/7] Computing and saving dimensionality reduction projections...")

# Compute PCA (reduce to 2D for visualization)
print("   Computing PCA...")
pca = PCA(n_components=2, random_state=42)
pca_projection = pca.fit_transform(points)
pca_filename = "pca.npy"
pca_path = os.path.join(output_dir, pca_filename)
np.save(pca_path, pca_projection)
print(f"   ✓ Saved {pca_filename}: {pca_projection.shape}")
print(f"   ✓ Explained variance: {pca.explained_variance_ratio_}")

# Compute t-SNE (reduce to 2D for visualization)
print("   Computing t-SNE...")
perplexity = min(30, (n_samples - 1) // 3)
perplexity = max(5, perplexity)  # Ensure minimum perplexity
tsne = TSNE(n_components=2, random_state=42, perplexity=perplexity, max_iter=1000)
tsne_projection = tsne.fit_transform(points)
tsne_filename = "tsne.npy"
tsne_path = os.path.join(output_dir, tsne_filename)
np.save(tsne_path, tsne_projection)
print(f"   ✓ Saved {tsne_filename}: {tsne_projection.shape}")

# Compute MDS (reduce to 2D for visualization)
print("   Computing MDS...")
mds = MDS(n_components=2, random_state=42, n_init=4, max_iter=1000)
mds_projection = mds.fit_transform(points)
mds_filename = "mds.npy"
mds_path = os.path.join(output_dir, mds_filename)
np.save(mds_path, mds_projection)
print(f"   ✓ Saved {mds_filename}: {mds_projection.shape}")

# Compute LDA (reduce to 2D for visualization)
# LDA requires labels, so we use true_labels
print("   Computing LDA...")
n_classes = len(np.unique(true_labels))
n_components = min(2, n_classes - 1)  # LDA can have at most n_classes - 1 components
if n_components >= 1:
    lda = LinearDiscriminantAnalysis(n_components=n_components)
    lda_projection = lda.fit_transform(points, true_labels)
    lda_filename = "lda.npy"
    lda_path = os.path.join(output_dir, lda_filename)
    np.save(lda_path, lda_projection)
    print(f"   ✓ Saved {lda_filename}: {lda_projection.shape}")
else:
    print("   ⚠ Skipping LDA: insufficient classes for 2D projection")

# ============================================================================
# 6. SAVE ALL DATA AS JSON
# ============================================================================
print("\n[6/7] Saving data to JSON files...")

# Save persistent homology cluster labels
ph_labels_file = os.path.join(output_dir, "ph_data_all_syn.json")
with open(ph_labels_file, 'w') as f:
    json.dump(ph_data_all, f, indent=4)
print(f"   ✓ Saved cluster labels: {ph_labels_file}")
print(f"      - {len(ph_data_all)} metrics")
print(f"      - Each with Original Labels + threshold stages")

# Save the raw point cloud data (optional, for reference)
point_cloud_file = os.path.join(output_dir, "point_cloud_data.json")
point_cloud_data = {
    "points": points.tolist(),
    "true_labels": true_labels.tolist(),
    "n_samples": n_samples,
    "n_features": points.shape[1],
    "n_clusters": len(centers)
}
with open(point_cloud_file, 'w') as f:
    json.dump(point_cloud_data, f, indent=2)
print(f"   ✓ Saved point cloud: {point_cloud_file}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("DATA GENERATION COMPLETE!")
print("=" * 70)
print("\nGenerated files:")
print(f"  JSON files:")
print(f"    • ph_data_all_syn.json - Cluster labels at PH thresholds")
print(f"    • point_cloud_data.json - Raw point cloud data")
print(f"  NumPy (.npy) files:")
print(f"    • dist_euclid_dist.npy - Euclidean distance matrix")
print(f"    • dist_maha_dist.npy - Mahalanobis distance matrix")
print(f"    • dist_density_euclid.npy - Density-normalized Euclidean")
print(f"    • dist_density_maha.npy - Density-normalized Mahalanobis")
print(f"    • pca.npy - PCA projection (2D)")
print(f"    • tsne.npy - t-SNE projection (2D)")
print(f"    • mds.npy - MDS projection (2D)")
print(f"    • lda.npy - LDA projection (2D)")
print("\nMetrics included:")
for metric_key in ph_data_all.keys():
    num_thresholds = len(ph_data_all[metric_key]) - 1  # -1 for Original Labels
    print(f"  • {metric_key}: {num_thresholds} PH threshold stages")
print("\nReady for dashboard visualization!")
print("=" * 70)

