<template>
  <div class="sankey-wrapper">
    <div ref="chart" class="chart-container"></div>
    <div class="info-box" ref="infoBox">
      <div v-if="selectedInfo">
        <h3>{{ selectedInfo.title }}</h3>
        <div class="info-stats">
          <div class="stat-item">
            <div class="stat-value">{{ selectedInfo.count }}</div>
            <div class="stat-label">Items</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ selectedInfo.incoming }}</div>
            <div class="stat-label">Incoming</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ selectedInfo.outgoing }}</div>
            <div class="stat-label">Outgoing</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ selectedInfo.total }}</div>
            <div class="stat-label">Total</div>
          </div>
        </div>
      </div>
      <div v-else class="empty-info">
        Hover over a cluster to see details
      </div>
    </div>
  </div>
</template>

<script>
import * as d3 from 'd3';

export default {
  name: 'ClusterSankey',
  props: {
    data: {
      type: Object,
      required: true,
      default: () => ({})
    },
    width: {
      type: Number,
      default: 800
    },
    height: {
      type: Number,
      default: 500
    },
    noisyThreshold: {
      type: Number,
      default: 5
    }
  },
  emits: ['threshold-selected', 'cluster-selected'],
  data() {
    return {
      selectedInfo: null,
      selectedThreshold: null
    };
  },
  mounted() {
    this.renderChart();
  },
  watch: {
    data: {
      handler() {
        this.renderChart();
      },
      deep: true
    },
    noisyThreshold() {
      this.renderChart();
    }
  },
  methods: {
    // Helper function to escape CSS selectors
    escapeSelector(selector) {
      return selector.replace(/[ !"#$%&'()*+,.:;<=>?@[\\\]^`{|}~]/g, '\\$&');
    },
    // Update the info box with cluster data
    updateInfoBox(stage, cluster, count, connections, isSelected = false) {
      this.selectedInfo = {
        title: `${stage} - Cluster ${cluster}${isSelected ? ' (Selected)' : ''}`,
        count: count,
        incoming: connections.incoming,
        outgoing: connections.outgoing,
        total: connections.total
      };
    },
    // Clear the info box
    clearInfoBox() {
      this.selectedInfo = null;
    },
    // Handle threshold selection
    selectThreshold(threshold) {
      this.selectedThreshold = threshold;
      this.$emit('threshold-selected', threshold);
    },
    renderChart() {
      const el = this.$refs.chart;
      if (!el || !this.data || Object.keys(this.data).length === 0) {
        return;
      }
      
      el.innerHTML = '';
      
      // Use container dimensions instead of props
      const width = el.clientWidth || 800;
      const height = el.clientHeight || 500;
      const margin = { top: 60, right: 50, bottom: 30, left: 50 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
      
      // Get stages (keys from data) and sort them properly
      const allStages = Object.keys(this.data);
      if (allStages.length < 2) return;
      
      // Sort stages: Original Labels first, then numerical stages in ascending order
      const stages = allStages.sort((a, b) => {
        if (a === 'Original Labels') return -1;
        if (b === 'Original Labels') return 1;
        return parseFloat(a) - parseFloat(b); // Ascending order for thresholds
      });
      
      // Create SVG
      const svg = d3.select(el)
        .append('svg')
        .attr('width', width)
        .attr('height', height);
      
      // Add a group for the chart
      const chart = svg.append('g')
        .attr('transform', `translate(${margin.left}, ${margin.top})`);
      
      // Find all unique clusters across all stages
      const uniqueClusters = new Set();
      stages.forEach(stage => {
        if (Array.isArray(this.data[stage])) {
          this.data[stage].forEach(cluster => {
            uniqueClusters.add(cluster);
          });
        }
      });
      
      // Convert to array and sort numerically by cluster ID
      const clusters = Array.from(uniqueClusters).sort((a, b) => {
        // Try to parse as numbers first
        const numA = parseFloat(a);
        const numB = parseFloat(b);
        
        // If both are valid numbers, sort numerically
        if (!isNaN(numA) && !isNaN(numB)) {
          return numA - numB;
        }
        
        // Otherwise, fall back to alphabetical sort
        return a.localeCompare(b);
      });
      
      // Extended color scheme for original labels (consistent with ClusterBlob)
      const originalLabelColors = [
        ...d3.schemeCategory10,
        "#8dd3c7", "#ffffb3", "#bebada", "#fb8072", "#80b1d3", 
        "#fdb462", "#b3de69", "#fccde5", "#d9d9d9", "#bc80bd"
      ];
      
      // Calculate majority class for each cluster in each stage
      const clusterMajorityClass = {};
      if (this.data['Original Labels']) {
        stages.forEach(stage => {
          if (!clusterMajorityClass[stage]) clusterMajorityClass[stage] = {};
          
          const stageData = this.data[stage];
          const originalLabels = this.data['Original Labels'];
          
          if (Array.isArray(stageData) && Array.isArray(originalLabels)) {
            clusters.forEach(cluster => {
              // Find all indices where this cluster appears in this stage
              const classCount = {};
              stageData.forEach((clusterValue, idx) => {
                if (clusterValue === cluster) {
                  const originalLabel = originalLabels[idx];
                  classCount[originalLabel] = (classCount[originalLabel] || 0) + 1;
                }
              });
              
              // Find majority class
              const majorityClass = Object.entries(classCount)
                .reduce((max, [label, count]) => count > max.count ? { label: parseInt(label), count } : max, 
                        { label: 0, count: 0 }).label;
              
              clusterMajorityClass[stage][cluster] = majorityClass;
            });
          }
        });
      }
      
      // Create color scale based on majority class
      const colorScale = (cluster, stage) => {
        const majorityClass = clusterMajorityClass[stage]?.[cluster] ?? 0;
        return originalLabelColors[majorityClass % originalLabelColors.length];
      };
      
      // Create x scale for stages
      const xScale = d3.scalePoint()
        .domain(stages)
        .range([0, innerWidth])
        .padding(0.5);
      
      // Calculate clusters per stage and their counts
      const stageData = {};
      stages.forEach(stage => {
        stageData[stage] = {};
        clusters.forEach(cluster => {
          stageData[stage][cluster] = 0;
        });
        
        if (Array.isArray(this.data[stage])) {
          this.data[stage].forEach(cluster => {
            stageData[stage][cluster]++;
          });
        }
      });
      
      // Calculate flows between stages
      const flows = [];
      for (let i = 0; i < stages.length - 1; i++) {
        const sourceStage = stages[i];
        const targetStage = stages[i + 1];
        
        const sourceData = this.data[sourceStage];
        const targetData = this.data[targetStage];
        
        if (Array.isArray(sourceData) && Array.isArray(targetData)) {
          // Count how many items go from each source cluster to each target cluster
          const flowMap = {};
          
          // Only process up to the length of the shorter array
          const minLength = Math.min(sourceData.length, targetData.length);
          
          for (let j = 0; j < minLength; j++) {
            const sourceCluster = sourceData[j];
            const targetCluster = targetData[j];
            const flowKey = `${sourceCluster}-${targetCluster}`;
            
            if (!flowMap[flowKey]) {
              flowMap[flowKey] = {
                source: sourceCluster,
                target: targetCluster,
                count: 0
              };
            }
            
            flowMap[flowKey].count++;
          }
          
          // Add flow data with stage information
          Object.values(flowMap).forEach(flow => {
            flows.push({
              sourceStage,
              targetStage,
              sourceCluster: flow.source,
              targetCluster: flow.target,
              count: flow.count
            });
          });
        }
      }
      
      // Calculate incoming and outgoing connections for each cluster in each stage
      const clusterConnections = {};
      stages.forEach(stage => {
        clusterConnections[stage] = {};
        clusters.forEach(cluster => {
          clusterConnections[stage][cluster] = {
            incoming: 0,
            outgoing: 0,
            total: 0
          };
        });
      });
      
      // Calculate outgoing connections
      flows.forEach(flow => {
        const { sourceStage, sourceCluster, count } = flow;
        clusterConnections[sourceStage][sourceCluster].outgoing += count;
      });
      
      // Calculate incoming connections
      flows.forEach(flow => {
        const { targetStage, targetCluster, count } = flow;
        clusterConnections[targetStage][targetCluster].incoming += count;
      });
      
      // Calculate total connections (incoming + outgoing)
      stages.forEach(stage => {
        clusters.forEach(cluster => {
          const connections = clusterConnections[stage][cluster];
          connections.total = connections.incoming + connections.outgoing;
        });
      });
      
      // Calculate vertical positions of clusters within each stage (STACKED BAR STYLE)
      const stageClusterPositions = {};
      stages.forEach(stage => {
        const clusterPositions = {};
        
        // Sort clusters by cluster ID (ascending) for consistent stacking, then by count
        const sortedClusters = Object.entries(stageData[stage])
          .filter(([, count]) => count > 0)
          .sort((a, b) => {
            // First sort by cluster ID numerically
            const numA = parseFloat(a[0]);
            const numB = parseFloat(b[0]);
            
            if (!isNaN(numA) && !isNaN(numB)) {
              return numA - numB; // Ascending order by cluster ID
            }
            
            // Fall back to alphabetical if not numeric
            return a[0].localeCompare(b[0]);
          })
          .map(([cluster]) => cluster);
        
        // Calculate total data points in this stage
        const totalDataPointsInStage = sortedClusters.reduce((sum, cluster) => {
          return sum + stageData[stage][cluster];
        }, 0);
        
        // Create stacked bars - each cluster gets height proportional to its data points
        const minVisibleHeight = 3; // Minimum height to make tiny clusters visible
        
        // First pass: calculate initial heights
        const initialHeights = {};
        sortedClusters.forEach(cluster => {
          const itemCount = stageData[stage][cluster];
          const proportionOfStage = itemCount / totalDataPointsInStage;
          let height = proportionOfStage * innerHeight;
          
          // Ensure tiny clusters are still visible
          if (height > 0 && height < minVisibleHeight) {
            height = minVisibleHeight;
          }
          
          initialHeights[cluster] = height;
        });
        
        // Calculate total height needed
        const totalNeededHeight = Object.values(initialHeights).reduce((sum, h) => sum + h, 0);
        
        // Small gap between segments for visual separation
        const segmentGap = 0.5;
        const totalGaps = (sortedClusters.length - 1) * segmentGap;
        const totalHeightWithGaps = totalNeededHeight + totalGaps;
        
        // Scale down if needed to fit within canvas
        const scaleFactor = totalHeightWithGaps > innerHeight ? innerHeight / totalHeightWithGaps : 1;
        
        // Second pass: assign positions with scaled heights and gaps
        let currentY = 0;
        sortedClusters.forEach((cluster, index) => {
          const height = initialHeights[cluster] * scaleFactor;
          
          clusterPositions[cluster] = {
            y: currentY,
            height,
            connections: clusterConnections[stage][cluster]
          };
          
          // Add gap after each segment except the last one
          currentY += height + (index < sortedClusters.length - 1 ? segmentGap * scaleFactor : 0);
        });
        
        stageClusterPositions[stage] = clusterPositions;
      });
      
      // Find maximum flow count for scaling line widths
      const maxFlowCount = Math.max(1, d3.max(flows, flow => flow.count));
      
      // Create a scale for line widths
      const lineWidthScale = d3.scaleLinear()
        .domain([1, maxFlowCount])
        .range([1, 6])
        .clamp(true);
      
      // Keep track of active selection state
      let activeSelection = {
        stage: null,
        cluster: null,
        active: false
      };
      
      // Helper for clearing active selection
      const clearActiveSelection = () => {
        // Reset all nodes to normal with transition
        chart.selectAll('.node')
          .transition()
          .duration(150)
          .attr('stroke', 'none')
          .attr('stroke-width', 0);
        
        // Reset all flows to normal with transition
        chart.selectAll('.flow')
          .transition()
          .duration(150)
          .style('opacity', 0.4)
          .style('stroke-width', d => lineWidthScale(d.count));
        
        activeSelection.active = false;
        
        // Clear info box
        this.clearInfoBox();
      };
      
      // Function to get incoming flows and source nodes for a cluster
      const getIncomingFlows = (targetStage, targetCluster) => {
        return flows.filter(flow => 
          flow.targetStage === targetStage && flow.targetCluster === targetCluster
        );
      };
      
      // Function to highlight incoming connections and source nodes
      const highlightIncoming = (targetStage, targetCluster, permanent = false) => {
        // Dim all flows with transition
        chart.selectAll('.flow')
          .transition()
          .duration(150)
          .style('opacity', 0.1)
          .style('stroke-width', d => lineWidthScale(d.count));
        
        // Get all incoming flows
        const incomingFlows = getIncomingFlows(targetStage, targetCluster);
        
        // Highlight incoming flows
        incomingFlows.forEach(flow => {
          // Escape selectors to handle spaces correctly
          const sourceClass = this.escapeSelector(`flow-source-${flow.sourceCluster}`);
          const targetClass = this.escapeSelector(`flow-target-${flow.targetCluster}`);
          
          chart.selectAll(`.${sourceClass}.${targetClass}`)
            .filter(d => d.sourceStage === flow.sourceStage && d.targetStage === flow.targetStage)
            .transition()
            .duration(150)
            .style('opacity', 0.8)
            .style('stroke-width', d => lineWidthScale(d.count) + 2);
          
          // Highlight source nodes if permanent selection (clicked)
          if (permanent) {
            // Escape selector
            const nodeClass = this.escapeSelector(`node-${flow.sourceStage}-${flow.sourceCluster}`);
            chart.selectAll(`.${nodeClass}`)
              .transition()
              .duration(150)
              .attr('stroke', '#ff8800')
              .attr('stroke-width', 2);
          }
        });
        
        // Highlight the target node (escape selector)
        const nodeClass = this.escapeSelector(`node-${targetStage}-${targetCluster}`);
        chart.selectAll(`.${nodeClass}`)
          .transition()
          .duration(150)
          .attr('stroke', permanent ? '#ff0000' : '#ffcc00')
          .attr('stroke-width', 2);
      };
      
      // Draw interactive threshold labels (discrete style)
      const self = this; // Store reference to Vue component
      chart.selectAll('.threshold-label')
        .data(stages.filter(stage => stage !== 'Original Labels'))
        .enter()
        .append('text')
        .attr('class', 'threshold-label')
        .attr('x', d => xScale(d))
        .attr('y', -10)
        .attr('text-anchor', 'middle')
        .attr('font-weight', 'bold')
        .attr('font-size', '12px')
        .attr('fill', d => self.selectedThreshold === d ? '#e74c3c' : '#333')
        .style('cursor', 'pointer')
        .style('transition', 'all 0.2s ease')
        .text(d => {
          const num = parseFloat(d);
          return isNaN(num) ? d : num.toFixed(3);
        })
        .on('mouseover', function(event, d) {
          if (d !== self.selectedThreshold) {
            d3.select(this)
              .attr('fill', '#666')
              .style('text-decoration', 'underline');
          }
        })
        .on('mouseout', function(event, d) {
          if (d !== self.selectedThreshold) {
            d3.select(this)
              .attr('fill', '#333')
              .style('text-decoration', 'none');
          }
        })
        .on('click', (event, d) => {
          // Update all threshold labels
          chart.selectAll('.threshold-label')
            .attr('fill', threshold => threshold === d ? '#e74c3c' : '#333')
            .style('text-decoration', 'none');
          
          self.selectThreshold(d);
        });
      
      // Draw stage labels (non-interactive for Original Labels)
      chart.selectAll('.stage-label')
        .data(stages.filter(stage => stage === 'Original Labels'))
        .enter()
        .append('text')
        .attr('class', 'stage-label')
        .attr('x', d => xScale(d))
        .attr('y', -10)
        .attr('text-anchor', 'middle')
        .attr('font-weight', 'bold')
        .attr('font-size', '12px')
        .text(d => d);
      
      // Draw clusters as rectangles in each stage
      stages.forEach(stage => {
        const stageX = xScale(stage);
        const nodeWidth = 20;
        
        // Draw only clusters that have data
        Object.entries(stageClusterPositions[stage]).forEach(([cluster, position]) => {
          // Create a safe class name with no spaces or special characters
          const safeStage = stage.replace(/[^a-zA-Z0-9-]/g, '_');
          const safeCluster = cluster.replace(/[^a-zA-Z0-9-]/g, '_');
          const nodeClassName = `node node-${safeStage}-${safeCluster}`;
          
          // Store the original stage and cluster for data use
          const originalData = {
            stage,
            cluster
          };
          
          // Draw rectangle
          const clusterCount = stageData[stage][cluster];
          const isNoisy = clusterCount < this.noisyThreshold;
          
          chart.append('rect')
            .attr('class', nodeClassName)
            .attr('x', stageX - nodeWidth/2)
            .attr('y', position.y)
            .attr('width', nodeWidth)
            .attr('height', position.height)
            .attr('fill', isNoisy ? '#999999' : colorScale(cluster, stage))
            .attr('stroke', 'none')
            .attr('stroke-width', 0)
            .attr('rx', 3)
            .style('cursor', 'pointer')
            .datum(originalData) // Store the original data
            .on('mouseover', (event, d) => {
              // Only handle mouseover if not in active selection mode
              if (!activeSelection.active) {
                // Update info box
                const count = stageData[d.stage][d.cluster];
                const connections = position.connections;
                this.updateInfoBox(d.stage, d.cluster, count, connections);
                
                // Highlight incoming connections
                highlightIncoming(d.stage, d.cluster);
              }
            })
            .on('mouseout', () => {
              // Only handle mouseout if not in active selection mode
              if (!activeSelection.active) {
                // Clear info box
                this.clearInfoBox();
                
                // Reset flows with transition
                chart.selectAll('.flow')
                  .transition()
                  .duration(150)
                  .style('opacity', 0.4)
                  .style('stroke-width', d => lineWidthScale(d.count));
                
                // Reset node highlighting with transition
                chart.selectAll('.node')
                  .transition()
                  .duration(150)
                  .attr('stroke', 'none')
                  .attr('stroke-width', 0);
              }
            })
            .on('click', (event, d) => {
              // If we click on the already selected node, clear selection
              if (activeSelection.active && 
                  activeSelection.stage === d.stage && 
                  activeSelection.cluster === d.cluster) {
                clearActiveSelection();
                return;
              }
              
              // Clear any existing selection
              clearActiveSelection();
              
              // Set new active selection
              activeSelection = {
                stage: d.stage,
                cluster: d.cluster,
                active: true
              };
              
              // Update info box with selected state
              const count = stageData[d.stage][d.cluster];
              const connections = position.connections;
              self.updateInfoBox(d.stage, d.cluster, count, connections, true);
              
              // Highlight with permanent selection
              highlightIncoming(d.stage, d.cluster, true);
              
              // Emit cluster selection event (only for threshold stages, not Original Labels)
              if (d.stage !== 'Original Labels') {
                self.$emit('cluster-selected', d.cluster);
              }
            });
          
          // Add label (only for Original Labels stage)
          if (stage === 'Original Labels') {
            chart.append('text')
              .attr('x', stageX)
              .attr('y', position.y + position.height/2 + 5)
              .attr('text-anchor', 'middle')
              .attr('font-size', '12px')
              .attr('fill', '#fff')
              .attr('pointer-events', 'none') // Make label transparent to mouse events
              .text(cluster);
          }
        });
      });
      
      // Background click to clear selection
      svg.on('click', (event) => {
        // Ignore if the click was on a node or threshold button
        if (event.target.classList.contains('node') || 
            event.target.classList.contains('threshold-button')) {
          return;
        }
        
        // Clear active selection
        if (activeSelection.active) {
          clearActiveSelection();
        }
      });
      
      // Draw flows between stages
      const linkGenerator = d3.linkHorizontal()
        .source(d => {
          const sourceX = xScale(d.sourceStage) + 10;
          const sourcePos = stageClusterPositions[d.sourceStage][d.sourceCluster];
          return [sourceX, sourcePos.y + sourcePos.height/2];
        })
        .target(d => {
          const targetX = xScale(d.targetStage) - 10;
          const targetPos = stageClusterPositions[d.targetStage][d.targetCluster];
          return [targetX, targetPos.y + targetPos.height/2];
        });
      
      chart.selectAll('.flow')
        .data(flows)
        .enter()
        .append('path')
        .attr('d', linkGenerator)
        .attr('fill', 'none')
        .attr('stroke', d => {
          // Check if source cluster is noisy (below threshold)
          const sourceCount = stageData[d.sourceStage] && stageData[d.sourceStage][d.sourceCluster] ? stageData[d.sourceStage][d.sourceCluster] : 0;
          if (sourceCount < this.noisyThreshold) {
            return '#999999'; // Gray for noisy thresholds
          }
          return colorScale(d.sourceCluster, d.sourceStage);
        })
        .attr('stroke-width', d => lineWidthScale(d.count))
        .attr('stroke-opacity', 0.4)
        .each(function(d) {
          // Create safe class names with no spaces
          const safeSourceCluster = d.sourceCluster.replace(/[^a-zA-Z0-9-]/g, '_');
          const safeTargetCluster = d.targetCluster.replace(/[^a-zA-Z0-9-]/g, '_');
          d3.select(this).attr('class', `flow flow-source-${safeSourceCluster} flow-target-${safeTargetCluster}`);
        })
        .on('mouseover', (event, d) => {
          // Only handle if not in active selection mode
          if (!activeSelection.active) {
            // Update info box with flow information
            this.selectedInfo = {
              title: `Flow: ${d.sourceStage} (${d.sourceCluster}) → ${d.targetStage} (${d.targetCluster})`,
              count: d.count,
              incoming: 'N/A',
              outgoing: 'N/A',
              total: d.count
            };
            
            // Highlight this flow with transition
            d3.select(event.target)
              .transition()
              .duration(150)
              .style('opacity', 0.8)
              .style('stroke-width', lineWidthScale(d.count) + 2);
            
            // Highlight connected nodes (using safe class names)
            const safeSourceStage = d.sourceStage.replace(/[^a-zA-Z0-9-]/g, '_');
            const safeSourceCluster = d.sourceCluster.replace(/[^a-zA-Z0-9-]/g, '_');
            const safeTargetStage = d.targetStage.replace(/[^a-zA-Z0-9-]/g, '_');
            const safeTargetCluster = d.targetCluster.replace(/[^a-zA-Z0-9-]/g, '_');
            
            chart.select(`.node-${safeSourceStage}-${safeSourceCluster}`)
              .transition()
              .duration(150)
              .attr('stroke', '#ffcc00')
              .attr('stroke-width', 2);
            
            chart.select(`.node-${safeTargetStage}-${safeTargetCluster}`)
              .transition()
              .duration(150)
              .attr('stroke', '#ffcc00')
              .attr('stroke-width', 2);
          }
        })
        .on('mouseout', () => {
          // Only handle if not in active selection mode
          if (!activeSelection.active) {
            // Clear info box
            this.clearInfoBox();
            
            // Reset this flow with transition
            chart.selectAll('.flow')
              .transition()
              .duration(150)
              .style('opacity', 0.4)
              .style('stroke-width', d => lineWidthScale(d.count));
            
            // Reset node highlighting with transition
            chart.selectAll('.node')
              .transition()
              .duration(150)
              .attr('stroke', 'none')
              .attr('stroke-width', 0);
          }
        });
      
      // Add instructions text
      svg.append('text')
        .attr('x', margin.left)
        .attr('y', height - 10)
        .attr('font-size', '12px')
        .attr('fill', '#666')
        .text('Hover: See details | Click: Select nodes or thresholds | Click background: Deselect');
    }
  }
}
</script>

<style scoped>
.sankey-wrapper {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chart-container {
  width: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background-color: #fafafa;
}

.info-box {
  width: 100%;
  flex-shrink: 0;
  min-height: 70px;
  max-height: 90px;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 8px;
  background-color: #f9f9f9;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  overflow: auto;
}

.info-box h3 {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: #333;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.info-stats {
  display: flex;
  justify-content: space-around;
}

.stat-item {
  text-align: center;
  padding: 0 10px;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
  color: #2c3e50;
}

.stat-label {
  font-size: 12px;
  color: #666;
}

.empty-info {
  color: #999;
  text-align: center;
  font-style: italic;
  padding: 20px;
}

</style>
