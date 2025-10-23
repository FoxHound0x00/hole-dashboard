# Data Directory

This directory contains all generated data files for the dashboard.

## Generated Files

### NumPy Binary Files (.npy)
- `dist_euclid_dist.npy` - Euclidean distance matrix (250×250)
- `dist_maha_dist.npy` - Mahalanobis distance matrix (250×250)
- `dist_density_euclid.npy` - Density-normalized Euclidean (250×250)
- `dist_density_maha.npy` - Density-normalized Mahalanobis (250×250)
- `pca.npy` - PCA projection for visualization (250×2)

### JSON Files
- `ph_data_all_syn.json` - Cluster labels at PH thresholds
- `point_cloud_data.json` - Raw point cloud data

## Regenerate Data

```bash
cd /home/sud/Documents/repos/hole-dashboard/services/backend/src
source /home/sud/Documents/repos/hole-dashboard/hole_env/bin/activate
python generate_ph_data.py
```

Data is automatically saved to this `data/` directory.


