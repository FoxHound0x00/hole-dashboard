<template>
  <div class="cluster-blob" :class="{ 'legend-expanded': legendExpanded, 'menu-expanded': menuExpanded }">
    <h3>Cluster Blob Visualization</h3>
    <div class="menu-toggle" @click="menuExpanded = !menuExpanded">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
        <path v-if="!menuExpanded" d="M5 3l6 5-6 5V3z"/>
        <path v-else d="M11 3L5 8l6 5V3z"/>
      </svg>
    </div>
    <div class="menu" v-show="menuExpanded">
      <div class="menu-header">Visualization Method</div>
      <button 
        v-for="method in visualizationMethods" 
        :key="method.id"
        class="menu-button"
        :class="{ active: selectedMethod === method.id }"
        @click="selectMethod(method.id)"
      >
        {{ method.label }}
      </button>
      
      <div class="menu-header" style="margin-top: 16px;">Display Mode</div>
      <div class="toggle-container">
        <label class="toggle-label">
          <input 
            type="checkbox" 
            v-model="showContours" 
            @change="createVisualization"
            class="toggle-checkbox"
          />
          <span class="toggle-slider"></span>
          <span class="toggle-text">{{ showContours ? 'Contours + Outliers' : 'All Points' }}</span>
        </label>
      </div>
      
      <div class="menu-header" style="margin-top: 16px;">Outlier Threshold</div>
      <div class="slider-container">
        <label class="slider-label">
          <span class="slider-text">Show classes &lt; {{ outlierThreshold }}%</span>
          <input 
            type="range" 
            v-model="outlierThreshold" 
            @input="createVisualization"
            min="5"
            max="50"
            step="5"
            class="slider"
          />
          <span class="slider-value">{{ outlierThreshold }}%</span>
        </label>
      </div>
    </div>
    <div ref="blobContainer" class="blob-container"></div>
    <div class="legend-toggle" @click="legendExpanded = !legendExpanded">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
        <path v-if="!legendExpanded" d="M11 3L5 8l6 5V3z"/>
        <path v-else d="M5 3l6 5-6 5V3z"/>
      </svg>
    </div>
    <div class="legend" ref="legendContainer" v-show="legendExpanded"></div>
  </div>
</template>

<script>
import { defineComponent, ref, onMounted, watch, onBeforeUnmount } from 'vue';
import * as d3 from 'd3';
import { contourDensity } from 'd3-contour';

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
  emits: ['blob-selected', 'point-selected', 'visualization-method-selected'],
  setup(props, { emit }) {
    const blobContainer = ref(null);
    const legendContainer = ref(null);
    const svg = ref(null);
    const width = ref(800);
    const height = ref(600);
    const projectionData = ref(null);  // Store projection data (PCA, t-SNE, LDA, MDS)
    const loading = ref(true);
    const legendExpanded = ref(false);
    const menuExpanded = ref(false);
    const selectedMethod = ref('pca');
    const showContours = ref(false);
    const outlierThreshold = ref(20); // Default 20% threshold
    
    // Visualization methods
    const visualizationMethods = [
      { id: 'pca', label: 'PCA' },
      { id: 'lda', label: 'LDA' },
      { id: 'mds', label: 'MDS' },
      { id: 'tsne', label: 'T-SNE' },
      { id: 'fd', label: 'FD-graph' }
    ];
    
    // Select visualization method
    const selectMethod = async (methodId) => {
      selectedMethod.value = methodId;
      emit('visualization-method-selected', methodId);
      
      // Fetch projection data for the selected method (except 'fd' which uses ForceDirectedGraph)
      if (methodId !== 'fd') {
        await fetchProjectionData(methodId);
        createVisualization();
      }
    };
    
    // Extended color scheme for original labels (consistent across all visualizations)
    const originalLabelColors = [
      ...d3.schemeCategory10,
      "#8dd3c7", "#ffffb3", "#bebada", "#fb8072", "#80b1d3", 
      "#fdb462", "#b3de69", "#fccde5", "#d9d9d9", "#bc80bd"
    ];
    
    // Fetch projection data from backend based on method
    const fetchProjectionData = async (method) => {
      try {
        loading.value = true;
        const endpoint = method === 'tsne' ? 'tsne' : method; // tsne endpoint is lowercase
        const response = await fetch(`http://localhost:5000/${endpoint}`);
        const data = await response.json();
        if (data.projection && data.labels) {
          projectionData.value = data;
        } else if (data.error) {
          console.error(`Error fetching ${method} data:`, data.error);
        }
        loading.value = false;
      } catch (error) {
        console.error(`Error fetching ${method} data:`, error);
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
      
      // Group for data points (on top)
      const pointGroup = svg.value.append('g').attr('class', 'points');
      
      // Draw blob hulls or contours based on mode
      if (showContours.value) {
        // CONTOUR MODE: Draw density contours with class color stripes for multi-class blobs
        console.log('=== CONTOUR MODE ===');
        console.log('Total blobs:', blobs.length);
        console.log('Total dataPoints:', dataPoints.length);
        console.log('Outlier threshold:', outlierThreshold.value + '%');
        
        // Calculate minority class points for each blob
        blobs.forEach(blob => {
          const blobPoints = dataPoints.filter(point => point.blobId === blob.id);
          
          if (blobPoints.length < 3) return;
          
          // Calculate class distribution in this blob
          const labelCounts = {};
          blobPoints.forEach(point => {
            labelCounts[point.originalLabel] = (labelCounts[point.originalLabel] || 0) + 1;
          });
          
          const totalPoints = blobPoints.length;
          
          // Mark minority class points (classes with < threshold %)
          blobPoints.forEach(point => {
            const classCount = labelCounts[point.originalLabel];
            const classPercentage = (classCount / totalPoints) * 100;
            point.isMinorityClass = classPercentage < outlierThreshold.value;
          });
          
          // Separate majority and minority points
          const majorityPoints = blobPoints.filter(p => !p.isMinorityClass);
          const minorityCount = blobPoints.filter(p => p.isMinorityClass).length;
          
          // Find the majority class (most frequent class in this blob)
          const classCounts = {};
          blobPoints.forEach(point => {
            classCounts[point.originalLabel] = (classCounts[point.originalLabel] || 0) + 1;
          });
          const majorityClass = Object.entries(classCounts)
            .reduce((max, [_, count]) => count > max.count ? { label: parseInt(_), count } : max, 
                    { label: 0, count: 0 }).label;
          
          console.log(`Blob ${blob.thresholdCluster}: ${blobPoints.length} total, ${majorityPoints.length} majority (for contours), ${minorityCount} minority (as points), majority class: ${majorityClass}`);
          
          // Check if this blob should be highlighted
          const isSelected = props.selectedCluster !== null && 
                           blob.thresholdCluster.toString() === props.selectedCluster.toString();
          
          // Get all classes in this blob with significant presence (>= threshold)
          const significantClasses = Object.entries(classCounts)
            .filter(([, count]) => (count / totalPoints * 100) >= outlierThreshold.value)
            .sort((a, b) => b[1] - a[1]) // Sort by count descending
            .map(([classLabel]) => parseInt(classLabel));
          
          const isMultiClass = significantClasses.length > 1;
          
          // Use majority class color for fill
          const fillColor = originalLabelColors[majorityClass % originalLabelColors.length];
          
          // Need at least 3 points for contours
          if (majorityPoints.length < 3) {
            console.warn(`Blob ${blob.thresholdCluster}: Not enough majority points for contours`);
            return;
          }
          
          // Create contour density generator for MAJORITY POINTS ONLY (exclude minority)
          // Use moderate bandwidth to keep contours within the point cloud
          const densityContours = contourDensity()
            .x(d => d.x)
            .y(d => d.y)
            .size([width.value, height.value])
            .bandwidth(20) // Smaller bandwidth = tighter contours around actual points
            .thresholds(10); // Moderate number of contour lines
          
          // Generate contours for majority class points only
          let contours;
          try {
            contours = densityContours(majorityPoints);
          } catch (error) {
            console.error(`Error generating contours for blob ${blob.thresholdCluster}:`, error);
            return;
          }
          
          if (!contours || contours.length === 0) return;
          
          // Fill the outer contour region
          const outerContour = contours[0];
          
          // For multi-class blobs, create a striped pattern stroke
          if (isMultiClass) {
            // Create a unique ID for this pattern
            const patternId = `stripe-pattern-${blob.id}`;
            
            // Define the pattern
            const defs = svg.value.select('defs').empty() 
              ? svg.value.append('defs') 
              : svg.value.select('defs');
            
            // Remove old pattern if exists
            defs.select(`#${patternId}`).remove();
            
            // Create pattern with stripes
            const pattern = defs.append('pattern')
              .attr('id', patternId)
              .attr('patternUnits', 'userSpaceOnUse')
              .attr('width', significantClasses.length * 8)
              .attr('height', 8)
              .attr('patternTransform', 'rotate(45)');
            
            // Add color stripes for each significant class
            significantClasses.forEach((classLabel, i) => {
              pattern.append('rect')
                .attr('x', i * 8)
                .attr('y', 0)
                .attr('width', 8)
                .attr('height', 8)
                .attr('fill', originalLabelColors[classLabel % originalLabelColors.length]);
            });
            
            // Draw the contour with striped stroke
            blobGroup.append('path')
              .attr('d', d3.geoPath()(outerContour))
              .attr('fill', fillColor)
              .attr('fill-opacity', isSelected ? 0.5 : 0.2)
              .attr('stroke', `url(#${patternId})`)
              .attr('stroke-width', isSelected ? 12 : 8)
              .attr('stroke-opacity', 1)
              .style('pointer-events', 'all')
              .style('cursor', 'pointer')
              .style('filter', isSelected ? 'drop-shadow(0px 4px 8px rgba(255, 107, 53, 0.4))' : 'none')
              .on('click', () => {
                emit('blob-selected', blob);
              })
              .on('mouseover', function(event) {
                d3.select(this)
                  .attr('fill-opacity', isSelected ? 0.6 : 0.4)
                  .attr('stroke-width', isSelected ? 12 : 10);
                showBlobTooltip(event, blob, blobPoints);
              })
              .on('mouseout', function() {
                d3.select(this)
                  .attr('fill-opacity', isSelected ? 0.5 : 0.2)
                  .attr('stroke-width', isSelected ? 12 : 8);
                hideBlobTooltip();
              });
          } else {
            // Single class - use simple colored stroke
            blobGroup.append('path')
              .attr('d', d3.geoPath()(outerContour))
              .attr('fill', fillColor)
              .attr('fill-opacity', isSelected ? 0.5 : 0.2)
              .attr('stroke', isSelected ? '#ff6b35' : fillColor)
              .attr('stroke-width', isSelected ? 4 : 2)
              .attr('stroke-opacity', isSelected ? 1 : 0.6)
              .style('pointer-events', 'all')
              .style('cursor', 'pointer')
              .style('filter', isSelected ? 'drop-shadow(0px 4px 8px rgba(255, 107, 53, 0.4))' : 'none')
              .on('click', () => {
                emit('blob-selected', blob);
              })
              .on('mouseover', function(event) {
                d3.select(this)
                  .attr('fill-opacity', isSelected ? 0.6 : 0.4)
                  .attr('stroke-width', isSelected ? 4 : 3);
                showBlobTooltip(event, blob, blobPoints);
              })
              .on('mouseout', function() {
                d3.select(this)
                  .attr('fill-opacity', isSelected ? 0.5 : 0.2)
                  .attr('stroke-width', isSelected ? 4 : 2);
                hideBlobTooltip();
              });
          }
          
          // Draw subtle inner contour lines to show density variation
          contours.slice(1).forEach((contour) => {
            blobGroup.append('path')
              .attr('d', d3.geoPath()(contour))
              .attr('fill', 'none')
              .attr('stroke', fillColor)
              .attr('stroke-width', 0.5)
              .attr('stroke-opacity', 0.3)
              .attr('stroke-linejoin', 'round')
              .style('pointer-events', 'none'); // Not interactive, just visual
          });
        });
      } else {
        // HULL MODE: Draw convex hulls with majority class colors
        blobs.forEach(blob => {
          const blobPoints = dataPoints.filter(point => point.blobId === blob.id);
          const points = blobPoints.map(point => [point.x, point.y]);
          
          if (points.length < 3) return null; // Need at least 3 points for a hull
          
          const hull = d3.polygonHull(points);
          
          if (hull) {
            const paddedHull = padHull(hull, 20);
            
            // Calculate majority class for this blob
            const classCounts = {};
            blobPoints.forEach(point => {
              classCounts[point.originalLabel] = (classCounts[point.originalLabel] || 0) + 1;
            });
            const majorityClass = Object.entries(classCounts)
              .reduce((max, [label, count]) => count > max.count ? { label: parseInt(label), count } : max, 
                      { label: 0, count: 0 }).label;
            
            // Use majority class color
            const color = originalLabelColors[majorityClass % originalLabelColors.length];
            
            // Check if this blob should be highlighted
            const isSelected = props.selectedCluster !== null && 
                             blob.thresholdCluster.toString() === props.selectedCluster.toString();
            
            blobGroup.append('path')
              .attr('d', `M${paddedHull.join('L')}Z`)
              .attr('fill', color)
              .attr('fill-opacity', isSelected ? 0.5 : 0.2)
              .attr('stroke', isSelected ? '#ff6b35' : color)
              .attr('stroke-width', isSelected ? 4 : 2)
              .attr('stroke-opacity', isSelected ? 1 : 0.6)
              .style('cursor', 'pointer')
              .style('filter', isSelected ? 'drop-shadow(0px 4px 8px rgba(255, 107, 53, 0.4))' : 'none')
              .on('click', () => {
                emit('blob-selected', blob);
              })
              .on('mouseover', function(event) {
                if (!isSelected) {
                  d3.select(this)
                    .attr('fill-opacity', 0.4)
                    .attr('stroke-width', 3);
                }
                // Show blob tooltip with distribution
                showBlobTooltip(event, blob, blobPoints);
              })
              .on('mouseout', function() {
                if (!isSelected) {
                  d3.select(this)
                    .attr('fill-opacity', 0.2)
                    .attr('stroke-width', 2);
                }
                // Hide blob tooltip
                hideBlobTooltip();
              });
          }
        });
      }
      
      // Draw data points - filter based on mode
      const pointsToShow = showContours.value 
        ? dataPoints.filter(d => d.isMinorityClass) // Only show minority class points in contour mode
        : dataPoints; // Show all points in hull mode
      
      // Clear existing points
      pointGroup.selectAll('circle').remove();
      
      // Use consistent styling for all points in both modes
      const circles = pointGroup.selectAll('circle')
        .data(pointsToShow)
        .join('circle')
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)
        .attr('r', d => d.isOutlier ? 3 : 5) // Consistent sizing
        .attr('fill', d => originalLabelColors[d.originalLabel % originalLabelColors.length])
        .attr('stroke', '#fff') // Always white stroke for consistency
        .attr('stroke-width', d => d.isOutlier ? 1 : 1.5) // Consistent stroke width
        .attr('fill-opacity', 1) // Always full opacity
        .style('cursor', 'pointer')
        .style('pointer-events', 'all');
      
      // Ensure points are drawn on top of contours/hulls
      pointGroup.raise();
      
      circles
        .on('click', (event, d) => {
          emit('point-selected', d);
        })
        .on('mouseover', function(event, d) {
          d3.select(this)
            .attr('r', d.isOutlier ? 4 : 7) // Consistent hover sizing
            .attr('stroke-width', 2);
            
          // Show tooltip or info
          showPointTooltip(event, d);
        })
        .on('mouseout', function(event, d) {
          d3.select(this)
            .attr('r', d.isOutlier ? 3 : 5) // Back to consistent size
            .attr('stroke-width', d.isOutlier ? 1 : 1.5);
            
          hidePointTooltip();
        });
      
      // Enable zoom and pan
      svg.value.call(d3.zoom()
        .extent([[0, 0], [width.value, height.value]])
        .scaleExtent([0.5, 5])
        .on('zoom', zoomed));
        
      function zoomed(event) {
        pointGroup.attr('transform', event.transform);
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
      
      // Use projection data if available, otherwise fallback to grid layout
      if (!projectionData.value || !projectionData.value.projection) {
        console.warn(`${selectedMethod.value.toUpperCase()} data not available, using fallback grid layout`);
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
      
      // USE PROJECTION DATA - The correct way!
      const projection = projectionData.value.projection;
      
      // Find extent of projection data for scaling
      const xExtent = d3.extent(projection.map(p => p[0]));
      const yExtent = d3.extent(projection.map(p => p[1]));
      
      // Create scales to map projection coordinates to SVG space
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
        
        // Calculate blob center from projection positions
        let centerX = 0, centerY = 0;
        points.forEach(point => {
          const projPos = projection[point.index];
          centerX += xScale(projPos[0]);
          centerY += yScale(projPos[1]);
        });
        centerX /= points.length;
        centerY /= points.length;
        
        blobs.push({
          id: blobIndex,
          thresholdCluster: parseInt(thresholdCluster),
          center: { x: centerX, y: centerY },
          radius: 50,  // Not used with projections
          pointCount: points.length,
          threshold: thresholdKey
        });
        
        // Position points using their actual projection coordinates
        points.forEach(point => {
          const projPos = projection[point.index];
          const x = xScale(projPos[0]);
          const y = yScale(projPos[1]);
          
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
    
    // Show blob tooltip with distribution
    const showBlobTooltip = (event, blob, blobPoints) => {
      // Calculate distribution of original labels in this blob
      const labelCounts = {};
      blobPoints.forEach(point => {
        const label = point.originalLabel;
        labelCounts[label] = (labelCounts[label] || 0) + 1;
      });
      
      // Convert to sorted array of {label, count} objects
      const labelDistribution = Object.entries(labelCounts)
        .map(([label, count]) => ({ label: parseInt(label), count }))
        .sort((a, b) => a.label - b.label);
      
      const totalCount = blobPoints.length;
      
      // Create or update tooltip
      let tooltip = d3.select('body').select('.blob-tooltip');
      if (tooltip.empty()) {
        tooltip = d3.select('body')
          .append('div')
          .attr('class', 'blob-tooltip')
          .style('position', 'absolute')
          .style('background', 'rgba(0, 0, 0, 0.9)')
          .style('color', 'white')
          .style('padding', '12px')
          .style('border-radius', '6px')
          .style('font-size', '12px')
          .style('pointer-events', 'none')
          .style('z-index', '1000')
          .style('max-width', '300px')
          .style('box-shadow', '0 4px 12px rgba(0, 0, 0, 0.3)');
      }
      
      // Build distribution HTML
      const distributionHtml = labelDistribution.length > 0
        ? labelDistribution.map(({ label, count }) => {
            const percentage = ((count / totalCount) * 100).toFixed(1);
            return `<div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
              <span style="display: flex; align-items: center;">
                <span style="display: inline-block; width: 12px; height: 12px; background: ${originalLabelColors[label % originalLabelColors.length]}; margin-right: 6px; border-radius: 2px;"></span>
                <span>Label ${label}:</span>
              </span>
              <span style="margin-left: 12px; font-weight: 600;">${count} (${percentage}%)</span>
            </div>`;
          }).join('')
        : '<div>No data</div>';
      
      // Calculate tooltip position (avoid going off-screen)
      const tooltipOffset = 15;
      const tooltipWidth = 300; // max-width
      const tooltipHeight = 200; // estimated height
      let left = event.pageX + tooltipOffset;
      let top = event.pageY - 10;
      
      // Adjust if tooltip would go off right edge
      if (left + tooltipWidth > window.innerWidth) {
        left = event.pageX - tooltipWidth - tooltipOffset;
      }
      
      // Adjust if tooltip would go off bottom edge
      if (top + tooltipHeight > window.innerHeight) {
        top = event.pageY - tooltipHeight - tooltipOffset;
      }
      
      // Ensure tooltip doesn't go off left or top edges
      left = Math.max(10, left);
      top = Math.max(10, top);
      
      tooltip
        .html(`
          <div style="font-weight: bold; font-size: 13px; margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 6px;">
            Cluster ${blob.thresholdCluster}
          </div>
          <div style="margin-bottom: 8px;">
            <strong>Total Points:</strong> ${totalCount}
          </div>
          <div style="margin-top: 8px;">
            <div style="font-weight: 600; margin-bottom: 6px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">Distribution:</div>
            ${distributionHtml}
          </div>
        `)
        .style('left', left + 'px')
        .style('top', top + 'px')
        .style('opacity', 1);
    };
    
    // Hide blob tooltip
    const hideBlobTooltip = () => {
      d3.select('.blob-tooltip').style('opacity', 0);
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
        
        // Find majority class for this cluster
        const majorityClass = labels && labels.length > 0
          ? labels.reduce((max, l) => l.count > max.count ? l : max, { label: 0, count: 0 }).label
          : 0;
        const clusterColor = originalLabelColors[majorityClass % originalLabelColors.length];
        
        // Background for alternating rows
        if (index % 2 === 0) {
          group.append('rect')
            .attr('x', 0)
            .attr('y', y)
            .attr('width', containerWidth - 6)
            .attr('height', itemHeight)
            .attr('fill', '#f9f9f9');
        }
        
        // Cluster indicator (colored square) - use majority class color
        group.append('rect')
          .attr('x', 3)
          .attr('y', y + 9)
          .attr('width', 10)
          .attr('height', 10)
          .attr('fill', clusterColor)
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
      // Clean up tooltips
      d3.select('.point-tooltip').remove();
      d3.select('.blob-tooltip').remove();
    });
    
    // Initialize on mount
    onMounted(async () => {
      window.addEventListener('resize', handleResize);
      await fetchProjectionData(selectedMethod.value);
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
      }, 150); // Increased debounce for better performance
    };

    // Watch for changes and recreate visualization (debounced)
    // Separate watches to avoid unnecessary re-renders
    watch([() => props.data, () => props.selectedThreshold, () => props.selectedCluster], () => {
      if (selectedMethod.value !== 'fd') {
        debouncedCreateVisualization();
      }
    }, { deep: false }); // Shallow watch for better performance
    
    // Separate watch for mode toggle
    watch(showContours, () => {
      if (selectedMethod.value !== 'fd') {
        createVisualization(); // Immediate update for toggle
      }
    });
    
    return {
      blobContainer,
      legendContainer,
      loading,
      legendExpanded,
      menuExpanded,
      selectedMethod,
      visualizationMethods,
      selectMethod,
      showContours,
      outlierThreshold
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
  grid-template-columns: 0px 24px 1fr 24px 0px;
  grid-template-rows: auto 1fr;
  grid-template-areas:
    ". title title . ."
    "menu menu-toggle blob legend-toggle legend";
  gap: 0;
  overflow: hidden;
  position: relative;
  transition: grid-template-columns 0.3s ease;
}

.cluster-blob.legend-expanded {
  grid-template-columns: 0px 24px 1fr 24px 350px;
}

.cluster-blob.menu-expanded {
  grid-template-columns: 200px 24px 1fr 24px 0px;
}

.cluster-blob.menu-expanded.legend-expanded {
  grid-template-columns: 200px 24px 1fr 24px 350px;
}

.cluster-blob h3 {
  grid-area: title;
  margin: 0 0 6px 0;
  font-size: 13px;
  color: #333;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.menu-toggle {
  grid-area: menu-toggle;
  grid-row: 2;
  width: 24px;
  height: 100%;
  background-color: #fafafa;
  border-top: 1px solid #d0d0d0;
  border-bottom: 1px solid #d0d0d0;
  border-left: 1px solid #d0d0d0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.15s;
  color: #666;
}

.menu-toggle:hover {
  background-color: #e8e8e8;
  color: #333;
}

.menu {
  grid-area: menu;
  background-color: white;
  padding: 8px;
  border-top: 1px solid #d0d0d0;
  border-bottom: 1px solid #d0d0d0;
  border-left: 1px solid #d0d0d0;
  overflow-y: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.menu-header {
  font-size: 13px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e0e0e0;
  letter-spacing: 0.3px;
}

.menu-button {
  width: 100%;
  padding: 8px 12px;
  margin-bottom: 4px;
  background-color: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #333;
  text-align: left;
  transition: all 0.15s ease;
}

.menu-button:hover {
  background-color: #e8e8e8;
  border-color: #c0c0c0;
}

.menu-button.active {
  background-color: #3498db;
  color: white;
  border-color: #2980b9;
  font-weight: 600;
}

.menu-button.active:hover {
  background-color: #2980b9;
}

.toggle-container {
  padding: 8px 4px;
}

.toggle-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.toggle-checkbox {
  display: none;
}

.toggle-slider {
  position: relative;
  width: 40px;
  height: 20px;
  background-color: #ccc;
  border-radius: 20px;
  transition: background-color 0.2s ease;
  margin-right: 8px;
  flex-shrink: 0;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  left: 2px;
  top: 2px;
  background-color: white;
  border-radius: 50%;
  transition: transform 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.toggle-checkbox:checked + .toggle-slider {
  background-color: #3498db;
}

.toggle-checkbox:checked + .toggle-slider::before {
  transform: translateX(20px);
}

.toggle-text {
  font-size: 11px;
  color: #333;
  font-weight: 500;
}

.slider-container {
  padding: 8px 4px;
}

.slider-label {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.slider-text {
  font-size: 11px;
  color: #555;
  font-weight: 500;
}

.slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #ddd;
  outline: none;
  -webkit-appearance: none;
}

.slider::-webkit-slider-thumb {
  appearance: none;
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #3498db;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #3498db;
  cursor: pointer;
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.slider:hover::-webkit-slider-thumb {
  background: #2980b9;
}

.slider:hover::-moz-range-thumb {
  background: #2980b9;
}

.slider-value {
  font-size: 12px;
  font-weight: 600;
  color: #3498db;
  text-align: center;
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
  grid-area: legend-toggle;
  grid-row: 2;
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
.point-tooltip,
.blob-tooltip {
  transition: opacity 0.2s ease;
}
</style>
