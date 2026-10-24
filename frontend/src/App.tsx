import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import {
  Activity, ArrowDownToLine, ArrowRight, BadgeCheck, BarChart3, Bell, Check, ChevronDown,
  CircleHelp, Clock3, CloudUpload, FileImage, Filter, Gauge, Globe2, HardHat, ImagePlus, LogOut, Camera,
  LayoutDashboard, MapPin, Menu, ScanSearch, Search, ShieldCheck, SlidersHorizontal,
  Sparkles, TrafficCone, TriangleAlert, UploadCloud, X, Zap,
} from 'lucide-react'
import { api, type Metrics, type Report, type ReportDetail } from './api'
import { makeAnnotatedImage } from './annotation'
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { CitizenReport, TrackReport } from './Citizen'
import { AuthorityGate, AuthorityLogin } from './AuthorityLogin'
import { clearAuthoritySession } from './api'

const nav = [
  { to:'/', label:'Overview', icon:LayoutDashboard },
  { to:'/scanner', label:'Road scanner', icon:ScanSearch },
  { to:'/reports', label:'Reports', icon:FileImage },
  { to:'/map', label:'Issue map', icon:MapPin },
  { to:'/analytics', label:'Analytics', icon:BarChart3 },
  { to:'/report', label:'Citizen report', icon:Camera },
]
const statusLabel: Record<string,string> = {
  pending_review:'Pending review', verified:'Verified', assigned:'Assigned', in_progress:'In progress', resolved:'Resolved', rejected:'Rejected',
}
const fmtDate = (date:string) => new Date(date).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'})
function StatusPill({status}:{status:string}) { return <span className={`status status-${status}`}>{statusLabel[status] || status.replace(/_/g,' ')}</span> }
function PriorityPill({priority}:{priority:string}) { return <span className={`priority priority-${priority}`}>{priority === 'review' ? 'Needs review' : `${priority} priority`}</span> }

function Shell({children}:{children:ReactNode}) {
  const location = useLocation()
  const [mobileOpen,setMobileOpen] = useState(false)
  const title = nav.find(n => n.to === location.pathname)?.label || 'CivicVision'
  return <div className="app-shell">
    <aside className={`sidebar ${mobileOpen?'sidebar-open':''}`}>
      <Link to="/" className="brand" onClick={()=>setMobileOpen(false)}>
        <span className="brand-mark"><TrafficCone size={22}/></span>
        <span><strong>CivicVision</strong><small>Community infrastructure</small></span>
      </Link>
      <div className="workspace-label">WORKSPACE</div>
      <nav className="nav-list">{nav.map(item=><NavLink key={item.to} to={item.to} end={item.to==='/'} onClick={()=>setMobileOpen(false)} className={({isActive})=>`nav-link ${isActive?'nav-active':''}`}><item.icon size={18}/><span>{item.label}</span>{item.to==='/reports'&&<span className="nav-count">•</span>}</NavLink>)}</nav>
      <div className="sidebar-bottom">
        <div className="help-card"><span className="help-icon"><ShieldCheck size={18}/></span><strong>Built for better streets</strong><p>Every report helps create a clearer picture of road conditions.</p><a href="https://arxiv.org/abs/2209.08538" target="_blank" rel="noreferrer">About the data <ArrowRight size={13}/></a></div>
        <div className="profile-row"><div className="avatar">CV</div><div><strong>Community workspace</strong><small>Local preview</small></div><ChevronDown size={15} className="muted-icon"/></div>
      </div>
    </aside>
    {mobileOpen&&<button aria-label="Close menu" className="mobile-scrim" onClick={()=>setMobileOpen(false)}/>}
    <main className="main-area">
      <header className="topbar"><button className="icon-button mobile-menu" onClick={()=>setMobileOpen(!mobileOpen)} aria-label="Toggle navigation"><Menu size={20}/></button><div className="breadcrumbs">Workspace <span>/</span> <strong>{title}</strong></div><div className="top-actions"><span className="system-status">Authority workspace</span><button className="icon-button" disabled title="Notifications are not connected" aria-label="Notifications unavailable"><Bell size={18}/></button><button className="signout-button" onClick={()=>{clearAuthoritySession();window.location.assign('/authority/login')}} aria-label="Sign out"><LogOut size={16}/><span>Sign out</span></button></div></header>
      <div className="page-wrap">{children}</div>
      <footer className="footer"><span>© 2026 CivicVision Community Tools</span><span>Road reports require human verification</span></footer>
    </main>
  </div>
}

function PageHeading({eyebrow,title,description,action}:{eyebrow:string;title:string;description:string;action?:React.ReactNode}) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action&&<div className="heading-action">{action}</div>}</div>
}
function StatCard({label,value,detail,icon:Icon,tone='blue'}:{label:string;value:string|number;detail:string;icon:typeof Activity;tone?:string}) {
  return <div className="stat-card"><div className={`stat-icon tone-${tone}`}><Icon size={19}/></div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-detail">{detail}</div></div>
}
function EmptyState({title,description,action}:{title:string;description:string;action?:React.ReactNode}) {
  return <div className="empty-state"><div className="empty-icon"><FileImage size={24}/></div><h3>{title}</h3><p>{description}</p>{action}</div>
}
function PrivateReportImage({id,title}:{id:number;title:string}) {
  const [src,setSrc]=useState('');const [failed,setFailed]=useState(false)
  useEffect(()=>{let active=true;let objectUrl='';api.reportImage(id).then(url=>{objectUrl=url;if(active)setSrc(url);else URL.revokeObjectURL(url)}).catch(()=>{if(active)setFailed(true)});return()=>{active=false;if(objectUrl)URL.revokeObjectURL(objectUrl)}},[id])
  if(failed)return <p className="field-help">Private evidence is unavailable.</p>
  return src?<img className="report-detail-image" src={src} alt={`Private evidence for ${title}`}/>:<div className="image-loading" role="status">Loading private evidence…</div>
}
function PrivateResolutionImage({reportId,evidenceId,title}:{reportId:number;evidenceId:number;title:string}) {
  const [src,setSrc]=useState('');const [failed,setFailed]=useState(false)
  useEffect(()=>{let active=true;let objectUrl='';api.evidenceImage(reportId,evidenceId).then(url=>{objectUrl=url;if(active)setSrc(url);else URL.revokeObjectURL(url)}).catch(()=>{if(active)setFailed(true)});return()=>{active=false;if(objectUrl)URL.revokeObjectURL(objectUrl)}},[reportId,evidenceId])
  return failed?<p className="field-help">Repair evidence is unavailable.</p>:src?<img className="report-detail-image" src={src} alt={`Repair completion evidence for ${title}`}/>:<div className="image-loading" role="status">Loading repair evidence…</div>
}
function ExportReportsButton({query}:{query:string}) {
  const [error,setError]=useState('')
  const download=async()=>{setError('');try{const blob=await api.exportReports(query);const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='civicvision-reports.csv';link.click();URL.revokeObjectURL(url)}catch(reason){setError(reason instanceof Error?reason.message:'Export failed')}}
  return <span><button className="button button-secondary" onClick={()=>void download()}><ArrowDownToLine size={16}/> Export CSV</button>{error&&<span className="field-help">{error}</span>}</span>
}
function ReportTable({reports,onStatus}:{reports:Report[];onStatus?:(r:Report)=>void}) {
  if(!reports.length) return <EmptyState title="No reports yet" description="Reports submitted through the scanner will appear here." action={<Link className="button button-secondary button-small" to="/scanner">Scan a road image <ArrowRight size={15}/></Link>}/>
  return <div className="table-scroll"><table><thead><tr><th>Report</th><th>Category</th><th>Priority</th><th>Status</th><th>Submitted</th><th></th></tr></thead><tbody>{reports.map(r=><tr key={r.id}><td><div className="report-id">CV-{String(r.id).padStart(4,'0')}</div><strong className="table-title">{r.title}</strong><small className="table-subtitle">{r.latitude!=null&&r.longitude!=null?`${r.latitude.toFixed(3)}, ${r.longitude.toFixed(3)}`:'Location not provided'}</small></td><td><span className="category-dot"/>{r.category}</td><td><PriorityPill priority={r.priority}/></td><td><StatusPill status={r.status}/></td><td>{fmtDate(r.created_at)}</td><td><button className="text-button" onClick={()=>onStatus?.(r)}>Review <ArrowRight size={14}/></button></td></tr>)}</tbody></table></div>
}
function Overview() {
  const [metrics,setMetrics] = useState<Metrics|null>(null); const [reports,setReports] = useState<Report[]>([]); const [error,setError] = useState('')
  const refresh=useCallback(async()=>{try{const [m,r]=await Promise.all([api.metrics(),api.reports()]);setMetrics(m);setReports(r.slice(0,5));setError('')}catch(e){setError(e instanceof Error?e.message:'Could not load the dashboard')}} ,[])
  useEffect(()=>{void refresh()},[refresh])
  return <><PageHeading eyebrow="COMMUNITY OVERVIEW" title="Good roads start with good data." description="A clear view of reported road conditions, review priorities and progress across your community." action={<Link className="button button-primary" to="/scanner"><ScanSearch size={17}/> Inspect a road <ArrowRight size={16}/></Link>}/>
    {error&&<div className="notice notice-warning"><TriangleAlert size={17}/><span>{error}. Start the API to load live data.</span><button className="text-button" onClick={()=>void refresh()}>Retry</button></div>}
    <div className="welcome-strip"><div className="welcome-icon"><Globe2 size={22}/></div><div><strong>A more informed view of local streets</strong><p>Submit a photo, review the findings and keep a record of what needs attention.</p></div><Link to="/reports" className="strip-link">View reports <ArrowRight size={15}/></Link></div>
    <div className="section-head"><div><h2>At a glance</h2><p>Current report activity</p></div><span className="muted-label"><Activity size={14}/> Updates when refreshed</span></div>
    <div className="stats-grid"><StatCard label="Total reports" value={metrics?.total??'—'} detail="All submitted reports" icon={FileImage}/><StatCard label="Awaiting review" value={metrics?.pending??'—'} detail="Needs human verification" icon={Clock3} tone="amber"/><StatCard label="In progress" value={metrics?.in_progress??'—'} detail="Being addressed" icon={HardHat} tone="violet"/><StatCard label="Resolved" value={metrics?.resolved??'—'} detail="Marked as resolved" icon={BadgeCheck} tone="green"/></div>
    <div className="content-grid"><section className="panel"><div className="panel-head"><div><h2>Recent reports</h2><p>Latest community submissions</p></div><Link to="/reports" className="text-button">View all <ArrowRight size={14}/></Link></div><ReportTable reports={reports}/></section><section className="panel side-panel"><div className="panel-head"><div><h2>Quick actions</h2><p>Pick up where you left off</p></div></div><div className="quick-actions"><Link to="/scanner" className="quick-action"><span className="quick-icon quick-blue"><ScanSearch size={19}/></span><span><strong>Inspect a road</strong><small>Analyze a photo for visible damage</small></span><ArrowRight size={16}/></Link><Link to="/reports" className="quick-action"><span className="quick-icon quick-amber"><SlidersHorizontal size={19}/></span><span><strong>Review submissions</strong><small>Check reports and update statuses</small></span><ArrowRight size={16}/></Link><Link to="/map" className="quick-action"><span className="quick-icon quick-green"><MapPin size={19}/></span><span><strong>Explore the map</strong><small>See reports with shared locations</small></span><ArrowRight size={16}/></Link></div><div className="tip-card"><div><Sparkles size={17}/><strong>Good to know</strong></div><p>Automated findings are suggestions, not official inspections. Verify each report before taking action.</p></div></section></div>
  </>
}
function Scanner() {
  const [file,setFile] = useState<File|null>(null); const [preview,setPreview] = useState(''); const [annotated,setAnnotated] = useState(''); const [loading,setLoading] = useState(false); const [result,setResult] = useState<Awaited<ReturnType<typeof api.scan>>|null>(null); const [error,setError] = useState(''); const [title,setTitle] = useState('Road condition report'); const [description,setDescription] = useState(''); const [category,setCategory] = useState(''); const [latitude,setLatitude] = useState(''); const [longitude,setLongitude] = useState(''); const [saving,setSaving] = useState(false); const [saved,setSaved] = useState<Report|null>(null)
  useEffect(()=>()=>{if(preview)URL.revokeObjectURL(preview)},[preview])
  useEffect(()=>()=>{if(annotated)URL.revokeObjectURL(annotated)},[annotated])
  const choose=(f?:File)=>{if(!f)return; if(!['image/jpeg','image/png','image/webp'].includes(f.type)){setError('Choose a JPG, PNG or WebP image.');return} if(f.size>8*1024*1024){setError('Image must be 8 MB or smaller.');return}setFile(f);setPreview(URL.createObjectURL(f));setResult(null);setAnnotated('');setError('');setSaved(null)}
  const scan=async()=>{if(!file)return;setLoading(true);setError('');setSaved(null);setAnnotated('');try{const scanned=await api.scan(file);setResult(scanned);if(scanned.mode==='model'&&scanned.detections.length){try{setAnnotated(await makeAnnotatedImage(preview,scanned.detections))}catch(e){setError(e instanceof Error?e.message:'Could not draw detection boxes')}}}catch(e){setError(e instanceof Error?e.message:'Scan failed')}finally{setLoading(false)}}
  const submit=async()=>{if(!file)return;let lat:number|undefined,lon:number|undefined;if(latitude.trim()||longitude.trim()){lat=Number(latitude);lon=Number(longitude);if(!latitude.trim()||!longitude.trim()||!Number.isFinite(lat)||!Number.isFinite(lon)||lat < -90||lat > 90||lon < -180||lon > 180){setError('Enter valid latitude and longitude, or leave both empty.');return}}setSaving(true);setError('');try{setSaved(await api.createReport(file,title,description,lat,lon,category))}catch(e){setError(e instanceof Error?e.message:'Could not submit report')}finally{setSaving(false)}}
  return <><PageHeading eyebrow="INSPECTION WORKSPACE" title="Road scanner" description="Upload a clear image of a road surface. Review the result before submitting a community report."/><div className="notice notice-info"><ShieldCheck size={18}/><div><strong>Image handling</strong><span>Location is optional. Images are validated and stored with reports; review the privacy and retention notes before sharing sensitive details.</span></div></div>
    <div className="scanner-layout"><section className="panel scanner-panel"><div className="panel-head"><div><h2>Image inspection</h2><p>JPG, PNG or WebP · Up to 8 MB</p></div><span className="step-chip">STEP 01</span></div>
      {!file?<label className="dropzone" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();choose(e.dataTransfer.files?.[0])}}><input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={e=>choose(e.target.files?.[0])}/><span className="drop-icon"><CloudUpload size={27}/></span><strong>Drop your road image here</strong><span>or click to browse or capture a photo</span><small>For best results, use a well-lit image with the road surface in focus.</small><span className="button button-secondary button-small"><ImagePlus size={15}/> Choose image</span></label>:<div className="preview-wrap"><img src={preview} alt="Selected road image"/><button className="remove-image" onClick={()=>{setFile(null);setPreview('');setResult(null);setAnnotated('');setSaved(null)}} aria-label="Remove image"><X size={16}/></button><div className="image-meta"><span><FileImage size={14}/>{file.name}</span><span>{(file.size/1024/1024).toFixed(2)} MB</span></div></div>}
      {error&&<div className="inline-error"><TriangleAlert size={16}/>{error}</div>}
      <div className="scanner-actions"><button className="button button-primary" disabled={!file||loading} onClick={()=>void scan()}>{loading?<><span className="spinner"/>Inspecting image…</>:<><ScanSearch size={17}/> Inspect image</>}</button>{file&&<button className="button button-ghost" onClick={()=>{setFile(null);setPreview('');setResult(null);setError('')}}>Clear</button>}</div>
      {result&&<div className="scan-result"><div className="result-heading"><div><span className="eyebrow">INSPECTION RESULT</span><h3>{result.mode==='demo'?'Scanner is ready':'Analysis complete'}</h3></div><span className={`mode-chip ${result.mode==='demo'?'mode-demo':'mode-model'}`}>{result.mode==='demo'?'Demo mode':'Configured model'}</span></div><p className="result-note">{result.note}</p><div className="result-stats"><div><strong>{result.detections.length}</strong><span>Detections</span></div><div><strong>{result.image_width} × {result.image_height}</strong><span>Image dimensions</span></div><div><strong>{result.mode==='demo'?'Not run':`${Math.round(result.inference_ms)} ms`}</strong><span>{result.mode==='demo'?'Model status':'Inference time'}</span></div></div>{result.mode==='model'&&<p className="field-help">Model version: {result.model_version||'Unversioned'}</p>}{annotated&&<div className="annotated-preview"><img src={annotated} alt="Inspection image with detection boxes"/><a className="button button-secondary button-small" href={annotated} download={`civicvision-inspection-${Date.now()}.jpg`}><ArrowDownToLine size={14}/> Download annotated image</a></div>}{result.detections.length>0&&<div className="detection-list">{result.detections.map((d,i)=><div className="detection-row" key={`${d.label}-${i}`}><span className="detection-number">{i+1}</span><span>{d.label}</span><strong>{(d.confidence*100).toFixed(1)}%</strong></div>)}</div>}</div>}
    </section>
    <section className="panel submit-panel"><div className="panel-head"><div><h2>Submit a report</h2><p>Save the issue for community review</p></div><span className="step-chip">STEP 02</span></div>
      <div className="form-stack"><label>Report title<input value={title} maxLength={140} onChange={e=>setTitle(e.target.value)} placeholder="e.g. Pothole near main entrance"/></label><label>Issue category<select value={category} onChange={e=>setCategory(e.target.value)}><option value="">Use model finding or leave unclassified</option><option value="pothole">Pothole</option><option value="crack">Crack</option><option value="other">Other road issue</option><option value="unknown">Unclassified</option></select></label><label>Description <span className="optional">Optional</span><textarea value={description} onChange={e=>setDescription(e.target.value)} maxLength={3000} rows={4} placeholder="Describe what you noticed and nearby landmarks…"/></label><div className="field-help">{description.length}/3000 characters</div><div className="form-section-label"><MapPin size={15}/> Location <span className="optional">Optional</span></div><div className="form-two"><label>Latitude<input inputMode="decimal" value={latitude} onChange={e=>setLatitude(e.target.value)} placeholder="17.3850"/></label><label>Longitude<input inputMode="decimal" value={longitude} onChange={e=>setLongitude(e.target.value)} placeholder="78.4867"/></label></div><p className="field-help">Coordinates are stored only when both are provided. Use a location you have permission to share.</p>
      <button className="button button-primary button-full" disabled={!file||saving} onClick={()=>void submit()}>{saving?<><span className="spinner"/>Submitting report…</>:<><ArrowDownToLine size={17}/> Submit for review</>}</button>
      {saved&&<div className="success-card"><Check size={18}/><div><strong>Report CV-{String(saved.id).padStart(4,'0')} submitted</strong><p>It is waiting for human review. The detector mode is {saved.detector_mode}.</p><Link to="/reports">View reports <ArrowRight size={14}/></Link></div></div>}
      <div className="submit-footnote"><ShieldCheck size={15}/> Submissions are stored for review; no municipality is contacted automatically.</div></div>
    </section></div>
  </>
}
function Reports() {
  const [reports,setReports]=useState<Report[]>([])
  const [hasNext,setHasNext]=useState(false)
  const [status,setStatus]=useState('')
  const [category,setCategory]=useState('')
  const [search,setSearch]=useState('')
  const [offset,setOffset]=useState(0)
  const [loading,setLoading]=useState(true)
  const [error,setError]=useState('')
  const [selected,setSelected]=useState<Report|null>(null)
  const [detail,setDetail]=useState<ReportDetail|null>(null)
  const [saving,setSaving]=useState(false)
  const [team,setTeam]=useState('')
  const [repairFile,setRepairFile]=useState<File|null>(null)
  const [repairNote,setRepairNote]=useState('')

  const load=useCallback(async()=>{setLoading(true);try{const page=await api.reports(status,category,search,offset,26);setReports(page.slice(0,25));setHasNext(page.length>25);setError('')}catch(e){setError(e instanceof Error?e.message:'Could not load reports')}finally{setLoading(false)}},[status,category,search,offset])
  useEffect(()=>{void load()},[load])
  useEffect(()=>{if(!selected)return;let current=true;setDetail(null);setTeam(selected.assigned_team||'');api.report(selected.id).then(value=>{if(current)setDetail(value)}).catch(e=>{if(current)setError(e instanceof Error?e.message:'Could not load report details')});return()=>{current=false}},[selected?.id])
  useEffect(()=>{if(!selected)return;const onKey=(event:KeyboardEvent)=>{if(event.key==='Escape')setSelected(null)};window.addEventListener('keydown',onKey);return()=>window.removeEventListener('keydown',onKey)},[selected])

  const exportQuery=new URLSearchParams({...(status?{status}:{}),...(category?{category}:{}),...(search?{search}:{})}).toString()
  const update=async(next:string)=>{if(!selected)return;setSaving(true);try{await api.updateStatus(selected.id,next,'Status updated from review workspace');setSelected(null);await load()}catch(e){setError(e instanceof Error?e.message:'Could not update status')}finally{setSaving(false)}}
  const assign=async()=>{if(!selected)return;setSaving(true);try{await api.assignReport(selected.id,team);setSelected(null);await load()}catch(e){setError(e instanceof Error?e.message:'Could not assign this report')}finally{setSaving(false)}}
  const resolve=async()=>{if(!selected||!repairFile)return;setSaving(true);try{await api.addResolutionEvidence(selected.id,repairFile,repairNote);setSelected(null);setRepairFile(null);setRepairNote('');await load()}catch(e){setError(e instanceof Error?e.message:'Could not submit repair evidence')}finally{setSaving(false)}}
  const close=()=>{setSelected(null);setRepairFile(null);setRepairNote('')}
  const options=selected?.status==='pending_review'?['pending_review','verified','rejected']:selected?.status==='verified'?['verified','in_progress','rejected']:selected?.status==='assigned'?['assigned','in_progress','verified']:selected?.status==='in_progress'?['in_progress','verified']:selected?.status==='resolved'?['resolved','in_progress']:['rejected','pending_review']
  const previousStatus=reports.find(item=>item.id===selected?.id)?.status

  return <>
    <PageHeading eyebrow="COMMUNITY SUBMISSIONS" title="Reports" description="Review submissions, assign repair teams and record completion evidence." action={<ExportReportsButton query={exportQuery}/>}/>
    <section className="panel">
      <div className="panel-head report-toolbar"><div><h2>Reports</h2><p>{reports.length} report{reports.length===1?'':'s'} on this page</p></div><div className="report-filters">
        <label className="search-box"><Search size={15}/><input value={search} onChange={e=>{setSearch(e.target.value);setOffset(0)}} placeholder="Search reports" aria-label="Search reports"/></label>
        <label className="filter-select"><Filter size={15}/><select aria-label="Filter by status" value={status} onChange={e=>{setStatus(e.target.value);setOffset(0)}}><option value="">All statuses</option><option value="pending_review">Pending review</option><option value="verified">Verified</option><option value="assigned">Assigned</option><option value="in_progress">In progress</option><option value="resolved">Resolved</option><option value="rejected">Rejected</option></select></label>
        <label className="filter-select"><select aria-label="Filter by category" value={category} onChange={e=>{setCategory(e.target.value);setOffset(0)}}><option value="">All categories</option><option value="pothole">Pothole</option><option value="crack">Crack</option><option value="other">Other</option><option value="unknown">Unclassified</option></select></label>
      </div></div>
      {error&&<div className="inline-error" role="alert">{error}</div>}
      {loading?<div className="loading-row"><span className="spinner"/> Loading reports…</div>:<ReportTable reports={reports} onStatus={setSelected}/>}
      <div className="pagination"><button className="button button-secondary button-small" disabled={offset===0||loading} onClick={()=>setOffset(Math.max(0,offset-25))}>Previous</button><span>Page {offset/25+1}</span><button className="button button-secondary button-small" disabled={!hasNext||loading} onClick={()=>setOffset(offset+25)}>Next</button></div>
    </section>
    {selected&&<div className="modal-backdrop" onClick={close}><div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="report-modal-title" onClick={e=>e.stopPropagation()}>
      <div className="modal-head"><div><span className="eyebrow">REPORT CV-{String(selected.id).padStart(4,'0')}</span><h2 id="report-modal-title">{selected.title}</h2></div><button className="icon-button" onClick={close} aria-label="Close report details"><X size={18}/></button></div>
      {selected.image_url&&<PrivateReportImage id={selected.id} title={selected.title}/>}<p>{selected.description||'No additional description provided.'}</p>
      <div className="detail-grid"><div><small>Category</small><strong>{selected.category}</strong></div><div><small>Priority</small><strong>{selected.priority}</strong></div><div><small>Submitted</small><strong>{fmtDate(selected.created_at)}</strong></div><div><small>Detector</small><strong>{selected.detector_mode}{selected.model_version?` · ${selected.model_version}`:''}</strong></div></div>
      {selected.priority_reason&&<p className="field-help priority-reason">{selected.priority_reason} Priority is a triage hint, not an engineering safety assessment.</p>}
      {selected.assigned_team&&<div className="assignment-summary"><strong>Assigned to {selected.assigned_team}</strong><span>{selected.assigned_by?`by ${selected.assigned_by}`:''}{selected.assigned_at?` · ${fmtDate(selected.assigned_at)}`:''}</span></div>}
      <h3 className="history-heading">Status history</h3>{detail?<ol className="history-list">{detail.history.map((event,index)=><li key={`${event.created_at}-${index}`}><StatusPill status={event.new_status}/><span>{event.note||'Status changed'}{event.actor&&<small className="history-actor"> by {event.actor}</small>}</span><time>{fmtDate(event.created_at)}</time></li>)}</ol>:<div className="loading-row"><span className="spinner"/> Loading history…</div>}
      <label className="form-label">Update status<select className="modal-select" value={selected.status} onChange={e=>setSelected({...selected,status:e.target.value})}>{options?.map(value=><option key={value} value={value}>{statusLabel[value]}</option>)}</select></label>
      <div className="modal-actions"><button className="button button-secondary" onClick={close}>Close</button><button className="button button-primary" disabled={saving||selected.status===previousStatus||selected.status==='assigned'||selected.status==='resolved'} onClick={()=>void update(selected.status)}>{saving?<span className="spinner"/>:<Check size={16}/>} Save status</button></div>
      {(selected.status==='verified'||selected.status==='assigned')&&<section className="workflow-card"><h3>Assign a repair team</h3><p>Record the responsible department or team in the report history.</p><label className="citizen-field">Team or department<input value={team} maxLength={120} onChange={e=>setTeam(e.target.value)} placeholder="e.g. Ward 12 roads team"/></label><button className="button button-secondary" disabled={saving||!team.trim()} onClick={()=>void assign()}>{selected.assigned_team?'Update assignment':'Assign team'}</button></section>}
      {selected.status==='in_progress'&&<section className="workflow-card"><h3>Repair completion</h3><p>Attach an after-repair photo and note. The report becomes resolved after evidence is stored.</p><label className="citizen-field">Completion photo<input type="file" accept="image/jpeg,image/png,image/webp" onChange={event=>setRepairFile(event.target.files?.[0]||null)}/></label><label className="citizen-field">Completion note<textarea rows={3} maxLength={1000} value={repairNote} onChange={event=>setRepairNote(event.target.value)} placeholder="Work completed and any verification details…"/></label><button className="button button-primary" disabled={saving||!repairFile} onClick={()=>void resolve()}>{saving?'Saving evidence…':'Submit evidence and resolve'}</button></section>}
      {detail?.resolution_evidence?.length? <section className="workflow-card"><h3>Repair evidence</h3>{detail.resolution_evidence.map(item=><div key={item.id}><PrivateResolutionImage reportId={selected.id} evidenceId={item.id} title={selected.title}/><p>{item.note||'No completion note.'} · {item.submitted_by} · {fmtDate(item.created_at)}</p></div>)}</section>:null}
      <p className="modal-note"><ShieldCheck size={14}/> Actions are attributed to the signed-in authority account. Resolution requires repair evidence.</p>
    </div></div>}
  </>
}
function FitReportBounds({points}:{points:[number,number][]}) {
  const map=useMap()
  useEffect(()=>{if(points.length>1)map.fitBounds(points,{padding:[28,28],maxZoom:14});else if(points.length===1)map.setView(points[0],12)},[map,points])
  return null
}
function IssueMap() {
  const [reports,setReports]=useState<Report[]>([]);const [error,setError]=useState('');const [selected,setSelected]=useState<Report|null>(null);const [status,setStatus]=useState('');const [category,setCategory]=useState('');const [loading,setLoading]=useState(true)
  const load=useCallback(async()=>{setLoading(true);setSelected(null);try{setReports(await api.reports(status,category,'',0,100));setError('')}catch(e){setError(e instanceof Error?e.message:'Could not load reports')}finally{setLoading(false)}},[status,category])
  useEffect(()=>{void load()},[load])
  const located=useMemo(()=>reports.filter(r=>r.latitude!=null&&r.longitude!=null),[reports]);const points=useMemo(()=>located.map(r=>[r.latitude!,r.longitude!] as [number,number]),[located])
  return <><PageHeading eyebrow="GEOGRAPHIC OVERVIEW" title="Issue map" description="Explore reports with voluntarily shared coordinates. Locations are provided by submitters and may need verification."/>{error&&<div className="inline-error" role="alert">{error}<button className="text-button" onClick={()=>void load()}>Retry</button></div>}<div className="map-layout"><section className="panel map-panel"><div className="panel-head map-toolbar"><div><h2>Reported locations</h2><p>{located.length} reports with coordinates on this page</p></div><div className="map-filters"><label className="filter-select"><span className="sr-only">Filter map by status</span><select value={status} onChange={e=>setStatus(e.target.value)} aria-label="Filter map by status"><option value="">All statuses</option>{Object.entries(statusLabel).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><label className="filter-select"><span className="sr-only">Filter map by category</span><select value={category} onChange={e=>setCategory(e.target.value)} aria-label="Filter map by category"><option value="">All categories</option><option value="pothole">Pothole</option><option value="crack">Crack</option><option value="other">Other</option><option value="unknown">Unclassified</option></select></label></div></div><div className="real-map">{loading?<div className="loading-row"><span className="spinner"/> Loading mapped reports…</div>:error?<div className="map-empty"><TriangleAlert size={24}/><strong>Map data could not be loaded</strong><button className="button button-secondary button-small" onClick={()=>void load()}>Retry</button></div>:located.length ? <MapContainer center={[located[0].latitude!, located[0].longitude!]} zoom={12} scrollWheelZoom className="leaflet-map"><TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" /><FitReportBounds points={points}/>{located.map(r=><CircleMarker key={r.id} center={[r.latitude!,r.longitude!]} radius={selected?.id===r.id?10:7} pathOptions={{color:'#6F4E37',fillColor:'#6F4E37',fillOpacity:.85}} eventHandlers={{click:()=>setSelected(r)}}><Popup><strong>CV-{String(r.id).padStart(4,'0')}</strong><br/>{r.title}<br/>{r.category} · {statusLabel[r.status]||r.status}<br/><Link to="/reports">Open report list</Link></Popup></CircleMarker>)}</MapContainer> : <div className="map-empty"><MapPin size={25}/><strong>No report locations in this view</strong><span>Reports without shared coordinates cannot appear on the map. Try changing the filters.</span></div>}</div><div className="map-foot"><span>{located.length} mapped reports shown</span><span>Map tiles © OpenStreetMap contributors</span></div></section><section className="panel map-detail"><div className="panel-head"><div><h2>Selected report</h2><p>Choose a marker to inspect details</p></div></div>{selected?<div className="selected-report"><div className="selected-pin"><MapPin size={21}/></div>{selected.image_url&&<PrivateReportImage id={selected.id} title={selected.title}/>}<span className="eyebrow">CV-{String(selected.id).padStart(4,'0')}</span><h3>{selected.title}</h3><p>{selected.description||'No additional description provided.'}</p><StatusPill status={selected.status}/><div className="detail-grid"><div><small>Category</small><strong>{selected.category}</strong></div><div><small>Priority</small><strong>{selected.priority}</strong></div><div><small>Latitude</small><strong>{selected.latitude?.toFixed(5)}</strong></div><div><small>Longitude</small><strong>{selected.longitude?.toFixed(5)}</strong></div></div><Link to="/reports" className="button button-secondary button-full">Open reports <ArrowRight size={15}/></Link></div>:<EmptyState title="No report selected" description="Select a marker to see the report summary."/>}</section></div></>
}
function Analytics() {
  const [metrics,setMetrics]=useState<Metrics|null>(null);const [reports,setReports]=useState<Report[]>([]);const [error,setError]=useState('')
  useEffect(()=>{Promise.all([api.metrics(),api.reports()]).then(([m,r])=>{setMetrics(m);setReports(r)}).catch(e=>setError(e instanceof Error?e.message:'Could not load analytics'))},[])
  const categories=Object.entries(metrics?.by_category||{});const statuses=Object.entries(metrics?.by_status||{})
  const max=Math.max(1,...categories.map(([,v])=>v))
  return <><PageHeading eyebrow="REPORT INTELLIGENCE" title="Analytics" description="Understand report volume, issue categories and progress using submitted community data." action={<ExportReportsButton query=""/>}/>{error&&<div className="notice notice-warning"><TriangleAlert size={17}/>{error}</div>}<div className="stats-grid"><StatCard label="Total reports" value={metrics?.total??'—'} detail="All recorded submissions" icon={FileImage}/><StatCard label="High priority" value={metrics?.high_priority??'—'} detail="Rule-based triage only" icon={Gauge} tone="amber"/><StatCard label="Resolved" value={metrics?.resolved??'—'} detail="Marked resolved by reviewer" icon={BadgeCheck} tone="green"/><StatCard label="Open work" value={(metrics?.pending??0)+(metrics?.in_progress??0)||'—'} detail="Pending review or in progress" icon={Activity} tone="violet"/></div><div className="analytics-grid"><section className="panel"><div className="panel-head"><div><h2>Reports by category</h2><p>Distribution of recorded issue labels</p></div></div>{categories.length? <div className="bar-list">{categories.map(([label,value])=><div className="bar-item" key={label}><div className="bar-label"><span>{label}</span><strong>{value}</strong></div><div className="bar-track"><div className="bar-fill" style={{width:`${value/max*100}%`}}/></div></div>)}</div>:<EmptyState title="Not enough data yet" description="Category charts will appear after reports are submitted."/>}</section><section className="panel"><div className="panel-head"><div><h2>Status breakdown</h2><p>Current workflow state</p></div></div>{statuses.length?<div className="status-breakdown">{statuses.map(([label,value])=><div className="status-break-row" key={label}><span className="status-key"><span className={`status-dot dot-${label}`}/>{statusLabel[label]||label}</span><strong>{value}</strong><span className="status-percent">{metrics?.total?Math.round(value/metrics.total*100):0}%</span></div>)}</div>:<EmptyState title="No status data" description="Status statistics appear here when reports exist."/>}</section></div><section className="panel"><div className="panel-head"><div><h2>Recent activity</h2><p>Latest reports recorded by the service</p></div></div><ReportTable reports={reports.slice(0,8)}/></section><p className="analytics-disclaimer"><CircleHelp size={15}/> These statistics reflect reports stored in this application, not verified city-wide road conditions or official municipal data.</p></>
}
function NotFound(){return <EmptyState title="Page not found" description="The page you're looking for doesn't exist." action={<Link to="/" className="button button-primary">Return to overview</Link>}/>}

function AuthorityWorkspace(){return <AuthorityGate><Shell><Routes><Route path="/" element={<Overview/>}/><Route path="/scanner" element={<Scanner/>}/><Route path="/reports" element={<Reports/>}/><Route path="/map" element={<IssueMap/>}/><Route path="/analytics" element={<Analytics/>}/><Route path="*" element={<NotFound/>}/></Routes></Shell></AuthorityGate>}

export default function App() {
  return <Routes><Route path="/report" element={<CitizenReport/>}/><Route path="/track" element={<TrackReport/>}/><Route path="/track/:id" element={<TrackReport/>}/><Route path="/authority/login" element={<AuthorityLogin/>}/><Route path="*" element={<AuthorityWorkspace/>}/></Routes>
}
