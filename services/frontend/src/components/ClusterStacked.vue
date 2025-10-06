<template>
  <div>
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
  name: 'ClusterStacked',
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
    }
  },
  methods: {
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
      
      const { width, height } = this;
      const margin = { top: 80, right: 180, bottom: 80, left: 70 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
      
      // Get stages (keys from data) and sort properly - include Original Labels
      const allStages = Object.keys(this.data);
      if (allStages.length === 0) return;
      
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
      
      // Create color scale
      const colorScale = d3.scaleOrdinal(d3.schemeCategory10)
        .domain(clusters);
      
      // Prepare data for stacking
      const stackData = stages.map(stage => {
        const stageObj = { stage };
        clusters.forEach(cluster => {
          stageObj[cluster] = this.data[stage] ? this.data[stage].filter(c => c === cluster).length : 0;
        });
        return stageObj;
      });
      
      // Create stack generator
      const stack = d3.stack()
        .keys(clusters)
        .order(d3.stackOrderNone)
        .offset(d3.stackOffsetNone);
      
      const stackedData = stack(stackData);
      
      // Create scales with better spacing
      const xScale = d3.scaleBand()
        .domain(stages)
        .range([0, innerWidth])
        .padding(0.15); // Slightly more padding for cleaner look
      
      const yScale = d3.scaleLinear()
        .domain([0, d3.max(stackedData, d => d3.max(d, d1 => d1[1]))])
        .range([innerHeight, 0]);
      
      // Add subtle background grid
      const yTicks = yScale.ticks(5);
      chart.selectAll('.grid-line')
        .data(yTicks)
        .enter()
        .append('line')
        .attr('class', 'grid-line')
        .attr('x1', 0)
        .attr('x2', innerWidth)
        .attr('y1', d => yScale(d))
        .attr('y2', d => yScale(d))
        .attr('stroke', '#f0f0f0')
        .attr('stroke-width', 1)
        .attr('opacity', 0.7);
      
      // Draw interactive threshold labels above bars (discrete style)
      const thresholdStages = stages.filter(stage => stage !== 'Original Labels');
      const self = this; // Store reference to Vue component
      chart.selectAll('.threshold-label')
        .data(thresholdStages)
        .enter()
        .append('text')
        .attr('class', 'threshold-label')
        .attr('x', d => xScale(d) + xScale.bandwidth()/2)
        .attr('y', -20)
        .attr('text-anchor', 'middle')
        .attr('font-weight', 'bold')
        .attr('font-size', '12px')
        .attr('fill', d => self.selectedThreshold === d ? '#e74c3c' : '#333')
        .style('cursor', 'pointer')
        .style('transition', 'all 0.2s ease')
        .text(d => d)
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
        .attr('x', d => xScale(d) + xScale.bandwidth()/2)
        .attr('y', -20)
        .attr('text-anchor', 'middle')
        .attr('font-weight', 'bold')
        .attr('font-size', '12px')
        .text(d => d);
      
      // Draw stacked bars with enhanced styling
      const stacks = chart.selectAll('.stack')
        .data(stackedData)
        .enter()
        .append('g')
        .attr('class', 'stack');
      
      stacks.selectAll('rect')
        .data(d => d)
        .enter()
        .append('rect')
        .attr('x', d => xScale(d.data.stage))
        .attr('y', d => yScale(d[1]))
        .attr('height', d => yScale(d[0]) - yScale(d[1]))
        .attr('width', xScale.bandwidth())
        .attr('fill', function() {
          const parentData = d3.select(this.parentNode).datum();
          return colorScale(parentData.key);
        })
        .attr('stroke', '#fff')
        .attr('stroke-width', 1)
        .attr('rx', 2) // Rounded corners
        .style('cursor', 'pointer')
        .style('transition', 'all 0.2s ease')
        .on('mouseover', (event, d) => {
          const parentData = d3.select(event.target.parentNode).datum();
          const cluster = parentData ? parentData.key : 'Unknown';
          const stage = d.data.stage;
          const count = d[1] - d[0];
          
          // Strong highlight effect similar to sankey
          const currentElement = d3.select(event.target);
          
          // Dim all other segments
          chart.selectAll('rect')
            .filter(function() { return this !== event.target; })
            .transition()
            .duration(150)
            .style('opacity', 0.3);
          
          // Strong highlight for the hovered segment
          currentElement
            .transition()
            .duration(150)
            .attr('stroke', '#ff8800')
            .attr('stroke-width', 3)
            .style('opacity', 1)
            .style('filter', 'brightness(1.15) drop-shadow(0px 2px 4px rgba(0,0,0,0.3))');
          
          self.updateInfoBox(stage, cluster, count, {
            incoming: 0,
            outgoing: 0,
            total: count
          });
        })
        .on('click', (event, d) => {
          const parentData = d3.select(event.target.parentNode).datum();
          const cluster = parentData ? parentData.key : 'Unknown';
          const stage = d.data.stage;
          
          // Emit cluster selection event (only for threshold stages, not Original Labels)
          if (stage !== 'Original Labels') {
            self.$emit('cluster-selected', cluster);
          }
        })
        .on('mouseout', () => {
          // Smooth reset of all bar effects
          chart.selectAll('.stack rect')
            .transition()
            .duration(200)
            .attr('stroke', '#fff')
            .attr('stroke-width', 1)
            .style('opacity', 1)
            .style('filter', 'none');
            
          self.clearInfoBox();
        });
      
      // Add X axis with better styling
      const xAxis = chart.append('g')
        .attr('transform', `translate(0, ${innerHeight})`)
        .call(d3.axisBottom(xScale));
      
      xAxis.selectAll('text')
        .style('text-anchor', 'end')
        .attr('dx', '-.5em')
        .attr('dy', '.15em')
        .attr('transform', 'rotate(-45)')
        .attr('font-size', '11px')
        .attr('fill', '#666')
        .style('max-width', '80px');
      
      xAxis.selectAll('line')
        .attr('stroke', '#ddd');
      
      xAxis.select('.domain')
        .attr('stroke', '#ddd');
      
      // Add Y axis with better styling
      const yAxis = chart.append('g')
        .call(d3.axisLeft(yScale).ticks(5));
      
      yAxis.selectAll('text')
        .attr('font-size', '11px')
        .attr('fill', '#666');
      
      yAxis.selectAll('line')
        .attr('stroke', '#ddd');
      
      yAxis.select('.domain')
        .attr('stroke', '#ddd');
      
      // Add Y axis label with better styling
      chart.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('y', 0 - margin.left + 15)
        .attr('x', 0 - (innerHeight / 2))
        .attr('dy', '1em')
        .style('text-anchor', 'middle')
        .style('font-size', '13px')
        .style('font-weight', '600')
        .style('fill', '#444')
        .text('Data Points');
      
      // Add chart title
      chart.append('text')
        .attr('x', innerWidth / 2)
        .attr('y', -50)
        .attr('text-anchor', 'middle')
        .style('font-size', '14px')
        .style('font-weight', '600')
        .style('fill', '#333')
        .text('Cluster Distribution Across Stages');
      
      // Add improved legend positioned outside the chart area
      const legendWidth = 150;
      const legend = svg.append('g') // Append to svg instead of chart to position outside
        .attr('class', 'legend')
        .attr('transform', `translate(${margin.left + innerWidth + 20}, ${margin.top + 20})`);
      
      // Legend background
      legend.append('rect')
        .attr('x', -10)
        .attr('y', -10)
        .attr('width', legendWidth)
        .attr('height', Math.min(clusters.length, 10) * 22 + 15) // Limit height
        .attr('fill', 'rgba(255, 255, 255, 0.95)')
        .attr('stroke', '#ddd')
        .attr('stroke-width', 1)
        .attr('rx', 4);
      
      const legendItems = legend.selectAll('.legend-item')
        .data(clusters.slice(0, 10)) // Limit to first 10 clusters to avoid overflow
        .enter()
        .append('g')
        .attr('class', 'legend-item')
        .attr('transform', (d, i) => `translate(0, ${i * 22})`);
      
      legendItems.append('rect')
        .attr('width', 12)
        .attr('height', 12)
        .attr('fill', d => colorScale(d))
        .attr('stroke', '#fff')
        .attr('stroke-width', 1)
        .attr('rx', 2);
      
      legendItems.append('text')
        .attr('x', 18)
        .attr('y', 9)
        .attr('font-size', '11px')
        .attr('fill', '#555')
        .text(d => d.length > 8 ? d.substring(0, 8) + '...' : d);
      
      // Add instructions text
      svg.append('text')
        .attr('x', margin.left)
        .attr('y', height - 10)
        .attr('font-size', '12px')
        .attr('fill', '#666')
        .text('Hover over bars to see details | Click threshold labels to select');
    }
  }
}
</script>

<style scoped>

.chart-container {
  width: 100%;
  min-height: 500px;
  margin-bottom: 20px;
}

.info-box {
  width: 100%;
  min-height: 80px;
  border: 1px solid #ddd;
  border-radius: 5px;
  padding: 10px;
  background-color: #f9f9f9;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.info-box h3 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 16px;
  color: #333;
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
