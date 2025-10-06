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

      // Chart dimensions
      const legendWidth = 100
      // const legendMargin = 20
      const margin = { top: 20, right: 50, bottom: 50, left: 50 }
      const width = chartContainer.value.clientWidth || 800
      const height = 300
      // const innerWidth = width - margin.left - margin.right - legendWidth - legendMargin
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
        .attr('fill', d => color(d.key))
        .attr('opacity', 0.7)
        .attr('stroke', '#fff')
        .attr('stroke-width', 1)


      // X Axis
      svg.append('g')
        .attr('transform', `translate(0,${innerHeight})`)
        // .call(d3.axisBottom(x).ticks(Math.min(5, reorderedData.length))
        .call(d3.axisBottom(x).ticks(Math.min(5, Object.keys(reorderedData).length))
              .tickFormat(i => {
                // Find the original tick value
                if (i >= 0 && i < reorderedData.length) {
                  return reorderedData[i].tick;
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


      // Legend
      const legend = svg.append('g')
        .attr('class', 'legend')
        // .attr('transform', `translate(${margin.left + innerWidth + legendMargin}, ${margin.top})`)
        .attr('transform', `translate(${margin.left + innerWidth}, ${margin.top})`)


      // Legend background
      legend.append('rect')
        .attr('x', -10)
        .attr('y', -10)
        .attr('width', legendWidth)
        .attr('height', keys.length * 20 + 15)
        .attr('fill', 'rgba(255, 255, 255, 0.95)')
        .attr('stroke', '#ddd')
        .attr('stroke-width', 1)
        .attr('rx', 4)

        
        // Legend color squares
        legend.selectAll('rect.legend-color')
          .data(keys)
          .enter()
          .append('rect')
          .attr('class', 'legend-color')
          .attr('x', 0)
          .attr('y', (d, i) => i * 20)
          .attr('width', 12)
          .attr('height', 12)
          .attr('fill', d => color(d))

        // Legend text
        legend.selectAll('text')
          .data(keys)
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

    return { chartContainer }
  }
})
</script>

<style scoped>
.cluster-selector {
  margin-bottom: 30px;
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.cluster-selector h3 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 16px;
  color: #2c3e50;
  font-weight: 600;
}

.chart-container {
  width: 100%;
  height: 300px;
  background-color: white;
  border-radius: 4px;
  overflow: hidden;
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