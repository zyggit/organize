<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useAppStore } from '../stores/app'
import type { Profile } from '../types'
import AppIcon from './AppIcon.vue'

const props = defineProps<{ saved: boolean }>()
const emit = defineEmits<{ loaded: [] }>()
const store = useAppStore()
const open = ref(false)
const confirmingRemove = ref(false)
const root = ref<HTMLElement>()

function close() { open.value = false; confirmingRemove.value = false }
function onDocumentClick(event: MouseEvent) { if (!root.value?.contains(event.target as Node)) close() }
function onKeydown(event: KeyboardEvent) { if (event.key === 'Escape') close() }
onMounted(() => { document.addEventListener('mousedown', onDocumentClick); document.addEventListener('keydown', onKeydown) })
onBeforeUnmount(() => { document.removeEventListener('mousedown', onDocumentClick); document.removeEventListener('keydown', onKeydown) })

function load(profile: Profile) {
  store.useProfile(profile)
  emit('loaded')
  close()
}
async function saveCopy() {
  store.profile.id = crypto.randomUUID()
  store.profile.name = `${store.profile.name} 副本`.slice(0, 80)
  await store.saveProfile()
  close()
}
async function remove() {
  if (!confirmingRemove.value) { confirmingRemove.value = true; return }
  await store.deleteProfile(store.profile.id)
  close()
}
const ruleCount = (profile: Profile) => profile.parameters.typeRules?.filter((rule) => rule.enabled).length
</script>

<template>
  <div ref="root" class="menu-anchor">
    <button class="button secondary" :aria-expanded="open" aria-haspopup="menu" @click="open ? close() : (open = true)">
      <AppIcon name="bookmark" :size="16" />方案库<span class="count-badge">{{ store.savedProfiles.length }}</span><AppIcon name="chevron" :size="14" />
    </button>
    <div v-if="open" class="popover profile-menu" role="menu">
      <header class="popover-head">已保存的方案</header>
      <div v-if="store.savedProfiles.length" class="profile-list">
        <button v-for="profile in store.savedProfiles" :key="profile.id" role="menuitem" class="profile-item" :class="{ current: profile.id === store.profile.id }" @click="load(profile)">
          <span><b>{{ profile.name }}</b><small>{{ profile.sourceFolders.length }} 个来源<template v-if="ruleCount(profile) !== undefined">，{{ ruleCount(profile) }} 个分类</template></small></span>
          <em v-if="profile.id === store.profile.id">当前</em>
        </button>
      </div>
      <p v-else class="popover-empty">还没有保存的方案。保存后可以在这里一键切换。</p>
      <footer class="popover-actions">
        <button role="menuitem" @click="saveCopy"><AppIcon name="duplicate" :size="15" />另存为新方案</button>
        <button v-if="props.saved" role="menuitem" class="danger" @click="remove"><AppIcon name="trash" :size="15" />{{ confirmingRemove ? '再点一次确认移除' : '从方案库移除' }}</button>
      </footer>
    </div>
  </div>
</template>
