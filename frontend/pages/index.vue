<template>
  <div class="h-screen flex flex-col overflow-hidden">
    <!-- Fixed height header -->
    <Menubar class="bg-black z-50 h-14">
      <template #start>
        <span class="text-white text-xl font-semibold px-4">Well Evaluation Tool</span>
      </template>
    </Menubar>
    <!-- Main content area: total height minus header height -->
    <div class="h-[calc(100vh-3.5rem)] flex overflow-hidden">
      <!-- Map Container (60% width) -->
      <div class="w-[60%] h-full">
        <Map />
      </div>
      <!-- Right Side Container (40% width) -->
      <div class="w-[40%] h-full overflow-hidden">
        <!-- Fixed heights for both sections -->
        <div class="h-[400px] bg-white overflow-hidden">
          <Tuning />
        </div>
        <!-- Added divider -->
        <div class="h-px bg-gray-200"></div>
        <div class="h-[calc(100%-401px)] bg-gray-50 overflow-hidden">
          <Outputs />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Map from '~/components/Map.vue'
import Tuning from '~/components/Tuning.vue'
import Outputs from '~/components/Outputs.vue'
</script>

<style>
#__nuxt {
  height: 100vh;
}
</style>