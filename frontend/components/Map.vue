<template>
  <div ref="mapContainer" class="w-full h-full relative">
    <MapLegend v-if="mapStore.wellsData?.features.length" />
    <WellDetailsPopup 
      v-if="hoveredWell"
      :well="hoveredWell"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import maplibregl, { Map as MapLibreMap } from 'maplibre-gl'
import { useMapStore } from '~/stores/map'
import MapLegend from './MapLegend.vue'
import WellDetailsPopup from './WellDetailsPopup.vue'

const mapContainer = ref<HTMLDivElement | null>(null)
const mapStore = useMapStore()
let mapInstance: MapLibreMap | null = null
const hoveredWell = ref<any>(null)

// Helper function to create the color expression
const createColorExpression = (colors: Record<string, string>) => {
  const expression = [
    'match',
    ['get', 'env_operator'],
    ...Object.entries(colors).flatMap(([operator, color]) => [operator, color]),
    '#000000' // default color
  ]
  console.log('Created color expression:', expression)
  return expression
}

onMounted(() => {
  if (!mapContainer.value) return

  // Wait for container to be available
  nextTick(() => {
    if (!mapContainer.value) return

    try {
      // Create map instance
      mapInstance = new maplibregl.Map({
        container: mapContainer.value,
        style: {
          version: 8,
          sources: {
            'cartodb-positron': {
              type: 'raster',
              tiles: [
                'https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png',
                'https://cartodb-basemaps-b.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png',
                'https://cartodb-basemaps-c.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png',
                'https://cartodb-basemaps-d.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png'
              ],
              tileSize: 256,
              attribution: '© OpenStreetMap, © CARTO'
            }
          },
          layers: [
            {
              id: 'cartodb-positron',
              type: 'raster',
              source: 'cartodb-positron',
              minzoom: 0,
              maxzoom: 19
            }
          ]
        },
        center: [-104.5, 40.5],
        zoom: 7
      })

      // Store map instance
      mapStore.setMap(mapInstance)

      // Set up map layers when loaded
      mapInstance.on('load', async () => {
        await mapStore.fetchTROptions()

        if (!mapStore.trData || !mapInstance) return

        // Add sources first
        mapInstance.addSource('tr-data', {
          type: 'geojson',
          data: mapStore.trData
        })

        mapInstance.addSource('wells-data', {
          type: 'geojson',
          data: {
            type: 'FeatureCollection',
            features: []
          }
        })

        // Add all layers in correct order
        // 1. TR borders (bottom layer)
        mapInstance.addLayer({
          id: 'tr-borders',
          type: 'line',
          source: 'tr-data',
          paint: {
            'line-color': '#9ca3af',
            'line-width': 1
          }
        })

        // 2. TR selected border
        mapInstance.addLayer({
          id: 'tr-selected-border',
          type: 'line',
          source: 'tr-data',
          paint: {
            'line-color': '#000000',
            'line-width': 2
          },
          filter: ['==', ['get', 'tr'], '']
        })

        // Helper function to ensure layer exists
        const ensureWellsLayers = () => {
          if (!mapInstance?.getLayer('wells-lines')) {
            // Wells lines with operator colors
            mapInstance?.addLayer({
              id: 'wells-lines',
              type: 'line',
              source: 'wells-data',
              paint: {
                'line-color': createColorExpression(mapStore.operatorColors),
                'line-width': 2
              }
            })
          }
        }

        // Ensure layers exist initially
        ensureWellsLayers()

        // Watch for wells data changes
        watch(() => mapStore.filteredWells, (newWells) => {
          if (mapInstance && mapInstance.getSource('wells-data')) {
            const source = mapInstance.getSource('wells-data') as maplibregl.GeoJSONSource
            source.setData(newWells)
          }
        }, { deep: true })

        // Watch for operator colors changes
        watch(() => mapStore.operatorColors, (newColors) => {
          if (mapInstance && Object.keys(newColors).length > 0) {
            // Ensure layers exist before updating
            ensureWellsLayers()
            
            if (mapInstance.getLayer('wells-lines')) {
              const colorExpression = createColorExpression(newColors)
              mapInstance.setPaintProperty('wells-lines', 'line-color', colorExpression)
            }
          }
        }, { deep: true })

        // Add click handler for TR selection
        mapInstance.on('click', (e) => {
          console.log('Map clicked')
          const features = mapInstance?.queryRenderedFeatures(e.point, {
            layers: ['tr-borders']
          })
          console.log('Features found:', features)

          if (features && features.length > 0) {
            const tr = features[0].properties?.tr
            console.log('TR property:', tr)
            if (tr) {
              console.log('Selecting TR:', tr)
              mapStore.setSelectedTR(tr)
            }
          }
        })

        // Watch for selection changes
        watch(() => mapStore.selectedTR, (newTR) => {
          console.log('Selection changed to:', newTR)
          if (mapInstance) {
            mapInstance.setFilter(
              'tr-selected-border',
              ['==', ['get', 'tr'], newTR || '']
            )
          }
        }, { immediate: true })

        // Watch for radius changes
        watch(() => mapStore.radius, (newRadius) => {
          console.log('Radius changed to:', newRadius)
          if (mapStore.selectedTR) {
            mapStore.setSelectedTR(mapStore.selectedTR)
          }
        })

        mapInstance.on('mouseenter', 'wells-lines', (e) => {
          if (e.features?.length > 0) {
            mapInstance!.getCanvas().style.cursor = 'pointer'
            hoveredWell.value = e.features[0]
          }
        })

        mapInstance.on('mouseleave', 'wells-lines', () => {
          mapInstance!.getCanvas().style.cursor = ''
          hoveredWell.value = null
        })
      })
    } catch (error) {
      console.error('Error initializing map:', error)
    }
  })
})

onUnmounted(() => {
  if (mapInstance) {
    mapInstance.remove()
  }
})
</script> 