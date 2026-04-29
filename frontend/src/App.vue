<script setup>
import { ref, onMounted } from 'vue'
import './styles.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

// ── State ──────────────────────────────────────────────────────
const message       = ref('')
const duration      = ref(null)
const loading       = ref(false)
const error         = ref(null)
const symphonies    = ref([])

// filters
const allComposers    = ref([])
const selectedComposers = ref([])
const verifiedOnly    = ref(false)
const showComposerFilter = ref(false)

// admin
const adminPanelOpen  = ref(false)
const adminInput      = ref('')
const adminSecret     = ref(sessionStorage.getItem('adminSecret') || '')
const adminError      = ref('')

// ── Boot ───────────────────────────────────────────────────────
onMounted(async () => {
  loading.value = true
  error.value = null
  try {
    const [rootRes, composersRes] = await Promise.all([
      fetch(`${API_BASE}/`),
      fetch(`${API_BASE}/composers/`),
    ])
    if (!rootRes.ok) throw new Error(`Server error: ${rootRes.status}`)
    const data = await rootRes.json()
    message.value = data.message
    if (composersRes.ok) allComposers.value = await composersRes.json()
  } catch (e) {
    error.value = 'Could not connect to the server. Please try again later.'
  } finally {
    loading.value = false
  }
})

// ── Search ─────────────────────────────────────────────────────
const submitForm = async () => {
  if (!duration.value || duration.value < 1) {
    error.value = 'Please enter a valid duration (at least 1 minute).'
    return
  }
  loading.value = true
  error.value = null
  symphonies.value = []

  const params = new URLSearchParams({ run_duration: duration.value })
  if (verifiedOnly.value) params.set('verified_only', 'true')
  selectedComposers.value.forEach(c => params.append('composers', c))

  try {
    const response = await fetch(`${API_BASE}/search/?${params}`)
    if (!response.ok) throw new Error(`Server error: ${response.status}`)
    const data = await response.json()
    if (!data || data.length === 0) {
      message.value = 'No works found for that duration and filters.'
      symphonies.value = []
    } else {
      symphonies.value = data
      message.value = ''
    }
  } catch (e) {
    error.value = 'Something went wrong. Please try again.'
  } finally {
    loading.value = false
  }
}

const toggleComposer = (composer) => {
  const idx = selectedComposers.value.indexOf(composer)
  if (idx === -1) selectedComposers.value.push(composer)
  else selectedComposers.value.splice(idx, 1)
}

// ── Formatting ─────────────────────────────────────────────────
const formatDuration = (ms) => {
  const totalSec = Math.round(ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return s > 0 ? `${m}′ ${s}″` : `${m}′`
}

// ── Admin ──────────────────────────────────────────────────────
const isAdmin = () => !!adminSecret.value

const loginAdmin = () => {
  if (!adminInput.value.trim()) return
  adminSecret.value = adminInput.value.trim()
  sessionStorage.setItem('adminSecret', adminSecret.value)
  adminInput.value = ''
  adminError.value = ''
}

const logoutAdmin = () => {
  adminSecret.value = ''
  sessionStorage.removeItem('adminSecret')
}

const adminAction = async (workId, action, currentValue) => {
  try {
    const res = await fetch(`${API_BASE}/works/${workId}/${action}?value=${!currentValue}`, {
      method: 'PATCH',
      headers: { 'x-admin-secret': adminSecret.value },
    })
    if (res.status === 403) {
      adminError.value = 'Wrong password.'
      logoutAdmin()
      return
    }
    if (!res.ok) throw new Error()
    // update local state optimistically
    const work = symphonies.value.find(s => s.id === workId)
    if (work) work[action] = !currentValue
  } catch {
    error.value = 'Action failed. Please try again.'
  }
}
</script>

<template>
  <div class="page">

    <!-- Header -->
    <header class="site-header">
      <div class="logo-mark">♩</div>
      <h1>Symphony<span class="brand-accent">2</span>Run</h1>
      <p class="tagline">Classical music for your run</p>
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

      <!-- Filter row -->
      <div class="filter-row">
        <button
          class="btn-ghost"
          :class="{ active: showComposerFilter }"
          @click="showComposerFilter = !showComposerFilter"
          type="button"
        >
          Composers
          <span v-if="selectedComposers.length" class="filter-count">{{ selectedComposers.length }}</span>
          <span class="chevron" :class="{ open: showComposerFilter }">›</span>
        </button>

        <label class="toggle-label">
          <input type="checkbox" v-model="verifiedOnly" />
          <span class="toggle-track"><span class="toggle-thumb"></span></span>
          Verified only
        </label>
      </div>

      <!-- Composer picker -->
      <transition name="expand">
        <div v-if="showComposerFilter" class="composer-picker">
          <button
            v-for="c in allComposers"
            :key="c"
            class="composer-chip"
            :class="{ selected: selectedComposers.includes(c) }"
            @click="toggleComposer(c)"
            type="button"
          >{{ c }}</button>
        </div>
      </transition>

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
            <div class="card-main">
              <div class="card-composer">{{ s.composer }}</div>
              <div class="card-work">{{ s.work }}</div>
              <div class="card-footer-row">
                <span class="card-duration">{{ formatDuration(s.duration_ms) }}</span>
                <span v-if="s.verified" class="badge-verified" title="Verified by the author">✓ verified</span>
              </div>
            </div>

            <!-- Admin controls -->
            <div v-if="isAdmin()" class="card-admin">
              <button
                class="admin-btn"
                :class="{ 'admin-btn--active': s.verified }"
                @click="adminAction(s.id, 'verified', s.verified)"
                :title="s.verified ? 'Remove verified' : 'Mark as verified'"
              >✓</button>
              <button
                class="admin-btn admin-btn--exclude"
                :class="{ 'admin-btn--active': s.excluded }"
                @click="adminAction(s.id, 'excluded', s.excluded)"
                :title="s.excluded ? 'Unexclude' : 'Mark as not good'"
              >✕</button>
            </div>
          </li>
        </ul>
      </section>
    </transition>

    <!-- Empty / welcome state -->
    <transition name="fade-up">
      <p v-if="!symphonies.length && message && !loading" class="welcome-msg">{{ message }}</p>
    </transition>

    <!-- Footer -->
    <footer class="site-footer">
      <span class="footer-notes">♩ &thinsp;♪ &thinsp;♫ &thinsp;♬</span>
      <span class="footer-legend">
        <span class="badge-verified small">✓ verified</span> — I've run to this
      </span>
      <button class="btn-admin-toggle" @click="adminPanelOpen = !adminPanelOpen" type="button">
        {{ isAdmin() ? '· admin ·' : '·' }}
      </button>
    </footer>

    <!-- Admin panel -->
    <transition name="fade-up">
      <div v-if="adminPanelOpen" class="admin-panel">
        <div v-if="!isAdmin()">
          <p class="admin-label">Admin password</p>
          <div class="form-row">
            <input
              type="password"
              v-model="adminInput"
              placeholder="secret"
              @keydown.enter="loginAdmin"
            />
            <button @click="loginAdmin">Enter</button>
          </div>
          <p v-if="adminError" class="error-msg">{{ adminError }}</p>
        </div>
        <div v-else class="admin-logged-in">
          <span class="admin-label">Admin mode active</span>
          <button class="btn-ghost" @click="logoutAdmin">Log out</button>
        </div>
      </div>
    </transition>

  </div>
</template>