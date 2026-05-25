<template>
  <n-modal v-model:show="visible" title="测试参数" preset="dialog" style="width: 500px">
    <n-form :model="formValues" label-placement="left" label-width="120">
      <n-form-item
        v-for="p in params"
        :key="p.name"
        :label="p.description || p.name"
        :required="p.required"
      >
        <n-input-number
          v-if="p.type === 'integer' || p.type === 'number'"
          v-model:value="formValues[p.name]"
          :placeholder="p.default != null ? String(p.default) : ''"
          style="width: 100%"
        />
        <n-switch
          v-else-if="p.type === 'boolean'"
          v-model:value="formValues[p.name]"
        />
        <n-input
          v-else-if="p.type === 'object'"
          v-model:value="formValues[p.name]"
          type="textarea"
          :rows="3"
          font="monospace"
          placeholder='{"key": "value"}'
        />
        <n-input
          v-else
          v-model:value="formValues[p.name]"
          :placeholder="p.default != null ? String(p.default) : ''"
        />
      </n-form-item>
    </n-form>
    <template #action>
      <n-button @click="visible = false">取消</n-button>
      <n-button type="primary" @click="handleConfirm">执行测试</n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { ParamDef } from './LowCodeConfigForm.vue'

const props = defineProps<{
  show: boolean
  params: ParamDef[]
}>()

const emit = defineEmits<{
  (e: 'update:show', val: boolean): void
  (e: 'confirm', params: Record<string, any>): void
}>()

const visible = ref(props.show)
watch(() => props.show, (v) => { visible.value = v })
watch(visible, (v) => emit('update:show', v))

const formValues = ref<Record<string, any>>({})

watch(() => props.params, (params) => {
  const values: Record<string, any> = {}
  for (const p of params) {
    if (p.type === 'boolean') {
      values[p.name] = p.default ?? false
    } else if (p.type === 'integer' || p.type === 'number') {
      values[p.name] = p.default ?? null
    } else {
      values[p.name] = p.default != null ? String(p.default) : ''
    }
  }
  formValues.value = values
}, { immediate: true })

function handleConfirm() {
  const result: Record<string, any> = {}
  for (const p of props.params) {
    const val = formValues.value[p.name]
    if (p.type === 'object' && typeof val === 'string' && val.trim()) {
      try { result[p.name] = JSON.parse(val) } catch { result[p.name] = val }
    } else if (val !== '' && val !== null && val !== undefined) {
      result[p.name] = val
    }
  }
  emit('confirm', result)
  visible.value = false
}
</script>
