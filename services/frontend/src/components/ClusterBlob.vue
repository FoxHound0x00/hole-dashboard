<template>
  <div class="cluster-blob">
    <h3>Cluster Blob Visualization</h3>
    <div ref="blobContainer" class="blob-container"></div>
    <div class="legend" ref="legendContainer"></div>
  </div>
</template>

<script>
import { defineComponent, ref, onMounted, watch, onBeforeUnmount } from 'vue';
import * as d3 from 'd3';

export default defineComponent({
  name: 'ClusterBlob',
  props: {
    data: {
      type: Object,
      required: true
    },
    selectedThreshold: {
      type: String,
      default: null
    },
    selectedCluster: {
      type: [String, Number],
      default: null
    },
    outliers: {
      type: Array,
      default: () => []
    }
  },
  emits: ['blob-selected', 'point-selected'],
  setup(props, { emit }) {
    const blobContainer = ref(null);
    const legendContainer = ref(null);
    const svg = ref(null);
    const width = ref(800);
    const height = ref(600);
    
    // Extended color scheme for original labels
    const originalLabelColors = [
      ...d3.schemeCategory10,
      "#8dd3c7", "#ffffb3", "#bebada", "#fb8072", "#80b1d3", 
      "#fdb462", "#b3de69", "#fccde5", "#d9d9d9", "#bc80bd"
    ];
    
    // Different color scheme for threshold-based blobs
    const thresholdBlobColors = [
      "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
      "#1abc9c", "#34495e", "#e67e22", "#95a5a6", "#f1c40f",
      "#8e44ad", "#27ae60", "#2980b9", "#c0392b", "#16a085"
    ];
    
    // Create the visualization
    const createVisualization = () => {
      if (!blobContainer.value) return;
      
      // Clear any previous visualization
      d3.select(blobContainer.value).selectAll("*").remove();
      
      // Get container dimensions
      width.value = blobContainer.value.clientWidth || 800;
      height.value = blobContainer.value.clientHeight || 600;
      
      // Create SVG
      svg.value = d3.select(blobContainer.value)
        .append('svg')
        .attr('width', width.value)
        .attr('height', height.value)
        .attr('viewBox', [0, 0, width.value, height.value])
        .attr('style', 'max-width: 100%; height: auto;');
      
      // Process data to create blobs and points
      const { blobs, dataPoints } = processClusterData();
      
      // Group for blob hulls (behind everything)
      const blobGroup = svg.value.append('g').attr('class', 'blobs');
      
      // Group for links
      const linkGroup = svg.value.append('g').attr('class', 'links');
      
      // Group for data points (on top)
      const pointGroup = svg.value.append('g').attr('class', 'points');
      
      // Create links between points in the same blob
      const links = [];
      blobs.forEach(blob => {
        const blobPoints = dataPoints.filter(point => point.blobId === blob.id);
        
        // Create some connections within each blob
        for (let i = 0; i < blobPoints.length; i++) {
          for (let j = i + 1; j < blobPoints.length; j++) {
            if (Math.random() > 0.7) { // Sparse connections
              links.push({
                source: blobPoints[i],
                target: blobPoints[j],
                blobId: blob.id
              });
            }
          }
        }
      });
      
      // Draw links
      linkGroup.selectAll('line')
        .data(links)
        .join('line')
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)
        .attr('stroke', d => {
          const blob = blobs.find(b => b.id === d.blobId);
          return thresholdBlobColors[blob.thresholdCluster % thresholdBlobColors.length];
        })
        .attr('stroke-opacity', 0.3)
        .attr('stroke-width', 1);
      
      // Draw blob hulls
      const blobHulls = blobs.map(blob => {
        const blobPoints = dataPoints.filter(point => point.blobId === blob.id);
        const points = blobPoints.map(point => [point.x, point.y]);
        
        if (points.length < 3) return null; // Need at least 3 points for a hull
        
        const hull = d3.polygonHull(points);
        
        if (hull) {
          const paddedHull = padHull(hull, 20);
          
          // Check if this blob should be highlighted
          const isSelected = props.selectedCluster !== null && 
                           blob.thresholdCluster.toString() === props.selectedCluster.toString();
          
          return {
            blobId: blob.id,
            blob: blob,
            element: blobGroup.append('path')
              .attr('d', `M${paddedHull.join('L')}Z`)
              .attr('fill', thresholdBlobColors[blob.thresholdCluster % thresholdBlobColors.length])
              .attr('fill-opacity', isSelected ? 0.5 : 0.2)
              .attr('stroke', isSelected ? '#ff6b35' : thresholdBlobColors[blob.thresholdCluster % thresholdBlobColors.length])
              .attr('stroke-width', isSelected ? 4 : 2)
              .attr('stroke-opacity', isSelected ? 1 : 0.6)
              .style('cursor', 'pointer')
              .style('filter', isSelected ? 'drop-shadow(0px 4px 8px rgba(255, 107, 53, 0.4))' : 'none')
              .on('click', () => {
                emit('blob-selected', blob);
              })
              .on('mouseover', function() {
                if (!isSelected) {
                  d3.select(this)
                    .attr('fill-opacity', 0.4)
                    .attr('stroke-width', 3);
                }
              })
              .on('mouseout', function() {
                if (!isSelected) {
                  d3.select(this)
                    .attr('fill-opacity', 0.2)
                    .attr('stroke-width', 2);
                }
              })
          };
        }
        return null;
      }).filter(Boolean);
      
      // Draw data points
      const pointCircles = pointGroup.selectAll('circle')
        .data(dataPoints)
        .join('circle')
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)
        .attr('r', d => d.isOutlier ? 3 : 5)
        .attr('fill', d => originalLabelColors[d.originalLabel % originalLabelColors.length])
        .attr('stroke', '#fff')
        .attr('stroke-width', d => d.isOutlier ? 1 : 1.5)
        .attr('fill-opacity', d => d.isOutlier ? 0.7 : 1)
        .style('cursor', 'pointer')
        .on('click', (event, d) => {
          emit('point-selected', d);
        })
        .on('mouseover', function(event, d) {
          d3.select(this)
            .attr('r', d.isOutlier ? 4 : 7)
            .attr('stroke-width', 2);
            
          // Show tooltip or info
          showPointTooltip(event, d);
        })
        .on('mouseout', function(event, d) {
          d3.select(this)
            .attr('r', d.isOutlier ? 3 : 5)
            .attr('stroke-width', d.isOutlier ? 1 : 1.5);
            
          hidePointTooltip();
        });
      
      // Create force simulation for interactive behavior
      const simulation = d3.forceSimulation(dataPoints)
        .force('x', d3.forceX(d => d.initialX).strength(0.05))
        .force('y', d3.forceY(d => d.initialY).strength(0.05))
        .force('collide', d3.forceCollide().radius(d => d.isOutlier ? 4 : 8))
        .force('link', d3.forceLink(links).id(d => d.id).strength(0.1))
        .on('tick', () => {
          // Update point positions
          pointCircles
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);
            
          // Update link positions
          linkGroup.selectAll('line')
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
            
          // Update hull positions
          updateBlobHulls(blobs, blobHulls, dataPoints);
        })
        .alphaDecay(0.02);
      
      // Add drag behavior
      pointCircles.call(d3.drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }));
      
      // Enable zoom and pan
      svg.value.call(d3.zoom()
        .extent([[0, 0], [width.value, height.value]])
        .scaleExtent([0.5, 5])
        .on('zoom', zoomed));
        
      function zoomed(event) {
        pointGroup.attr('transform', event.transform);
        linkGroup.attr('transform', event.transform);
        blobGroup.attr('transform', event.transform);
      }
      
      // Create legend
      createLegend(blobs, dataPoints);
    };
    
    // Process cluster data to create blobs and points
    const processClusterData = () => {
      const blobs = [];
      const dataPoints = [];
      
      if (!props.data || Object.keys(props.data).length === 0) {
        return { blobs, dataPoints };
      }
      
      // Get the selected threshold data, fallback to Original Labels as default
      const thresholdKey = props.selectedThreshold || 'Original Labels';
      const originalLabelsKey = 'Original Labels';
      
      if (!thresholdKey || !props.data[thresholdKey] || !props.data[originalLabelsKey]) {
        return { blobs, dataPoints };
      }
      
      const thresholdData = props.data[thresholdKey];
      const originalLabelsData = props.data[originalLabelsKey];
      
      // Group data points by threshold cluster
      const thresholdGroups = {};
      thresholdData.forEach((thresholdCluster, index) => {
        if (!thresholdGroups[thresholdCluster]) {
          thresholdGroups[thresholdCluster] = [];
        }
        thresholdGroups[thresholdCluster].push({
          index,
          thresholdCluster,
          originalLabel: originalLabelsData[index] || 0,
          isOutlier: props.outliers.includes(index)
        });
      });
      
      // Create blobs and position data points
      const blobIds = Object.keys(thresholdGroups);
      const gridSize = Math.ceil(Math.sqrt(blobIds.length));
      const cellWidth = width.value / (gridSize + 1);
      const cellHeight = height.value / (gridSize + 1);
      
      blobIds.forEach((thresholdCluster, blobIndex) => {
        const points = thresholdGroups[thresholdCluster];
        
        // Calculate blob position
        const row = Math.floor(blobIndex / gridSize);
        const col = blobIndex % gridSize;
        const blobCenter = {
          x: cellWidth * (col + 1) + (Math.random() * 60 - 30),
          y: cellHeight * (row + 1) + (Math.random() * 60 - 30)
        };
        
        // Calculate blob radius based on number of points
        const blobRadius = Math.min(Math.max(points.length * 3, 30), 80);
        
        // Create blob
        blobs.push({
          id: blobIndex,
          thresholdCluster: parseInt(thresholdCluster),
          center: blobCenter,
          radius: blobRadius,
          pointCount: points.length,
          threshold: thresholdKey
        });
        
        // Position points within the blob
        points.forEach((point, pointIndex) => {
          // Use spiral or circular arrangement
          const angle = (pointIndex / points.length) * Math.PI * 2;
          const spiralRadius = (pointIndex / points.length) * blobRadius * 0.8;
          
          const x = blobCenter.x + Math.cos(angle) * spiralRadius + (Math.random() * 20 - 10);
          const y = blobCenter.y + Math.sin(angle) * spiralRadius + (Math.random() * 20 - 10);
          
          dataPoints.push({
            id: `point-${point.index}`,
            x,
            y,
            initialX: x,
            initialY: y,
            originalLabel: point.originalLabel,
            thresholdCluster: point.thresholdCluster,
            blobId: blobIndex,
            isOutlier: point.isOutlier,
            dataIndex: point.index
          });
        });
      });
      
      return { blobs, dataPoints };
    };
    
    // Update blob hulls when points move
    const updateBlobHulls = (blobs, blobHulls, dataPoints) => {
      blobs.forEach((blob, i) => {
        if (blobHulls[i]) {
          const blobPoints = dataPoints.filter(point => point.blobId === blob.id);
          const points = blobPoints.map(point => [point.x, point.y]);
          
          if (points.length >= 3) {
            const hull = d3.polygonHull(points);
            if (hull) {
              const paddedHull = padHull(hull, 20);
              blobHulls[i].element.attr('d', `M${paddedHull.join('L')}Z`);
            }
          }
        }
      });
    };
    
    // Function to pad hull points outward
    const padHull = (hull, padding) => {
      if (!hull || hull.length === 0) return [];
      
      // Calculate centroid
      const centroid = hull.reduce(
        (acc, point) => [acc[0] + point[0], acc[1] + point[1]],
        [0, 0]
      );
      centroid[0] /= hull.length;
      centroid[1] /= hull.length;
      
      // Pad points outward from centroid
      return hull.map(point => {
        const dx = point[0] - centroid[0];
        const dy = point[1] - centroid[1];
        const len = Math.sqrt(dx * dx + dy * dy);
        const scale = (len + padding) / len;
        
        return [
          centroid[0] + dx * scale,
          centroid[1] + dy * scale
        ];
      });
    };
    
    // Show point tooltip
    const showPointTooltip = (event, point) => {
      // Create or update tooltip
      let tooltip = d3.select('body').select('.point-tooltip');
      if (tooltip.empty()) {
        tooltip = d3.select('body')
          .append('div')
          .attr('class', 'point-tooltip')
          .style('position', 'absolute')
          .style('background', 'rgba(0, 0, 0, 0.8)')
          .style('color', 'white')
          .style('padding', '8px')
          .style('border-radius', '4px')
          .style('font-size', '12px')
          .style('pointer-events', 'none')
          .style('z-index', '1000');
      }
      
      tooltip
        .html(`
          <div><strong>Point ${point.dataIndex}</strong></div>
          <div>Original Label: ${point.originalLabel}</div>
          <div>Threshold Cluster: ${point.thresholdCluster}</div>
          <div>Outlier: ${point.isOutlier ? 'Yes' : 'No'}</div>
        `)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px')
        .style('opacity', 1);
    };
    
    // Hide point tooltip
    const hidePointTooltip = () => {
      d3.select('.point-tooltip').style('opacity', 0);
    };
    
    // Create legend
    const createLegend = (blobs, dataPoints) => {
      if (!legendContainer.value) return;
      
      // Clear previous legend
      d3.select(legendContainer.value).selectAll("*").remove();
      
      // Get unique threshold clusters and analyze their composition
      const uniqueThresholdClusters = [...new Set(blobs.map(b => b.thresholdCluster))].sort((a, b) => a - b);
      
      // For each cluster, count the distribution of original labels
      const clusterComposition = {};
      
      uniqueThresholdClusters.forEach(cluster => {
        // Find the blob for this cluster
        const blob = blobs.find(b => b.thresholdCluster === cluster);
        // Get points that belong to this blob
        const pointsInCluster = dataPoints.filter(p => p.blobId === blob.id);
        
        // Count occurrences of each original label
        const labelCounts = {};
        pointsInCluster.forEach(point => {
          const label = point.originalLabel;
          labelCounts[label] = (labelCounts[label] || 0) + 1;
        });
        
        // Convert to sorted array of {label, count} objects
        const labelDistribution = Object.entries(labelCounts)
          .map(([label, count]) => ({ label: parseInt(label), count }))
          .sort((a, b) => a.label - b.label);
        
        clusterComposition[cluster] = labelDistribution;
      });
      
      // Table dimensions
      const rowHeight = 35;
      const headerHeight = 40;
      const colWidth = 250;
      const tableWidth = colWidth * 2;
      const tableHeight = headerHeight + (uniqueThresholdClusters.length * rowHeight);
      
      const legendSvg = d3.select(legendContainer.value)
        .append('svg')
        .attr('width', tableWidth + 20)
        .attr('height', tableHeight + 20);
      
      const tableGroup = legendSvg.append('g')
        .attr('transform', 'translate(10, 10)');
      
      // Draw table border
      tableGroup.append('rect')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', tableWidth)
        .attr('height', tableHeight)
        .attr('fill', 'white')
        .attr('stroke', '#dee2e6')
        .attr('stroke-width', 2);
      
      // Draw header background
      tableGroup.append('rect')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', tableWidth)
        .attr('height', headerHeight)
        .attr('fill', '#f8f9fa')
        .attr('stroke', '#dee2e6')
        .attr('stroke-width', 1);
      
      // Draw vertical separator
      tableGroup.append('line')
        .attr('x1', colWidth)
        .attr('y1', 0)
        .attr('x2', colWidth)
        .attr('y2', tableHeight)
        .attr('stroke', '#dee2e6')
        .attr('stroke-width', 1);
      
      // Draw horizontal separator after header
      tableGroup.append('line')
        .attr('x1', 0)
        .attr('y1', headerHeight)
        .attr('x2', tableWidth)
        .attr('y2', headerHeight)
        .attr('stroke', '#dee2e6')
        .attr('stroke-width', 2);
      
      // Draw horizontal row separators
      for (let i = 1; i < uniqueThresholdClusters.length; i++) {
        tableGroup.append('line')
          .attr('x1', 0)
          .attr('y1', headerHeight + (i * rowHeight))
          .attr('x2', tableWidth)
          .attr('y2', headerHeight + (i * rowHeight))
          .attr('stroke', '#f0f0f0')
          .attr('stroke-width', 1);
      }
      
      // Header text
      tableGroup.append('text')
        .attr('x', colWidth / 2)
        .attr('y', headerHeight / 2 + 5)
        .attr('text-anchor', 'middle')
        .attr('font-weight', 'bold')
        .attr('font-size', '14px')
        .attr('fill', '#2c3e50')
        .text(`Cluster (${props.selectedThreshold || 'Original Labels'})`);
      
      tableGroup.append('text')
        .attr('x', colWidth + (colWidth / 2))
        .attr('y', headerHeight / 2 + 5)
        .attr('text-anchor', 'middle')
        .attr('font-weight', 'bold')
        .attr('font-size', '14px')
        .attr('fill', '#2c3e50')
        .text('Original Label Distribution');
      
      // Draw data rows
      uniqueThresholdClusters.forEach((cluster, i) => {
        const rowY = headerHeight + (i * rowHeight);
        const labels = clusterComposition[cluster];
        
        // Cluster column (left)
        // Rectangle
        tableGroup.append('rect')
          .attr('x', 14)
          .attr('y', rowY + rowHeight / 2 - 6)
          .attr('width', 12)
          .attr('height', 12)
          .attr('rx', 2)
          .attr('fill', thresholdBlobColors[cluster % thresholdBlobColors.length])
          .attr('fill-opacity', 0.7)
          .attr('stroke', '#fff')
          .attr('stroke-width', 1);
        
        // Cluster text
        tableGroup.append('text')
          .attr('x', 35)
          .attr('y', rowY + rowHeight / 2 + 4)
          .attr('font-size', '12px')
          .attr('fill', '#555')
          .text(`Cluster ${cluster}`);
        
        // Original Label Distribution column (right)
        if (labels && labels.length > 0) {
          let labelX = colWidth + 15;
          labels.forEach((labelInfo, labelIndex) => {
            const { label, count } = labelInfo;
            
            // Circle for each label
            tableGroup.append('circle')
              .attr('cx', labelX)
              .attr('cy', rowY + rowHeight / 2)
              .attr('r', 5)
              .attr('fill', originalLabelColors[label % originalLabelColors.length])
              .attr('stroke', '#fff')
              .attr('stroke-width', 1);
            
            // Label and count text
            tableGroup.append('text')
              .attr('x', labelX + 12)
              .attr('y', rowY + rowHeight / 2 + 3)
              .attr('font-size', '10px')
              .attr('fill', '#555')
              .text(`${label}(${count})`);
            
            labelX += 45; // More space for label + count
            
            // If we have too many labels, wrap to next line or truncate
            if (labelX > colWidth + 200) {
              if (labelIndex < labels.length - 1) {
                tableGroup.append('text')
                  .attr('x', labelX)
                  .attr('y', rowY + rowHeight / 2 + 3)
                  .attr('font-size', '10px')
                  .attr('fill', '#999')
                  .text('...');
              }
              return;
            }
          });
        } else {
          // Show "No data" if empty
          tableGroup.append('text')
            .attr('x', colWidth + 15)
            .attr('y', rowY + rowHeight / 2 + 3)
            .attr('font-size', '10px')
            .attr('fill', '#999')
            .text('No data');
        }
      });
    };
    
    // Handle window resize
    const handleResize = () => {
      if (!blobContainer.value) return;
      createVisualization();
    };
    
    // Clean up event listeners on unmount
    onBeforeUnmount(() => {
      window.removeEventListener('resize', handleResize);
      // Clean up tooltip
      d3.select('.point-tooltip').remove();
    });
    
    // Initialize on mount
    onMounted(() => {
      window.addEventListener('resize', handleResize);
      createVisualization();
    });
    
    // Recreate visualization when data, threshold, or selected cluster changes
    watch([() => props.data, () => props.selectedThreshold, () => props.selectedCluster, () => props.outliers], () => {
      createVisualization();
    }, { deep: true });
    
    return {
      blobContainer,
      legendContainer
    };
  }
});
</script>

<style scoped>
.cluster-blob {
  margin-bottom: 30px;
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.cluster-blob h3 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 16px;
  color: #2c3e50;
  font-weight: 600;
}

.blob-container {
  width: 100%;
  height: 500px;
  background-color: white;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid #dcdfe6;
  margin-bottom: 20px;
}

.legend {
  background-color: white;
  padding: 15px;
  border-radius: 4px;
  border: 1px solid #dcdfe6;
  max-height: 200px;
  overflow-y: auto;
}

svg {
  display: block;
  max-width: 100%;
}
</style>

<style>
.point-tooltip {
  transition: opacity 0.2s ease;
}
</style>
