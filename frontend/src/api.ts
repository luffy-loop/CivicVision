export type Report = {
  id: number; title: string; description: string; category: string; status: string;
  priority: string; confidence: number | null; latitude: number | null; longitude: number | null;
  image_name: string | null; detector_mode: string; created_at: string; updated_at: string;
  image_url: string | null;
}
export type ReportDetail = Report & { history: { old_status: string|null; new_status: string; note: string; created_at: string }[] }
export type Metrics = {
  total: number; pending: number; in_progress: number; resolved: number; high_priority: number;
  by_category: Record<string, number>; by_status: Record<string, number>;
}
const API_BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`, init)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${response.status})`)
  }
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
  createReport: (file: File, title: string, description: string, latitude?: number, longitude?: number, category?: string) => {
    const form = new FormData(); form.append('file', file); form.append('title', title); form.append('description', description)
    if (category) form.append('category_override', category)
    if (latitude !== undefined && longitude !== undefined) { form.append('latitude', String(latitude)); form.append('longitude', String(longitude)) }
    return request<Report>('/api/reports', { method:'POST', body:form })
  },
  updateStatus: (id:number, status:string, note='', reviewerKey='') => {
    const form = new FormData(); form.append('status', status); form.append('note', note)
    return request<Report>(`/api/reports/${id}/status`, { method:'PATCH', body:form, headers:{'X-Reviewer-Key':reviewerKey} })
  },
}
