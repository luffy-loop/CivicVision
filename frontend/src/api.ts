export type Report = {
  id: number; title: string; description: string; category: string; status: string;
  priority: string; confidence: number | null; latitude: number | null; longitude: number | null;
  image_name: string | null; detector_mode: string; model_version: string | null; inference_ms: number | null;
  detections: {label:string;confidence:number;box:number[]}[]; location_accuracy_m: number | null;
  priority_reason: string | null; assigned_team: string | null; assigned_at: string | null; assigned_by: string | null;
  created_at: string; updated_at: string;
  image_url: string | null;
}
export type ReportCreated = Report & { tracking_token: string }
export type ReportDetail = Report & { history: { old_status: string|null; new_status: string; note: string; actor?:string|null; created_at: string }[]; resolution_evidence: {id:number;note:string;submitted_by:string;created_at:string;image_url:string}[] }
export type Tracking = Pick<Report,'id'|'title'|'category'|'status'|'created_at'|'updated_at'> & {history:{old_status:string|null;new_status:string;note:string;created_at:string}[]}
export type Metrics = {
  total: number; pending: number; verified:number; assigned:number; in_progress: number; resolved: number; high_priority: number;
  by_category: Record<string, number>; by_status: Record<string, number>;
}
const API_BASE = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '')
const TOKEN_KEY = 'civicvision-authority-session'
export function saveAuthoritySession(token: string) { sessionStorage.setItem(TOKEN_KEY, token) }
export function clearAuthoritySession() { sessionStorage.removeItem(TOKEN_KEY) }

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  const token = sessionStorage.getItem(TOKEN_KEY)
  if (token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`)
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), 60_000)
  let response: Response
  try {
    response = await fetch(`${API_BASE}${url}`, { ...init, headers, signal: init?.signal ?? controller.signal })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw new Error('The request timed out. Check your connection and retry.')
    throw new Error('The service could not be reached. Check your connection and try again.')
  } finally {
    window.clearTimeout(timer)
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: string }
    if (response.status === 401 && url !== '/api/auth/login' && token) {
      clearAuthoritySession()
      window.dispatchEvent(new Event('civicvision-auth-expired'))
    }
    throw new Error(body.detail || `Request failed (${response.status}). Please retry.`)
  }
  if (response.status === 204) return undefined as T
  if (!response.headers.get('content-type')?.includes('application/json')) throw new Error(`The service returned an unexpected response (${response.status}). Check the API URL and try again.`)
  return response.json() as Promise<T>
}
export const api = {
  health: () => request<{status:string; mode:string}>('/api/health'),
  metrics: () => request<Metrics>('/api/metrics'),
  reports: (status = '', category = '', search = '', offset = 0, limit = 25) => {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    if (category) params.set('category', category)
    if (search.trim()) params.set('search', search.trim())
    params.set('offset', String(offset)); params.set('limit', String(limit))
    return request<Report[]>(`/api/reports?${params.toString()}`)
  },
  report: (id:number) => request<ReportDetail>(`/api/reports/${id}`),
  scan: (file: File) => {
    const form = new FormData(); form.append('file', file)
    return request<{mode:string; model_version:string|null; inference_ms:number; image_width:number; image_height:number; detections:{label:string;confidence:number;box:number[]}[];note:string}>('/api/scan', { method:'POST', body:form })
  },
  createReport: (file: File, title: string, description: string, latitude?: number, longitude?: number, category?: string, accuracy?: number, locationCapturedAt?: string, idempotencyKey?: string) => {
    const form = new FormData(); form.append('file', file); form.append('title', title); form.append('description', description)
    if (category) form.append('category_override', category)
    if (latitude !== undefined && longitude !== undefined) { form.append('latitude', String(latitude)); form.append('longitude', String(longitude)) }
    if (accuracy !== undefined && latitude !== undefined && longitude !== undefined) form.append('location_accuracy_m', String(accuracy))
    if (locationCapturedAt && latitude !== undefined && longitude !== undefined) form.append('location_captured_at', locationCapturedAt)
    const headers = idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined
    return request<ReportCreated>('/api/reports', { method:'POST', body:form, headers })
  },
  track: (id:number, token:string) => request<Tracking>(`/api/reports/${id}/tracking`, {headers:{'X-Tracking-Token':token}}),
  login: (username:string,password:string) => request<{access_token:string;expires_in:number;username:string;role:string}>('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password})}),
  currentAuthority: () => request<{username:string;role:string}>('/api/auth/me'),
  reportImage: async (id:number) => {
    const headers = new Headers()
    const token = sessionStorage.getItem(TOKEN_KEY)
    if (token) headers.set('Authorization', `Bearer ${token}`)
    const response = await fetch(`${API_BASE}/api/reports/${id}/image`,{headers})
    if (!response.ok) throw new Error('Could not load private report evidence.')
    return URL.createObjectURL(await response.blob())
  },
  evidenceImage: async (reportId:number,evidenceId:number) => {
    const headers = new Headers()
    const token = sessionStorage.getItem(TOKEN_KEY)
    if (token) headers.set('Authorization', `Bearer ${token}`)
    const response = await fetch(`${API_BASE}/api/reports/${reportId}/resolution-evidence/${evidenceId}/image`,{headers})
    if (!response.ok) throw new Error('Could not load private repair evidence.')
    return URL.createObjectURL(await response.blob())
  },
  exportReports: async (query:string) => {
    const headers = new Headers()
    const token = sessionStorage.getItem(TOKEN_KEY)
    if (token) headers.set('Authorization', `Bearer ${token}`)
    const response = await fetch(`${API_BASE}/api/reports-export.csv?${query}`, {headers})
    if (!response.ok) throw new Error('Could not export reports. Check your authority session and retry.')
    return response.blob()
  },
  updateStatus: (id:number, status:string, note='') => {
    const form = new FormData(); form.append('status', status); form.append('note', note)
    return request<Report>(`/api/reports/${id}/status`, { method:'PATCH', body:form })
  },
  assignReport: (id:number,team:string) => request<Report>(`/api/reports/${id}/assignment`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({team})}),
  addResolutionEvidence: (id:number,file:File,note:string) => {const form=new FormData();form.append('file',file);form.append('note',note);return request<ReportDetail>(`/api/reports/${id}/resolution-evidence`,{method:'POST',body:form})},
}
