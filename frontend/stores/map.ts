import { defineStore } from 'pinia'
import type { Map } from 'maplibre-gl'
import type maplibregl from 'maplibre-gl'
import type { FeatureCollection, GeoJSON } from 'geojson'
import { LngLatBounds } from 'maplibre-gl'
import { generateColors } from '~/utils/colors'

// Create a simpler map interface to avoid deep type instantiation
interface SimpleMap {
  flyTo: (options: { center: [number, number], zoom: number, duration: number }) => void
  getSource: (id: string) => any
}

interface MapState {
  map: SimpleMap | null
  trData: FeatureCollection | null
  wellsData: FeatureCollection | null
  selectedTR: string | null
  radius: number
  isLoadingWells: boolean
  operatorColors: Record<string, string>
  selectedOperators: string[]
  selectedFormations: string[]
  lateralLengthRange: {
    min: number
    max: number
  }
}

export const useMapStore = defineStore('map', {
  state: (): MapState => ({
    map: null,
    trData: null,
    wellsData: null,
    selectedTR: null,
    radius: 10,
    isLoadingWells: false,
    operatorColors: {},
    selectedOperators: [],
    selectedFormations: [],
    lateralLengthRange: {
      min: 8000,
      max: 12000
    }
  }),

  getters: {
    // Get unique operators from wells data
    availableOperators: (state): { label: string; value: string }[] => {
      if (!state.wellsData?.features) return []
      
      const operators = new Set(
        state.wellsData.features
          .map(f => f.properties?.env_operator)
          .filter(Boolean)
      )
      
      return Array.from(operators)
        .map(op => ({ label: op, value: op }))
        .sort((a, b) => a.label.localeCompare(b.label))
    },

    // Get unique formations from wells data
    availableFormations: (state): { label: string; value: string }[] => {
      if (!state.wellsData?.features) return []
      
      const formations = new Set(
        state.wellsData.features
          .map(f => f.properties?.interval)
          .filter(Boolean)
      )
      
      return Array.from(formations)
        .map(f => ({ label: f, value: f }))
        .sort((a, b) => a.label.localeCompare(b.label))
    },

    // Filter wells based on selected criteria
    filteredWells: (state): FeatureCollection => {
      if (!state.wellsData) {
        return { type: 'FeatureCollection', features: [] }
      }

      return {
        type: 'FeatureCollection',
        features: state.wellsData.features.filter(feature => {
          const props = feature.properties
          if (!props) return false

          // Filter by operators if any selected
          if (state.selectedOperators.length > 0 && 
              !state.selectedOperators.includes(props.env_operator)) {
            return false
          }

          // Filter by formations if any selected
          if (state.selectedFormations.length > 0 && 
              !state.selectedFormations.includes(props.interval)) {
            return false
          }

          // Filter by lateral length range
          const lateralLength = props.lateral_length
          if (lateralLength < state.lateralLengthRange.min || 
              lateralLength > state.lateralLengthRange.max) {
            return false
          }

          return true
        })
      }
    }
  },

  actions: {
    setMap(map: Map) {
      this.map = {
        flyTo: map.flyTo.bind(map),
        getSource: map.getSource.bind(map)
      }
    },

    async fetchTROptions() {
      const config = useRuntimeConfig()
      try {
        const response = await fetch(`${config.public.flaskBaseUrl}/tr`)
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
        this.trData = await response.json()
      } catch (error) {
        this.trData = { type: 'FeatureCollection', features: [] }
      }
    },

    async fetchWellsByTR(tr: string) {
      if (!tr) return
      
      this.isLoadingWells = true
      const config = useRuntimeConfig()
      try {
        const response = await fetch(`${config.public.flaskBaseUrl}/wells/${tr}?radius=${this.radius}`)
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.message || `HTTP error! status: ${response.status}`)
        }
        const wellsData = await response.json() as FeatureCollection
        
        if (wellsData.type !== 'FeatureCollection') {
          throw new Error('Invalid GeoJSON response')
        }

        // Generate colors for unique operators
        const operators = new Set(
          wellsData.features.map(f => f.properties?.env_operator).filter(Boolean)
        )
        
        this.operatorColors = generateColors([...operators])
        this.wellsData = wellsData
        
        // Update map source if it exists
        if (this.map && this.map.getSource('wells-data')) {
          const source = this.map.getSource('wells-data') as maplibregl.GeoJSONSource
          source.setData(this.filteredWells)
        }

        this.updateMapView()
      } catch (error) {
        console.error('Error fetching wells:', error)
        this.wellsData = { type: 'FeatureCollection', features: [] }
        throw error // Re-throw to handle in components if needed
      } finally {
        this.isLoadingWells = false
      }
    },

    setSelectedTR(tr: string | null) {
      if (tr === this.selectedTR) return
      this.selectedTR = tr
      
      if (tr && this.trData?.features) {
        this.fetchWellsByTR(tr)
      }
    },

    updateMapView() {
      if (!this.selectedTR || !this.trData?.features || !this.map) return

      const selectedFeature = this.trData.features.find(
        feature => feature.properties?.tr === this.selectedTR
      )

      if (selectedFeature?.geometry) {
        try {
          let coordinates: [number, number][] = []
          
          if (selectedFeature.geometry.type === 'Polygon') {
            coordinates = selectedFeature.geometry.coordinates[0] as [number, number][]
          } else if (selectedFeature.geometry.type === 'MultiPolygon') {
            coordinates = selectedFeature.geometry.coordinates[0][0] as [number, number][]
          }

          if (coordinates.length > 0) {
            let sumX = 0
            let sumY = 0
            
            coordinates.forEach(coord => {
              sumX += coord[0]
              sumY += coord[1]
            })
            
            const centroid: [number, number] = [
              sumX / coordinates.length,
              sumY / coordinates.length
            ]

            const zoomLevel = 12 - Math.log2(this.radius / 2.5)

            this.map.flyTo({
              center: centroid,
              zoom: zoomLevel,
              duration: 1500
            })
          }
        } catch (error) {
          // Silent error handling for map view updates
        }
      }
    },

    setRadius(radius: number) {
      if (radius === this.radius) return
      this.radius = radius
      if (this.selectedTR) {
        this.fetchWellsByTR(this.selectedTR)
      }
    },

    setSelectedOperators(operators: string[]) {
      this.selectedOperators = operators
      // Update map source with filtered wells
      if (this.map && this.map.getSource('wells-data')) {
        const source = this.map.getSource('wells-data') as maplibregl.GeoJSONSource
        source.setData(this.filteredWells)
      }
    },

    setSelectedFormations(formations: string[]) {
      this.selectedFormations = formations
      // Update map source with filtered wells
      if (this.map && this.map.getSource('wells-data')) {
        const source = this.map.getSource('wells-data') as maplibregl.GeoJSONSource
        source.setData(this.filteredWells)
      }
    },

    setLateralLengthRange(min: number, max: number) {
      this.lateralLengthRange = { min, max }
      // Update map source with filtered wells
      if (this.map && this.map.getSource('wells-data')) {
        const source = this.map.getSource('wells-data') as maplibregl.GeoJSONSource
        source.setData(this.filteredWells)
      }
    },

    async fetchWellProduction(apis: string[]) {
      if (!apis.length) return null
      
      const config = useRuntimeConfig()
      try {
        const response = await fetch(`${config.public.flaskBaseUrl}/wells/aggregate-production`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ apis }),
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          console.error('Production fetch error:', errorData)
          throw new Error(errorData.message || `HTTP error! status: ${response.status}`)
        }

        const data = await response.json()
        if (!data.success) {
          throw new Error(data.message || 'Failed to fetch production data')
        }

        return data.data
      } catch (error) {
        console.error('Error fetching production:', error)
        throw error
      }
    }
  }
}) 