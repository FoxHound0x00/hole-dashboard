<template>
  <div class="cluster-blob" :class="{ 'legend-expanded': legendExpanded }">
    <h3>Cluster Blob Visualization</h3>
    <div ref="blobContainer" class="blob-container"></div>
    <div class="legend-toggle" @click="legendExpanded = !legendExpanded">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
        <path v-if="!legendExpanded" d="M5 3l6 5-6 5V3z"/>
        <path v-else d="M11 3L5 8l6 5V3z"/>
      </svg>
    </div>
    <div class="legend" ref="legendContainer" v-show="legendExpanded"></div>
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
    const pcaData = ref(null);  // Store PCA projections
    const loading = ref(true);
    const legendExpanded = ref(false);
    
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
    
    // Fetch PCA data from backend
    const fetchPCAData = async () => {
      try {
        loading.value = true;
        const response = await fetch('http://localhost:5000/pca');
        const data = await response.json();
        if (data.projection && data.labels) {
          pcaData.value = data;
        }
        loading.value = false;
      } catch (error) {
        console.error('Error fetching PCA data:', error);
        loading.value = false;
      }
    };
    
    // Create the visualization
    const createVisualization = () => {
      if (!blobContainer.value) return;
      
      // Clear any previous visualization efficiently
      const container = blobContainer.value;
      while (container.firstChild) {
        container.removeChild(container.firstChild);
      }
      
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
      
      // Use PCA projections if available, otherwise fallback to grid layout
      if (!pcaData.value || !pcaData.value.projection) {
        console.warn('PCA data not available, using fallback grid layout');
        // Fallback: Create blobs and position data points in grid
        const blobIds = Object.keys(thresholdGroups);
        const gridSize = Math.ceil(Math.sqrt(blobIds.length));
        const cellWidth = width.value / (gridSize + 1);
        const cellHeight = height.value / (gridSize + 1);
        
        blobIds.forEach((thresholdCluster, blobIndex) => {
          const points = thresholdGroups[thresholdCluster];
          const row = Math.floor(blobIndex / gridSize);
          const col = blobIndex % gridSize;
          const blobCenter = {
            x: cellWidth * (col + 1),
            y: cellHeight * (row + 1)
          };
          const blobRadius = Math.min(Math.max(points.length * 3, 30), 80);
          
          blobs.push({
            id: blobIndex,
            thresholdCluster: parseInt(thresholdCluster),
            center: blobCenter,
            radius: blobRadius,
            pointCount: points.length,
            threshold: thresholdKey
          });
          
          points.forEach((point, pointIndex) => {
            const angle = (pointIndex / points.length) * Math.PI * 2;
            const spiralRadius = (pointIndex / points.length) * blobRadius * 0.8;
            const x = blobCenter.x + Math.cos(angle) * spiralRadius;
            const y = blobCenter.y + Math.sin(angle) * spiralRadius;
            
            dataPoints.push({
              id: `point-${point.index}`,
              x, y,
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
      }
      
      // USE PCA PROJECTIONS - The correct way!
      const projection = pcaData.value.projection;
      
      // Find extent of PCA data for scaling
      const xExtent = d3.extent(projection.map(p => p[0]));
      const yExtent = d3.extent(projection.map(p => p[1]));
      
      // Create scales to map PCA coordinates to SVG space
      const margin = 50;
      const xScale = d3.scaleLinear()
        .domain(xExtent)
        .range([margin, width.value - margin]);
      const yScale = d3.scaleLinear()
        .domain(yExtent)
        .range([height.value - margin, margin]);  // Flip Y axis
      
      // Create blobs based on threshold clusters
      const blobIds = Object.keys(thresholdGroups);
      blobIds.forEach((thresholdCluster, blobIndex) => {
        const points = thresholdGroups[thresholdCluster];
        
        // Calculate blob center from PCA positions
        let centerX = 0, centerY = 0;
        points.forEach(point => {
          const pcaPos = projection[point.index];
          centerX += xScale(pcaPos[0]);
          centerY += yScale(pcaPos[1]);
        });
        centerX /= points.length;
        centerY /= points.length;
        
        blobs.push({
          id: blobIndex,
          thresholdCluster: parseInt(thresholdCluster),
          center: { x: centerX, y: centerY },
          radius: 50,  // Not used with PCA
          pointCount: points.length,
          threshold: thresholdKey
        });
        
        // Position points using their actual PCA coordinates
        points.forEach(point => {
          const pcaPos = projection[point.index];
          const x = xScale(pcaPos[0]);
          const y = yScale(pcaPos[1]);
          
          dataPoints.push({
            id: `point-${point.index}`,
            x, y,
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
      
      // Get container width and height for responsive sizing
      const containerWidth = legendContainer.value.clientWidth || 350;
      const containerHeight = legendContainer.value.clientHeight || 400;
      
      // Calculate optimal item height to fit all clusters without scrolling
      const headerHeight = 25;
      const padding = 10;
      const availableHeight = containerHeight - headerHeight - padding;
      const itemHeight = Math.max(20, Math.min(35, availableHeight / uniqueThresholdClusters.length));
      const totalHeight = headerHeight + (uniqueThresholdClusters.length * itemHeight) + padding;
      
      const legendSvg = d3.select(legendContainer.value)
        .append('svg')
        .attr('width', containerWidth)
        .attr('height', '100%')
        .attr('viewBox', `0 0 ${containerWidth} ${totalHeight}`)
        .attr('preserveAspectRatio', 'xMidYMin meet')
        .style('font-family', 'Arial, sans-serif');
      
      const group = legendSvg.append('g')
        .attr('transform', 'translate(3, 3)');
      
      // Header
      group.append('text')
        .attr('x', 3)
        .attr('y', 14)
        .attr('font-weight', 'bold')
        .attr('font-size', '11px')
        .attr('fill', '#2c3e50')
        .text('Label Distribution');
      
      // Draw each cluster as a compact list item
      uniqueThresholdClusters.forEach((cluster, index) => {
        const y = headerHeight + (index * itemHeight);
        const labels = clusterComposition[cluster];
        
        // Background for alternating rows
        if (index % 2 === 0) {
          group.append('rect')
            .attr('x', 0)
            .attr('y', y)
            .attr('width', containerWidth - 6)
            .attr('height', itemHeight)
            .attr('fill', '#f9f9f9');
        }
        
        // Cluster indicator (colored square)
        group.append('rect')
          .attr('x', 3)
          .attr('y', y + 9)
          .attr('width', 10)
          .attr('height', 10)
          .attr('fill', thresholdBlobColors[cluster % thresholdBlobColors.length])
          .attr('stroke', '#fff')
          .attr('stroke-width', 1);
        
        // Cluster number
        group.append('text')
          .attr('x', 18)
          .attr('y', y + 17)
          .attr('font-size', '10px')
          .attr('font-weight', '600')
          .attr('fill', '#333')
          .text(`C${cluster}`);
        
        // Label distribution - horizontal stacked bar chart
        if (labels && labels.length > 0) {
          const barStartX = 45;
          const barWidth = containerWidth - barStartX - 15;
          const barHeight = 16;
          const barY = y + 10;
          
          // Calculate total count
          const totalCount = labels.reduce((sum, l) => sum + l.count, 0);
          
          // Draw stacked bar
          let currentX = barStartX;
          labels.forEach((labelInfo) => {
            const { label, count } = labelInfo;
            const segmentWidth = (count / totalCount) * barWidth;
            
            // Draw bar segment
            group.append('rect')
              .attr('x', currentX)
              .attr('y', barY)
              .attr('width', segmentWidth)
              .attr('height', barHeight)
              .attr('fill', originalLabelColors[label % originalLabelColors.length])
              .attr('stroke', '#fff')
              .attr('stroke-width', 0.5)
              .append('title')
              .text(`Label ${label}: ${count} (${(count/totalCount*100).toFixed(1)}%)`);
            
            // Add count text if segment is wide enough
            if (segmentWidth > 20) {
              group.append('text')
                .attr('x', currentX + segmentWidth / 2)
                .attr('y', barY + barHeight / 2 + 3)
                .attr('text-anchor', 'middle')
                .attr('font-size', '8px')
                .attr('fill', '#fff')
                .attr('font-weight', 'bold')
                .text(count);
            }
            
            currentX += segmentWidth;
          });
          
          // Draw border around entire bar
          group.append('rect')
            .attr('x', barStartX)
            .attr('y', barY)
            .attr('width', barWidth)
            .attr('height', barHeight)
            .attr('fill', 'none')
            .attr('stroke', '#ddd')
            .attr('stroke-width', 1);
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
    onMounted(async () => {
      window.addEventListener('resize', handleResize);
      await fetchPCAData();
      createVisualization();
    });
    
    // Debounced visualization update
    let visualizationTimeout = null;
    const debouncedCreateVisualization = () => {
      if (visualizationTimeout) {
        clearTimeout(visualizationTimeout);
      }
      visualizationTimeout = setTimeout(() => {
        createVisualization();
      }, 100); // 100ms debounce
    };

    // Watch for changes and recreate visualization (debounced)
    watch([() => props.data, () => props.selectedThreshold, () => props.selectedCluster, () => props.outliers], () => {
      debouncedCreateVisualization();
    });
    
    return {
      blobContainer,
      legendContainer,
      loading,
      legendExpanded
    };
  }
});
</script>

<style scoped>
.cluster-blob {
  width: 100%;
  height: 100%;
  background-color: #f8f9fa;
  padding: 8px;
  border: 1px solid #e0e0e0;
  display: grid;
  grid-template-columns: 1fr 24px 0px;
  grid-template-rows: auto 1fr;
  grid-template-areas:
    "title title title"
    "blob toggle legend";
  gap: 0;
  overflow: hidden;
  position: relative;
  transition: grid-template-columns 0.3s ease;
}

.cluster-blob.legend-expanded {
  grid-template-columns: 1fr 24px 350px;
}

.cluster-blob h3 {
  grid-area: title;
  margin: 0 0 6px 0;
  font-size: 13px;
  color: #333;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.blob-container {
  grid-area: blob;
  background-color: white;
  overflow: hidden;
  border: 1px solid #d0d0d0;
  min-height: 0;
  min-width: 0;
  margin-right: 0;
}

.legend-toggle {
  grid-area: toggle;
  width: 24px;
  height: 100%;
  background-color: #fafafa;
  border-top: 1px solid #d0d0d0;
  border-bottom: 1px solid #d0d0d0;
  border-right: 1px solid #d0d0d0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.15s;
  color: #666;
}

.legend-toggle:hover {
  background-color: #e8e8e8;
  color: #333;
}

.legend {
  grid-area: legend;
  background-color: white;
  padding: 8px;
  border-top: 1px solid #d0d0d0;
  border-bottom: 1px solid #d0d0d0;
  border-right: 1px solid #d0d0d0;
  overflow: hidden;
  font-size: 10px;
  min-height: 0;
  margin-left: 0;
  display: flex;
  flex-direction: column;
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
