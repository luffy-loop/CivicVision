import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createServer } from 'vite'

process.env.VITE_API_URL = 'https://api.example.test/'
let vite
let api
let citizenUtils
let saveAuthoritySession
let clearAuthoritySession
const originalFetch = globalThis.fetch
const originalSessionStorage = globalThis.sessionStorage
const originalWindow = globalThis.window
const storage = new Map()

before(async () => {
  vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  ;({ api, saveAuthoritySession, clearAuthoritySession } = await vite.ssrLoadModule('/src/api.ts'))
  citizenUtils = await vite.ssrLoadModule('/src/citizen-utils.ts')
  globalThis.sessionStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) }
  globalThis.window = { setTimeout, clearTimeout, dispatchEvent() {} }
})

after(async () => {
  globalThis.fetch = originalFetch
  globalThis.sessionStorage = originalSessionStorage
  globalThis.window = originalWindow
  await vite?.close()
})

test('normalizes API base URL and attaches authority session', async () => {
  saveAuthoritySession('signed-session')
  let request
  globalThis.fetch = async (url, init) => {
    request = { url, init }
    return new Response(JSON.stringify({ status: 'ok', mode: 'demo' }), { headers: { 'content-type': 'application/json' } })
  }
  assert.deepEqual(await api.health(), { status: 'ok', mode: 'demo' })
  assert.equal(request.url, 'https://api.example.test/api/health')
  assert.equal(new Headers(request.init.headers).get('authorization'), 'Bearer signed-session')
  clearAuthoritySession()
})

test('turns JSON and non-JSON API failures into useful errors', async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Database is not ready' }), { status: 503, headers: { 'content-type': 'application/json' } })
  await assert.rejects(api.health(), /Database is not ready/)
  globalThis.fetch = async () => new Response('<html>proxy error</html>', { status: 500, headers: { 'content-type': 'text/html' } })
  await assert.rejects(api.health(), /Request failed \(500\)/)
})

test('reports connection and timeout failures without leaking browser internals', async () => {
  globalThis.fetch = async () => { throw new TypeError('network details') }
  await assert.rejects(api.health(), /service could not be reached/i)
  const originalSetTimeout = window.setTimeout
  window.setTimeout = callback => { callback(); return 1 }
  globalThis.fetch = async (_url, init) => { if (init.signal.aborted) throw new DOMException('aborted', 'AbortError'); return new Response('{}') }
  await assert.rejects(api.health(), /request timed out/i)
  window.setTimeout = originalSetTimeout
})

test('validates citizen photo types and sizes', () => {
  assert.equal(citizenUtils.validateCitizenPhoto({ type: 'image/jpeg', size: 100 }), null)
  assert.match(citizenUtils.validateCitizenPhoto({ type: 'image/gif', size: 100 }), /JPG, PNG or WebP/)
  assert.match(citizenUtils.validateCitizenPhoto({ type: 'image/png', size: 9 * 1024 * 1024 }), /8 MB/)
})

test('maps camera and geolocation failures to actionable messages', () => {
  assert.match(citizenUtils.cameraFailureMessage('NotAllowedError'), /permission was denied/i)
  assert.match(citizenUtils.cameraFailureMessage('NotFoundError'), /No camera is available/i)
  assert.match(citizenUtils.locationFailureMessage(1), /permission was denied/i)
  assert.match(citizenUtils.locationFailureMessage(2), /could not be determined/i)
})
