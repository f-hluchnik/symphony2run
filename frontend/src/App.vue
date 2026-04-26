<script setup>
import { ref, onMounted } from 'vue'
import './styles.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

const message = ref('')
const duration = ref(null)
const loading = ref(false)
const error = ref(null)
const symphonies = ref([])

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
  symphonies.value = []
  try {
    const response = await fetch(`${API_BASE}/search/?run_duration=${duration.value}`)
    if (!response.ok) throw new Error(`Server error: ${response.status}`)
    const data = await response.json()
    if (!data || data.length === 0) {
      message.value = 'No symphonies found for that duration.'
    } else {
      symphonies.value = data
    }
  } catch (e) {
    error.value = 'Something went wrong. Please try again.'
  } finally {
    loading.value = false
  }
}

const formatDuration = (ms) => {
  const totalSec = Math.round(ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return s > 0 ? `${m}′ ${s}″` : `${m}′`
}
</script>

<template>
  <div class="page">
    <!-- Header -->
    <header class="site-header">
      <div class="logo-mark">♩</div>
      <h1>Symphony<span class="brand-accent">2</span>Run</h1>
      <p class="tagline">Score your stride with the classical canon</p>
    </header>

    <!-- Search form -->
    <section class="search-section">
      <label class="field-label" for="dur-input">Run duration</label>
      <div class="form-row">
        <input
          id="dur-input"
          type="number"
          v-model.number="duration"
          min="1"
          placeholder="45"
          :disabled="loading"
        />
        <span class="input-unit">min</span>
        <button @click="submitForm" :disabled="loading">
          <span v-if="!loading">Find works</span>
          <span v-else class="loader-dots"><span>.</span><span>.</span><span>.</span></span>
        </button>
      </div>
      <p v-if="error" class="error-msg">{{ error }}</p>
    </section>

    <!-- Results -->
    <transition name="fade-up">
      <section v-if="symphonies.length > 0" class="results">
        <div class="results-header">
          <span class="results-label">Suggestions</span>
          <span class="results-meta">~{{ duration }} min</span>
        </div>

        <ul class="suggestion-list">
          <li
            v-for="(s, i) in symphonies"
            :key="s.id"
            class="suggestion-card"
            :style="{ animationDelay: `${i * 0.07}s` }"
          >
            <div class="card-composer">{{ s.composer }}</div>
            <div class="card-work">{{ s.work }}</div>
            <div class="card-duration">{{ formatDuration(s.duration_ms) }}</div>
          </li>
        </ul>
      </section>
    </transition>

    <!-- Empty / welcome state -->
    <transition name="fade-up">
      <p v-if="!symphonies.length && message && !loading" class="welcome-msg">{{ message }}</p>
    </transition>

    <footer class="site-footer">♩ &thinsp;♪ &thinsp;♫ &thinsp;♬</footer>
  </div>
</template>