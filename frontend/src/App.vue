<script setup>
import { ref, onMounted } from 'vue'
import './styles.css'

// Same origin in production; Vite proxies /api to the backend in development.
const API_BASE = '/api'

const duration = ref(null)
const loading = ref(false)
const error = ref('')
const works = ref([])
const searched = ref(false)

const allComposers = ref([])
const selectedComposers = ref([])
const verifiedOnly = ref(false)
const showComposers = ref(false)

const adminPanelOpen = ref(false)
const adminInput = ref('')
const adminSecret = ref(sessionStorage.getItem('adminSecret') || '')
const adminError = ref('')
const isAdmin = () => !!adminSecret.value

onMounted(async () => {
  try {
    const response = await fetch(`${API_BASE}/composers/`)
    if (!response.ok) throw new Error(`Server error: ${response.status}`)
    allComposers.value = await response.json()
  } catch {
    error.value = 'Could not reach the server. Please try again later.'
  }
})

// ── Search ─────────────────────────────────────────────────────
const search = async () => {
  if (!duration.value || duration.value < 1) {
    error.value = 'Enter how many minutes you’re running.'
    return
  }
  loading.value = true
  error.value = ''

  const params = new URLSearchParams({ run_duration: duration.value })
  if (verifiedOnly.value) params.set('verified_only', 'true')
  selectedComposers.value.forEach((c) => params.append('composers', c))

  try {
    // As admin, search also returns excluded works (greyed out), so they can be restored.
    const headers = isAdmin() ? { 'x-admin-secret': adminSecret.value } : {}
    const response = await fetch(`${API_BASE}/search/?${params}`, { headers })
    if (!response.ok) throw new Error(`Server error: ${response.status}`)
    works.value = await response.json()
    searched.value = true
  } catch {
    error.value = 'Something went wrong. Please try again.'
  } finally {
    loading.value = false
  }
}

const toggleComposer = (composer) => {
  const i = selectedComposers.value.indexOf(composer)
  if (i === -1) selectedComposers.value.push(composer)
  else selectedComposers.value.splice(i, 1)
}

const composersLabel = () => {
  const n = selectedComposers.value.length
  return n === 0 ? 'All composers' : n === 1 ? selectedComposers.value[0] : `${n} composers`
}

const formatDuration = (ms) => {
  const seconds = Math.round(ms / 1000)
  return `${Math.floor(seconds / 60)}′ ${String(seconds % 60).padStart(2, '0')}″`
}

// Keep "B‑flat" and "Hammer‑Klavier" on one line: non-breaking hyphens.
const noBreakHyphens = (title) => title.replace(/-/g, '‑')

// ── Admin ──────────────────────────────────────────────────────
const loginAdmin = async () => {
  const secret = adminInput.value.trim()
  if (!secret) return
  try {
    const response = await fetch(`${API_BASE}/admin/verify`, {
      headers: { 'x-admin-secret': secret },
    })
    if (response.status === 403) {
      adminError.value = 'Wrong password.'
      return
    }
    adminSecret.value = secret
    sessionStorage.setItem('adminSecret', secret)
    adminInput.value = ''
    adminError.value = ''
  } catch {
    adminError.value = 'Could not verify. Please try again.'
  }
}

const logoutAdmin = () => {
  adminSecret.value = ''
  sessionStorage.removeItem('adminSecret')
}

const toggleFlag = async (work, flag) => {
  try {
    const response = await fetch(`${API_BASE}/works/${work.id}/${flag}?value=${!work[flag]}`, {
      method: 'PATCH',
      headers: { 'x-admin-secret': adminSecret.value },
    })
    if (response.status === 403) {
      adminError.value = 'Wrong password.'
      logoutAdmin()
      return
    }
    if (!response.ok) throw new Error(`Server error: ${response.status}`)
    work[flag] = !work[flag]
  } catch {
    error.value = 'That didn’t work. Please try again.'
  }
}
</script>

<template>
  <main class="page">
    <header>
      <h1 class="wordmark">Symphony<span class="wordmark-2">2</span>Run</h1>
      <p class="tagline">Classical music for your run</p>
    </header>

    <form class="ask" @submit.prevent="search">
      <label class="ask-sentence" for="minutes">
        I’m running for
        <input
          id="minutes"
          v-model.number="duration"
          class="ask-minutes"
          type="number"
          inputmode="numeric"
          min="1"
          max="1440"
          placeholder="45"
        />
        minutes.
      </label>

      <div class="controls">
        <button type="submit" class="button-primary" :disabled="loading">
          {{ loading ? 'Finding…' : 'Find works' }}
        </button>
        <button
          type="button"
          class="button-secondary"
          :aria-expanded="showComposers"
          aria-controls="composers"
          @click="showComposers = !showComposers"
        >
          {{ composersLabel() }}
          <svg class="chevron" width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
            <path d="M2 3.5 5 6.5 8 3.5" fill="none" stroke="currentColor" stroke-width="1.4"
                  stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
        <label class="switch">
          <input v-model="verifiedOnly" type="checkbox" role="switch" />
          <span class="switch-track" aria-hidden="true"></span>
          Verified only
        </label>
      </div>

      <div v-if="showComposers" id="composers" class="composers">
        <button
          v-for="composer in allComposers"
          :key="composer"
          type="button"
          class="composer"
          :aria-pressed="selectedComposers.includes(composer)"
          @click="toggleComposer(composer)"
        >
          {{ composer }}
        </button>
      </div>

      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </form>

    <section v-if="works.length" :key="works.map((w) => w.id).join()" class="results" aria-label="Suggestions">
      <ul class="works">
        <li v-for="work in works" :key="work.id" class="card" :class="{ 'card--excluded': work.excluded }">
          <div class="card-main">
            <p class="card-composer">{{ work.composer }}</p>
            <h2 class="card-work">{{ noBreakHyphens(work.work) }}</h2>
            <p class="card-meta">
              <span class="card-length">{{ formatDuration(work.duration_ms) }}</span>
              <span v-if="work.verified" class="badge">✓ verified</span>
              <span v-if="work.excluded" class="badge badge--excluded">excluded</span>
            </p>
          </div>
          <div v-if="isAdmin()" class="card-admin">
            <button
              type="button"
              class="icon-button"
              :aria-pressed="work.verified"
              :title="work.verified ? 'Remove verified' : 'Mark as verified'"
              @click="toggleFlag(work, 'verified')"
            >
              ✓
            </button>
            <button
              type="button"
              class="icon-button icon-button--exclude"
              :aria-pressed="work.excluded"
              :title="work.excluded ? 'Show to visitors again' : 'Hide from visitors'"
              @click="toggleFlag(work, 'excluded')"
            >
              ✕
            </button>
          </div>
        </li>
      </ul>
    </section>
    <p v-else-if="searched && !loading" class="empty">
      No works of that length. Try a few minutes more or less, or other composers.
    </p>

    <footer class="footer">
      <p><span class="badge">✓ verified</span> I’ve run to this one myself.</p>
      <p>Lengths are typical recording times from MusicBrainz; your recording may differ by a minute or two.</p>
      <button
        type="button"
        class="admin-toggle"
        :aria-label="isAdmin() ? 'Admin' : 'Admin sign-in'"
        @click="adminPanelOpen = !adminPanelOpen"
      >
        ·
      </button>
      <div v-if="adminPanelOpen" class="admin">
        <template v-if="!isAdmin()">
          <input v-model="adminInput" type="password" placeholder="Admin password" @keydown.enter="loginAdmin" />
          <button type="button" class="link" @click="loginAdmin">Enter</button>
          <p v-if="adminError" class="error">{{ adminError }}</p>
        </template>
        <template v-else>
          <span>Admin mode</span>
          <button type="button" class="link" @click="logoutAdmin">Log out</button>
        </template>
      </div>
    </footer>
  </main>
</template>
