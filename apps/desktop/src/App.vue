<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { darkTheme, NConfigProvider, NMessageProvider, type GlobalThemeOverrides } from 'naive-ui'
import AppSidebar from './components/AppSidebar.vue'
import FlowStepper from './components/FlowStepper.vue'
import HomePage from './pages/HomePage.vue'
import ConfigPage from './pages/ConfigPage.vue'
import ScanPage from './pages/ScanPage.vue'
import PreviewPage from './pages/PreviewPage.vue'
import DuplicatesPage from './pages/DuplicatesPage.vue'
import ExecutingPage from './pages/ExecutingPage.vue'
import ResultPage from './pages/ResultPage.vue'
import HistoryPage from './pages/HistoryPage.vue'
import QuarantinePage from './pages/QuarantinePage.vue'
import SettingsPage from './pages/SettingsPage.vue'
import AboutPage from './pages/AboutPage.vue'
import OnboardingPage from './pages/OnboardingPage.vue'
import UndoPage from './pages/UndoPage.vue'
import { useAppStore } from './stores/app'
import type { ViewName } from './types'

const store = useAppStore()
const pages = { onboarding: OnboardingPage, home: HomePage, config: ConfigPage, scan: ScanPage, preview: PreviewPage, duplicates: DuplicatesPage, executing: ExecutingPage, result: ResultPage, history: HistoryPage, undo: UndoPage, quarantine: QuarantinePage, settings: SettingsPage, about: AboutPage }
const current = computed(() => pages[store.view as keyof typeof pages] ?? HomePage)
const flowSteps: Partial<Record<ViewName, number>> = { config: 2, scan: 3, preview: 4, duplicates: 4, executing: 5, result: 6 }
const flowStep = computed(() => flowSteps[store.view] ?? 0)
const themeOverrides: GlobalThemeOverrides = { common: { primaryColor: '#4D8DFF', successColor: '#38D39F', warningColor: '#FF9147', errorColor: '#FF5D6E', bodyColor: '#0C1220', cardColor: '#121A2B', borderColor: '#23304C', textColor1: '#E8EDF7', textColor2: '#9AA8C3', textColor3: '#66759A', borderRadius: '6px' } }
onMounted(() => store.initialize())
</script>

<template>
  <NConfigProvider :theme="darkTheme" :theme-overrides="themeOverrides">
    <NMessageProvider>
      <div class="window-shell">
        <header class="titlebar"><div class="window-lights"><i /><i /><i /></div><strong>organize</strong><span><i :class="{ ready: store.engineReady }" />{{ store.engineReady ? '整理引擎已就绪' : '正在启动整理引擎' }}</span></header>
        <div class="app-body">
          <AppSidebar v-if="store.view !== 'onboarding'" />
          <main class="main-content">
            <FlowStepper v-if="flowStep" :step="flowStep" />
            <div v-if="store.error" class="global-error"><b>出现了问题</b><span>{{ store.error }}</span><button @click="store.error = undefined">×</button></div>
            <component :is="current" />
          </main>
        </div>
      </div>
    </NMessageProvider>
  </NConfigProvider>
</template>
