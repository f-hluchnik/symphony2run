<script setup>
import { ref, onMounted } from 'vue'
import './styles.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const message = ref('')
const duration = ref(null)
const loading = ref(false)
const error = ref(null)

onMounted(async () => {
  loading.value = true
  error.value = null
  try {
    const response = await fetch(`${API_BASE}/`)
    if (!response.ok) throw new Error(`Server error: ${response.status}`)
    const data = await response.json()
    message.value = data.message
  } catch (e) {
    error.value = 'Could not connect to the server. Please try again later.'
  } finally {
    loading.value = false
  }
})

const submitForm = async () => {
  if (!duration.value || duration.value < 1) {
    error.value = 'Please enter a valid duration (at least 1 minute).'
    return
  }

  loading.value = true
  error.value = null
  try {
    const response = await fetch(`${API_BASE}/run/?run_duration=${duration.value}`)
    if (!response.ok) throw new Error(`Server error: ${response.status}`)
    const data = await response.json()
    message.value = data.message ?? data
  } catch (e) {
    error.value = 'Something went wrong. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <h1>Find a symphony for your run</h1>

  <div class="form-row">
    <span class="input-label">minutes</span>
    <input
      type="number"
      v-model.number="duration"
      min="1"
      placeholder="45"
      :disabled="loading"
    />
    <button @click="submitForm" :disabled="loading">
      {{ loading ? 'Loading…' : 'Run' }}
    </button>
  </div>

  <p v-if="error" class="error">{{ error }}</p>
  <p v-else-if="message">{{ message }}</p>
</template>
