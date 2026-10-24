import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Camera, Check, Clipboard, Crosshair, ImagePlus, MapPin, RotateCcw, ShieldCheck, TrafficCone, TriangleAlert, UploadCloud, X } from 'lucide-react'
import { api, type ReportCreated, type Tracking } from './api'
import { cameraFailureMessage, locationFailureMessage, validateCitizenPhoto } from './citizen-utils'

const TOKEN_PREFIX = 'civicvision-tracking-'

function useCamera() {
  const video = useRef<HTMLVideoElement>(null)
  const stream = useRef<MediaStream | null>(null)
  const [error, setError] = useState('')
  const [starting, setStarting] = useState(false)
  const [facing, setFacing] = useState<'environment'|'user'>('environment')
  const [torchAvailable, setTorchAvailable] = useState(false)
  const [torch, setTorch] = useState(false)
  const stop = useCallback(() => {
    stream.current?.getTracks().forEach(track => track.stop())
    stream.current = null
    setTorchAvailable(false)
    setTorch(false)
  }, [])
  const start = useCallback(async (direction = facing) => {
    setError('')
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setError('Camera access requires a supported browser on HTTPS or localhost. You can still choose a photo below.')
      return
    }
    stop()
    setStarting(true)
    try {
      const next = await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:direction},width:{ideal:1920},height:{ideal:1080}}})
      stream.current = next
      const track = next.getVideoTracks()[0]
      const caps = typeof track.getCapabilities === 'function' ? track.getCapabilities() as MediaTrackCapabilities & {torch?:boolean} : {}
      setTorchAvailable(Boolean(caps.torch))
      setFacing(direction)
      if (video.current) { video.current.srcObject = next; await video.current.play() }
    } catch (reason) {
      stop()
      const name = reason instanceof DOMException ? reason.name : ''
      setError(cameraFailureMessage(name))
    } finally { setStarting(false) }
  }, [facing, stop])
  const toggleTorch = useCallback(async () => {
    const track = stream.current?.getVideoTracks()[0]
    if (!track || !torchAvailable) return
    try {
      await track.applyConstraints({advanced:[{torch:!torch} as MediaTrackConstraintSet]})
      setTorch(value => !value)
    } catch { setError('This camera could not change its flash setting.') }
  }, [torch, torchAvailable])
  useEffect(() => () => stop(), [stop])
  return {video,stream,start,stop,error,setError,starting,facing,setFacing,torchAvailable,torch,toggleTorch}
}

export function CitizenReport() {
  const navigate = useNavigate()
  const camera = useCamera()
  const fileInput = useRef<HTMLInputElement>(null)
  const submitLock = useRef(false)
  const submissionKey = useRef('')
  const [file,setFile] = useState<File|null>(null)
  const [preview,setPreview] = useState('')
  const [scan,setScan] = useState<Awaited<ReturnType<typeof api.scan>>|null>(null)
  const [scanning,setScanning] = useState(false)
  const [saving,setSaving] = useState(false)
  const [error,setError] = useState('')
  const [title,setTitle] = useState('Road damage report')
  const [description,setDescription] = useState('')
  const [category,setCategory] = useState('')
  const [lat,setLat] = useState('')
  const [lon,setLon] = useState('')
  const [accuracy,setAccuracy] = useState<number|null>(null)
  const [locationCapturedAt,setLocationCapturedAt] = useState('')
  const [locationState,setLocationState] = useState('Location has not been requested.')
  const [locating,setLocating] = useState(false)
  const [saved,setSaved] = useState<ReportCreated|null>(null)

  useEffect(() => { void camera.start('environment') }, [])

  useEffect(() => {
    if (!file) { setPreview(''); return }
    const url = URL.createObjectURL(file)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const setPhoto = useCallback(async (next?:File) => {
    if (!next) return
    const validationError = validateCitizenPhoto(next)
    if (validationError) { setError(validationError); return }
    camera.stop()
    setFile(next); setScan(null); setSaved(null); setError('')
    setScanning(true)
    try { setScan(await api.scan(next)) }
    catch (reason) { setError(reason instanceof Error ? `${reason.message} You can still submit the photo for human review.` : 'Detection was unavailable. You can still submit the photo for human review.') }
    finally { setScanning(false) }
  }, [camera.stop])

  const capture = useCallback(() => {
    const element = camera.video.current
    if (!element?.videoWidth || !element.videoHeight) { setError('Wait until the camera preview is ready, then capture again.'); return }
    const canvas = document.createElement('canvas')
    canvas.width = element.videoWidth; canvas.height = element.videoHeight
    const context = canvas.getContext('2d')
    if (!context) { setError('This browser could not prepare the captured image.'); return }
    context.drawImage(element,0,0)
    canvas.toBlob(blob => {
      if (!blob) { setError('The captured photo could not be encoded. Please try again.'); return }
      void setPhoto(new File([blob],`civicvision-${Date.now()}.jpg`,{type:'image/jpeg'}))
    },'image/jpeg',0.9)
  }, [camera.video,setPhoto])

  const getLocation = useCallback(() => {
    if (!navigator.geolocation) { setLocationState('Location is unsupported here. Enter coordinates manually if you want to share them.'); return }
    setLocating(true); setLocationState('Requesting your location…')
    navigator.geolocation.getCurrentPosition(position => {
      setLat(String(position.coords.latitude)); setLon(String(position.coords.longitude)); setAccuracy(position.coords.accuracy); setLocationCapturedAt(new Date(position.timestamp).toISOString())
      setLocationState(`Location captured ${new Date(position.timestamp).toLocaleTimeString()} (about ${Math.round(position.coords.accuracy)} m accuracy). Review it before sharing.`)
      setLocating(false)
    }, reason => {
      setAccuracy(null);setLocationCapturedAt('')
      setLocationState(locationFailureMessage(reason.code))
      setLocating(false)
    }, {enableHighAccuracy:true,timeout:15_000,maximumAge:0})
  }, [])

  const submit = async () => {
    if (!file || submitLock.current || saving) return
    let latitude:number|undefined, longitude:number|undefined
    if (lat.trim() || lon.trim()) {
      latitude=Number(lat); longitude=Number(lon)
      if (!lat.trim() || !lon.trim() || !Number.isFinite(latitude) || !Number.isFinite(longitude) || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) { setError('Enter valid latitude and longitude, or clear both fields to submit without a location.'); return }
    }
    submitLock.current=true; setSaving(true); setError('')
    if (!submissionKey.current) submissionKey.current = crypto.randomUUID()
    try {
      const report = await api.createReport(file,title.trim()||'Road damage report',description.trim(),latitude,longitude,category||undefined,accuracy??undefined,locationCapturedAt||undefined,submissionKey.current)
      setSaved(report); submissionKey.current=''
      sessionStorage.setItem(`${TOKEN_PREFIX}${report.id}`,report.tracking_token)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Your report could not be submitted. Check your connection and retry. Your photo and details are still here.') }
    finally { submitLock.current=false; setSaving(false) }
  }

  if (saved) return <main className="citizen-page"><CitizenHeader/><section className="citizen-card citizen-success" aria-live="polite"><span className="citizen-success-icon"><Check size={27}/></span><p className="citizen-eyebrow">REPORT RECEIVED</p><h1>Thank you for helping improve local roads.</h1><p>Your report is stored for human review. No municipality is contacted automatically.</p><div className="complaint-number">Complaint ID <strong>CV-{String(saved.id).padStart(4,'0')}</strong></div><div className="tracking-secret"><ShieldCheck size={17}/><div><strong>Private tracking key</strong><code>{saved.tracking_token}</code><small>Keep this key private. You need it with the complaint ID to check status.</small></div></div><button className="button button-primary button-full" onClick={()=>navigate(`/track/${saved.id}`)}>Track this report</button><button className="citizen-link-button" onClick={()=>{setSaved(null);setFile(null);setScan(null);setTitle('Road damage report');setDescription('');setCategory('');setLat('');setLon('');setAccuracy(null);setLocationState('Location has not been requested.')}}>Submit another report</button></section></main>

  return <main className="citizen-page"><CitizenHeader/><div className="citizen-intro"><p className="citizen-eyebrow">COMMUNITY ROAD REPORT</p><h1>Help us spot road damage.</h1><p>Take a clear photo, confirm a location if you can, and send it for human review.</p></div>
    <div className="citizen-grid"><section className="citizen-card"><div className="citizen-section-title"><span>1</span><div><h2>Photograph the road</h2><p>Photo is sent for detector analysis; a report is saved only after you submit.</p></div></div>
      {camera.error&&<div className="citizen-alert" role="alert"><TriangleAlert size={17}/>{camera.error}</div>}
      {!file ? <><div className={`citizen-camera ${camera.stream.current?'citizen-camera-ready':''}`}><video ref={camera.video} playsInline muted aria-label="Live rear camera preview"/><div className="camera-placeholder"><Camera size={26}/><span>{camera.starting?'Starting camera…':'Camera preview will appear here'}</span></div></div><div className="citizen-camera-actions"><button className="button button-primary" onClick={()=>void camera.start()} disabled={camera.starting}><Camera size={17}/>{camera.starting?'Starting…':'Start camera'}</button><button className="button button-secondary" onClick={()=>void camera.start(camera.facing==='environment'?'user':'environment')} disabled={camera.starting}>Switch camera</button>{camera.torchAvailable&&<button className="button button-secondary" onClick={()=>void camera.toggleTorch()}>{camera.torch?'Turn flash off':'Turn flash on'}</button>}<button className="button button-secondary" onClick={()=>fileInput.current?.click()}><ImagePlus size={16}/>Choose photo</button></div><input ref={fileInput} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={e=>void setPhoto(e.target.files?.[0])}/>{camera.stream.current&&<button className="citizen-capture" onClick={capture} aria-label="Capture road photo"><span/></button>}</>
      : <div className="citizen-photo-review"><img src={preview} alt="Photo selected for the road damage report"/><div><span>{file.name} · {(file.size/1024/1024).toFixed(2)} MB</span><button className="button button-secondary" disabled={scanning||saving} onClick={()=>{setFile(null);setScan(null);setError('');void camera.start()}}><RotateCcw size={15}/>Retake</button><button className="button button-secondary" disabled={scanning||saving} onClick={()=>fileInput.current?.click()}><UploadCloud size={15}/>Choose another</button></div><input ref={fileInput} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={e=>void setPhoto(e.target.files?.[0])}/></div>}
      {scanning&&<p className="citizen-model-status" role="status">Checking the image with the configured detector…</p>}{scan&&<div className={`citizen-model-status ${scan.mode==='demo'?'citizen-demo':''}`}><strong>{scan.mode==='model'?'Model analysis complete':'Detection unavailable in demo mode'}</strong><p>{scan.note}</p>{scan.mode==='model'&&<p>{scan.detections.length} detections · {Math.round(scan.inference_ms)} ms{scan.model_version?` · ${scan.model_version}`:''}</p>}</div>}
    </section>
    <section className="citizen-card"><div className="citizen-section-title"><span>2</span><div><h2>Confirm location and details</h2><p>Sharing location is optional. We do not guess it.</p></div></div><button className="button button-secondary" onClick={getLocation} disabled={locating}><Crosshair size={16}/>{locating?'Finding location…':'Use my current location'}</button><p className="citizen-location-state" role="status">{locationState}</p><div className="form-two citizen-coordinates"><label>Latitude<input inputMode="decimal" value={lat} onChange={e=>{setLat(e.target.value);setAccuracy(null);setLocationCapturedAt('');setLocationState('Coordinates entered manually; accuracy is not verified.')}} placeholder="Optional"/></label><label>Longitude<input inputMode="decimal" value={lon} onChange={e=>{setLon(e.target.value);setAccuracy(null);setLocationCapturedAt('');setLocationState('Coordinates entered manually; accuracy is not verified.')}} placeholder="Optional"/></label></div><label className="citizen-field">Issue category<select value={category} onChange={e=>setCategory(e.target.value)}><option value="">Let the reviewer classify</option><option value="pothole">Pothole</option><option value="crack">Road crack</option><option value="other">Other road damage</option></select></label><label className="citizen-field">Short title<input value={title} maxLength={140} onChange={e=>setTitle(e.target.value)} placeholder="What did you see?"/></label><label className="citizen-field">Description <span>Optional</span><textarea value={description} maxLength={3000} rows={4} onChange={e=>setDescription(e.target.value)} placeholder="Nearby landmark or anything that helps find the issue…"/></label><div className="citizen-privacy"><ShieldCheck size={16}/><span>Submitting shares the photo and any coordinates you provided with the authority review workspace. Do not include people or sensitive details.</span></div>{error&&<div className="citizen-alert" role="alert"><TriangleAlert size={17}/>{error}</div>}<button className="button button-primary button-full" disabled={!file||saving||scanning} onClick={()=>void submit()}>{saving?'Sending report…':'Submit for review'}</button><p className="citizen-footnote">You can send this report without GPS. A human reviewer checks all submissions.</p></section></div><footer className="citizen-footer"><Link to="/authority/login">Authority workspace sign in</Link><span>Predictions are assistance only, not an official inspection.</span></footer>
  </main>
}

function CitizenHeader(){return <header className="citizen-header"><Link to="/report" className="citizen-brand"><span><TrafficCone size={21}/></span><strong>CivicVision</strong></Link><Link to="/track" className="citizen-header-link">Track a report <ArrowLeft size={14}/></Link></header>}

export function TrackReport(){
  const {id:rawId}=useParams(); const [idValue,setIdValue]=useState(rawId||''); const id=Number(idValue); const [token,setToken]=useState(''); const [result,setResult]=useState<Tracking|null>(null); const [loading,setLoading]=useState(false); const [error,setError]=useState(''); const [copied,setCopied]=useState(false)
  useEffect(()=>{setIdValue(rawId||'');const nextId=Number(rawId);if(Number.isSafeInteger(nextId)&&nextId>0)setToken(sessionStorage.getItem(`${TOKEN_PREFIX}${nextId}`)||'')},[rawId])
  const lookup=async()=>{if(!Number.isSafeInteger(id)||id<=0){setError('Enter the complaint ID from your confirmation.');return}setLoading(true);setError('');try{const value=await api.track(id,token.trim());setResult(value);sessionStorage.setItem(`${TOKEN_PREFIX}${id}`,token.trim())}catch(reason){setResult(null);setError(reason instanceof Error?reason.message:'Tracking details could not be loaded.')}finally{setLoading(false)}}
  const copy=async()=>{try{await navigator.clipboard.writeText(token);setCopied(true);setTimeout(()=>setCopied(false),1800)}catch{setError('Clipboard access is unavailable. Select and copy the tracking key manually.')}}
  return <main className="citizen-page"><CitizenHeader/><section className="citizen-card tracking-card"><Link to="/report" className="citizen-back"><ArrowLeft size={15}/>Report a road issue</Link><p className="citizen-eyebrow">PRIVATE STATUS LOOKUP</p><h1>Track your report</h1><p>Use the complaint ID and private tracking key from your confirmation. Only the status timeline is shown.</p><label className="citizen-field">Complaint ID<input type="number" inputMode="numeric" value={idValue} onChange={e=>setIdValue(e.target.value)} aria-describedby="tracking-id-help"/><small id="tracking-id-help">For example, enter the number from CV-0012.</small></label><label className="citizen-field">Private tracking key<input value={token} onChange={e=>setToken(e.target.value)} autoComplete="off" spellCheck={false} placeholder="Paste your tracking key"/></label><button className="button button-primary button-full" disabled={loading||!token.trim()} onClick={()=>void lookup()}>{loading?'Checking…':'Check status'}</button>{error&&<div className="citizen-alert" role="alert"><TriangleAlert size={17}/>{error}</div>}{result&&<div className="tracking-result" aria-live="polite"><div className="complaint-number">CV-{String(result.id).padStart(4,'0')} · {result.category}</div><h2>{result.title}</h2><p>Current status: <strong>{result.status.replace(/_/g,' ')}</strong></p><ol className="tracking-history">{result.history.map((event,index)=><li key={`${event.created_at}-${index}`}><span className="tracking-dot"/><strong>{event.new_status.replace(/_/g,' ')}</strong><time>{new Date(event.created_at).toLocaleString()}</time></li>)}</ol><button className="button button-secondary" onClick={()=>void copy()}><Clipboard size={15}/>{copied?'Copied':'Copy tracking key'}</button></div>}</section></main>
}
