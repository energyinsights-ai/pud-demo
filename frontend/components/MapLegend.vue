<template>
  <div class="absolute top-4 left-4 bg-white p-4 rounded-lg shadow-lg z-10">
    <h3 class="text-sm font-semibold mb-2">Operators</h3>
    <div class="flex flex-col gap-2">
      <div v-for="(color, operator) in operatorColors" :key="operator" class="flex items-center gap-2">
        <div 
          class="w-4 h-4 rounded-full" 
          :style="{ backgroundColor: color }"
        />
        <span class="text-xs">{{ operator }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useMapStore } from '~/stores/map'

const mapStore = useMapStore()

const operatorColors = computed(() => mapStore.operatorColors)
</script> 