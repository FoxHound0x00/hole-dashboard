<template>
  <div class="app">
    <!-- Compact Header -->
    <div class="header">
      <h1>Cluster Flow Visualization</h1>
      <div class="dropdown-container">
        <div class="dropdown-item" v-for="(options, title) in dropdownOptions" :key="title">
          <label>{{ title }}</label>
          <select v-model="selectedOptions[title]" @change="updateClusterData">
            <option v-for="option in options" :key="option" :value="option">{{ option }}</option>
          </select>
        </div>
      </div>
    </div>
    
    <!-- Left Sidebar: Selectors and Filters -->
    <div class="sidebar">
      <ClusterSelectorSlider 
        :deathData="deathData"
        :availableStages="availableStages"
        :noisyThreshold="noisyThreshold"
        @update:selected-stages="updateSelectedStages"
        @update:selected-clusters="updateSelectedClusters"
      />
      
      <ClusterFilterSlider 
        :cluster-data="filteredClusterData" 
        @update:filtered-data="updateClusterSizeFiltered"
      />
      
      <!-- Noisy Threshold Control -->
      <div class="noisy-threshold-control">
        <h3>Noisy Threshold:</h3>
        <div class="threshold-input-container">
          <input 
            type="number" 
            v-model.number="noisyThreshold"
            min="1"
            max="50"
            class="threshold-input"
          />
          <span class="threshold-label">datapoints</span>
        </div>
        <p class="threshold-help">Clusters with fewer than {{ noisyThreshold }} datapoints will appear gray</p>
      </div>
    </div>
    
    <!-- Top Right: Main Visualization (Sankey/Stacked) -->
    <div class="main-viz">
      <div class="chart-header">
        <h3>Flow Visualization</h3>
        <button 
          @click="toggleChartType" 
          class="chart-toggle-btn"
          :class="{ 'active': chartType === 'stacked' }"
        >
          {{ chartType === 'sankey' ? 'Stacked Bars' : 'Sankey' }}
        </button>
      </div>
      
      <ClusterSankey 
        v-if="chartType === 'sankey'"
        :data="sizeFilteredClusterData" 
        :noisyThreshold="noisyThreshold"
        @threshold-selected="handleThresholdSelection"
        @cluster-selected="handleClusterSelection"
      />
      
      <ClusterStacked 
        v-if="chartType === 'stacked'"
        :data="sizeFilteredClusterData" 
        :noisyThreshold="noisyThreshold"
        @threshold-selected="handleThresholdSelection"
        @cluster-selected="handleClusterSelection"
      />
    </div>

    <!-- Bottom Left: Blob Visualization -->
    <div class="blob-viz">
      <ClusterBlob 
        v-if="visualizationMethod !== 'fd'"
        :data="sizeFilteredClusterData" 
        :selected-threshold="selectedThreshold"
        :selected-cluster="selectedCluster"
        :outliers="[]"
        @blob-selected="handleBlobSelection"
        @point-selected="handlePointSelection"
        @visualization-method-selected="handleVisualizationMethodSelected"
      />
      <ForceDirectedGraph 
        v-if="visualizationMethod === 'fd'"
        :data="sizeFilteredClusterData"
        @visualization-method-selected="handleVisualizationMethodSelected"
      />
    </div>

    <!-- Bottom Right: Heatmap -->
    <div class="heatmap-viz">
      <HeatmapDendrogram 
        v-if="selectedOptions['Distance Metric']"
        :metric="selectedOptions['Distance Metric']"
        :cluster-data="rawClusterData"
        :selected-threshold="selectedThreshold"
      />
    </div>
  </div>
</template>

<script>
import ClusterSankey from './components/ClusterSankey.vue';
import ClusterStacked from './components/ClusterStacked.vue';
import ClusterFilterSlider from './components/ClusterFilterSlider.vue';
import ClusterSelectorSlider from './components/ClusterSelectorSlider.vue';
import ClusterBlob from './components/ClusterBlob.vue';
import ForceDirectedGraph from './components/ForceDirectedGraph.vue';
import HeatmapDendrogram from './components/HeatmapDendrogram.vue';
import axios from 'axios';
import * as d3 from 'd3';

export default {
  name: 'App',
  components: {
    ClusterSankey,
    ClusterStacked,
    ClusterFilterSlider,
    ClusterSelectorSlider,
    ClusterBlob,
    ForceDirectedGraph,
    HeatmapDendrogram
  },
  data() {
    return {
      dropdownOptions: {},
      selectedOptions: {},
      rawClusterData: {},
      formattedClusterData: {},
      filteredClusterData: {},
      sizeFilteredClusterData: {},
      availableStages: [],
      deathData: {},
      selectedStages: [],
      brushChart: null,
      chartType: 'sankey',
      selectedThreshold: null,
      selectedCluster: null,
      noisyThreshold: 5,
      visualizationMethod: 'pca'
    };
  },
  created() {
    this.fetchConfig();
  },
  mounted() {
    // Initialize brush container after DOM is ready
    this.$nextTick(() => {
      this.initializeBrushChart();
    });
  },
  methods: {
    async fetchConfig() {
      try {
        const response = await axios.get('http://127.0.0.1:5000/config');
        this.dropdownOptions = response.data;
        
        // Initialize selected options
        this.selectedOptions = {};
        for (const [key, values] of Object.entries(this.dropdownOptions)) {
          if (values.length > 0) {
            this.selectedOptions[key] = values[0];
          }
        }
        
        this.updateClusterData();
      } catch (error) {
        console.error('Error fetching configuration:', error);
      }
    },
    async updateClusterData() {
      if (!this.selectedOptions['Distance Metric']) return;
      
      try {
        // Get data for the selected distance metric
        const response = await axios.get(`http://127.0.0.1:5000/data/${this.selectedOptions['Distance Metric']}`);
        
        // Store the raw data
        this.rawClusterData = response.data;
        
        // Format the data
        this.formatClusterData();
        
        // Update available stages
        this.availableStages = Object.keys(this.formattedClusterData);
        const deaths_ = await axios.get(`http://127.0.0.1:5000/cluster_data/${this.selectedOptions['Distance Metric']}`);
        this.deathData = deaths_.data;

        // Initially select all stages
        this.selectedStages = [...this.availableStages];
        
        // Update filtered data
        this.updateFilteredData();
        
        // Update brush chart with new data
        this.updateBrushChart();
      } catch (error) {
        console.error('Error fetching cluster data:', error);
      }
    },
    formatClusterData() {
      const formattedData = {};
      
      // Process each stage (key) in the raw data
      Object.entries(this.rawClusterData).forEach(([stage, clusterIds]) => {
        // Format stage name if it's a number (but not "Original Labels")
        let formattedStage = stage;
        if (stage !== "Original Labels" && !isNaN(parseFloat(stage))) {
          formattedStage = parseFloat(stage).toFixed(3);
        }
        
        // Simply convert numbers to strings
        formattedData[formattedStage] = clusterIds.map(id => String(id));
      });
      
      this.formattedClusterData = formattedData;
    },
    updateSelectedStages(stages) {
    this.selectedStages = stages;
    this.updateFilteredData();
  },
    updateFilteredData() {
      // Filter data to only include selected stages
      const filteredData = {};
      this.selectedStages.forEach(stage => {
        if (this.formattedClusterData[stage]) {
          filteredData[stage] = this.formattedClusterData[stage];
        }
      });
      
      this.filteredClusterData = filteredData;
      
      // Initialize the size-filtered data with the stage-filtered data
      this.sizeFilteredClusterData = { ...filteredData };
    },
    // Method to update selected clusters from ClusterSelectorSlider
    updateSelectedClusters(selectedClusters) {
      console.log("Selected clusters updated:", selectedClusters);
      // Implement handling of selected clusters if needed
    },
    // Method to update data after filtering by cluster size
    updateClusterSizeFiltered(filteredData) {
      this.sizeFilteredClusterData = filteredData;
    },
    // Handle threshold selection from chart components
    handleThresholdSelection(threshold) {
      this.selectedThreshold = threshold;
      console.log('Selected threshold:', threshold);
      // You can add additional logic here to handle threshold selection
    },
    // Handle cluster selection from chart components
    handleClusterSelection(cluster) {
      this.selectedCluster = cluster;
      console.log('Selected cluster:', cluster);
      // You can add additional logic here to handle cluster selection
    },
    // Toggle between chart types
    toggleChartType() {
      this.chartType = this.chartType === 'sankey' ? 'stacked' : 'sankey';
    },
    // Handle blob selection from ClusterBlob component
    handleBlobSelection(blob) {
      console.log('Selected blob:', blob);
      // You can add additional logic here to handle blob selection
    },
    // Handle point selection from ClusterBlob component
    handlePointSelection(point) {
      console.log('Selected point:', point);
      // You can add additional logic here to handle point selection
    },
    // Handle visualization method selection from ClusterBlob component
    handleVisualizationMethodSelected(method) {
      this.visualizationMethod = method;
      console.log('Selected visualization method:', method);
    },
    // Initialize the brush chart
    initializeBrushChart() {
      // Make sure the container exists
      if (!this.$refs.brushContainer) return;
      
      // Create the basic structure for the brush chart
      this.brushChart = {};
      this.updateBrushChart();
    },
    // Update the brush chart with current available stages
    updateBrushChart() {
      if (!this.$refs.brushContainer || this.availableStages.length === 0) return;
      
      // Clear previous chart
      d3.select(this.$refs.brushContainer).selectAll("*").remove();
      
      // Chart dimensions
      const margin = { top: 20, right: 30, bottom: 50, left: 50 };
      const width = this.$refs.brushContainer.clientWidth || 800;
      const height = 150;
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
      
      // Create SVG
      const svg = d3.select(this.$refs.brushContainer)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);
      
      // Prepare data
      const data = this.availableStages.map((stage, index) => ({
        stage, 
        index
      }));
      
      // Scales
      const x = d3.scaleLinear()
        .domain([0, this.availableStages.length - 1])
        .range([0, innerWidth]);
        // .range([innerWidth, 0]);

      
      // Create bars for each stage
      svg.selectAll('.stage-bar')
        .data(data)
        .enter()
        .append('rect')
        .attr('class', 'stage-bar')
        .attr('x', d => x(d.index))
        .attr('y', 0)
        .attr('width', innerWidth / this.availableStages.length)
        .attr('height', innerHeight)
        .attr('fill', '#69b3a2')
        .attr('opacity', 0.7);
      
      // X Axis - show indices
      svg.append('g')
        .attr('transform', `translate(0,${innerHeight})`)
        .call(d3.axisBottom(x).ticks(Math.min(20, this.availableStages.length))
              .tickFormat(i => Math.floor(i)));
      
      // Brush
      const brush = d3.brushX()
        .extent([[0, 0], [innerWidth, innerHeight]])
        .on("end", brushed);
      
      svg.append("g")
        .attr("class", "brush")
        .call(brush);
      
      // Brush callback
      const self = this;
      // function brushed(event) {
      //   if (!event.selection) {
      //     // No selection, use all stages
      //     self.selectedStages = [...self.availableStages];
      //     self.updateFilteredData();
      //     return;
      //   }
        
      //   const [brushStart, brushEnd] = event.selection;
        
      //   // Convert brush positions to indices
      //   const startIndex = Math.floor(x.invert(brushStart));
      //   const endIndex = Math.ceil(x.invert(brushEnd));
        
      //   // Get stages in the selected range
      //   self.selectedStages = self.availableStages.filter((_, index) => 
      //     index >= startIndex && index <= endIndex
      //   );
        
      //   // Update data with selected stages
      //   self.updateFilteredData();
      // }
      function brushed(event) {
        if (!event.selection) {
          // No selection, use all stages
          self.selectedStages = [...self.availableStages];
          self.updateFilteredData();
          return;
        }
        
        const [brushStart, brushEnd] = event.selection;
        
        // Convert brush positions to indices
        const startIndex = Math.floor(x.invert(brushStart));
        const endIndex = Math.ceil(x.invert(brushEnd));
        
        // Get stages in the selected range (in reverse order)
        const brushedStages = self.availableStages
          .filter((_, index) => index >= startIndex && index <= endIndex)
          .reverse();
        
        // Always include the 0th index and attach reversed brushed stages
        const zeroStage = self.availableStages[0];
        self.selectedStages = zeroStage 
          ? [zeroStage, ...brushedStages.filter(stage => stage !== zeroStage)] 
          : [...brushedStages];
        
        // Update data with selected stages
        self.updateFilteredData();
      }
    }
  }
}
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.app {
  font-family: Arial, sans-serif;
  height: 100vh;
  width: 100vw;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto minmax(0, 1fr) minmax(0, 1fr);
  grid-template-areas:
    "header header"
    "sidebar main-viz"
    "blob-viz heatmap-viz";
  gap: 8px;
  padding: 8px;
  overflow: hidden;
  background-color: #f5f5f5;
}

/* Header Area */
.header {
  grid-area: header;
  background: white;
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  gap: 15px;
  min-height: 0;
}

.header h1 {
  font-size: 18px;
  color: #2c3e50;
  margin: 0;
  white-space: nowrap;
  line-height: 1;
}

.dropdown-container {
  display: flex;
  align-items: center;
  gap: 15px;
  flex: 1;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dropdown-item label {
  font-weight: 600;
  color: #2c3e50;
  font-size: 13px;
  white-space: nowrap;
}

.dropdown-item select {
  padding: 6px 10px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 13px;
  background-color: white;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23555' d='M6 8.825L1.175 4 2.05 3.125 6 7.075 9.95 3.125 10.825 4z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  padding-right: 30px;
}

.dropdown-item select:hover {
  border-color: #3498db;
}

.dropdown-item select:focus {
  outline: none;
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

/* Sidebar (Selectors and Filters) */
.sidebar {
  grid-area: sidebar;
  display: grid;
  grid-template-rows: 2fr 1fr auto;
  gap: 8px;
  overflow: hidden;
  min-height: 0;
}

.noisy-threshold-control {
  background-color: #f8f9fa;
  padding: 8px;
  border: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.noisy-threshold-control h3 {
  margin: 0 0 6px 0;
  font-size: 13px;
  color: #333;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.threshold-input-container {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.threshold-input {
  width: 60px;
  padding: 4px 8px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 13px;
  text-align: center;
}

.threshold-input:focus {
  outline: none;
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.threshold-label {
  font-size: 12px;
  color: #666;
}

.threshold-help {
  margin: 0;
  font-size: 11px;
  color: #666;
  font-style: italic;
}

/* Main Visualization Area */
.main-viz {
  grid-area: main-viz;
  background: white;
  border: 1px solid #e0e0e0;
  padding: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  flex-shrink: 0;
}

.chart-header h3 {
  margin: 0;
  color: #2c3e50;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.chart-toggle-btn {
  background-color: #3498db;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.chart-toggle-btn:hover {
  background-color: #2980b9;
}

.chart-toggle-btn.active {
  background-color: #e74c3c;
}

.chart-toggle-btn.active:hover {
  background-color: #c0392b;
}

/* Blob Visualization */
.blob-viz {
  grid-area: blob-viz;
  background: white;
  border: 1px solid #e0e0e0;
  padding: 10px;
  overflow: hidden;
  min-height: 0;
}

/* Heatmap Visualization */
.heatmap-viz {
  grid-area: heatmap-viz;
  background: white;
  border: 1px solid #e0e0e0;
  padding: 10px;
  overflow: hidden;
  min-height: 0;
}

/* Ensure components fill their containers */
.sidebar > * {
  min-height: 0;
  overflow: hidden;
}

.main-viz > *:not(.chart-header) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.blob-viz > *,
.heatmap-viz > * {
  height: 100%;
  width: 100%;
}
</style>