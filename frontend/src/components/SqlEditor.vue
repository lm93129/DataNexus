<template>
  <div ref="editorContainer" :style="{ height: height, width: '100%' }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as monaco from 'monaco-editor'
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'

self.MonacoEnvironment = {
  getWorker() {
    return new editorWorker()
  },
}

const props = withDefaults(defineProps<{
  modelValue?: string
  height?: string
  readOnly?: boolean
}>(), {
  modelValue: '',
  height: '200px',
  readOnly: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'execute': []
}>()

const editorContainer = ref<HTMLElement>()
let editor: monaco.editor.IStandaloneCodeEditor | null = null

onMounted(() => {
  if (!editorContainer.value) return
  editor = monaco.editor.create(editorContainer.value, {
    value: props.modelValue,
    language: 'sql',
    theme: 'vs',
    minimap: { enabled: false },
    readOnly: props.readOnly,
    automaticLayout: true,
    fontSize: 14,
    lineNumbers: 'on',
    scrollBeyondLastLine: false,
  })
  editor.onDidChangeModelContent(() => {
    emit('update:modelValue', editor!.getValue())
  })
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
    emit('execute')
  })
})

watch(() => props.modelValue, (val) => {
  if (editor && editor.getValue() !== val) {
    editor.setValue(val)
  }
})

onBeforeUnmount(() => {
  editor?.dispose()
})
</script>
