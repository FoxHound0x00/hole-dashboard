Remove scrolling aspect --- single view dashboard
Tooltip -- representative subset of that particular class/cluster



display marker (dotted line) for stacked area chart
Clipped polygon inside blob
----
python library

use saturation based coloring as an alternative to contour lines.



----

PCA to blob vis
send rasterized heatmap if there's no interactivity.



stacked bar chart is overflowing, and the legend thing is too massive in terms of width


----

color the outlier clusters gray (single stacked area)

legends --> most significant
clip the threshold 

get rid of the fd-layout
add tsne, mds, to the blob vis
add contours for blobs

----
## NEW FEATURES & UPGRADES

### Backend API Enhancements
- [ ] Add `/upload_data` endpoint to handle point cloud data uploads (.csv, .txt, .npy)
- [ ] Implement clustering quality metrics API endpoint (silhouette score, Calinski-Harabasz, Davies-Bouldin)
- [ ] Add batch processing endpoint for multiple distance metrics at once
- [ ] Create API endpoint to compute custom persistence diagrams on-demand
- [ ] Add endpoint for computing alternative clustering algorithms (DBSCAN, OPTICS, Spectral)
- [ ] Implement real-time clustering progress/status endpoint for large datasets
- [ ] Add endpoint to export/download processed cluster data (JSON, CSV)
- [ ] Create versioning system for uploaded models and datasets
- [ ] Add authentication/API key support for multi-user deployments

### Visualization Features
- [ ] Add UMAP dimensionality reduction alongside PCA/t-SNE/MDS/LDA in blob vis
- [ ] Implement 3D visualization mode toggle (using three.js or plotly.js)
- [ ] Add animation/transition between different thresholds (scrubbing timeline)
- [ ] Create persistence barcode visualization
- [ ] Add cluster stability visualization over threshold ranges
- [ ] Implement cluster lineage tracking (birth/death events)
- [ ] Add voronoi diagram overlay option for blob visualization
- [ ] Create cluster comparison view (side-by-side different metrics)
- [ ] Add brushing & linking across all visualizations
- [ ] Implement dark mode theme toggle
- [ ] Add customizable color palettes/schemes

### Interactive Features
- [ ] Add cluster annotation/labeling capability with export
- [ ] Implement cluster merging/splitting manual override
- [ ] Add bookmark/save state functionality (save current config as preset)
- [ ] Create shareable URLs with encoded visualization state
- [ ] Add undo/redo for filter and selection changes
- [ ] Implement zoom sync across multiple visualizations
- [ ] Add keyboard shortcuts for common operations
- [ ] Create guided tour/tutorial overlay for first-time users

### Data Export & Reporting
- [ ] Export cluster assignments as CSV/JSON with metadata
- [ ] Generate PDF reports with all visualizations and statistics
- [ ] Add SVG export option (currently only PNG in ZIP)
- [ ] Export individual visualizations separately (not just "Save All")
- [ ] Create data provenance/lineage tracking (record all transformations)
- [ ] Add export to Jupyter notebook format (.ipynb)
- [ ] Implement session history log (all actions/parameters used)

### Performance Optimizations
- [ ] Implement WebGL rendering for large point clouds (>10k points)
- [ ] Add progressive loading for large distance matrices
- [ ] Implement data virtualization for cluster lists
- [ ] Add caching layer for computed projections (PCA/t-SNE/etc)
- [ ] Optimize dendrogram rendering for >500 clusters
- [ ] Add Web Workers for heavy computations (distance calculations)
- [ ] Implement incremental/lazy rendering for heatmaps

### Analysis Tools
- [ ] Add cluster statistics panel (size, density, cohesion, separation)
- [ ] Implement outlier detection algorithms with highlighting
- [ ] Add cluster quality metrics dashboard
- [ ] Create cluster composition breakdown charts (class distribution)
- [ ] Add statistical significance tests between clusters
- [ ] Implement dimensionality reduction quality metrics (stress, preservation)
- [ ] Add feature importance visualization for clustering
- [ ] Create cluster-to-cluster distance/similarity matrix

### UI/UX Improvements
- [ ] Add responsive mobile/tablet layout
- [ ] Implement collapsible panels for better space utilization
- [ ] Add loading skeletons/progress indicators for all async operations
- [ ] Create contextual help tooltips for all controls
- [ ] Add error recovery (retry failed API calls)
- [ ] Implement drag-and-drop for file uploads
- [ ] Add recent files/datasets quick access menu
- [ ] Create visualization presets gallery (e.g., "Focus on outliers", "High-level overview")
- [ ] Add status bar showing current operation/memory usage
- [ ] Implement notification system for long-running operations

### Data Management
- [ ] Add dataset version control/history
- [ ] Implement data validation and quality checks on upload
- [ ] Create data preprocessing pipeline UI (normalization, scaling, PCA pre-reduction)
- [ ] Add support for streaming/chunked data uploads for large files
- [ ] Implement data source connections (databases, cloud storage)
- [ ] Add dataset metadata editor (description, tags, notes)
- [ ] Create dataset search/filter functionality

### Advanced Analysis
- [ ] Implement multi-scale persistent homology (0D, 1D, 2D features)
- [ ] Add bootstrap resampling for cluster stability analysis
- [ ] Create cluster evolution animation over parameter space
- [ ] Implement topological feature detection (loops, voids, connected components)
- [ ] Add hierarchical clustering with different linkage methods
- [ ] Create cluster consensus analysis (agreement across methods)
- [ ] Implement time-series clustering support

### Testing & Documentation
- [ ] Add comprehensive unit tests for all components
- [ ] Create integration tests for API endpoints
- [ ] Add E2E tests for critical user workflows
- [ ] Create interactive documentation/help system
- [ ] Add code examples for common use cases
- [ ] Create video tutorials for main features
- [ ] Add API documentation (OpenAPI/Swagger)

### Deployment & Infrastructure
- [ ] Add Docker Compose profiles (dev, prod, minimal)
- [ ] Create Kubernetes deployment configs
- [ ] Implement health check endpoints
- [ ] Add logging and monitoring (Prometheus/Grafana compatible)
- [ ] Create CI/CD pipeline configuration
- [ ] Add database backend option for persistent storage
- [ ] Implement multi-user workspace isolation
- [ ] Add backup/restore functionality