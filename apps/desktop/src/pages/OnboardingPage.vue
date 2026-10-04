<script setup lang="ts">
import { useAppStore } from '../stores/app'

const store = useAppStore()
</script>

<template>
  <div class="page onboarding-page">
    <section class="onboarding-hero">
      <span class="brand-mark">↓</span>
      <h1>把杂乱文件夹整理好，也保留反悔的余地</h1>
      <p>organize 会先扫描并给出准确预览。只有你确认后才移动文件，清理项会进入隔离区。</p>
    </section>
    <section class="onboarding-grid">
      <article><span>1</span><h2>选择整理方案</h2><p>从按类型、按日期、旧安装包和重复文件四个常用方案开始。</p></article>
      <article><span>2</span><h2>先看完整预览</h2><p>每个文件从哪里到哪里、是否重名、为什么跳过，都在执行前说明。</p></article>
      <article><span>3</span><h2>需要时可以撤销</h2><p>历史记录保存每次操作，目标文件没有变化时可安全恢复。</p></article>
    </section>
    <div class="onboarding-safe">✓ 永不覆盖已有文件　✓ 不永久删除　✓ 执行前必须确认</div>
    <button class="button primary onboarding-start" @click="store.completeOnboarding">开始使用 organize</button>
  </div>
</template>

