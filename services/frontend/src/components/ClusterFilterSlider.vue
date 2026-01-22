<!-- ClusterFilterSlider.vue -->
<template>
    <div class="cluster-filter">
      <h3>Filter Clusters by Size</h3>
      <div class="slider-container">
        <input 
          type="range" 
          class="size-slider" 
          min="0" 
          :max="maxClusterSize" 
          v-model.number="minClusterSize"
          @input="updateFilteredData" 
        />
        <div class="slider-value">{{ minClusterSize }} items</div>
      </div>
      <div class="filter-info">
        <p>Only showing clusters with {{ minClusterSize }} or more items</p>
        <div class="stats">
          <div class="stat-item">
            <span class="stat-label">Original data points:</span>
            <span class="stat-value">{{ totalOriginalItems }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Filtered data points:</span>
            <span class="stat-value">{{ totalFilteredItems }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Removed:</span>
            <span class="stat-value">{{ totalOriginalItems - totalFilteredItems }}</span>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script>
  export default {
    name: 'ClusterFilterSlider',
    props: {
      clusterData: {
        type: Object,
        required: true
      }
    },
    data() {
      return {
        minClusterSize: 0,
        maxClusterSize: 1,
        filteredData: {},
        totalOriginalItems: 0,
        totalFilteredItems: 0
      };
    },
    watch: {
      clusterData: {
        immediate: true,
        handler() {
          this.calculateMaxClusterSize();
          this.updateFilteredData();
        }
      }
    },
    methods: {
      calculateMaxClusterSize() {
        let max = 1;
        
        if (Object.keys(this.clusterData).length === 0) {
          return;
        }
        
        // For each stage, find the maximum count for any cluster
        Object.entries(this.clusterData).forEach(([, clusterIds]) => {
          const counts = this.getCounts(clusterIds);
          const stageMax = Math.max(...Object.values(counts));
          if (stageMax > max) {
            max = stageMax;
          }
        });
        
        this.maxClusterSize = max;
        // Reset the min cluster size if needed
        if (this.minClusterSize > this.maxClusterSize) {
          this.minClusterSize = 0;
        }
      },
      
      // Helper to count occurrences of each element
      getCounts(array) {
        const counts = {};
        array.forEach(item => {
          counts[item] = (counts[item] || 0) + 1;
        });
        return counts;
      },
      
      updateFilteredData() {
        if (Object.keys(this.clusterData).length === 0) {
          this.filteredData = {};
          this.totalOriginalItems = 0;
          this.totalFilteredItems = 0;
          return;
        }
        
        // 1. For each stage, identify small clusters (counts < threshold)
        const smallClusters = new Map();
        
        Object.entries(this.clusterData).forEach(([stageName, clusterIds]) => {
          const counts = this.getCounts(clusterIds);
          
          // For each unique cluster ID, check if it's below the threshold
          Object.entries(counts).forEach(([clusterId, count]) => {
            if (count < this.minClusterSize) {
              if (!smallClusters.has(stageName)) {
                smallClusters.set(stageName, new Set());
              }
              smallClusters.get(stageName).add(clusterId);
            }
          });
        });
        
        // 2. Find all indexes to remove from each stage
        const indexesToRemove = new Set();
        
        Object.entries(this.clusterData).forEach(([stageName, clusterIds]) => {
          if (smallClusters.has(stageName)) {
            const smallClusterIds = smallClusters.get(stageName);
            
            clusterIds.forEach((id, index) => {
              if (smallClusterIds.has(id)) {
                indexesToRemove.add(index);
              }
            });
          }
        });
        
        // 3. Create filtered data by removing identified indexes from all stages
        const filtered = {};
        
        // Count the original items from the first stage (all stages should have same length)
        if (Object.keys(this.clusterData).length > 0) {
          const firstStageName = Object.keys(this.clusterData)[0];
          this.totalOriginalItems = this.clusterData[firstStageName].length;
        } else {
          this.totalOriginalItems = 0;
        }
        
        // Remove the indexes from all stages
        Object.entries(this.clusterData).forEach(([stageName, clusterIds]) => {
          filtered[stageName] = clusterIds.filter((_, index) => !indexesToRemove.has(index));
        });
        
        this.filteredData = filtered;
        
        // Count filtered items (should be the same for all stages)
        if (Object.keys(filtered).length > 0) {
          const firstStageName = Object.keys(filtered)[0];
          this.totalFilteredItems = filtered[firstStageName].length;
        } else {
          this.totalFilteredItems = 0;
        }
        
        // Emit the filtered data to the parent component
        this.$emit('update:filtered-data', filtered);
      }
    }
  }
  </script>
  
  <style scoped>
  .cluster-filter {
    background-color: #f8f9fa;
    padding: 8px;
    border: 1px solid #e0e0e0;
  }
  
  .cluster-filter h3 {
    margin: 0 0 6px 0;
    font-size: 13px;
    color: #333;
    font-weight: 600;
    letter-spacing: 0.3px;
  }
  
  .slider-container {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }
  
  .size-slider {
    flex: 1;
    min-width: 0;
    height: 6px;
    background: linear-gradient(to right, #e1e1e1, #4caf50);
    border-radius: 3px;
    -webkit-appearance: none;
    appearance: none;
    outline: none;
  }
  
  .size-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #4caf50;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    transition: all 0.15s ease;
  }
  
  .size-slider::-webkit-slider-thumb:hover {
    background: #3d8b40;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
    transform: scale(1.1);
  }
  
  .size-slider::-moz-range-thumb {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #4caf50;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    transition: all 0.15s ease;
    border: none;
  }
  
  .size-slider::-moz-range-thumb:hover {
    background: #3d8b40;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
    transform: scale(1.1);
  }
  
  .slider-value {
    min-width: 70px;
    text-align: right;
    font-weight: 600;
    font-size: 13px;
    color: #4caf50;
    white-space: nowrap;
    flex-shrink: 0;
  }
  
.filter-info {
  font-size: 11px;
  color: #666;
  line-height: 1.5;
}

.filter-info p {
  margin: 0 0 8px 0;
  font-weight: 500;
}
  
  .stats {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
  
  .stat-item {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
  }
  
  .stat-label {
    color: #777;
    font-weight: 500;
  }
  
  .stat-value {
    font-weight: 700;
    color: #2c3e50;
  }
  
  </style>