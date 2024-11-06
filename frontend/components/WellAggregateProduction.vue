<template>
  <div class="h-full w-full p-4 overflow-hidden flex flex-col">
    <div class="flex-grow overflow-hidden">
      <Line
        v-if="chartData"
        :data="chartData"
        :options="chartOptions"
        class="h-full w-full"
      />
      <div v-else-if="loading" class="flex items-center justify-center h-full text-gray-500">
        Loading production data...
      </div>
      <div v-else class="flex items-center justify-center h-full text-gray-500">
        No production data available
      </div>
    </div>
    <!-- Download Button -->
    <div class="mt-4 flex justify-end">
      <Button
        v-if="chartData"
        icon="pi pi-download"
        label="Download Percentile Data"
        severity="secondary"
        size="small"
        @click="handleDownload"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Line } from 'vue-chartjs'
import { useMapStore } from '~/stores/map'
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
import Button from 'primevue/button'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

interface ProductionPoint {
  month: number
  oil: number
}

interface WellsData {
  [api: string]: ProductionPoint[]
}

const mapStore = useMapStore()
const loading = ref(false)
const wellsData = ref<WellsData>({})
const wellCount = ref(0)

const fetchWellsProduction = async (wells: any[]) => {
  const apis = wells.map(well => well.properties.api_14)
  const config = useRuntimeConfig()
  
  try {
    loading.value = true
    console.log('Fetching production for APIs:', apis.slice(0, 5))
    
    const response = await fetch(`${config.public.flaskBaseUrl}/wells/aggregate-production`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ apis })
    })
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      console.error('Production fetch error:', errorData)
      throw new Error(errorData.message || `HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    console.log('Production response:', data)
    
    if (data.success) {
      wellsData.value = data.data
      wellCount.value = data.well_count
    } else {
      console.error('Error in production response:', data.error)
      throw new Error(data.message || 'Failed to fetch production data')
    }
  } catch (error) {
    console.error('Error fetching production:', error)
    wellsData.value = {}
    wellCount.value = 0
    throw error
  } finally {
    loading.value = false
  }
}

const debouncedFetch = useDebouncedRef(async (wells: any[]) => {
  if (!wells?.length) {
    wellsData.value = {}
    wellCount.value = 0
    return
  }

  loading.value = true
  try {
    await fetchWellsProduction(wells)
  } finally {
    loading.value = false
  }
}, 300) // 300ms debounce

watch(() => mapStore.filteredWells, (newWells) => {
  if (newWells?.features) {
    debouncedFetch(newWells.features)
  }
}, { deep: true })

const chartData = computed(() => {
  if (!Object.keys(wellsData.value).length) return null

  const wellDatasets = Object.entries(wellsData.value).map(([api, production]) => {
    if (!Array.isArray(production)) {
      console.error('Production is not an array for API:', api, production)
      return null
    }

    return {
      label: api,
      data: production.map(p => ({ x: p.month, y: p.oil })),
      borderColor: 'rgba(156, 163, 175, 0.2)',
      backgroundColor: 'rgba(156, 163, 175, 0.1)',
      borderWidth: 1,
      pointRadius: 0,
      tension: 0.1,
      order: 2
    }
  }).filter(dataset => dataset !== null)

  const monthlyStats = new Map<number, number[]>()
  Object.values(wellsData.value).forEach(production => {
    if (Array.isArray(production)) {
      production.forEach(p => {
        if (!monthlyStats.has(p.month)) {
          monthlyStats.set(p.month, [])
        }
        monthlyStats.get(p.month)?.push(p.oil)
      })
    }
  })

  const sortedMonths = Array.from(monthlyStats.entries())
    .sort(([a], [b]) => a - b)
    .filter(([_, values]) => values.length > 0)

  const getPercentile = (values: number[], percentile: number) => {
    const sorted = [...values].sort((a, b) => a - b)
    const index = Math.ceil(((100 - percentile) / 100) * sorted.length) - 1
    return sorted[index]
  }

  const p90Data = sortedMonths.map(([month, values]) => ({
    x: month,
    y: getPercentile(values, 90)
  }))

  const p50Data = sortedMonths.map(([month, values]) => ({
    x: month,
    y: getPercentile(values, 50)
  }))

  const p10Data = sortedMonths.map(([month, values]) => ({
    x: month,
    y: getPercentile(values, 10)
  }))

  return {
    datasets: [
      ...wellDatasets,
      {
        label: 'P90',
        data: p90Data,
        borderColor: '#EF4444',
        borderWidth: 3,
        pointRadius: 0,
        tension: 0.1,
        fill: false,
        order: 1
      },
      {
        label: 'P50',
        data: p50Data,
        borderColor: '#22C55E',
        borderWidth: 3,
        pointRadius: 0,
        tension: 0.1,
        fill: false,
        order: 1
      },
      {
        label: 'P10',
        data: p10Data,
        borderColor: '#3B82F6',
        borderWidth: 3,
        pointRadius: 0,
        tension: 0.1,
        fill: false,
        order: 1
      }
    ]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: {
    duration: 0 // Disable animations
  },
  transitions: {
    active: {
      animation: {
        duration: 0 // Disable transitions
      }
    }
  },
  plugins: {
    legend: {
      display: true,
      position: 'top' as const,
      labels: {
        filter: (item: any) => ['P90', 'P50', 'P10'].includes(item.text)
      }
    },
    tooltip: {
      mode: 'nearest' as const,
      intersect: false
    }
  },
  scales: {
    x: {
      type: 'linear' as const,
      title: {
        display: true,
        text: 'Months from First Production'
      },
      min: 1,
      max: 48
    },
    y: {
      title: {
        display: true,
        text: 'Oil Production (bbl)'
      },
      animation: {
        duration: 0 // Disable y-axis animations
      }
    }
  }
}

// Add these new functions for CSV export
const generateCsvContent = (p90Data: any[], p50Data: any[], p10Data: any[]) => {
  const headers = 'Month,P90,P50,P10\n'
  const rows = p90Data.map((_, index) => {
    return `${p90Data[index].x},${p90Data[index].y},${p50Data[index].y},${p10Data[index].y}`
  }).join('\n')
  return headers + rows
}

const downloadCsv = (content: string, filename: string) => {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', filename)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
}

const handleDownload = () => {
  if (!chartData.value) return

  // Find the percentile datasets from chartData
  const p90Dataset = chartData.value.datasets.find(d => d.label === 'P90')
  const p50Dataset = chartData.value.datasets.find(d => d.label === 'P50')
  const p10Dataset = chartData.value.datasets.find(d => d.label === 'P10')

  if (!p90Dataset?.data || !p50Dataset?.data || !p10Dataset?.data) {
    console.error('Missing percentile data')
    return
  }

  const csvContent = generateCsvContent(
    p90Dataset.data as any[],
    p50Dataset.data as any[],
    p10Dataset.data as any[]
  )

  const filename = `well-percentiles-${new Date().toISOString().split('T')[0]}.csv`
  downloadCsv(csvContent, filename)
}

function useDebouncedRef(fn: Function, delay: number) {
  let timeout: NodeJS.Timeout
  return async (...args: any[]) => {
    clearTimeout(timeout)
    return new Promise((resolve) => {
      timeout = setTimeout(async () => {
        resolve(await fn(...args))
      }, delay)
    })
  }
}
</script> 