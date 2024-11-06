<template>
  <div 
    v-if="well" 
    class="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg p-4 w-[500px] z-10"
  >
    <div class="flex flex-col gap-4">
      <!-- Well Info -->
      <div class="border-b pb-3">
        <h3 class="text-lg font-semibold text-gray-800 mb-2">{{ well.properties.well_name }}</h3>
        <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-gray-600">
          <p><span class="font-medium">API:</span> {{ well.properties.api_14 }}</p>
          <p><span class="font-medium">Operator:</span> {{ well.properties.env_operator }}</p>
          <p><span class="font-medium">Interval:</span> {{ well.properties.interval }}</p>
          <p><span class="font-medium">Spud Date:</span> {{ formatDate(well.properties.spud_date) }}</p>
          <p><span class="font-medium">Lateral Length:</span> {{ formatLength(well.properties.lateral_length) }}</p>
        </div>
      </div>

      <!-- Production Chart -->
      <div class="flex flex-col gap-2">
        <h4 class="text-sm font-semibold text-gray-700">Production History</h4>
        <div v-if="isLoadingProduction" class="h-48 flex items-center justify-center">
          <span class="text-sm text-gray-500">Loading production data...</span>
        </div>
        <div v-else-if="productionData?.production?.length" class="h-48">
          <div v-if="chartData.datasets.length" class="h-full">
            <Line
              :data="chartData"
              :options="chartOptions"
            />
          </div>
          <div v-else class="flex items-center justify-center h-full">
            <span class="text-sm text-gray-500">Error creating chart data</span>
          </div>
        </div>
        <div v-else class="h-48 flex items-center justify-center">
          <span class="text-sm text-gray-500">No production data available</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Line } from 'vue-chartjs'
import { format } from 'date-fns'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

const props = defineProps<{
  well: any | null
}>()

const productionData = ref<any>(null)
const isLoadingProduction = ref(false)

// Format helpers
const formatDate = (date: string) => format(new Date(date), 'MM/dd/yyyy')
const formatLength = (length: number) => `${Math.round(length).toLocaleString()} ft`

// Fetch production data when well changes
watch(() => props.well, async (newWell) => {
  if (newWell?.properties?.api_14) {
    const api = newWell.properties.api_14
    isLoadingProduction.value = true
    const config = useRuntimeConfig()
    const url = `${config.public.flaskBaseUrl}/wells/${api}/production`
    
    try {
      const response = await $fetch(url)
      console.log('=== Production Data ===')
      console.log('Raw Response:', response)
      productionData.value = response
      
      // Log the computed chart data
      const computedData = chartData.value
      console.log('Computed Chart Data:', {
        labels: computedData.labels,
        datasets: computedData.datasets.map(d => ({
          label: d.label,
          dataPoints: d.data
        }))
      })
    } catch (error: any) {
      console.error('Production Error:', error)
      productionData.value = null
    } finally {
      isLoadingProduction.value = false
    }
  } else {
    productionData.value = null
  }
}, { immediate: true })

// Chart configuration
const chartData = computed(() => {
  console.log('Computing chart data from:', productionData.value)
  
  if (!productionData.value?.production?.length) {
    console.log('No production data available for chart')
    return {
      labels: [],
      datasets: []
    }
  }

  const labels = productionData.value.production.map((p: any) => {
    console.log('Processing date:', p.prod_date)
    return format(new Date(p.prod_date), 'MM/yyyy')
  })

  const oilData = productionData.value.production.map((p: any) => {
    console.log('Processing oil:', p.oil)
    return parseFloat(p.oil)
  })

  const gasData = productionData.value.production.map((p: any) => {
    console.log('Processing gas:', p.gas)
    return parseFloat(p.gas)
  })

  return {
    labels,
    datasets: [
      {
        label: 'Oil (bbl)',
        data: oilData,
        borderColor: '#22C55E',
        backgroundColor: '#22C55E20',
        fill: true,
        tension: 0.1,
        yAxisID: 'y-oil'
      },
      {
        label: 'Gas (mcf)',
        data: gasData,
        borderColor: '#EF4444',
        backgroundColor: '#EF444420',
        fill: true,
        tension: 0.1,
        yAxisID: 'y-gas'
      }
    ]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    intersect: false,
    mode: 'index' as const
  },
  scales: {
    'y-oil': {
      type: 'linear' as const,
      display: true,
      position: 'left' as const,
      title: {
        display: true,
        text: 'Oil (bbl)'
      },
      grid: {
        drawOnChartArea: false
      }
    },
    'y-gas': {
      type: 'linear' as const,
      display: true,
      position: 'right' as const,
      title: {
        display: true,
        text: 'Gas (mcf)'
      },
      grid: {
        drawOnChartArea: false
      }
    }
  },
  plugins: {
    legend: {
      position: 'top' as const
    },
    tooltip: {
      callbacks: {
        label: (context: any) => {
          const label = context.dataset.label || ''
          const value = context.parsed.y?.toLocaleString() || ''
          return `${label}: ${value}`
        }
      }
    }
  }
}
</script> 