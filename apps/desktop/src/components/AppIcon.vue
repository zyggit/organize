<script setup lang="ts">
withDefaults(defineProps<{ name: string; size?: number }>(), { size: 20 })
const paths: Record<string, string[]> = {
  sparkle: ['m12 3 2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3L12 3Z', 'm20 2 .7 2.3L23 5l-2.3.7L20 8l-.7-2.3L17 5l2.3-.7L20 2Z'],
  folder: ['M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z', 'M3 10h18'],
  download: ['M12 3v12', 'm7 10 5 5 5-5', 'M4 16v4h16v-4'],
  image: ['M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z', 'm3 17 6-6 4 4 3-3 5 5', 'M16 7h.01'],
  archive: ['M4 4h16v4H4V4Z', 'M6 8v13h12V8', 'M10 12h4'],
  duplicate: ['M9 9h11v12H9V9Z', 'M15 9V3H3v12h6'],
  history: ['M3 11a9 9 0 1 1 2.7 7', 'M3 4v7h7', 'M12 7v5l3 2'],
  shield: ['m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z', 'm8 12 3 3 5-6'],
  settings: ['M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z', 'M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1 1-3Z'],
  info: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z', 'M12 11v6', 'M12 7h.01'],
  arrow: ['M4 12h16', 'm14 6 6 6-6 6'],
  check: ['m5 12 4 4L19 6'],
  search: ['M10.5 3a7.5 7.5 0 1 0 0 15 7.5 7.5 0 0 0 0-15Z', 'm16 16 5 5'],
  file: ['M5 3h9l5 5v13H5V3Z', 'M14 3v5h5', 'M8 12h8', 'M8 16h6'],
  undo: ['M4 10h10a6 6 0 0 1 0 12', 'm8 5-5 5 5 5'],
  lock: ['M5 10h14v11H5V10Z', 'M8 10V7a4 4 0 0 1 8 0v3', 'M12 14v3'],
}
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="app-icon">
    <path v-for="(path, index) in (paths[name] ?? paths.file)" :key="index" :d="path" />
  </svg>
</template>
