<template>
  <div class="h-full w-full bg-gray-50 p-4">
    <h2 class="text-xl font-semibold text-gray-800 mb-4">Tuning Parameters</h2>
    
    <div class="flex flex-col gap-4">
      <!-- Township/Range Selection -->
      <div class="flex flex-col gap-2">
        <label for="tr-select" class="text-sm font-medium text-gray-700">Township/Range</label>
        <Select
          id="tr-select"
          v-model="selectedTR"
          :options="trOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Select Township/Range"
          class="w-full"
          :loading="loading"
        />
      </div>

      <!-- Numeric Controls Group -->
      <div class="flex flex-col gap-2" :class="{ 'opacity-50': !selectedTR }">
        <div class="grid grid-cols-3 gap-2">
          <!-- Radius Control -->
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-gray-700">Mile Radius</label>
            <InputNumber
              v-model="radius"
              placeholder="Radius"
              :min="5"
              :max="15"
              :step="1"
              :disabled="!selectedTR"
              :minFractionDigits="0"
              :maxFractionDigits="0"
              @update:modelValue="handleRadiusChange"
              buttonLayout="horizontal"
              :inputStyle="{ width: '100%' }"
              :showButtons="true"
            >
              <template #prefix>
                <i class="pi pi-search" />
              </template>
            </InputNumber>
          </div>

          <!-- Lateral Length Min -->
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-gray-700">Min Lateral</label>
            <InputNumber
              v-model="lateralMin"
              placeholder="Min Length"
              :min="5000"
              :max="lateralMax"
              :step="1000"
              :disabled="!selectedTR"
              :minFractionDigits="0"
              :maxFractionDigits="0"
              @update:modelValue="handleLateralChange"
              buttonLayout="horizontal"
              :inputStyle="{ width: '100%' }"
              :showButtons="true"
            >
              <template #prefix>
                <i class="pi pi-arrows-h" />
              </template>
            </InputNumber>
          </div>

          <!-- Lateral Length Max -->
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-gray-700">Max Lateral</label>
            <InputNumber
              v-model="lateralMax"
              placeholder="Max Length"
              :min="lateralMin"
              :max="20000"
              :step="1000"
              :disabled="!selectedTR"
              :minFractionDigits="0"
              :maxFractionDigits="0"
              @update:modelValue="handleLateralChange"
              buttonLayout="horizontal"
              :inputStyle="{ width: '100%' }"
              :showButtons="true"
            >
              <template #prefix>
                <i class="pi pi-arrows-h" />
              </template>
            </InputNumber>
          </div>
        </div>
      </div>

      <!-- Operator Selection -->
      <div class="flex flex-col gap-2">
        <label for="operator-select" class="text-sm font-medium text-gray-700">Operators</label>
        <MultiSelect
          id="operator-select"
          v-model="selectedOperators"
          :options="operatorOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Select Operators"
          class="w-full"
          :disabled="!selectedTR"
          display="chip"
        />
      </div>

      <!-- Formation Selection -->
      <div class="flex flex-col gap-2">
        <label for="formation-select" class="text-sm font-medium text-gray-700">Formations</label>
        <MultiSelect
          id="formation-select"
          v-model="selectedFormations"
          :options="formationOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Select Formations"
          class="w-full"
          :disabled="!selectedTR"
          display="chip"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useMapStore } from '~/stores/map'

const mapStore = useMapStore()
const selectedTR = ref<string | null>(null)
const loading = ref(true)
const radius = ref<number>(10)
const selectedOperators = ref<string[]>([])
const selectedFormations = ref<string[]>([])
const lateralMin = ref<number>(8000)
const lateralMax = ref<number>(12000)

// Options for dropdowns
const trOptions = computed(() => {
  if (!mapStore.trData?.features) return []
  
  return mapStore.trData.features
    .map(feature => ({
      label: feature.properties.tr,
      value: feature.properties.tr
    }))
    .sort((a, b) => a.label.localeCompare(b.label))
})

const operatorOptions = computed(() => mapStore.availableOperators)
const formationOptions = computed(() => mapStore.availableFormations)

onMounted(async () => {
  if (!mapStore.trData) {
    await mapStore.fetchTROptions()
  }
  loading.value = false
  
  // Initialize local state from store
  radius.value = mapStore.radius
  selectedTR.value = mapStore.selectedTR || null
  selectedOperators.value = mapStore.selectedOperators
  selectedFormations.value = mapStore.selectedFormations
  lateralMin.value = mapStore.lateralLengthRange.min
  lateralMax.value = mapStore.lateralLengthRange.max
})

// Watch for changes and update store
watch(() => selectedTR.value, async (newTR) => {
  if (newTR !== undefined) {
    try {
      await mapStore.setSelectedTR(newTR)
    } catch (error) {
      // Handle error appropriately, maybe show a toast notification
      console.error('Error fetching well data:', error)
    }
  }
})

watch(() => selectedOperators.value, (newOperators) => {
  mapStore.setSelectedOperators(newOperators)
})

watch(() => selectedFormations.value, (newFormations) => {
  mapStore.setSelectedFormations(newFormations)
})

const handleRadiusChange = (value: number) => {
  if (value >= 5 && value <= 15) {
    mapStore.setRadius(Math.round(value))
  }
}

const handleLateralChange = () => {
  if (lateralMin.value && lateralMax.value) {
    mapStore.setLateralLengthRange(lateralMin.value, lateralMax.value)
  }
}
</script>

<style scoped>
:deep(.p-inputnumber) {
  width: 100%;
}

:deep(.p-inputnumber-input) {
  width: 100% !important;
}

:deep(.p-multiselect) {
  width: 100%;
}
</style> 