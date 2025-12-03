<template>
  <div class="cluster-selector">
    <h3>Select Death Threshold:</h3>
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script>
import { ref, onMounted, watch, defineComponent } from 'vue'
import * as d3 from 'd3'

export default defineComponent({
  name: 'ClusterSelectorSlider',
  props: {
    deathData: {
      type: Object,
      required: true
    },
    availableStages: {
      type: Array,
      default: () => []
    },
    noisyThreshold: {
      type: Number,
      default: 5
    }
  },
  emits: ['update:selected-clusters', 'update:selected-stages'],
  setup(props, { emit }) {
    const chartContainer = ref(null)
    const selectedStages = ref([])

    const createChart = () => {
      // Clear previous chart
      d3.select(chartContainer.value).selectAll("*").remove()

      // Validate data
      if (!props.deathData || Object.keys(props.deathData).length === 0) {
        console.warn('No death data provided')
        return
      }

      // Extract all unique subkeys across all ticks
      const allSubkeys = new Set()
      Object.values(props.deathData).forEach(tickData => {
        Object.keys(tickData).forEach(subkey => allSubkeys.add(subkey))
      })

      // Chart dimensions - responsive to container
      const legendWidth = 100
      const margin = { top: 20, right: 50, bottom: 40, left: 50 }
      const width = chartContainer.value.clientWidth || 800
      const height = chartContainer.value.clientHeight || 200
      const innerWidth = width - margin.left - margin.right - legendWidth 
      const innerHeight = height - margin.top - margin.bottom

      // Create SVG
      const svg = d3.select(chartContainer.value)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`)

      // Prepare data for stacking
      const keys = Array.from(allSubkeys)
      
      // Get original labels from the "Original Labels" stage
      // The deathData structure is { stageName: { clusterLabel: count, ... }, ... }
      const originalLabelsData = props.deathData['Original Labels']
      
      const originalLabels = originalLabelsData ? Object.keys(originalLabelsData).sort((a, b) => {
        const numA = parseFloat(a);
        const numB = parseFloat(b);
        if (!isNaN(numA) && !isNaN(numB)) {
          return numA - numB;
        }
        return a.localeCompare(b);
      }) : keys
      
      const stackedData = Object.entries(props.deathData).map(([tick, tickData]) => {
        const entry = { tick: Number(tick) }
        keys.forEach(key => {
          entry[key] = tickData[key] || 0
        })
        return entry
      }).sort((a, b) => a.tick - b.tick)

      // Remove Original Labels (tick 0) and keep natural order for threshold visualization
      // Lower thresholds (more clusters) on left, higher thresholds (fewer clusters) on right
      const reorderedData = stackedData
        .filter(d => d.tick !== 0)  // Remove Original Labels
        // Keep natural order - no reverse needed

      // Assign new tick values for x-axis placement
      reorderedData.forEach((d, i) => {
        d.displayTick = i  // New property for x-axis positioning
      })

      const stack = d3.stack().keys(keys)
      const series = stack(reorderedData)

      // Scales
      const x = d3.scaleLinear()
        .domain([0, reorderedData.length - 1])
        .range([0, innerWidth])

      const y = d3.scaleLinear()
        .domain([0, d3.max(series, d => d3.max(d, d1 => d1[1]))])
        .range([innerHeight, 0])

      // Color scale
      const color = d3.scaleOrdinal(d3.schemeCategory10)

      // Area generator
      const area = d3.area()
        // .x((d, i) => x(d.data.displayTick)) 
        .x((d, i) => x(i))
        .y0(d => y(d[0]))
        .y1(d => y(d[1]))

      // Render stacked areas
      svg.selectAll('path')
        .data(series)
        .enter()
        .append('path')
        .attr('d', area)
        .attr('fill', seriesData => {
          // Check if cluster count is below noisy threshold at any point
          // seriesData is the series array for this cluster, each element has data[seriesData.key] as the count
          const clusterKey = seriesData.key;
          const maxCount = d3.max(seriesData, point => point.data[clusterKey] || 0);
          if (maxCount < props.noisyThreshold) {
            return '#999999'; // Gray for noisy thresholds
          }
          return color(clusterKey);
        })
        .attr('opacity', 0.7)
        .attr('stroke', seriesData => {
          // Check if cluster count is below noisy threshold at any point
          const clusterKey = seriesData.key;
          const maxCount = d3.max(seriesData, point => point.data[clusterKey] || 0);
          if (maxCount < props.noisyThreshold) {
            return '#999999'; // Gray for noisy thresholds
          }
          return color(clusterKey);
        })
        .attr('stroke-width', 0.5)


      // X Axis
      svg.append('g')
        .attr('transform', `translate(0,${innerHeight})`)
        // .call(d3.axisBottom(x).ticks(Math.min(5, reorderedData.length))
        .call(d3.axisBottom(x).ticks(Math.min(5, Object.keys(reorderedData).length))
              .tickFormat(i => {
                // Find the original tick value and format to 3 decimals
                if (i >= 0 && i < reorderedData.length) {
                  const tick = reorderedData[i].tick;
                  const num = parseFloat(tick);
                  return isNaN(num) || tick === 'Original Labels' ? tick : num.toFixed(3);
                }
                return i;
              }))
        .append('text')
        .attr('x', innerWidth / 2)
        .attr('y', 40)
        .attr('fill', '#000')
        .attr('font-weight', 'bold')
        .text('Deaths')


      // Y Axis
      svg.append('g')
        .call(d3.axisLeft(y))
        .append('text')
        .attr('transform', 'rotate(-90)')
        .attr('y', -40)
        .attr('x', -innerHeight / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', '#000')
        .attr('font-weight', 'bold')
        .text('Cluster Count')

      // Brush
      const brush = d3.brushX()
        .extent([[0, 0], [innerWidth, innerHeight]])
        .on("end", brushed)

      svg.append("g")
        .attr("class", "brush")
        .call(brush)

      // Brush event handler 
      function brushed(event) {
        if (!event.selection) {
          // No selection, emit all stages
          selectedStages.value = [...props.availableStages]
          emit('update:selected-stages', selectedStages.value)
          return
        }

        const [brushStart, brushEnd] = event.selection
        
        // Convert brush positions to indices
        const startIndex = Math.floor(x.invert(brushStart))
        const endIndex = Math.ceil(x.invert(brushEnd))
        
        // Map brush indices directly to the reorderedData stages
        // reorderedData contains the exact stages shown in the brush, in the correct order
        const selectedReorderedData = reorderedData.filter((_, index) => index >= startIndex && index <= endIndex);
        
        // Convert ticks back to stage names using a simpler approach
        const brushedStages = selectedReorderedData.map(d => {
          const tickValue = d.tick;
          // Find the stage name that has this tick value in the formatted data
          // Since availableStages are formatted (e.g., "3.088"), we need to match properly
          return props.availableStages.find(stage => {
            if (stage === 'Original Labels') return false;
            // Try to match the formatted stage name with the tick
            return Math.abs(parseFloat(stage) - tickValue) < 0.001; // Small tolerance for floating point
          });
        }).filter(Boolean);
        
        // Always include Original Labels first, then add brushed stages
        const originalLabelsStage = props.availableStages[0]
        selectedStages.value = originalLabelsStage 
          ? [originalLabelsStage, ...brushedStages] 
          : [...brushedStages]
        
        // Emit selected stages
        emit('update:selected-stages', selectedStages.value)
        
        // Filter data based on brush selection
        const filteredData = {}
        
        // Add Original Labels data first (always included)
        if (originalLabelsStage && props.deathData[0]) {
          filteredData[originalLabelsStage] = props.deathData[0]
        }
        
        // Then add the brushed threshold stages
        brushedStages.forEach((stage) => {
          // Find the original index of this stage in availableStages
          const index = props.availableStages.indexOf(stage)
          if (index !== -1 && props.deathData[index]) {
            filteredData[stage] = props.deathData[index]
          }
        })
        
        // Emit filtered data for clusters
        emit('update:selected-clusters', filteredData)
      }


      // Legend - only show original labels
      const legend = svg.append('g')
        .attr('class', 'legend')
        // .attr('transform', `translate(${margin.left + innerWidth + legendMargin}, ${margin.top})`)
        .attr('transform', `translate(${margin.left + innerWidth}, ${margin.top})`)


      // Legend background
      legend.append('rect')
        .attr('x', -10)
        .attr('y', -10)
        .attr('width', legendWidth)
        .attr('height', originalLabels.length * 20 + 15)
        .attr('fill', 'rgba(255, 255, 255, 0.95)')
        .attr('stroke', '#ddd')
        .attr('stroke-width', 1)
        .attr('rx', 4)

        
        // Legend color squares - only original labels
        // Note: Legend colors don't reflect noisy threshold since they show original labels
        legend.selectAll('rect.legend-color')
          .data(originalLabels)
          .enter()
          .append('rect')
          .attr('class', 'legend-color')
          .attr('x', 0)
          .attr('y', (d, i) => i * 20)
          .attr('width', 12)
          .attr('height', 12)
          .attr('fill', d => color(d))

        // Legend text - only original labels
        legend.selectAll('text')
          .data(originalLabels)
          .enter()
          .append('text')
          .attr('x', 18)
          .attr('y', (d, i) => i * 20 + 9)
          .attr('font-size', '11px')
          .attr('fill', '#555')
          .text(d => d)
      }

    // Initialize
    onMounted(() => {
      if (props.availableStages.length > 0) {
        selectedStages.value = [...props.availableStages]
      }
      createChart()
    })
    
    // Watch for data changes
    watch(() => props.deathData, createChart, { deep: true })
    watch(() => props.availableStages, (newStages) => {
      if (newStages.length > 0) {
        selectedStages.value = [...newStages]
      }
    })
    watch(() => props.noisyThreshold, createChart)

    return { chartContainer }
  }
})
</script>

<style scoped>
.cluster-selector {
  background-color: #f8f9fa;
  padding: 8px;
  border: 1px solid #e0e0e0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.cluster-selector h3 {
  margin: 0 0 6px 0;
  font-size: 13px;
  color: #333;
  font-weight: 600;
  flex-shrink: 0;
  letter-spacing: 0.3px;
}

.chart-container {
  width: 100%;
  flex: 1;
  background-color: white;
  border: 1px solid #d0d0d0;
  overflow: hidden;
  min-height: 0;
}

.brush .selection {
  fill: #69b3a2;
  fill-opacity: 0.3;
  stroke: #69b3a2;
  stroke-width: 1;
}

.brush .handle {
  fill: #2c3e50;
}

.brush .overlay {
  cursor: crosshair;
}

svg {
  max-width: 100%;
  height: auto;
}
</style>