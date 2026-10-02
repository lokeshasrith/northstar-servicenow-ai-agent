import {
  Activity, ArrowDownUp, ArrowRight, Bell, BookOpen, Bot, CheckCircle2, ChevronDown,
  CircleHelp, Command, Database, Filter, Gauge, Headphones, LayoutDashboard, LockKeyhole,
  Moon, MoreHorizontal, Plus, RefreshCw, Search, Settings2, ShieldAlert, Sparkles, Sun, Timer,
  Wifi, X, Zap,
} from 'lucide-react';
import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';

type Incident = {
  id: string; number: string; servicenow_sys_id: string; servicenow_sync_status: string;
  title: string; description: string; category: string; subcategory: string; priority: string;
  confidence: number; status: string; assigned_group: string; assigned_to: string;
  decision: Record<string, any>; knowledge: any[]; actions: any[]; timeline: any[];
  work_notes: string; created_at: string; updated_at: string;
};
type Page = 'Overview' | 'Agent activity' | 'Knowledge base' | 'Approvals' | 'Evaluations' | 'Settings';
type KnowledgeResult = { id: string; title: string; source: string; category: string; snippet: string; score: number };
type ActionSpec = { name: string; description: string; risk: string; approval: boolean; category: string; validation: string };

const API = (import.meta.env.VITE_API_BASE || (import.meta.env.DEV ? 'http://localhost:8000/api' : '/api')).replace(/\/$/, '');
const NAV: { label: Page; icon: typeof LayoutDashboard }[] = [
  { label: 'Overview', icon: LayoutDashboard }, { label: 'Agent activity', icon: Activity },
  { label: 'Knowledge base', icon: Database }, { label: 'Approvals', icon: ShieldAlert },
  { label: 'Evaluations', icon: Gauge }, { label: 'Settings', icon: Settings2 },
];
const today = new Intl.DateTimeFormat('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }).format(new Date()).toUpperCase();

async function request<T = any>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  headers.set('Content-Type', 'application/json');
  const key = localStorage.getItem('northstar-api-key');
  if (key) headers.set('X-API-Key', key);
  let response: Response;
  try { response = await fetch(`${API}${path}`, { ...init, headers }); }
  catch { throw new Error('Could not reach the API. Check the deployment health and try again.'); }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { const body = await response.json(); message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body); } catch { /* keep status */ }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function friendlyError(error: unknown) { return error instanceof Error ? error.message : 'Something went wrong. Please try again.'; }
function formatTime(value?: string) { return value ? new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'; }
function percent(value?: number) { return `${Math.round((value || 0) * 100)}%`; }
function getSavedTheme(): 'light' | 'dark' { try { return localStorage.getItem('northstar-theme') === 'dark' ? 'dark' : 'light'; } catch { return 'light'; } }

export default function App() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [audit, setAudit] = useState<any[]>([]);
  const [policy, setPolicy] = useState<any>(null);
  const [actions, setActions] = useState<ActionSpec[]>([]);
  const [evaluation, setEvaluation] = useState<any>(null);
  const [knowledge, setKnowledge] = useState<KnowledgeResult[]>([]);
  const [knowledgeQuery, setKnowledgeQuery] = useState('');
  const [knowledgeSearched, setKnowledgeSearched] = useState(false);
  const [page, setPage] = useState<Page>('Overview');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState('All statuses');
  const [priorityFilter, setPriorityFilter] = useState('All priorities');
  const [categoryFilter, setCategoryFilter] = useState('All categories');
  const [sort, setSort] = useState<'priority' | 'newest' | 'oldest'>('priority');
  const [pageIndex, setPageIndex] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [detailAction, setDetailAction] = useState('');
  const [operatorName, setOperatorName] = useState('Jordan Davis');
  const [actionOperator, setActionOperator] = useState('Jordan Davis');
  const [escalationReason, setEscalationReason] = useState('Needs support team investigation');
  const [assignmentGroup, setAssignmentGroup] = useState('');
  const [workNotes, setWorkNotes] = useState('');
  const [createForm, setCreateForm] = useState({ title: '', description: '', affected_users: 1, business_criticality: 2, service: '' });
  const [createError, setCreateError] = useState('');
  const [servicenowResult, setServicenowResult] = useState('');
  const [theme, setTheme] = useState<'light' | 'dark'>(getSavedTheme);
  const [guideOpen, setGuideOpen] = useState(false);

  const refresh = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const rows = await request<Incident[]>('/incidents');
      setIncidents(rows);
      setSelected(current => current ? (rows.find(x => x.id === current.id) || null) : null);
      setLastUpdated(new Date());
      setError('');
      return rows;
    } catch (e) { setError(friendlyError(e)); return null; }
    finally { if (showLoading) setLoading(false); }
  }, []);

  const loadPolicy = useCallback(async () => {
    try {
      const [config, registry] = await Promise.all([request('/config'), request<Record<string, ActionSpec>>('/actions')]);
      setPolicy(config);
      setActions(Object.values(registry));
    } catch (e) { setError(friendlyError(e)); }
  }, []);

  useEffect(() => {
    void refresh(true);
    void loadPolicy();
    const poll = window.setInterval(() => { if (document.visibilityState === 'visible') void refresh(); }, 7000);
    const onFocus = () => { if (document.visibilityState === 'visible') void refresh(); };
    document.addEventListener('visibilitychange', onFocus);
    window.addEventListener('focus', onFocus);
    return () => { window.clearInterval(poll); document.removeEventListener('visibilitychange', onFocus); window.removeEventListener('focus', onFocus); };
  }, [refresh, loadPolicy]);

  useEffect(() => {
    try { localStorage.setItem('northstar-theme', theme); } catch { /* Theme still works for this session when storage is unavailable. */ }
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
  }, [theme]);

  useEffect(() => {
    if (page === 'Evaluations' && !evaluation) request('/evaluation').then(setEvaluation).catch(e => setError(friendlyError(e)));
  }, [page, evaluation]);

  const withBusy = async (work: () => Promise<void>, success?: string) => {
    setBusy(true); setError(''); setNotice('');
    try { await work(); if (success) setNotice(success); }
    catch (e) { setError(friendlyError(e)); }
    finally { setBusy(false); }
  };

  const openIncident = async (item: Incident) => {
    setSelected(item); setDetailAction(''); setAssignmentGroup(item.assigned_group); setWorkNotes(item.work_notes || '');
    try {
      const [fresh, events] = await Promise.all([request<Incident>(`/incidents/${item.id}`), request<any[]>(`/incidents/${item.id}/audit`)]);
      setSelected(fresh); setAudit(events);
    } catch (e) { setError(friendlyError(e)); }
  };

  const doCreate = async (event: FormEvent) => {
    event.preventDefault(); setCreateError(''); setError(''); setBusy(true);
    try {
      const created = await request<Incident>('/incidents', { method: 'POST', body: JSON.stringify(createForm) });
      const processed = await request<Incident>(`/incidents/${created.id}/process`, { method: 'POST' });
      await refresh(); setCreateOpen(false); setCreateForm({ title: '', description: '', affected_users: 1, business_criticality: 2, service: '' });
      setPage('Overview'); setNotice(`AI test complete: ${processed.status} in this simulation. Review its decision and verification below.`); await openIncident(processed);
    } catch (e) { setCreateError(friendlyError(e)); await refresh(); }
    finally { setBusy(false); }
  };

  const processSelected = async () => {
    if (!selected) return;
    await withBusy(async () => { const fresh = await request<Incident>(`/incidents/${selected.id}/process`, { method: 'POST' }); await refresh(); await openIncident(fresh); }, 'Incident analysis complete.');
  };
  const escalateSelected = async () => {
    if (!selected) return;
    await withBusy(async () => { const fresh = await request<Incident>(`/incidents/${selected.id}/escalate`, { method: 'POST', body: JSON.stringify({ reason: escalationReason, assignment_group: assignmentGroup || null }) }); await refresh(); await openIncident(fresh); setDetailAction(''); }, 'Incident escalated for human review.');
  };
  const approve = async (item: Incident) => {
    await withBusy(async () => { await request(`/incidents/${item.id}/approve-action`, { method: 'POST', body: JSON.stringify({ approved_by: operatorName }) }); await refresh(); if (selected?.id === item.id) await openIncident(item); }, 'Approval recorded. The action was simulated; a human must verify the incident.');
  };
  const requestAction = async () => {
    if (!selected || !detailAction) return;
    await withBusy(async () => { const fresh = await request<Incident>(`/incidents/${selected.id}/actions`, { method: 'POST', body: JSON.stringify({ action: detailAction, requested_by: actionOperator }) }); await refresh(); await openIncident(fresh); }, 'Action request recorded in the audit log.');
  };
  const saveIncident = async (fields: Record<string, string>, message: string) => {
    if (!selected) return;
    await withBusy(async () => { const fresh = await request<Incident>(`/incidents/${selected.id}`, { method: 'PATCH', body: JSON.stringify(fields) }); await refresh(); await openIncident(fresh); }, message);
  };

  const openView = (next: Page) => { setPage(next); setPageIndex(0); setError(''); };
  const active = selected || incidents[0];
  const openCount = incidents.filter(x => !['Resolved', 'Closed'].includes(x.status)).length;
  const resolvedCount = incidents.filter(x => x.status === 'Resolved').length;
  const reviewCount = incidents.filter(x => ['Human review', 'Escalated'].includes(x.status)).length;
  const meanConfidence = incidents.length ? Math.round(incidents.reduce((sum, x) => sum + x.confidence, 0) / incidents.length * 100) : 0;
  const reviewRate = incidents.length ? reviewCount / incidents.length : 0;
  const confidenceSeries = incidents.slice(0, 12).map(x => x.confidence);
  const approvalCount = incidents.reduce((n, x) => n + x.actions.filter(a => a.status === 'approval_required').length, 0);
  const statuses = useMemo(() => ['All statuses', ...Array.from(new Set(incidents.map(x => x.status))).sort()], [incidents]);
  const categories = useMemo(() => ['All categories', ...Array.from(new Set(incidents.map(x => x.category))).sort()], [incidents]);
  const filteredIncidents = useMemo(() => {
    const q = search.trim().toLowerCase();
    const rows = incidents.filter(x => (statusFilter === 'All statuses' || x.status === statusFilter)
      && (priorityFilter === 'All priorities' || x.priority === priorityFilter)
      && (categoryFilter === 'All categories' || x.category === categoryFilter)
      && (!q || [x.number, x.title, x.description, x.category, x.subcategory, x.assigned_group].some(v => v?.toLowerCase().includes(q))));
    const weight: Record<string, number> = { P1: 1, P2: 2, P3: 3, P4: 4 };
    return rows.sort((a, b) => sort === 'priority' ? (weight[a.priority] ?? 9) - (weight[b.priority] ?? 9) || b.created_at.localeCompare(a.created_at) : sort === 'newest' ? b.created_at.localeCompare(a.created_at) : a.created_at.localeCompare(b.created_at));
  }, [incidents, statusFilter, priorityFilter, categoryFilter, search, sort]);
  const pageSize = 8;
  const visibleIncidents = filteredIncidents.slice(pageIndex * pageSize, (pageIndex + 1) * pageSize);
  const pendingApprovals = incidents.flatMap(item => item.actions.some(a => a.status === 'approval_required') ? [{ ...item, pending: item.actions.filter(a => a.status === 'approval_required') }] : []);
  const allTimeline = incidents.flatMap(item => (item.timeline || []).map((event: any, index: number) => ({ ...event, incident: item, key: `${item.id}-${index}` }))).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()).slice(0, 60);
  const matchingActions = selected ? actions.filter(a => a.category === '*' || a.category === selected.category) : [];
  const activeTitle = page === 'Overview' ? 'Overview' : page;

  const runKnowledgeSearch = async (event: FormEvent) => {
    event.preventDefault(); if (knowledgeQuery.trim().length < 2) { setError('Enter at least two characters to search the runbooks.'); return; }
    await withBusy(async () => { const result = await request<{ results: KnowledgeResult[] }>(`/knowledge/search?q=${encodeURIComponent(knowledgeQuery.trim())}&limit=10`); setKnowledge(result.results); setKnowledgeSearched(true); }, 'Knowledge search complete.');
  };
  const syncServiceNow = async () => await withBusy(async () => { const result = await request<any>('/servicenow/sync', { method: 'POST' }); setServicenowResult(`Fetched ${result.fetched}; imported ${result.imported}; updated ${result.updated}; failed ${result.failed}.`); await refresh(); }, 'ServiceNow sync finished.');
  const retryPending = async () => await withBusy(async () => { const result = await request<any>('/servicenow/retry-pending', { method: 'POST' }); setServicenowResult(`Retried ${result.retried}; succeeded ${result.succeeded}; failed ${result.failed}.`); await refresh(); }, 'Pending sync retry finished.');

  const navLink = (label: Page, icon: typeof LayoutDashboard) => {
    const Icon = icon;
    return <button className={`nav-item ${page === label ? 'active' : ''}`} key={label} onClick={() => openView(label)}><Icon/>{label}{label === 'Overview' && <span className="nav-count">{incidents.length}</span>}{label === 'Approvals' && <span className="nav-badge">{approvalCount}</span>}</button>;
  };

  return <div className="shell" data-theme={theme}>
    <aside className="sidebar">
      <div className="brand"><div className="brandmark"><Command size={18}/></div><div><b>northstar</b><span>IT OPERATIONS</span></div></div>
      <div className="workspace"><i/> ACME CORPORATION</div>
      <div className="side-label">WORKSPACE</div><nav>{NAV.slice(0, 4).map(item => navLink(item.label, item.icon))}</nav>
      <div className="side-label systems-label">SYSTEM</div><nav>{NAV.slice(4).map(item => navLink(item.label, item.icon))}</nav>
      <div className="sidebar-bottom"><button className="support-card" onClick={() => setGuideOpen(true)}><CircleHelp/><span><b>Quick start guide</b><small>Learn to use and deploy this agent</small></span><ArrowRight/></button><div className="profile"><div className="avatar profile-avatar">JD</div><div className="profile-copy"><b>Jordan Davis</b><span>IT Administrator · demo</span></div><MoreHorizontal/></div></div>
    </aside>

    <main className="main"><header className="topbar"><div className="breadcrumbs"><span>Workspace</span><span>/</span><b>{activeTitle}</b></div><div className="top-actions"><button className="refresh-top" onClick={() => void refresh(true)} title="Refresh now" disabled={busy}><RefreshCw className={loading ? 'spin' : ''}/></button><div className="system-status"><i className={error ? 'offline' : ''}/>{error ? 'API needs attention' : 'Backend connected'}<small>{lastUpdated ? `Updated ${formatTime(lastUpdated.toISOString())}` : ''}</small></div>{searchOpen && <input className="global-search" autoFocus placeholder="Search incidents…" value={search} onChange={e => { setSearch(e.target.value); setPage('Overview'); setPageIndex(0); }}/>}<button onClick={() => { setSearchOpen(x => !x); setSearch(''); }} title="Search incidents" aria-label="Search incidents"><Search/></button><button className={approvalCount > 0 ? 'has-dot' : ''} onClick={() => openView('Approvals')} title={`${approvalCount} pending approvals`} aria-label={`${approvalCount} pending approvals`}><Bell/>{approvalCount > 0 && <span className="notification-count">{approvalCount}</span>}</button><button className="utility-button" onClick={() => setGuideOpen(true)} title="Quick start guide" aria-label="Open quick start guide"><CircleHelp/></button><button className="utility-button theme-toggle" onClick={() => setTheme(current => current === 'dark' ? 'light' : 'dark')} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>{theme === 'dark' ? <Sun/> : <Moon/>}<span>{theme === 'dark' ? 'Light' : 'Dark'}</span></button><div className="avatar top-avatar">JD</div></div></header>
      <div className="content">
        {error && <div className="api-error" role="alert"><span><b>Action needed:</b> {error}</span><button onClick={() => setError('')} aria-label="Dismiss error"><X size={15}/></button></div>}
        {notice && <div className="success-banner" role="status"><CheckCircle2 size={15}/><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss message"><X size={15}/></button></div>}

        {page === 'Overview' && <>
          <section className="page-heading"><div><div className="eyebrow"><i/> {today}</div><h1>Good morning, Jordan <span>✳</span></h1><p>Try a fictional incident and watch the agent triage it, run a safe mock check, and explain its next step.</p></div><button className="primary-button" onClick={() => { setCreateError(''); setCreateOpen(true); }} disabled={busy}><Sparkles/> Try your incident</button></section>
          <section className="metrics"><Metric title="Open incidents" value={String(openCount)} change="live queue" foot={`${incidents.length} persisted in this workspace`} icon={<Activity/>} tone="blue" chart="none"/><Metric title="Resolved in simulation" value={String(resolvedCount)} change="demo only" foot="mock verification; no real systems changed" icon={<Sparkles/>} tone="green" chart="none"/><Metric title="Human review" value={String(reviewCount)} change={`${Math.round(reviewRate * 100)}% of queue`} foot="escalated or held for support" icon={<Headphones/>} tone="amber" chart="progress" chartValue={reviewRate}/><Metric title="Mean confidence" value={`${meanConfidence}%`} change="current sample" foot="per-incident confidence, most recent 12" icon={<Timer/>} tone="purple" chart="bars" series={confidenceSeries}/></section>
          <section className="queue-card"><div className="section-heading"><div><h2>Incident queue <span className="sub-count">{filteredIncidents.length}</span></h2><p>Automatically refreshes every 7 seconds while this page is open</p></div><div className="queue-actions"><button onClick={() => setFiltersOpen(x => !x)} className={filtersOpen ? 'selected-control' : ''}><Filter/> Filters {(statusFilter !== 'All statuses' || priorityFilter !== 'All priorities' || categoryFilter !== 'All categories') && <b>On</b>}</button><button onClick={() => setSort(current => current === 'priority' ? 'newest' : current === 'newest' ? 'oldest' : 'priority')} title="Cycle sorting"><ArrowDownUp/> {sort === 'priority' ? 'Priority' : sort === 'newest' ? 'Newest' : 'Oldest'} <ChevronDown/></button><button className="dots" onClick={() => void refresh(true)} title="Refresh incident list"><MoreHorizontal/></button></div></div>
            {(filtersOpen || search) && <div className="filter-row"><label>Status<select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPageIndex(0); }}>{statuses.map(x => <option key={x}>{x}</option>)}</select></label><label>Priority<select value={priorityFilter} onChange={e => { setPriorityFilter(e.target.value); setPageIndex(0); }}>{['All priorities', 'P1', 'P2', 'P3', 'P4'].map(x => <option key={x}>{x}</option>)}</select></label><label>Category<select value={categoryFilter} onChange={e => { setCategoryFilter(e.target.value); setPageIndex(0); }}>{categories.map(x => <option key={x}>{x}</option>)}</select></label>{search && <span className="filter-search-label">Search: “{search}”</span>}<button className="link-button" onClick={() => { setStatusFilter('All statuses'); setPriorityFilter('All priorities'); setCategoryFilter('All categories'); setSearch(''); }}>Clear filters</button></div>}
            <div className="table-wrap"><table><thead><tr><th>INCIDENT</th><th>CATEGORY</th><th>PRIORITY</th><th>AI CONFIDENCE</th><th>STATUS</th><th>ASSIGNED TO</th><th/></tr></thead><tbody>{loading && !incidents.length ? <tr><td colSpan={7} className="empty-state">Loading incidents…</td></tr> : visibleIncidents.map(x => <IncidentRow key={x.id} incident={x} onOpen={() => void openIncident(x)}/>)}{!loading && !visibleIncidents.length && <tr><td colSpan={7} className="empty-state">{incidents.length ? 'No incidents match these filters.' : 'No incidents yet. Create one to start the agent workflow.'}</td></tr>}</tbody></table></div>
            <div className="table-footer"><span>Showing <b>{visibleIncidents.length ? pageIndex * pageSize + 1 : 0}–{Math.min((pageIndex + 1) * pageSize, filteredIncidents.length)}</b> of <b>{filteredIncidents.length}</b> incidents</span><div><button onClick={() => setPageIndex(x => Math.max(0, x - 1))} disabled={pageIndex === 0}>Previous</button><button onClick={() => setPageIndex(x => x + 1)} disabled={(pageIndex + 1) * pageSize >= filteredIncidents.length}>Next <ArrowRight/></button></div></div>
          </section>
          <section className="bottom-grid"><ActivityCard active={active} events={active?.timeline || []} onViewAll={() => openView('Agent activity')}/><SafetyCard policy={policy} onOpen={() => openView('Settings')}/></section>
          <footer><span>Northstar AI <b>v0.2.0</b> · Public mock demo</span><span><i/> ServiceNow adapter: {policy?.servicenow_mode || 'mock'} <i>·</i> {lastUpdated ? `Last refresh ${formatTime(lastUpdated.toISOString())}` : 'Connecting…'}</span></footer>
        </>}

        {page === 'Agent activity' && <PageHeading title="Agent activity" description="Persisted classification, decisions, escalations, and action events." action={<button className="secondary-button" onClick={() => void refresh(true)}><RefreshCw/> Refresh activity</button>}/>}
        {page === 'Agent activity' && <section className="page-card"><div className="card-title-row"><div><h2>Recent event timeline</h2><p>Updates when the incident queue refreshes</p></div><span className="live-pill"><i/> LIVE</span></div>{allTimeline.length ? <div className="event-list">{allTimeline.map(event => <button className="event-row" key={event.key} onClick={() => void openIncident(event.incident)}><time>{new Date(event.timestamp).toLocaleString()}</time><i/><span><b>{event.event.replace(/_/g, ' ')}</b><small>{event.incident.number} · {event.incident.title}</small></span><ArrowRight/></button>)}</div> : <EmptyState title="No recorded activity" detail="Create or process an incident to populate this audit-backed feed."/>}</section>}

        {page === 'Knowledge base' && <><PageHeading title="Knowledge base" description="Search the included runbooks used to ground incident recommendations."/><section className="page-card"><form className="knowledge-search" onSubmit={runKnowledgeSearch}><Search/><input value={knowledgeQuery} onChange={e => setKnowledgeQuery(e.target.value)} placeholder="Try “VPN connection”, “DNS”, or “account locked”…" minLength={2}/><button className="primary-button" disabled={busy}>Search runbooks</button></form><p className="muted-note">Knowledge results are local project runbooks; they are not fetched from a connected ServiceNow instance in this public demo.</p>{knowledgeSearched && <div className="knowledge-results">{knowledge.map(item => <article className="knowledge-result" key={item.id}><div><span className="result-category">{item.category} · relevance {percent(item.score)}</span><h3>{item.title}</h3><p>{item.snippet}</p><small>{item.source}</small></div><BookOpen/></article>)}{!knowledge.length && <EmptyState title="No matching runbooks" detail="Try a shorter term or a different incident keyword."/>}</div>}</section></>}

        {page === 'Approvals' && <><PageHeading title="Human approvals" description="High-impact actions stay paused until a different operator approves them."/><section className="page-card"><div className="approval-summary"><ShieldAlert/><div><b>{approvalCount} action{approvalCount === 1 ? '' : 's'} awaiting approval</b><small>Approvals execute a mock action and are written to the incident audit log.</small></div></div><label className="operator-field">Approver name<input value={operatorName} onChange={e => setOperatorName(e.target.value)} placeholder="Enter your name"/></label>{pendingApprovals.map(item => <article className="approval-item" key={item.id}><div><span className="result-category">{item.number} · {item.priority} · {item.status}</span><h3>{item.title}</h3><p>{item.pending.map(a => `${a.name} — ${a.description || a.result}`).join(' · ')}</p><small>Requested by {item.pending[0]?.requested_by || 'an operator'} · {item.assigned_group}</small></div><button className="primary-button" disabled={busy || !operatorName.trim() || item.pending.some(a => a.requested_by?.toLowerCase() === operatorName.trim().toLowerCase())} onClick={() => void approve(item)}><CheckCircle2/> Approve next</button></article>)}{!pendingApprovals.length && <EmptyState title="Nothing needs approval" detail="Approval requests will appear here before any elevated action can run."/>}</section></>}

        {page === 'Evaluations' && <><PageHeading title="Agent evaluations" description="Deterministic evaluation against the labeled sample incidents bundled with this project." action={<button className="secondary-button" onClick={() => { setEvaluation(null); void request('/evaluation').then(setEvaluation).catch(e => setError(friendlyError(e))); }}><RefreshCw/> Recalculate</button>}/>{evaluation ? <><section className="evaluation-grid">{[['Sample size', evaluation.sample_size], ['Classification accuracy', percent(evaluation.classification_accuracy)], ['Priority accuracy', percent(evaluation.priority_accuracy)], ['Escalation accuracy', percent(evaluation.escalation_accuracy)], ['Mean confidence', percent(evaluation.mean_confidence)], ['Confidence Brier score', evaluation.confidence_brier_score], ['False autonomous resolutions', evaluation.false_autonomous_resolutions], ['Human review rate', percent(evaluation.human_escalation_or_review_rate)]].map(([label, value]) => <div className="evaluation-card" key={label}><span>{label}</span><b>{value}</b></div>)}</section><div className="page-card evaluation-note"><ShieldAlert/><span><b>Simulation evaluation only.</b> {evaluation.notes}</span></div></> : <section className="page-card"><EmptyState title="Loading evaluation" detail="Fetching the labeled mock evaluation dataset…"/></section>}</>}

        {page === 'Settings' && <><PageHeading title="System settings" description="Runtime configuration, safety thresholds, and demo integration tools."/><section className="settings-grid"><article className="page-card"><h2>Runtime and safety</h2><p>Configuration reported by the running API.</p><div className="settings-list"><Setting label="Environment" value={policy?.environment || 'Public demo'}/><Setting label="Language model" value={policy?.llm_provider || 'Loading…'}/><Setting label="ServiceNow adapter" value={policy?.servicenow_mode || 'Loading…'}/><Setting label="Automatic decision threshold" value={policy ? percent(policy.confidence_auto_threshold) : '—'}/><Setting label="Human review threshold" value={policy ? percent(policy.confidence_investigate_threshold) : '—'}/><Setting label="Authentication" value={policy?.authentication_enabled ? 'Enabled' : 'Disabled in public demo'}/><Setting label="Knowledge sources" value={policy?.knowledge_sources ?? '—'}/></div><div className="demo-notice"><LockKeyhole/><span><b>Public demo guardrails</b><small>AI and ServiceNow providers are mock-only. Proposed actions are simulated and do not change external systems. The public demo has no sign-in.</small></span></div></article><article className="page-card"><h2>ServiceNow demo sync</h2><p>These controls call the configured adapter. In this deployment it is a mock, not your company instance.</p><div className="settings-buttons"><button className="secondary-button" onClick={() => void syncServiceNow()} disabled={busy}><RefreshCw/> Sync incidents</button><button className="secondary-button" onClick={() => void retryPending()} disabled={busy}><RefreshCw/> Retry pending sync</button></div>{servicenowResult && <div className="sync-result" role="status">{servicenowResult}</div>}<div className="demo-notice"><Wifi/><span><b>Live dashboard updates</b><small>The incident queue polls the backend every 7 seconds while the page is visible and refreshes when you return to the tab.</small></span></div></article></section></>}
      </div>
    </main>

    {createOpen && <div className="detail-backdrop" onMouseDown={e => { if (e.target === e.currentTarget && !busy) setCreateOpen(false); }}><section className="form-modal" role="dialog" aria-modal="true" aria-labelledby="create-title"><button className="detail-close" onClick={() => setCreateOpen(false)} disabled={busy}><X/></button><div className="eyebrow">PUBLIC AI TEST DRIVE</div><h2 id="create-title">Test an incident with AI</h2><p>Enter a fictional issue. The agent will classify it, find a runbook, perform a safe mock check, and explain whether it can verify recovery or needs a human.</p><div className="test-disclaimer"><ShieldAlert/><span><b>Use fictional, anonymized details only.</b><small>This is a shared public demo. Submitted incident text is stored in the shared queue and visible to other visitors. No real system is checked or changed.</small></span></div><div className="scenario-buttons"><span>Try an example</span><button type="button" onClick={() => { setCreateForm({ title: 'VPN access restored after password reset', description: 'The user could not connect to the corporate VPN after changing their password. They signed out and signed back in; VPN authentication is now working again.', affected_users: 1, business_criticality: 1, service: 'Corporate VPN' }); setCreateError(''); }}>Recovered · show simulated resolution</button><button type="button" onClick={() => { setCreateForm({ title: 'VPN still failing after password reset', description: 'The user still cannot connect to the corporate VPN after changing their password. The VPN is not working and recovery has not been confirmed.', affected_users: 1, business_criticality: 1, service: 'Corporate VPN' }); setCreateError(''); }}>Still failing · show human escalation</button></div><form onSubmit={doCreate} className="stacked-form"><label>Short description<input autoFocus required minLength={4} maxLength={200} value={createForm.title} onChange={e => setCreateForm({ ...createForm, title: e.target.value })} placeholder="e.g. VPN disconnects after sign-in"/></label><label>Description<textarea required minLength={8} maxLength={8000} rows={4} value={createForm.description} onChange={e => setCreateForm({ ...createForm, description: e.target.value })} placeholder="Describe the fictional issue, impact, and what you know so far."/></label><label>Affected users<input type="number" required min={1} max={100000} value={createForm.affected_users} onChange={e => setCreateForm({ ...createForm, affected_users: Number(e.target.value) })}/></label><label>Business criticality<select value={createForm.business_criticality} onChange={e => setCreateForm({ ...createForm, business_criticality: Number(e.target.value) })}><option value={1}>Low</option><option value={2}>Medium</option><option value={3}>High</option></select></label><label>Service (optional)<input maxLength={100} value={createForm.service} onChange={e => setCreateForm({ ...createForm, service: e.target.value })} placeholder="Business service"/></label>{createError && <div className="form-error">{createError}</div>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setCreateOpen(false)} disabled={busy}>Cancel</button><button className="primary-button" disabled={busy}>{busy ? 'Creating and testing…' : 'Create and run AI test'}</button></div></form><small className="mock-disclaimer">Mock agent · it may mark a simulated recovery only when the incident description already reports recovery; otherwise it escalates for human review.</small></section></div>}

    {guideOpen && <div className="detail-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setGuideOpen(false); }}><section className="guide-modal" role="dialog" aria-modal="true" aria-labelledby="guide-title"><button className="detail-close" onClick={() => setGuideOpen(false)} aria-label="Close quick start guide"><X/></button><div className="eyebrow">NORTHSTAR · QUICK START</div><h2 id="guide-title">Use the incident agent</h2><p className="guide-intro">Try the hosted demo now, or connect your own GitHub copy and deploy a separate instance.</p><div className="guide-section"><h3>Try it here</h3><ol><li>Click <b>Try an incident</b> and choose one of the examples or describe a fictional issue.</li><li>Select <b>Create and run AI test</b>. The agent classifies the issue, finds runbooks, records its decision, and shows simulated verification or human escalation.</li><li>Open the incident in the queue to review its sources, actions, status, and audit history.</li></ol><button className="primary-button" onClick={() => { setGuideOpen(false); setCreateError(''); setCreateOpen(true); }}><Sparkles/> Try an incident</button></div><div className="guide-section"><h3>Connect your own GitHub copy</h3><ol><li>Open the repository and choose <b>Fork</b> to copy it into your GitHub account.</li><li>In Render, choose <b>New + → Blueprint</b>, connect GitHub if prompted, and select your forked repository.</li><li>Review <code>render.yaml</code> and create the Blueprint. The mock demo needs no API keys or ServiceNow credentials.</li><li>When the deploy finishes, open the service URL. If a push does not start a deploy, use <b>Manual Deploy → Deploy latest commit</b>.</li></ol><div className="guide-links"><a href="https://github.com/lokeshasrith/northstar-servicenow-ai-agent" target="_blank" rel="noreferrer">GitHub repository <ArrowRight/></a><a href="https://dashboard.render.com/blueprints" target="_blank" rel="noreferrer">Open Render blueprints dashboard <ArrowRight/></a><a href="https://github.com/lokeshasrith/northstar-servicenow-ai-agent/blob/main/docs/getting-started.md" target="_blank" rel="noreferrer">Full setup guide <ArrowRight/></a></div></div><div className="guide-safety"><ShieldAlert/><span><b>Safe demo only</b><small>Use fictional, anonymized details. Visitor submissions appear in a shared queue. The mock agent does not access or repair real systems. Free hosting can sleep and the demo database expires; see the setup guide before using it for a portfolio.</small></span></div></section></div>}

    {selected && <div className="detail-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setSelected(null); }}><section className="detail-panel" role="dialog" aria-modal="true" aria-labelledby="detail-title"><button className="detail-close" onClick={() => setSelected(null)}>Close <X/></button><div className="eyebrow">INCIDENT DETAIL · {selected.number}</div><h2 id="detail-title">{selected.title}</h2><p>{selected.description}</p><div className="detail-stats"><span><b>{selected.priority}</b> Priority</span><span><b>{percent(selected.confidence)}</b> Confidence</span><span><b>{selected.status}</b> Status</span><span><b>{selected.assigned_group}</b> Assignment group</span></div><h3>Decision explanation</h3><p>{selected.decision.decision_explanation || selected.decision.escalation_reason || 'Not analyzed yet.'}</p><h3>Knowledge sources</h3>{selected.knowledge?.length ? selected.knowledge.map((item: any) => <div className="detail-item" key={item.id}><b>{item.title}</b><span>{item.source} · relevance {percent(item.score)}</span></div>) : <p className="muted-note">No matching knowledge sources recorded.</p>}<h3>Actions and verification</h3>{selected.actions?.length ? selected.actions.map((item: any, index: number) => <div className="detail-item" key={`${item.name}-${index}`}><b>{item.name} · {item.status}</b><span>{item.result}{item.requested_by ? ` · requested by ${item.requested_by}` : ''}</span>{item.status === 'approval_required' && <button className="secondary-button" onClick={() => void approve(selected)}>Approve next action</button>}</div>) : <p className="muted-note">No action recorded yet.</p>}{selected.decision.verification && <div className="demo-notice"><CheckCircle2/><span><b>{selected.decision.verification.verified ? 'Simulation verified' : 'Needs human verification'}</b><small>{selected.decision.verification.message}</small></span></div>}
      <h3>Agent controls</h3><div className="detail-actions"><button className="secondary-button" onClick={() => void processSelected()} disabled={busy}><Sparkles/> Process / re-analyze</button><button className="primary-button" onClick={() => setDetailAction(detailAction === 'escalate' ? '' : 'escalate')} disabled={busy}><Headphones/> Escalate</button></div>
      {detailAction === 'escalate' && <div className="inline-form"><label>Reason<input value={escalationReason} onChange={e => setEscalationReason(e.target.value)} minLength={4}/></label><label>Assignment group<input value={assignmentGroup} onChange={e => setAssignmentGroup(e.target.value)} placeholder={selected.assigned_group}/></label><button className="primary-button" onClick={() => void escalateSelected()} disabled={busy || escalationReason.trim().length < 4}>Confirm escalation</button></div>}
      <div className="inline-form action-request"><label>Request an allowlisted action<select value={detailAction && detailAction !== 'escalate' ? detailAction : ''} onChange={e => setDetailAction(e.target.value)}><option value="">Select action…</option>{matchingActions.map(a => <option key={a.name} value={a.name}>{a.name} · {a.risk} risk{a.approval ? ' · approval required' : ''}</option>)}</select></label><label>Requesting operator<input value={actionOperator} onChange={e => setActionOperator(e.target.value)} minLength={2}/></label><button className="secondary-button" onClick={() => void requestAction()} disabled={busy || !detailAction || detailAction === 'escalate' || actionOperator.trim().length < 2}>Submit action request</button></div>
      <h3>Incident record</h3><div className="inline-form"><label>Assignment group<input value={assignmentGroup} onChange={e => setAssignmentGroup(e.target.value)}/></label><label>Status<select value={selected.status} onChange={e => void saveIncident({ status: e.target.value }, 'Incident status updated.')}>{['New', 'Investigating', 'Human review', 'Escalated', 'Resolved', 'Closed'].map(x => <option key={x}>{x}</option>)}</select></label><button className="secondary-button" onClick={() => void saveIncident({ assigned_group: assignmentGroup }, 'Assignment group updated.')} disabled={busy}>Save assignment</button></div><label className="notes-editor">Work notes<textarea rows={4} value={workNotes} onChange={e => setWorkNotes(e.target.value)} maxLength={8000}/></label><button className="secondary-button notes-save" onClick={() => void saveIncident({ work_notes: workNotes }, 'Work notes saved to the incident timeline.')} disabled={busy}>Save work notes</button>
      <h3>Activity and audit</h3>{audit.length ? audit.slice().reverse().map(event => <div className="detail-item" key={event.id}><b>{event.event.replace(/_/g, ' ')}</b><span>{new Date(event.timestamp).toLocaleString()} · {event.model}</span>{event.payload && <small>{JSON.stringify(event.payload)}</small>}</div>) : <p className="muted-note">Audit events load when you open this record.</p>}{selected.work_notes && <><h3>Escalation work notes</h3><pre>{selected.work_notes}</pre></>}</section></div>}
  </div>;
}

function IncidentRow({ incident: x, onOpen }: { incident: Incident; onOpen: () => void }) {
  const tone = x.status === 'Escalated' ? 'red' : x.status === 'Human review' ? 'amber' : x.status === 'Resolved' ? 'green' : 'blue';
  const icon = x.category.toLowerCase().includes('vpn') ? 'vpn' : x.category.toLowerCase().includes('authentication') || x.category.toLowerCase().includes('access') ? 'lock' : x.category.toLowerCase().includes('software') ? 'mail' : 'globe';
  return <tr onClick={onOpen} className="clickable"><td><div className="incident-title"><div className={`ticket-icon ${icon}`}>{icon === 'vpn' ? <Wifi/> : icon === 'lock' ? <LockKeyhole/> : icon === 'mail' ? <Bot/> : <Activity/>}</div><div><b>{x.title}</b><span>{x.number} <i>·</i> {formatTime(x.created_at)}</span></div></div></td><td>{x.category} · {x.subcategory}</td><td><span className={`priority ${x.priority.toLowerCase()}`}><i/>{x.priority}</span></td><td><div className="confidence"><div><i className={tone} style={{ width: percent(x.confidence) }}/></div><span>{percent(x.confidence)}</span></div></td><td><span className={`status ${x.status.toLowerCase().replace(/\s/g, '-')}`}><i/>{x.status}</span></td><td><div className="assignee"><span className={`avatar avatar-${tone}`}>{x.assigned_group.slice(0, 2).toUpperCase()}</span>{x.assigned_group}</div></td><td><button className="dots" aria-label={`Open ${x.number}`} onClick={e => { e.stopPropagation(); onOpen(); }}><MoreHorizontal/></button></td></tr>;
}

function Metric({ title, value, change, foot, icon, tone, chart, chartValue = 0, series = [] }: { title: string; value: string; change: string; foot: string; icon: React.ReactNode; tone: string; chart: string; chartValue?: number; series?: number[] }) {
  return <div className="metric-card"><div className="metric-top"><span>{title}</span><div className={`metric-icon ${tone}`}>{icon}</div></div><div className="metric-value">{value}<span className={tone === 'amber' ? 'warning' : 'positive'}>{change}</span></div><div className="metric-foot">{foot}</div>{chart === 'progress' ? <div className="metric-progress"><i style={{ width: `${Math.round(chartValue * 100)}%` }}/></div> : chart === 'bars' ? <div className="bars" aria-label="Confidence per recent incident">{series.map((confidence, index) => <i key={index} title={`${Math.round(confidence * 100)}%`} style={{ height: `${Math.max(8, Math.round(confidence * 100))}%` }}/>)}</div> : null}</div>;
}

function ActivityCard({ active, events, onViewAll }: { active?: Incident; events: any[]; onViewAll: () => void }) {
  const recent = events.slice(-6).reverse();
  return <div className="activity-card"><div className="card-title-row"><div><h2>Agent activity</h2><p>Persisted decisions and actions</p></div><button className="text-button" onClick={onViewAll}>View all <ArrowRight/></button></div><div className="activity-incident"><div className="activity-symbol"><Wifi/></div><div><b>{active?.number || 'No incidents yet'} <i>·</i> {active?.title || 'Create an incident to begin'}</b><span>{active?.status || 'Waiting'} · {active ? `${percent(active.confidence)} confidence` : ''}</span></div><span className="live-pill"><i/> LIVE</span></div><div className="timeline">{recent.map((event: any, index: number) => <div className="timeline-row" key={`${event.timestamp}-${index}`}><time>{formatTime(event.timestamp)}</time><i className={index === 0 ? 'green' : 'blue'}/><span>{String(event.event).replace(/_/g, ' ')}</span></div>)}{!recent.length && <div className="empty-inline">No events recorded for this incident.</div>}</div><div className="timeline-current"><Zap/> {active?.decision?.escalation_reason || active?.decision?.recommended_action || 'No active analysis'}</div></div>;
}

function SafetyCard({ policy, onOpen }: { policy: any; onOpen: () => void }) {
  return <div className="safety-card"><div className="card-title-row"><div><h2>Safety overview</h2><p>Your guardrails at a glance</p></div><button className="dots" onClick={onOpen} aria-label="Open safety configuration"><MoreHorizontal/></button></div><div className="safety-score"><div className="score-ring"><b>✓<small>ON</small></b></div><div><b>Human oversight enforced</b><span>Policy configuration loaded</span></div><CheckCircle2/></div><div className="guardrail-list"><div><span><i/>Confidence threshold</span><b>≥ {policy ? percent(policy.confidence_auto_threshold) : '—'}</b></div><div><span><i/>Elevated actions</span><b>Approval required</b></div><div><span><i/>Knowledge sources</span><b>{policy?.knowledge_sources ?? '—'} runbooks</b></div></div><button className="guardrail-button" onClick={onOpen}><LockKeyhole/> View safety policies <ArrowRight/></button></div>;
}

function PageHeading({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) { return <section className="page-heading"><div><div className="eyebrow"><i/> NORTHSTAR WORKSPACE</div><h1>{title}</h1><p>{description}</p></div>{action}</section>; }
function EmptyState({ title, detail }: { title: string; detail: string }) { return <div className="empty-state-block"><div className="empty-icon"><Activity/></div><b>{title}</b><span>{detail}</span></div>; }
function Setting({ label, value }: { label: string; value: string | number }) { return <div className="setting-row"><span>{label}</span><b>{value}</b></div>; }
