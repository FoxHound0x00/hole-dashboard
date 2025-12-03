<template>
  <div class="heatmap-dendrogram-container">
    <h3>Heatmap Dendrogram - {{ metric }}</h3>
    <div v-if="loading" class="loading">Loading distance matrix...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <p style="color: #666; font-size: 12px; margin-bottom: 10px;">
        Matrix size: {{ distanceMatrix ? distanceMatrix.length : 0 }}x{{ distanceMatrix ? distanceMatrix.length : 0 }}
      </p>
      <div ref="chartContainer" class="chart-container"></div>
    </div>
  </div>
</template>

<script>
import * as d3 from 'd3';

export default {
  name: 'HeatmapDendrogram',
  props: {
    metric: {
      type: String,
      required: true
    },
    clusterData: {
      type: Object,
      default: () => ({})
    },
    selectedThreshold: {
      type: String,
      default: null
    }
  },
  data() {
    return {
      distanceMatrix: null,
      loading: false,
      error: null,
      heatmapColorScale: null,
      fetchTimeout: null,
      renderTimeout: null,
      svg: null,
      dendrogramGroup: null,
      xScale: null,
      margin: null,
      height: null
    };
  },
  watch: {
    metric: {
      immediate: true,
      handler() {
        // Debounce to avoid rapid fetches
        if (this.fetchTimeout) {
          clearTimeout(this.fetchTimeout);
        }
        this.fetchTimeout = setTimeout(() => {
          this.fetchDistanceMatrix();
        }, 300);
      }
    },
    selectedThreshold: {
      handler() {
        // Only re-render threshold line, not entire visualization
        this.updateThresholdLine();
      }
    },
    clusterData: {
      deep: true,
      handler() {
        // Debounce cluster data changes
        if (this.renderTimeout) {
          clearTimeout(this.renderTimeout);
        }
        this.renderTimeout = setTimeout(() => {
          this.renderVisualization();
        }, 300);
      }
    }
  },
  beforeUnmount() {
    if (this.fetchTimeout) {
      clearTimeout(this.fetchTimeout);
    }
  },
  methods: {
    async fetchDistanceMatrix() {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await fetch(`http://127.0.0.1:5000/distance_matrix/${this.metric}`);
        const data = await response.json();
        
        if (data.error) {
          this.error = data.error;
          this.loading = false;
          return;
        }
        
        this.distanceMatrix = data.matrix;
        this.loading = false;
        
        // Wait for DOM to update after loading is set to false
        await this.$nextTick();
        // Wait one more tick to ensure the ref is available
        await this.$nextTick();
        
        this.renderVisualization();
      } catch (err) {
        this.error = 'Failed to fetch distance matrix: ' + err.message;
        this.loading = false;
      }
    },
    
    renderVisualization() {
      if (!this.distanceMatrix || !this.$refs.chartContainer) {
        return;
      }
      
      try {
        // Clear previous visualization efficiently
        const container = this.$refs.chartContainer;
        while (container.firstChild) {
          container.removeChild(container.firstChild);
        }
        
        const containerWidth = container.clientWidth || 1000;
        
        // Dimensions - make both dendrogram and heatmap square
        this.margin = { top: 50, right: 20, bottom: 50, left: 150 };
        const legendWidth = 80;
        
        // Calculate square size based on available space
        const availableWidth = containerWidth - this.margin.left - this.margin.right - legendWidth;
        const squareSize = Math.min(500, availableWidth / 2); // Fit both squares
        
        const dendrogramWidth = squareSize;
        const heatmapWidth = squareSize;
        this.height = squareSize + this.margin.top + this.margin.bottom;
        
        const totalWidth = this.margin.left + dendrogramWidth + heatmapWidth + legendWidth + this.margin.right;
        
        // Create SVG
        this.svg = d3.select(container)
          .append('svg')
          .attr('width', totalWidth)
          .attr('height', this.height)
          .attr('viewBox', [0, 0, totalWidth, this.height])
          .attr('style', 'max-width: 100%; height: auto;');
        
        // Create hierarchical clustering using distance matrix
        const n = this.distanceMatrix.length;
        const clustering = this.performHierarchicalClustering(this.distanceMatrix);
        
        // Get the order of leaves from clustering
        const leafOrder = this.getLeafOrder(clustering);
        
        // Reorder distance matrix according to clustering
        const reorderedMatrix = this.reorderMatrix(this.distanceMatrix, leafOrder);
        
        // Get cluster labels from the data
        const originalLabels = this.getClusterLabels(leafOrder);
        
        // Get threshold-based cluster assignments if available
        const thresholdClusters = this.getThresholdClusters(leafOrder);
        
        // Render dendrogram and store xScale
        this.xScale = this.renderDendrogram(this.svg, clustering, this.margin, dendrogramWidth, this.height, n, originalLabels, thresholdClusters);
        
        // Render heatmap
        this.renderHeatmap(this.svg, reorderedMatrix, this.margin, dendrogramWidth, heatmapWidth, this.height, leafOrder);
        
        // Add color legend (completely to the right of heatmap)
        const legendX = this.margin.left + dendrogramWidth + heatmapWidth + 40;
        this.addColorLegend(this.svg, this.heatmapColorScale, this.margin, legendX, this.height);
        
        // Draw threshold line if one is selected
        if (this.selectedThreshold) {
          this.$nextTick(() => {
            this.updateThresholdLine();
          });
        }
      } catch (error) {
        console.error('Error rendering visualization:', error);
        this.error = 'Error rendering visualization: ' + error.message;
      }
    },
    
    performHierarchicalClustering(matrix) {
      const n = matrix.length;
      const clusters = new Array(n);
      
      // Initialize each point as its own cluster
      for (let i = 0; i < n; i++) {
        clusters[i] = {
          id: i,
          indices: [i],
          height: 0,
          left: null,
          right: null
        };
      }
      
      let nextId = n;
      let activeClusters = n;
      
      // Perform agglomerative clustering with optimizations
      while (activeClusters > 1) {
        // Find the two closest clusters
        let minDist = Infinity;
        let minI = 0, minJ = 1;
        
        const len = clusters.length;
        for (let i = 0; i < len; i++) {
          if (!clusters[i]) continue;
          for (let j = i + 1; j < len; j++) {
            if (!clusters[j]) continue;
            const dist = this.clusterDistance(clusters[i], clusters[j], matrix);
            if (dist < minDist) {
              minDist = dist;
              minI = i;
              minJ = j;
            }
          }
        }
        
        // Merge the two closest clusters
        const newCluster = {
          id: nextId++,
          indices: [...clusters[minI].indices, ...clusters[minJ].indices],
          height: minDist,
          left: clusters[minI],
          right: clusters[minJ]
        };
        
        // Mark old clusters as null instead of splicing
        clusters[minI] = null;
        clusters[minJ] = null;
        clusters.push(newCluster);
        activeClusters--;
      }
      
      // Return the last non-null cluster
      return clusters[clusters.length - 1];
    },
    
    clusterDistance(cluster1, cluster2, matrix) {
      // Average linkage
      let sum = 0;
      let count = 0;
      
      for (const i of cluster1.indices) {
        for (const j of cluster2.indices) {
          sum += matrix[i][j];
          count++;
        }
      }
      
      return sum / count;
    },
    
    getLeafOrder(root) {
      // Perform optimal leaf ordering to minimize distances between adjacent leaves
      this.optimizeLeafOrder(root, this.distanceMatrix);
      
      const order = [];
      
      function traverse(node) {
        if (!node.left && !node.right) {
          // Leaf node
          order.push(node.id);
        } else {
          if (node.left) traverse(node.left);
          if (node.right) traverse(node.right);
        }
      }
      
      traverse(root);
      return order;
    },
    
    optimizeLeafOrder(node, distanceMatrix) {
      // Optimal leaf ordering: recursively optimize the order of leaves
      // to minimize the sum of distances between adjacent leaves
      if (!node.left || !node.right) return;
      
      // Recursively optimize children first
      this.optimizeLeafOrder(node.left, distanceMatrix);
      this.optimizeLeafOrder(node.right, distanceMatrix);
      
      // Get all leaves from left and right subtrees
      const leftLeaves = this.getSubtreeLeaves(node.left);
      const rightLeaves = this.getSubtreeLeaves(node.right);
      
      if (leftLeaves.length === 0 || rightLeaves.length === 0) return;
      
      // Calculate average distance between boundaries
      // Try all 4 configurations: LL, LR, RL, RR
      const configs = [
        { swap: false, flipLeft: false, flipRight: false }, // normal
        { swap: false, flipLeft: false, flipRight: true },  // flip right
        { swap: false, flipLeft: true, flipRight: false },  // flip left
        { swap: false, flipLeft: true, flipRight: true },   // flip both
      ];
      
      let bestCost = Infinity;
      let bestConfig = configs[0];
      
      for (const config of configs) {
        const leftBoundary = config.flipLeft ? leftLeaves[0] : leftLeaves[leftLeaves.length - 1];
        const rightBoundary = config.flipRight ? rightLeaves[rightLeaves.length - 1] : rightLeaves[0];
        const cost = distanceMatrix[leftBoundary][rightBoundary];
        
        if (cost < bestCost) {
          bestCost = cost;
          bestConfig = config;
        }
      }
      
      // Apply the best configuration
      if (bestConfig.flipLeft) {
        this.flipSubtree(node.left);
      }
      if (bestConfig.flipRight) {
        this.flipSubtree(node.right);
      }
    },
    
    getSubtreeLeaves(node) {
      if (!node) return [];
      if (!node.left && !node.right) return [node.id];
      
      const leftLeaves = node.left ? this.getSubtreeLeaves(node.left) : [];
      const rightLeaves = node.right ? this.getSubtreeLeaves(node.right) : [];
      return [...leftLeaves, ...rightLeaves];
    },
    
    flipSubtree(node) {
      if (!node) return;
      // Swap left and right children
      const temp = node.left;
      node.left = node.right;
      node.right = temp;
    },
    
    getClusterLabels(order) {
      // Get the original labels from cluster data
      if (!this.clusterData || !this.clusterData['Original Labels']) {
        return order.map(() => 0);
      }
      
      const originalLabels = this.clusterData['Original Labels'];
      return order.map(idx => originalLabels[idx]);
    },
    
    getThresholdClusters(order) {
      // Get threshold-based cluster assignments
      if (!this.clusterData || !this.selectedThreshold || !this.clusterData[this.selectedThreshold]) {
        return null;
      }
      
      const thresholdClusters = this.clusterData[this.selectedThreshold];
      return order.map(idx => thresholdClusters[idx]);
    },
    
    reorderMatrix(matrix, order) {
      const n = order.length;
      const reordered = [];
      
      for (let i = 0; i < n; i++) {
        reordered[i] = [];
        for (let j = 0; j < n; j++) {
          reordered[i][j] = matrix[order[i]][order[j]];
        }
      }
      
      return reordered;
    },
    
    renderDendrogram(svg, root, margin, width, height, n, originalLabels, thresholdClusters) {
      this.dendrogramGroup = svg.append('g')
        .attr('transform', `translate(${margin.left}, ${margin.top})`);
      
      const dendrogramGroup = this.dendrogramGroup;
      
      // Calculate y positions for leaves
      const yScale = d3.scaleLinear()
        .domain([0, n - 1])
        .range([0, height - margin.top - margin.bottom]);
      
      // Calculate x scale for dendrogram (based on height/distance)
      const maxHeight = root.height;
      
      console.log('Dendrogram maxHeight:', maxHeight);
      
      // Standard dendrogram layout: leaves on right (high x), root on left (low x)
      // Domain: 0 (leaves) to maxHeight (root)
      // Range: width (leaves) to 0 (root)
      const xScale = d3.scaleLinear()
        .domain([0, maxHeight])
        .range([width, 0]);
      
      console.log('xScale domain:', xScale.domain(), 'range:', xScale.range());
      
      // Assign y positions to all nodes
      const leafPositions = {};
      let leafIndex = 0;
      
      function assignPositions(node) {
        if (!node.left && !node.right) {
          // Leaf node
          node.y = yScale(leafIndex);
          leafPositions[node.id] = node.y;
          leafIndex++;
        } else {
          // Internal node
          if (node.left) assignPositions(node.left);
          if (node.right) assignPositions(node.right);
          node.y = (node.left.y + node.right.y) / 2;
        }
      }
      
      assignPositions(root);
      
      // Extended color scheme for original labels (consistent with ClusterBlob and Sankey)
      const originalLabelColors = [
        ...d3.schemeCategory10,
        "#8dd3c7", "#ffffb3", "#bebada", "#fb8072", "#80b1d3", 
        "#fdb462", "#b3de69", "#fccde5", "#d9d9d9", "#bc80bd"
      ];
      
      // Use threshold clusters if available, otherwise use original labels
      const labelsToUse = thresholdClusters || originalLabels;
      
      // If using threshold clusters, calculate majority class for each cluster
      let clusterColors = {};
      if (thresholdClusters) {
        // Group by threshold cluster and find majority original label
        const clusterComposition = {};
        thresholdClusters.forEach((cluster, idx) => {
          if (!clusterComposition[cluster]) {
            clusterComposition[cluster] = {};
          }
          const originalLabel = originalLabels[idx];
          clusterComposition[cluster][originalLabel] = (clusterComposition[cluster][originalLabel] || 0) + 1;
        });
        
        // Find majority class for each threshold cluster
        Object.keys(clusterComposition).forEach(cluster => {
          const counts = clusterComposition[cluster];
          const majorityLabel = Object.entries(counts)
            .reduce((max, [label, count]) => count > max.count ? { label: parseInt(label), count } : max,
                    { label: 0, count: 0 }).label;
          clusterColors[cluster] = originalLabelColors[majorityLabel % originalLabelColors.length];
        });
      } else {
        // Direct mapping of original labels to colors
        const uniqueLabels = [...new Set(originalLabels)];
        uniqueLabels.forEach(label => {
          clusterColors[label] = originalLabelColors[label % originalLabelColors.length];
        });
      }
      
      // Assign cluster labels to each node based on its leaves
      let clusterIndex = 0;
      function assignClusterToNode(node) {
        if (!node.left && !node.right) {
          // Leaf node - get its cluster label
          node.cluster = labelsToUse[clusterIndex];
          clusterIndex++;
        } else {
          // Internal node - recursively process children
          if (node.left) assignClusterToNode(node.left);
          if (node.right) assignClusterToNode(node.right);
          
          // For internal node, use the cluster of the left child (or could use majority)
          node.cluster = node.left ? node.left.cluster : (node.right ? node.right.cluster : 0);
        }
      }
      
      assignClusterToNode(root);
      
      // Create color scale function
      const clusterColorScale = (cluster) => clusterColors[cluster] || '#999';
      
      // Draw dendrogram links
      function drawLinks(node) {
        if (node.left && node.right) {
          const x = xScale(node.height);
          const branchColor = clusterColorScale(node.cluster);
          
          // Vertical line
          dendrogramGroup.append('line')
            .attr('x1', x)
            .attr('y1', node.left.y)
            .attr('x2', x)
            .attr('y2', node.right.y)
            .attr('stroke', branchColor)
            .attr('stroke-width', 2.5)
            .attr('opacity', 0.8);
          
          // Horizontal line to left child
          dendrogramGroup.append('line')
            .attr('x1', x)
            .attr('y1', node.left.y)
            .attr('x2', xScale(node.left.height))
            .attr('y2', node.left.y)
            .attr('stroke', clusterColorScale(node.left.cluster))
            .attr('stroke-width', 2.5)
            .attr('opacity', 0.8);
          
          // Horizontal line to right child
          dendrogramGroup.append('line')
            .attr('x1', x)
            .attr('y1', node.right.y)
            .attr('x2', xScale(node.right.height))
            .attr('y2', node.right.y)
            .attr('stroke', clusterColorScale(node.right.cluster))
            .attr('stroke-width', 2.5)
            .attr('opacity', 0.8);
          
          drawLinks(node.left);
          drawLinks(node.right);
        }
      }
      
      drawLinks(root);
      
      // Threshold line will be drawn via updateThresholdLine() method after initial render
      
      // Create axis with regular ticks (not threshold-based)
      const xAxis = d3.axisTop(xScale)
        .ticks(6)
        .tickFormat(d => {
          // Remove NaN, format numbers properly, and ensure clean values
          if (isNaN(d) || d === null || d === undefined) return '';
          // Round to avoid floating point issues
          return Number(d.toFixed(1));
        });
      
      const axisGroup = dendrogramGroup.append('g')
        .attr('transform', 'translate(0, 0)')
        .call(xAxis);
      
      // Style axis
      axisGroup.selectAll('text')
        .attr('font-size', '10px')
        .attr('fill', '#555');
      
      // Remove any NaN or invalid tick marks
      axisGroup.selectAll('.tick').filter(function() {
        const text = d3.select(this).select('text').text();
        return text === '' || text === 'NaN' || text === 'null';
      }).remove();
      
      // Return xScale for threshold line updates
      return xScale;
    },
    
    updateThresholdLine() {
      // Fast update - only redraw threshold line without re-rendering entire dendrogram
      if (!this.dendrogramGroup || !this.xScale || !this.selectedThreshold) {
        return;
      }
      
      // Remove existing threshold line and label
      this.dendrogramGroup.selectAll('.threshold-line, .threshold-label, .threshold-label-bg').remove();
      
      // Parse threshold value - it should be a numeric string like "8.867"
      const thresholdValue = parseFloat(this.selectedThreshold);
      if (isNaN(thresholdValue)) {
        console.warn('Invalid threshold value:', this.selectedThreshold);
        return;
      }
      
      const thresholdX = this.xScale(thresholdValue);
      
      // Draw vertical dotted line at threshold
      this.dendrogramGroup.append('line')
        .attr('class', 'threshold-line')
        .attr('x1', thresholdX)
        .attr('y1', 0)
        .attr('x2', thresholdX)
        .attr('y2', this.height - this.margin.top - this.margin.bottom)
        .attr('stroke', '#ff6b35')
        .attr('stroke-width', 3)
        .attr('stroke-dasharray', '5,5')
        .attr('opacity', 0.9);
      
      // Add label background
      const text = this.dendrogramGroup.append('text')
        .attr('class', 'threshold-label')
        .attr('x', thresholdX)
        .attr('y', -15)
        .attr('text-anchor', 'middle')
        .attr('font-size', '11px')
        .attr('font-weight', 'bold')
        .attr('fill', '#ff6b35')
        .text(this.selectedThreshold);
      
      // Add white background
      const bbox = text.node()?.getBBox();
      if (bbox) {
        this.dendrogramGroup.insert('rect', '.threshold-label')
          .attr('class', 'threshold-label-bg')
          .attr('x', bbox.x - 2)
          .attr('y', bbox.y - 1)
          .attr('width', bbox.width + 4)
          .attr('height', bbox.height + 2)
          .attr('fill', 'white')
          .attr('opacity', 0.9);
      }
    },
    
    renderHeatmap(svg, matrix, margin, dendrogramWidth, width, height, order) {
      const heatmapGroup = svg.append('g')
        .attr('transform', `translate(${margin.left + dendrogramWidth}, ${margin.top})`);
      
      const n = matrix.length;
      
      // Calculate cell size
      const cellWidth = width / n;
      const cellHeight = (height - margin.top - margin.bottom) / n;
      
      // grayscale for heatmap
      const maxDist = d3.max(matrix.flat());
      const colorScale = d3.scaleSequential(d3.interpolateGreys)
        .domain([0, maxDist]);
      
      // Store for legend
      this.heatmapColorScale = colorScale;
      
      // Draw heatmap cells
      for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
          heatmapGroup.append('rect')
            .attr('x', j * cellWidth)
            .attr('y', i * cellHeight)
            .attr('width', cellWidth)
            .attr('height', cellHeight)
            .attr('fill', colorScale(matrix[i][j]))
            .attr('stroke', 'none')
            .append('title')
            .text(`Row: ${order[i]}, Col: ${order[j]}, Distance: ${matrix[i][j].toFixed(2)}`);
        }
      }
    },
    
    addColorLegend(svg, colorScale, margin, x, totalHeight) {
      const legendHeight = Math.min(200, totalHeight - margin.top - margin.bottom);
      const legendWidth = 20;
      
      const legendGroup = svg.append('g')
        .attr('transform', `translate(${x}, ${margin.top})`);
      
      // Create gradient
      const defs = svg.append('defs');
      const gradient = defs.append('linearGradient')
        .attr('id', 'heatmap-gradient')
        .attr('x1', '0%')
        .attr('y1', '100%')
        .attr('x2', '0%')
        .attr('y2', '0%');
      
      const numStops = 10;
      for (let i = 0; i <= numStops; i++) {
        const offset = (i / numStops) * 100;
        const value = (i / numStops) * colorScale.domain()[1];
        gradient.append('stop')
          .attr('offset', `${offset}%`)
          .attr('stop-color', colorScale(value));
      }
      
      // Draw legend rectangle
      legendGroup.append('rect')
        .attr('width', legendWidth)
        .attr('height', legendHeight)
        .style('fill', 'url(#heatmap-gradient)');
      
      // Add scale
      const legendScale = d3.scaleLinear()
        .domain(colorScale.domain())
        .range([legendHeight, 0]);
      
      const legendAxis = d3.axisRight(legendScale).ticks(5);
      legendGroup.append('g')
        .attr('transform', `translate(${legendWidth}, 0)`)
        .call(legendAxis);
      
      // Add label
      legendGroup.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('y', -30)
        .attr('x', -legendHeight / 2)
        .attr('text-anchor', 'middle')
        .style('font-size', '12px')
        .text('Distance');
    }
  }
};
</script>

<style scoped>
.heatmap-dendrogram-container {
  width: 100%;
  height: 100%;
  padding: 8px;
  background-color: #f8f9fa;
  border: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.heatmap-dendrogram-container h3 {
  margin: 0 0 6px 0;
  color: #333;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
  letter-spacing: 0.3px;
}

.chart-container {
  width: 100%;
  flex: 1;
  overflow: auto;
  background-color: white;
  padding: 10px;
  border: 1px solid #d0d0d0;
  min-height: 0;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
  font-size: 13px;
}

.error {
  text-align: center;
  padding: 40px;
  color: #e74c3c;
  font-size: 13px;
  background-color: #fadbd8;
  border-radius: 4px;
}
</style>

