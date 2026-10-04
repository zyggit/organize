<script setup lang="ts">
const props = defineProps<{ step: number }>()
const steps = ['选择方案', '设置文件夹', '扫描', '预览', '整理', '结果']
</script>

<template>
  <div class="flow-stepper">
    <template v-for="(label, index) in steps" :key="label">
      <div class="flow-step" :class="{ done: index + 1 < props.step, current: index + 1 === props.step }">
        <span>{{ index + 1 < props.step ? '✓' : index + 1 }}</span>{{ label }}
      </div>
      <i v-if="index < steps.length - 1" :class="{ done: index + 1 < props.step }" />
    </template>
    <div class="flow-safe">♢ {{ props.step < 5 ? '确认前不会改动任何文件' : '每个文件的去向都会记录，可以撤销' }}</div>
  </div>
</template>
