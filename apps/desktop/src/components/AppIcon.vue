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
  video: ['M4 6h11a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Z', 'm17 10 5-3v10l-5-3'],
  music: ['M9 18V5l11-2v13', 'M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z', 'M17 19a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z'],
  package: ['m12 3 9 4.5v9L12 21l-9-4.5v-9L12 3Z', 'm3 7.5 9 4.5 9-4.5', 'M12 12v9'],
  tag: ['M3 12V4h8l10 10-8 8L3 12Z', 'M7.5 7.5h.01'],
  plus: ['M12 5v14', 'M5 12h14'],
  close: ['M6 6l12 12', 'M18 6 6 18'],
  chevron: ['m6 9 6 6 6-6'],
  edit: ['M4 20h4L19 9l-4-4L4 16v4Z', 'm13.5 6.5 4 4'],
  swap: ['M7 7h13', 'm16 3 4 4-4 4', 'M17 17H4', 'm8 13-4 4 4 4'],
  layers: ['m12 3 9 5-9 5-9-5 9-5Z', 'm3 13 9 5 9-5'],
  alert: ['M12 3 2 21h20L12 3Z', 'M12 10v5', 'M12 18h.01'],
  bookmark: ['M6 3h12v18l-6-4-6 4V3Z'],
  trash: ['M4 7h16', 'M10 11v6', 'M14 11v6', 'M6 7l1 14h10l1-14', 'M9 7V4h6v3'],
}
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="app-icon">
    <path v-for="(path, index) in (paths[name] ?? paths.file)" :key="index" :d="path" />
  </svg>
</template>
