import React, { useState, useEffect, useRef, useCallback, createContext, useContext } from 'react';
import axios from 'axios';
import ErrorBoundary from './ErrorBoundary';

// ─── Dark Mode Context ────────────────────────────────────────────────
const DarkModeContext = createContext();

function DarkModeProvider({ children }) {
  const [dark, setDark] = useState(() => {
    try {
      const saved = localStorage.getItem('careeros-dark');
      if (saved !== null) return saved === 'true';
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    } catch { return false; }
  });

  useEffect(() => {
    localStorage.setItem('careeros-dark', dark);
    document.documentElement.classList.toggle('dark', dark);
  }, [dark]);

  return (
    <DarkModeContext.Provider value={{ dark, toggle: () => setDark(d => !d) }}>
      {children}
    </DarkModeContext.Provider>
  );
}

function useDarkMode() { return useContext(DarkModeContext); }

// ─── Icons (inline SVGs) ───────────────────────────────────────────────
const Icons = {
  Upload: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8"><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" /></svg>,
  Check: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>,
  External: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4"><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" /></svg>,
  Sparkle: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" /></svg>,
  Briefcase: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0M12 12.75h.008v.008H12v-.008z" /></svg>,
  MapPin: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4"><path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" /></svg>,
  Search: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" /></svg>,
  FileText: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>,
  Close: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>,
  ArrowRight: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4"><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" /></svg>,
  Globe: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" /></svg>,
  Loading: () => <svg className="animate-spin w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>,
  Chart: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" /></svg>,
  Book: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" /></svg>,
  Trophy: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M18.75 4.236c.982.143 1.954.317 2.916.52A6.003 6.003 0 0016.27 9.728M18.75 4.236V4.5c0 2.108-.966 3.99-2.48 5.228m0 0a6.015 6.015 0 01-2.27.308 6.015 6.015 0 01-2.27-.308" /></svg>,
  Roadmap: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M9 6.75V15m6-6v8.25m.503 1.413l-1.503-1.503M5.503 12.413l1.503-1.503M12 3v3.75m6.75 3l-3.75 3.75M5.25 9.75L9 6m9 6l-3.75 3.75" /></svg>,
  Target: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5"><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" /></svg>,
  Star: () => <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24" className="w-4 h-4 text-yellow-400"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>,
  Filter: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" /></svg>,
  Menu: () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" /></svg>,
};

// ─── Platform badge colors ────────────────────────────────────────────
const platformStyles = {
  LinkedIn: 'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800',
  Unstop: 'bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-800',
  Internshala: 'bg-teal-100 text-teal-700 border-teal-200 dark:bg-teal-900/30 dark:text-teal-300 dark:border-teal-800',
  Indeed: 'bg-indigo-100 text-indigo-700 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-300 dark:border-indigo-800',
  'Google Jobs': 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800',
  Wellfound: 'bg-pink-100 text-pink-700 border-pink-200 dark:bg-pink-900/30 dark:text-pink-300 dark:border-pink-800',
  'YC Jobs': 'bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-800',
  Greenhouse: 'bg-cyan-100 text-cyan-700 border-cyan-200 dark:bg-cyan-900/30 dark:text-cyan-300 dark:border-cyan-800',
  Lever: 'bg-violet-100 text-violet-700 border-violet-200 dark:bg-violet-900/30 dark:text-violet-300 dark:border-violet-800',
  Other: 'bg-gray-100 text-gray-700 border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700',
};
const platformFor = (src) => platformStyles[src] || platformStyles.Other;

// ─── Score Color Helper ────────────────────────────────────────────────
const scoreColor = (pct) => {
  if (pct >= 80) return 'text-emerald-600';
  if (pct >= 60) return 'text-blue-600';
  if (pct >= 40) return 'text-amber-600';
  return 'text-red-500';
};

const scoreBg = (pct) => {
  if (pct >= 80) return 'bg-emerald-500';
  if (pct >= 60) return 'bg-blue-500';
  if (pct >= 40) return 'bg-amber-500';
  return 'bg-red-400';
};

const difficultyColor = (d) => {
  if (d === 'easy') return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
  if (d === 'medium') return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300';
  return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
};

// ─── Score Ring Component ──────────────────────────────────────────────
function ScoreRing({ score, size = 48, label }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg className="w-full h-full -rotate-90" viewBox={`0 0 ${size} ${size}`}>
          <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="currentColor" strokeWidth="4" className="text-gray-200 dark:text-slate-600" />
          <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="currentColor" strokeWidth="4"
            strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
            className={scoreColor(score)} style={{ transition: 'stroke-dashoffset 1s ease' }} />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-xs font-bold ${scoreColor(score)}`}>{Math.round(score)}</span>
        </div>
      </div>
      {label && <span className="text-[10px] text-gray-500 dark:text-gray-400 font-medium">{label}</span>}
    </div>
  );
}

// ─── Dark Mode Toggle Icon ─────────────────────────────────────────────
Icons.Sun = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
  </svg>
);
Icons.Moon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
  </svg>
);

// ─── Header ───────────────────────────────────────────────────────────
function Header({ activeTab, setActiveTab }) {
  const { dark, toggle } = useDarkMode();
  const tabs = [
    { id: 'recommend', label: 'AI Recommend', icon: <Icons.Sparkle /> },
    { id: 'dashboard', label: 'Dashboard', icon: <Icons.Chart /> },
    { id: 'learning', label: 'Learn', icon: <Icons.Book /> },
    { id: 'roadmap', label: 'Roadmap', icon: <Icons.Roadmap /> },
    { id: 'certifications', label: 'Certs', icon: <Icons.Trophy /> },
    { id: 'internships', label: 'Board', icon: <Icons.Briefcase /> },
  ];
  return (
    <header className="sticky top-0 z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border-b border-gray-200/60 dark:border-slate-700/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-primary-500/25">C</div>
          <span className="font-display font-bold text-xl bg-gradient-to-r from-primary-600 to-purple-600 bg-clip-text text-transparent hidden sm:block">CareerOS</span>
        </div>
        <div className="flex items-center gap-2">
          <nav className="flex items-center gap-1 bg-gray-100/80 dark:bg-slate-800/80 rounded-xl p-1 overflow-x-auto">
            {tabs.map(t => (
              <button key={t.id} onClick={() => setActiveTab(t.id)}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-200 whitespace-nowrap ${
                  activeTab === t.id ? 'bg-white dark:bg-slate-700 text-primary-600 dark:text-primary-400 shadow-sm' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}`}>
                {t.icon}<span className="hidden sm:inline">{t.label}</span>
              </button>
            ))}
          </nav>
          <button onClick={toggle}
            className="p-2 rounded-xl bg-gray-100/80 dark:bg-slate-800/80 text-gray-500 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 transition-all"
            title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}>
            {dark ? <Icons.Sun /> : <Icons.Moon />}
          </button>
        </div>
      </div>
    </header>
  );
}

// ─── Hero ─────────────────────────────────────────────────────────────
function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-primary-900 via-primary-800 to-purple-900 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900">
      <div className="absolute inset-0">
        <div className="absolute top-20 left-10 w-72 h-72 bg-blue-500/20 rounded-full blur-3xl" />
        <div className="absolute bottom-10 right-10 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl" />
      </div>
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24 text-center">
        <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm border border-white/20 rounded-full px-4 py-1.5 mb-6">
          <Icons.Sparkle />        <span className="text-sm text-blue-200 dark:text-slate-300 font-medium">AI Career Intelligence</span>
        </div>
        <h1 className="font-display font-extrabold text-3xl sm:text-5xl lg:text-6xl text-white leading-tight mb-6">
          Not Just Jobs.<br />
          <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">Career Intelligence.</span>
        </h1>
        <p className="text-blue-200 dark:text-slate-300 text-lg sm:text-xl max-w-2xl mx-auto mb-10">
          Upload your resume. We analyze 8+ platforms, score every opportunity, explain why it matches, and build your career roadmap.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4 text-sm text-blue-300 dark:text-slate-400">
          <span className="flex items-center gap-1.5"><Icons.Check /> 15+ platforms</span>
          <span className="flex items-center gap-1.5"><Icons.Check /> Match scoring</span>
          <span className="flex items-center gap-1.5"><Icons.Check /> Career roadmap</span>
          <span className="flex items-center gap-1.5"><Icons.Check /> Learning paths</span>
        </div>
      </div>
    </section>
  );
}

// ─── Search Filters Panel ─────────────────────────────────────────────
function SearchFilters({ filters, setFilters }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-4">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 font-medium transition-colors">
        <Icons.Filter /> {open ? 'Hide Filters' : 'Show Filters'}
        {!open && <span className="text-xs bg-primary-100 text-primary-600 px-2 py-0.5 rounded-full">{filters.job_type} · {filters.sort_by || 'newest'}</span>}
      </button>
      {open && (
        <div className="mt-3 bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 p-5 space-y-4 animate-slide-up">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <label className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">Job Type</label>
              <select value={filters.job_type} onChange={e => setFilters({...filters, job_type: e.target.value})}
                className="mt-1 w-full px-3 py-2 rounded-xl border border-gray-200 text-sm focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none dark:bg-slate-700 dark:border-slate-600 dark:text-white dark:focus:border-primary-500 dark:focus:ring-primary-900">
                <option value="internship">Internship</option>
                <option value="full-time">Full-Time</option>
                <option value="both">Both</option>
                <option value="contract">Contract</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Work Style</label>
              <select value={filters.work_style} onChange={e => setFilters({...filters, work_style: e.target.value})}
                className="mt-1 w-full px-3 py-2 rounded-xl border border-gray-200 text-sm focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none dark:bg-slate-700 dark:border-slate-600 dark:text-white dark:focus:border-primary-500 dark:focus:ring-primary-900">
                <option value="any">Any</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="on-site">On-site</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Experience</label>
              <select value={filters.experience_level} onChange={e => setFilters({...filters, experience_level: e.target.value})}
                className="mt-1 w-full px-3 py-2 rounded-xl border border-gray-200 text-sm focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none dark:bg-slate-700 dark:border-slate-600 dark:text-white dark:focus:border-primary-500 dark:focus:ring-primary-900">
                <option value="0-1">0-1 years</option>
                <option value="1-3">1-3 years</option>
                <option value="3-5">3-5 years</option>
                <option value="5+">5+ years</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Location</label>
              <input type="text" value={filters.city} onChange={e => setFilters({...filters, city: e.target.value})}
                placeholder="City" className="mt-1 w-full px-3 py-2 rounded-xl border border-gray-200 text-sm focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none dark:bg-slate-700 dark:border-slate-600 dark:text-white dark:focus:border-primary-500 dark:focus:ring-primary-900" />
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Date Posted</label>
              <select value={filters.recency || 'week'} onChange={e => setFilters({...filters, recency: e.target.value})}
                className="mt-1 w-full px-3 py-2 rounded-xl border border-gray-200 text-sm focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none dark:bg-slate-700 dark:border-slate-600 dark:text-white">
                <option value="today">Today</option>
                <option value="24h">Past 24 Hours</option>
                <option value="3days">Past 3 Days</option>
                <option value="week">Past Week</option>
                <option value="month">Past Month</option>
                <option value="all">All Time</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Sort By</label>
              <select value={filters.sort_by || 'newest'} onChange={e => setFilters({...filters, sort_by: e.target.value})}
                className="mt-1 w-full px-3 py-2 rounded-xl border border-gray-200 text-sm focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none dark:bg-slate-700 dark:border-slate-600 dark:text-white">
                <option value="newest">Newest First</option>
                <option value="match">Highest Match</option>
                <option value="salary">Highest Salary</option>
                <option value="faang">Top Companies</option>
                <option value="startups">Top Startups</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Preferred Tech Stack</label>
              <input type="text" value={filters.preferred_tech} onChange={e => setFilters({...filters, preferred_tech: e.target.value})}
                placeholder="Python, React, Docker" className="mt-1 w-full px-3 py-2 rounded-xl border border-gray-200 text-sm focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none dark:bg-slate-700 dark:border-slate-600 dark:text-white" />
            </div>
          </div>
          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
              <input type="checkbox" checked={filters.easy_apply_only || false} onChange={e => setFilters({...filters, easy_apply_only: e.target.checked})} className="w-4 h-4 rounded border-gray-300 text-primary-600" /> Easy Apply Only
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
              <input type="checkbox" checked={filters.faang_only || false} onChange={e => setFilters({...filters, faang_only: e.target.checked})} className="w-4 h-4 rounded border-gray-300 text-primary-600" /> FAANG Only
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
              <input type="checkbox" checked={filters.startups_only || false} onChange={e => setFilters({...filters, startups_only: e.target.checked})} className="w-4 h-4 rounded border-gray-300 text-primary-600" /> Startups Only
            </label>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Resume Upload Zone ───────────────────────────────────────────────
function UploadZone({ file, setFile, onAnalyze, loading, filters, setFilters }) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);
  const handleDrop = useCallback((e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files?.[0]; if (f && f.type === 'application/pdf') setFile(f); }, [setFile]);
  const handleSelect = (e) => { const f = e.target.files?.[0]; if (f) setFile(f); };

  return (
    <div className="max-w-2xl mx-auto animate-fade-in">
      <SearchFilters filters={filters} setFilters={setFilters} />
      <div
        className={`relative border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-300 cursor-pointer group ${
          dragOver ? 'border-primary-500 bg-primary-50/50 dark:bg-primary-900/20 scale-[1.02]' : file ? 'border-green-400 bg-green-50/30 dark:bg-green-900/10' : 'border-gray-300 dark:border-slate-600 hover:border-primary-400 hover:bg-gray-50 dark:hover:bg-slate-800'}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}>
        <input ref={inputRef} type="file" accept=".pdf" onChange={handleSelect} className="hidden" />
        {file ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-green-100 dark:bg-green-900/30 flex items-center justify-center text-green-600"><Icons.Check /></div>
            <div><p className="font-semibold text-gray-900 dark:text-white">{file.name}</p><p className="text-sm text-gray-500 dark:text-gray-400">{(file.size / 1024).toFixed(1)} KB</p></div>
            <button onClick={(e) => { e.stopPropagation(); setFile(null); }} className="text-sm text-red-500 hover:text-red-700 font-medium">Remove</button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center text-primary-500 group-hover:scale-110 transition-transform"><Icons.Upload /></div>
            <div><p className="font-semibold text-gray-900 dark:text-white">Drop your resume here</p><p className="text-sm text-gray-500 dark:text-gray-400 mt-1">PDF only · Max 10 MB</p></div>
          </div>
        )}
      </div>
      <button onClick={onAnalyze} disabled={!file || loading}
        className={`w-full mt-5 py-4 rounded-2xl font-semibold text-lg transition-all duration-300 flex items-center justify-center gap-3 ${
          file && !loading ? 'bg-gradient-to-r from-primary-600 to-purple-600 text-white shadow-xl hover:shadow-2xl hover:scale-[1.02] active:scale-[0.98]' : 'bg-gray-100 dark:bg-slate-800 text-gray-400 dark:text-slate-500 cursor-not-allowed'}`}>
        {loading ? <><Icons.Loading /> Analyzing Career Profile...</> : <><Icons.Search /> Get Career Intelligence</>}
      </button>
    </div>
  );
}

// ─── Resume Summary ───────────────────────────────────────────────────
function ResumeSummary({ data }) {
  if (!data) return null;
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-gray-100 dark:border-slate-700 overflow-hidden animate-slide-up">
      <div className="bg-gradient-to-r from-primary-600 to-purple-600 px-6 py-4">
        <h3 className="text-white font-display font-bold flex items-center gap-2"><Icons.Check /> Resume Parsed</h3>
      </div>
      <div className="p-6 space-y-5">
        {data.target_roles?.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">🎯 Target Roles (AI Inferred)</h4>
            <div className="flex flex-wrap gap-2">{data.target_roles.map((r, i) => (
              <span key={i} className="px-3 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/30 dark:to-purple-900/30 text-primary-700 dark:text-primary-300 border border-primary-100 dark:border-primary-800/50">{r}</span>
            ))}</div>
          </div>
        )}
        {data.skills?.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">Skills Detected ({data.skills.length})</h4>
            <div className="flex flex-wrap gap-2">{data.skills.map((s, i) => (
              <span key={i} className="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-slate-600">{s}</span>
            ))}</div>
          </div>
        )}
        <div className="grid grid-cols-2 gap-4">
          {data.education?.length > 0 && <div><h4 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">Education</h4>{data.education.map((e, i) => <p key={i} className="text-sm text-gray-700 dark:text-gray-300">🎓 {e}</p>)}</div>}
          {data.experience?.length > 0 && <div><h4 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">Experience</h4>{data.experience.map((e, i) => <p key={i} className="text-sm text-gray-700 dark:text-gray-300">💼 {e}</p>)}</div>}
        </div>
      </div>
    </div>
  );
}

// ─── Job Card with Intelligence Scores ────────────────────────────────
function JobCard({ job, onSelect }) {
  const { job: j, intelligence: intel } = job;
  const cls = platformFor(j.source);
  return (
    <div onClick={() => onSelect?.(job)} className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 p-5 card-hover hover:border-primary-200 dark:hover:border-primary-800 cursor-pointer group">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${cls}`}>{j.source}</span>
            {j.remote && <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800">Remote</span>}
          </div>
          <h4 className="font-semibold text-gray-900 dark:text-white group-hover:text-primary-600 transition-colors truncate">{j.title}</h4>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">{j.company}</p>
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1"><Icons.MapPin /> {j.location}</span>
            {j.salary && <span>💰 {j.salary}</span>}
            {j.stipend && <span>💰 {j.stipend}</span>}
            {j.freshness_badge && <span className="text-emerald-600 font-medium">{j.freshness_badge}</span>}
          </div>
        </div>
        <ScoreRing score={intel.overall_match_pct} size={52} label="Match" />
      </div>

      {/* Score bars */}
      <div className="mt-4 space-y-2">
        {[
          { label: 'Skills', pct: intel.skill_match_pct },
          { label: 'Experience', pct: intel.experience_match_pct },
          { label: 'Location', pct: intel.location_match_pct },
        ].map(s => (
          <div key={s.label} className="flex items-center gap-2">
            <span className="text-[10px] text-gray-400 dark:text-gray-500 w-16">{s.label}</span>
            <div className="flex-1 h-1.5 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${scoreBg(s.pct)}`} style={{ width: `${s.pct}%` }} />
            </div>
            <span className={`text-[10px] font-medium w-8 text-right ${scoreColor(s.pct)}`}>{Math.round(s.pct)}%</span>
          </div>
        ))}
      </div>

      {/* Match explanation preview */}
      {intel.match_explanation?.reasons_for?.length > 0 && (
        <div className="mt-3 text-xs text-gray-500">
          {intel.match_explanation.reasons_for.slice(0, 2).map((r, i) => (
            <span key={i} className="text-emerald-600">{r} </span>
          ))}
        </div>
      )}

      <div className="mt-3 flex items-center justify-between">
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${difficultyColor(intel.difficulty)}`}>
          {intel.difficulty} · {intel.estimated_learning_time}
        </span>
        <div className="flex items-center gap-2 text-xs">
          {intel.hiring_probability > 0 && <span className="text-blue-600 dark:text-blue-400 font-medium">{Math.round(intel.hiring_probability)}% hire</span>}
          <span className="text-primary-500 dark:text-primary-400 group-hover:text-primary-600 transition-colors font-medium flex items-center gap-1">
            Details <Icons.ArrowRight />
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Job Details Modal ────────────────────────────────────────────────
function JobDetailsModal({ details, onClose, loading }) {
  useEffect(() => {
    const handleEsc = (e) => { if (e.key === 'Escape') onClose(); };
    if (details || loading) {
      document.addEventListener('keydown', handleEsc);
      document.body.style.overflow = 'hidden';
    }
    return () => { document.removeEventListener('keydown', handleEsc); document.body.style.overflow = ''; };
  }, [details, loading, onClose]);
  if (!details && !loading) return null;
  if (loading) return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-slate-800 rounded-3xl max-w-2xl w-full p-12 shadow-2xl flex flex-col items-center gap-4" onClick={e => e.stopPropagation()}>
        <Icons.Loading />
        <p className="text-gray-500 dark:text-gray-400 font-medium">Analyzing job match...</p>
      </div>
    </div>
  );
  const { job: j, intelligence: intel } = details;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-slate-800 rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl animate-slide-up" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="sticky top-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl border-b border-gray-100 dark:border-slate-700 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <ScoreRing score={intel.overall_match_pct} size={48} />
            <div>
              <h2 className="font-display font-bold text-lg text-gray-900 dark:text-white truncate">{j.title}</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">{j.company} · {j.location}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-xl"><Icons.Close /></button>
        </div>

        <div className="p-6 space-y-6">
          {/* Score Grid */}
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Skills', pct: intel.skill_match_pct },
              { label: 'Experience', pct: intel.experience_match_pct },
              { label: 'Opportunity', pct: intel.opportunity_score },
              { label: 'Growth', pct: intel.career_growth_score },
            ].map(s => (
              <div key={s.label} className="text-center p-3 bg-gray-50 dark:bg-slate-700 rounded-xl">
                <ScoreRing score={s.pct} size={40} />
                <span className="text-xs text-gray-500 mt-1 block">{s.label}</span>
              </div>
            ))}
          </div>

          {/* Match Explanation */}
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-2xl p-5">
            <h3 className="font-display font-bold text-sm text-gray-900 dark:text-white mb-3">Why This Match?</h3>
            <div className="space-y-2">
              {intel.match_explanation?.reasons_for?.map((r, i) => (
                <p key={i} className="text-sm text-emerald-700">{r}</p>
              ))}
              {intel.match_explanation?.reasons_against?.map((r, i) => (
                <p key={i} className="text-sm text-red-600">{r}</p>
              ))}
            </div>
          </div>

          {/* Skills */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-2xl p-4">
              <h4 className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 uppercase mb-2">Skills You Have</h4>
              <div className="flex flex-wrap gap-1">{intel.match_explanation?.matched_skills?.map((s, i) => (
                <span key={i} className="px-2 py-0.5 rounded-full text-xs bg-emerald-100 dark:bg-emerald-800/50 text-emerald-700 dark:text-emerald-300">{s}</span>
              ))}</div>
            </div>
            <div className="bg-amber-50 dark:bg-amber-900/20 rounded-2xl p-4">
              <h4 className="text-xs font-semibold text-amber-700 dark:text-amber-400 uppercase mb-2">Missing Skills</h4>
              <div className="flex flex-wrap gap-1">{intel.match_explanation?.missing_skills?.map((s, i) => (
                <span key={i} className="px-2 py-0.5 rounded-full text-xs bg-amber-100 dark:bg-amber-800/50 text-amber-700 dark:text-amber-300">{s}</span>
              ))}</div>
            </div>
          </div>

          {/* Resume Suggestions */}
          {details.resume_suggestions?.length > 0 && (
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-2xl p-5">
              <h3 className="font-display font-bold text-sm text-gray-900 dark:text-white mb-3">📋 Resume Suggestions</h3>
              <ul className="space-y-2">{details.resume_suggestions.map((s, i) => (
                <li key={i} className="text-sm text-blue-700 flex items-start gap-2">
                  <span className="mt-0.5">•</span>{s}
                </li>
              ))}</ul>
            </div>
          )}

          {/* Interview */}
          {details.likely_questions?.length > 0 && (
            <div className="bg-purple-50 dark:bg-purple-900/20 rounded-2xl p-5">
              <h3 className="font-display font-bold text-sm text-gray-900 dark:text-white mb-3">🎤 Likely Interview Questions</h3>
              <ul className="space-y-2">{details.likely_questions.map((q, i) => (
                <li key={i} className="text-sm text-purple-700">{i + 1}. {q}</li>
              ))}</ul>
            </div>
          )}

          {/* AI Recommendation */}
          {details.ai_recommendation && (
            <div className="bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 rounded-2xl border border-amber-200 dark:border-amber-800/50 p-5">
              <h3 className="font-display font-bold text-sm text-gray-900 mb-3"><Icons.Sparkle /> AI Recommendation</h3>
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{details.ai_recommendation}</p>
            </div>
          )}

          {/* Apply Button */}
          <a href={j.apply_link} target="_blank" rel="noopener noreferrer"
            className="block w-full py-4 rounded-2xl bg-gradient-to-r from-primary-600 to-purple-600 text-white font-semibold text-center hover:shadow-xl transition-all">
            Apply on {j.source} →
          </a>
        </div>
      </div>
    </div>
  );
}

// ─── AI Suggestions ───────────────────────────────────────────────────
function AISuggestions({ text }) {
  if (!text) return null;
  return (
    <div className="bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 rounded-2xl border border-amber-200 dark:border-amber-800/50 p-6 animate-slide-up">
      <h3 className="font-display font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-3"><Icons.Sparkle /> AI Career Recommendations</h3>
      <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">{text}</div>
    </div>
  );
}

// ─── Learning Section ─────────────────────────────────────────────────
function LearningSection({ learning, certifications }) {
  if (!learning?.length && !certifications?.length) return null;
  return (
    <div className="space-y-6 animate-slide-up">
      {learning?.length > 0 && (
        <div>
          <h3 className="font-display font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-4"><Icons.Book /> Recommended Learning</h3>
          <div className="grid gap-3 sm:grid-cols-2">{learning.map((l, i) => (
            <a key={i} href={l.url} target="_blank" rel="noopener noreferrer"
              className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 p-5 card-hover hover:border-primary-200 dark:hover:border-primary-800 group">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <span className="text-xs text-gray-400 font-medium">{l.provider}</span>
                  <h4 className="font-semibold text-gray-900 group-hover:text-primary-600 text-sm mt-0.5">{l.resource_name}</h4>
                  <p className="text-xs text-gray-500 mt-1">For: {l.skill}</p>
                </div>
                <ScoreRing score={l.learning_match_pct} size={36} />
              </div>
              <div className="mt-3 flex items-center gap-3 text-xs text-gray-500">
                <span>⏱ {l.estimated_time}</span>
                <span className={`px-1.5 py-0.5 rounded ${difficultyColor(l.difficulty)}`}>{l.difficulty}</span>
                {l.certificate_available && <span className="text-emerald-600">✓ Certificate</span>}
              </div>
              <div className="mt-2 flex items-center gap-2">
                <span className="text-xs text-emerald-600">Resume +{l.resume_improvement_pct}%</span>
                <span className="text-xs text-blue-600">Career impact: {l.career_impact_pct}%</span>
              </div>
            </a>
          ))}</div>
        </div>
      )}
      {certifications?.length > 0 && (
        <div>
          <h3 className="font-display font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-4"><Icons.Trophy /> Recommended Certifications</h3>
          <div className="grid gap-3 sm:grid-cols-2">{certifications.map((c, i) => (
            <a key={i} href={c.url} target="_blank" rel="noopener noreferrer"
              className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 p-5 card-hover hover:border-primary-200 dark:hover:border-primary-800 group">
              <h4 className="font-semibold text-gray-900 dark:text-white group-hover:text-primary-600 text-sm">{c.name}</h4>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{c.provider}</p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <span className="text-emerald-600">Resume +{c.resume_match_increase}%</span>
                <span className="text-blue-600">Salary {c.estimated_salary_impact}</span>
                <span className="text-purple-600">⏱ {c.learning_time}</span>
                <span className={`px-1.5 py-0.5 rounded ${difficultyColor(c.difficulty)}`}>{c.difficulty}</span>
              </div>
            </a>
          ))}</div>
        </div>
      )}
    </div>
  );
}

// ─── ROI Section ──────────────────────────────────────────────────────
function ROISection({ roi_actions }) {
  if (!roi_actions?.length) return null;
  return (
    <div className="animate-slide-up">
      <h3 className="font-display font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-4"><Icons.Target /> Resume ROI — Highest Career Return</h3>
      <div className="space-y-3">{roi_actions.slice(0, 8).map((a, i) => (
        <div key={i} className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 p-4 flex items-center gap-4">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-sm ${
            a.category === 'skill' ? 'bg-blue-500' : a.category === 'certification' ? 'bg-purple-500' : a.category === 'project' ? 'bg-emerald-500' : 'bg-amber-500'
          }`}>+{a.resume_increase_pct}%</div>
          <div className="flex-1">
            <p className="font-medium text-gray-900 dark:text-white text-sm">{a.action}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">⏱ {a.estimated_time} · {a.difficulty}</p>
          </div>
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
            a.career_impact === 'high' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
          }`}>{a.career_impact}</span>
        </div>
      ))}</div>
    </div>
  );
}

// ─── Roadmap Section ──────────────────────────────────────────────────
function RoadmapSection({ roadmap }) {
  if (!roadmap) return null;
  const phases = [
    { label: 'Days 1-30', subtitle: 'Foundation', tasks: roadmap.day_30, color: 'from-blue-500 to-blue-600' },
    { label: 'Days 31-60', subtitle: 'Growth', tasks: roadmap.day_60, color: 'from-purple-500 to-purple-600' },
    { label: 'Days 61-90', subtitle: 'Mastery', tasks: roadmap.day_90, color: 'from-emerald-500 to-emerald-600' },
  ];
  return (
    <div className="space-y-6 animate-slide-up">
      <div className="flex items-center justify-between">
        <h3 className="font-display font-bold text-gray-900 flex items-center gap-2"><Icons.Roadmap /> 30/60/90 Day Career Roadmap</h3>
        <span className="text-sm text-emerald-600 font-medium">Total score increase: +{roadmap.total_career_score_increase}%</span>
      </div>
      {phases.map((p, pi) => (
        <div key={pi} className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 overflow-hidden">
          <div className={`bg-gradient-to-r ${p.color} px-6 py-4`}>
            <h4 className="text-white font-display font-bold">{p.label}</h4>
            <p className="text-white/70 text-sm">{p.subtitle}</p>
          </div>
          <div className="p-5 space-y-3">{p.tasks.map((t, ti) => (
            <div key={ti} className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-lg bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center text-primary-600 dark:text-primary-400 text-xs font-bold shrink-0 mt-0.5">
                {ti + 1}
              </div>
              <div className="flex-1">
                <p className="text-sm text-gray-900 dark:text-white font-medium">{t.task}</p>
                <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-gray-400">
                  <span>⏱ {t.estimated_time}</span>
                  <span>•</span>
                  <span className="text-emerald-600">+{t.career_score_impact}%</span>
                </div>
              </div>
            </div>
          ))}</div>
        </div>
      ))}
    </div>
  );
}

// ─── Dashboard Section ────────────────────────────────────────────────
function DashboardSection({ dashboard }) {
  if (!dashboard) return null;
  const metrics = [
    { label: 'Career Score', value: dashboard.career_score, change: dashboard.career_score_change, color: 'from-primary-500 to-purple-600' },
    { label: 'Resume Strength', value: dashboard.resume_strength, color: 'from-blue-500 to-cyan-500' },
    { label: 'Interview Readiness', value: dashboard.interview_readiness, color: 'from-emerald-500 to-teal-500' },
    { label: 'Skill Gap', value: dashboard.skill_gap_score, color: 'from-amber-500 to-orange-500' },
  ];

  return (
    <div className="space-y-6 animate-slide-up">
      {/* AI Daily Insight */}
      <div className="bg-gradient-to-br from-primary-600 to-purple-700 rounded-2xl p-6 text-white">
        <div className="flex items-center gap-2 mb-3">
          <Icons.Sparkle /><span className="font-display font-bold">AI Daily Insight</span>
        </div>
        <p className="text-white/90 leading-relaxed">{dashboard.ai_daily_insight}</p>
      </div>

      {/* Score Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m, i) => (
          <div key={i} className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 p-5 text-center">
            <div className={`w-12 h-12 mx-auto rounded-2xl bg-gradient-to-br ${m.color} flex items-center justify-center mb-3`}>
              <ScoreRing score={m.value} size={40} />
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">{m.label}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{Math.round(m.value)}%</p>
            {m.change > 0 && <p className="text-xs text-emerald-600 mt-1">↑ +{m.change}%</p>}
          </div>
        ))}
      </div>

      {/* Today's Goal */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 p-6">
        <h3 className="font-display font-bold text-gray-900 dark:text-white mb-3">🎯 Today's Goal</h3>
        <p className="text-gray-700 dark:text-gray-300">{dashboard.today_goal}</p>
      </div>

      {/* Recommended Actions */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 p-6">
        <h3 className="font-display font-bold text-gray-900 dark:text-white mb-3">⚡ Recommended Actions</h3>
        <ul className="space-y-2">{dashboard.recommended_actions?.map((a, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
            <span className="text-primary-500 mt-0.5">•</span>{a}
          </li>
        ))}</ul>
      </div>

      {/* Top Missing Skills */}
      {dashboard.top_missing_skills?.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 p-6">
          <h3 className="font-display font-bold text-gray-900 dark:text-white mb-3">🔴 Top Missing Skills</h3>
          <div className="flex flex-wrap gap-2">{dashboard.top_missing_skills.map((s, i) => (
            <span key={i} className="px-3 py-1 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200">{s}</span>
          ))}</div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'New Opportunities', value: dashboard.new_opportunities },
          { label: 'Learning Progress', value: `${Math.round(dashboard.learning_progress)}%` },
          { label: 'Weekly Improvement', value: `+${dashboard.weekly_improvement}%` },
        ].map((s, i) => (
          <div key={i} className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 p-4 text-center">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{s.value}</p>
            <p className="text-xs text-gray-500 mt-1">{s.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Results View ─────────────────────────────────────────────────────
function ResultsView({ results, onReset, onSelectJob }) {
  if (!results) return null;
  const { resume_data, jobs, ai_suggestions, sources_searched, learning, certifications, roi_actions, career_roadmap, dashboard } = results;
  const grouped = {};
  jobs.forEach(j => { (grouped[j.job.source] = grouped[j.job.source] || []).push(j); });

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="bg-gradient-to-r from-green-500 to-emerald-600 dark:from-emerald-600 dark:to-teal-600 rounded-2xl p-6 text-white flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center"><Icons.Check /></div>
          <div>
            <h3 className="font-bold text-lg">Career Analysis Complete!</h3>
            <p className="text-green-100 text-sm">{jobs.length} scored opportunities across {sources_searched?.length || 0} platforms</p>
          </div>
        </div>
        <button onClick={onReset} className="bg-white/20 hover:bg-white/30 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all">New Search</button>
      </div>

      {/* Dashboard summary cards at top */}
      {dashboard && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Career Score', value: dashboard.career_score, change: dashboard.career_score_change },
            { label: 'Resume Strength', value: dashboard.resume_strength },
            { label: 'Interview Readiness', value: dashboard.interview_readiness },
            { label: 'New Opportunities', value: dashboard.new_opportunities, isCount: true },
          ].map((m, i) => (
            <div key={i} className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 p-4 text-center">
              <p className={`text-2xl font-bold ${scoreColor(m.isCount ? m.value * 10 : m.value)}`}>{m.isCount ? m.value : Math.round(m.value) + '%'}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{m.label}</p>
              {m.change > 0 && <p className="text-xs text-emerald-600">↑ +{m.change}%</p>}
            </div>
          ))}
        </div>
      )}

      {/* Resume Summary */}
      <ResumeSummary data={resume_data} />

      {/* AI Suggestions */}
      <AISuggestions text={ai_suggestions} />

      {/* ROI */}
      <ROISection roi_actions={roi_actions} />

      {/* Jobs */}
      <div>
        <h3 className="font-display font-bold text-gray-900 dark:text-white text-xl mb-4">{jobs.length} Scored Opportunities</h3>
        {Object.entries(grouped).map(([src, list]) => (
          <div key={src} className="mb-6">
            <h4 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">{src} ({list.length})</h4>
            <div className="grid gap-3 sm:grid-cols-2">{list.map((j, i) => <JobCard key={j.job.id || i} job={j} onSelect={onSelectJob} />)}</div>
          </div>
        ))}
      </div>

      {/* Learning */}
      <LearningSection learning={learning} certifications={certifications} />

      {/* Roadmap */}
      <RoadmapSection roadmap={career_roadmap} />
    </div>
  );
}

// ─── Internship Form ──────────────────────────────────────────────────
function InternshipForm({ onSuccess }) {
  const empty = { title: '', company: '', location: '', description: '', stipend: '', remote: false, apply_link: '' };
  const [form, setForm] = useState(empty);
  const [busy, setBusy] = useState(false);
  const h = (e) => { const { name, value, type, checked } = e.target; setForm(p => ({ ...p, [name]: type === 'checkbox' ? checked : value })); };
  const submit = async (e) => { e.preventDefault(); setBusy(true); try { await axios.post('/api/internships', form); setForm(empty); onSuccess?.(); } finally { setBusy(false); } };

  return (
    <form onSubmit={submit} className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 p-6 space-y-4">
      <h3 className="font-display font-bold text-gray-900 flex items-center gap-2"><Icons.Briefcase /> Add Internship</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <input name="title" value={form.title} onChange={h} placeholder="Title *" required className="px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none text-sm dark:bg-slate-700 dark:border-slate-600 dark:text-white dark:focus:border-primary-500 dark:focus:ring-primary-900" />
        <input name="company" value={form.company} onChange={h} placeholder="Company *" required className="px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none text-sm dark:bg-slate-700 dark:border-slate-600 dark:text-white dark:focus:border-primary-500 dark:focus:ring-primary-900" />
        <input name="location" value={form.location} onChange={h} placeholder="Location *" required className="px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none text-sm dark:bg-slate-700 dark:border-slate-600 dark:text-white dark:focus:border-primary-500 dark:focus:ring-primary-900" />
        <input name="stipend" value={form.stipend} onChange={h} placeholder="Stipend" className="px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none text-sm dark:bg-slate-700 dark:border-slate-600 dark:text-white dark:focus:border-primary-500 dark:focus:ring-primary-900" />
        <input name="apply_link" value={form.apply_link} onChange={h} placeholder="Apply Link *" required className="px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none text-sm sm:col-span-2" />
        <textarea name="description" value={form.description} onChange={h} placeholder="Description *" required rows={3} className="px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 outline-none text-sm sm:col-span-2 resize-none dark:bg-slate-700 dark:border-slate-600 dark:text-white dark:focus:border-primary-500 dark:focus:ring-primary-900" />
      </div>
      <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
        <input name="remote" type="checkbox" checked={form.remote} onChange={h} className="w-4 h-4 rounded border-gray-300 text-primary-600" /> Remote
      </label>
      <button type="submit" disabled={busy} className="bg-primary-600 hover:bg-primary-700 text-white font-medium px-6 py-3 rounded-xl transition-all disabled:opacity-50 flex items-center gap-2">
        {busy ? <><Icons.Loading /> Adding...</> : <><Icons.Check /> Add Internship</>}
      </button>
    </form>
  );
}

// ─── Internship List ──────────────────────────────────────────────────
function InternshipList({ items, onDelete }) {
  if (!items?.length) return <p className="text-center text-gray-400 py-12">No internships yet.</p>;
  return (
    <div className="space-y-3">{items.map(int => (
      <div key={int.id} className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 p-5 card-hover flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-gray-900 dark:text-white truncate">{int.title}</h4>
          <p className="text-sm text-gray-600 dark:text-gray-400">{int.company}</p>
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1"><Icons.MapPin /> {int.location}</span>
            {int.stipend && <span>💰 {int.stipend}</span>}
            {int.remote && <span className="bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300 px-2 py-0.5 rounded-full">Remote</span>}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {int.apply_link && <a href={int.apply_link} target="_blank" rel="noopener noreferrer" className="p-2 text-primary-500 hover:bg-primary-50 rounded-lg"><Icons.External /></a>}
          <button onClick={() => onDelete(int.id)} className="p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg"><Icons.Close /></button>
        </div>
      </div>
    ))}</div>
  );
}

// ─── Footer ───────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="border-t border-gray-100 dark:border-slate-800 bg-white dark:bg-slate-900 mt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-gray-400 dark:text-gray-500">
        <span>CareerOS v4.0 © 2026 · AI Career Intelligence Engine</span>
        <span className="flex items-center gap-2"><Icons.Globe /> 15+ platforms · AI-powered intelligence</span>
      </div>
    </footer>
  );
}

// ─── Certifications Discovery Page ─────────────────────────────────────
function CertificationsPage({ skills }) {
  const [certs, setCerts] = useState([]);
  const [providers, setProviders] = useState([]);
  const [categories, setCategories] = useState([]);
  const [filter, setFilter] = useState('all');
  const [freeOnly, setFreeOnly] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await axios.post('/api/certifications/discover', { skills: skills || [], free_only: freeOnly, category: filter === 'all' ? null : filter });
        setCerts(r.data.certifications || []);
        setProviders(r.data.providers || []);
        setCategories(r.data.categories || []);
      } catch { setCerts([]); } finally { setLoading(false); }
    };
    load();
  }, [skills, filter, freeOnly]);

  if (loading) return <div className="flex items-center justify-center py-20"><Icons.Loading /><span className="ml-3 text-gray-500">Loading certifications...</span></div>;

  return (
    <div className="space-y-6 animate-fade-in">
      <h2 className="font-display font-bold text-2xl sm:text-3xl text-gray-900 dark:text-white">Certification Discovery</h2>
      <p className="text-gray-500 dark:text-gray-400">Discover {certs.length} certifications from {providers.length} providers, ranked by relevance to your skills.</p>
      <div className="flex flex-wrap items-center gap-3">
        <select value={filter} onChange={e => setFilter(e.target.value)} className="px-3 py-2 rounded-xl border border-gray-200 text-sm dark:bg-slate-700 dark:border-slate-600 dark:text-white">
          <option value="all">All Categories</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
          <input type="checkbox" checked={freeOnly} onChange={e => setFreeOnly(e.target.checked)} className="w-4 h-4 rounded border-gray-300 text-primary-600" /> Free Only
        </label>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {certs.map((c, i) => (
          <a key={i} href={c.url} target="_blank" rel="noopener noreferrer" className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 p-5 card-hover hover:border-primary-200 dark:hover:border-primary-800 group">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <h4 className="font-semibold text-gray-900 dark:text-white group-hover:text-primary-600 text-sm leading-tight">{c.name}</h4>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{c.provider}</p>
              </div>
              <ScoreRing score={c.relevance_score || 0} size={40} />
            </div>
            <div className="flex flex-wrap gap-2 mb-3">
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${c.free ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'}`}>{c.free ? 'Free' : c.exam_cost || 'Paid'}</span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${difficultyColor(c.difficulty)}`}>{c.difficulty}</span>
              {c.category && <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">{c.category}</span>}
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="text-center"><p className="font-bold text-emerald-600">+{c.resume_boost_pct || 0}%</p><p className="text-gray-400">Resume</p></div>
              <div className="text-center"><p className="font-bold text-blue-600">+{c.salary_impact_pct || 0}%</p><p className="text-gray-400">Salary</p></div>
              <div className="text-center"><p className="font-bold text-purple-600">{c.study_hours || 0}h</p><p className="text-gray-400">Study</p></div>
            </div>
            {c.related_skills?.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">{c.related_skills.slice(0, 3).map((s, j) => <span key={j} className="px-1.5 py-0.5 rounded text-[10px] bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-400">{s}</span>)}</div>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState('recommend');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [toast, setToast] = useState(null);
  const [internships, setInternships] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobDetails, setJobDetails] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [filters, setFilters] = useState({
    job_type: 'internship', work_style: 'any', city: '', experience_level: '0-1', preferred_tech: '',
    recency: 'week', sort_by: 'newest', easy_apply_only: false, faang_only: false, startups_only: false,
  });

  useEffect(() => { axios.get('/api/internships').then(r => setInternships(r.data)).catch(() => {}); }, []);

  const showToast = (msg, type = 'success') => { setToast({ msg, type }); setTimeout(() => setToast(null), 4000); };

  const analyze = async () => {
    if (!file) return;
    setLoading(true); setResults(null);
    const fd = new FormData();
    fd.append('file', file);
    fd.append('job_type', filters.job_type);
    fd.append('work_style', filters.work_style);
    fd.append('experience_level', filters.experience_level);
    fd.append('recency', filters.recency || 'week');
    fd.append('sort_by', filters.sort_by || 'newest');
    if (filters.city) fd.append('location', filters.city);
    if (filters.preferred_tech) fd.append('preferred_tech', filters.preferred_tech);
    if (filters.easy_apply_only) fd.append('easy_apply_only', 'true');
    if (filters.faang_only) fd.append('faang_only', 'true');
    if (filters.startups_only) fd.append('startups_only', 'true');
    try {
      const r = await axios.post('/api/recommendations', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      setResults(r.data);
      showToast(`Found and scored ${r.data.jobs?.length || 0} opportunities!`);
    } catch (err) {
      showToast(err.response?.data?.detail || 'Analysis failed. Try again.', 'error');
    } finally { setLoading(false); }
  };

  const selectJob = async (scoredJob) => {
    setSelectedJob(scoredJob);
    setDetailsLoading(true);
    setJobDetails(null);
    try {
      // Send resume text as JSON instead of re-uploading the PDF
      const r = await axios.post('/api/job-details-json', {
        resume_text: results?.resume_data?.text || '',
        job_title: scoredJob.job.title,
        job_company: scoredJob.job.company,
        job_location: scoredJob.job.location,
        job_description: scoredJob.job.description || '',
        job_apply_link: scoredJob.job.apply_link || '',
      });
      setJobDetails(r.data);
    } catch {
      setJobDetails({ job: scoredJob.job, intelligence: scoredJob.intelligence, resume_suggestions: [], likely_questions: [], ai_recommendation: 'Details unavailable' });
    } finally { setDetailsLoading(false); }
  };

  const deleteInternship = async (id) => {
    await axios.delete(`/api/internships/${id}`).catch(() => {});
    setInternships(p => p.filter(i => i.id !== id));
    showToast('Deleted');
  };

  return (
    <DarkModeProvider>
    <div className="min-h-screen bg-gray-50/50 dark:bg-slate-900 transition-colors duration-300">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-5 py-3 rounded-xl shadow-2xl text-white text-sm font-medium animate-slide-down ${toast.type === 'error' ? 'bg-red-600' : 'bg-primary-600'}`}>
          {toast.msg}
        </div>
      )}
      <Header activeTab={tab} setActiveTab={setTab} />
      {tab === 'recommend' && !results && <Hero />}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 dark:text-slate-200">
      <ErrorBoundary key={tab} resetKeys={[tab]}>
          <>
            {!results ? (
              <div id="upload-section">
                <h2 className="font-display font-bold text-2xl sm:text-3xl text-gray-900 dark:text-white text-center mb-2">Get Your Career Intelligence</h2>
                <p className="text-gray-500 dark:text-gray-400 text-center mb-8">We'll score, rank, and explain every opportunity across 8+ platforms</p>
                <UploadZone file={file} setFile={setFile} onAnalyze={analyze} loading={loading} filters={filters} setFilters={setFilters} />
              </div>
            ) : (
              <ResultsView results={results} onReset={() => { setResults(null); setFile(null); }} onSelectJob={selectJob} />
            )}
          </>
        )}
        {tab === 'dashboard' && results?.dashboard && <DashboardSection dashboard={results.dashboard} />}
        {tab === 'dashboard' && !results && <p className="text-center text-gray-400 dark:text-gray-500 py-20">Run a career analysis first to see your dashboard.</p>}
        {tab === 'learning' && results && <LearningSection learning={results.learning} certifications={results.certifications} />}
        {tab === 'learning' && !results && <p className="text-center text-gray-400 dark:text-gray-500 py-20">Run a career analysis first to see learning recommendations.</p>}
        {tab === 'roadmap' && results && <RoadmapSection roadmap={results.career_roadmap} />}
        {tab === 'roadmap' && !results && <p className="text-center text-gray-400 dark:text-gray-500 py-20">Run a career analysis first to see your roadmap.</p>}
        {tab === 'certifications' && <CertificationsPage skills={results?.resume_data?.skills || []} />}
        {tab === 'certifications' && !results && <p className="text-center text-gray-400 dark:text-gray-500 py-20">Run a career analysis first to discover relevant certifications.</p>}
        {tab === 'internships' && (
          <div className="space-y-6 animate-fade-in">
            <h2 className="font-display font-bold text-2xl sm:text-3xl text-gray-900 dark:text-white">Internship Board</h2>
            <InternshipForm onSuccess={() => axios.get('/api/internships').then(r => setInternships(r.data))} />
            <InternshipList items={internships} onDelete={deleteInternship} />
          </div>
        )}
      </ErrorBoundary>
      </main>
      {/* Job Details Modal */}
      {selectedJob && (
        <JobDetailsModal
          details={jobDetails}
          loading={detailsLoading}
          onClose={() => { setSelectedJob(null); setJobDetails(null); }}
        />
      )}
      <Footer />
    </div>
    </DarkModeProvider>
  );
}
