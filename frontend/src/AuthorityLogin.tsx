import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ArrowLeft, ShieldCheck, TrafficCone } from 'lucide-react'
import { api, saveAuthoritySession } from './api'

export function AuthorityLogin(){
  const navigate=useNavigate();const location=useLocation();const [username,setUsername]=useState('');const [password,setPassword]=useState('');const [error,setError]=useState('');const [loading,setLoading]=useState(false)
  const destination=(location.state as {from?:string}|null)?.from||'/'
  if(sessionStorage.getItem('civicvision-authority-session'))return <Navigate to="/" replace/>
  const submit=async(event:FormEvent)=>{event.preventDefault();setLoading(true);setError('');try{const session=await api.login(username,password);saveAuthoritySession(session.access_token);navigate(destination,{replace:true})}catch(reason){setError(reason instanceof Error?reason.message:'Sign in failed. Check the service and retry.')}finally{setLoading(false)}}
  return <main className="authority-login-page"><Link to="/report" className="citizen-brand"><span><TrafficCone size={21}/></span><strong>CivicVision</strong></Link><form className="citizen-card authority-login-card" onSubmit={submit}><span className="citizen-success-icon"><ShieldCheck size={23}/></span><p className="citizen-eyebrow">AUTHORITY WORKSPACE</p><h1>Staff sign in</h1><p>Use your named reviewer or administrator account. Citizen reports and evidence are only visible after sign in.</p><label className="citizen-field">Username<input autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)} required maxLength={120}/></label><label className="citizen-field">Password<input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required maxLength={200}/></label>{error&&<div className="citizen-alert" role="alert">{error}</div>}<button className="button button-primary button-full" disabled={loading}>{loading?'Signing in…':'Sign in securely'}</button><div className="citizen-privacy"><ShieldCheck size={16}/><span>Accounts are configured by the service operator. There is no public sign-up.</span></div></form><Link className="citizen-back" to="/report"><ArrowLeft size={15}/>Return to citizen reporting</Link></main>
}

export function AuthorityGate({children}:{children:ReactNode}){
  const location=useLocation();const [allowed,setAllowed]=useState<boolean|null>(null)
  useEffect(()=>{let active=true;const expired=()=>{sessionStorage.removeItem('civicvision-authority-session');setAllowed(false)};window.addEventListener('civicvision-auth-expired',expired);const token=sessionStorage.getItem('civicvision-authority-session');if(!token){setAllowed(false);return()=>window.removeEventListener('civicvision-auth-expired',expired)}void api.currentAuthority().then(()=>{if(active)setAllowed(true)}).catch(()=>{sessionStorage.removeItem('civicvision-authority-session');if(active)setAllowed(false)});return()=>{active=false;window.removeEventListener('civicvision-auth-expired',expired)}},[])
  if(allowed===null)return <main className="authority-loading">Checking authority session…</main>
  if(!allowed)return <Navigate to="/authority/login" state={{from:location.pathname+location.search}} replace/>
  return <>{children}</>
}
