import { StrictMode, useState, useSyncExternalStore } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { HashRouter, Link, NavLink, Navigate, Route, Routes, useNavigate, useLocation } from "react-router-dom";
import { Activity, CalendarDays, ClipboardList, Users, Menu, X, ArrowUpLeft, RotateCcw, ExternalLink, Monitor } from "lucide-react";
import PatientsPage from "../src/PatientsPage";
import AppointmentsPage from "../src/AppointmentsPage";
import VisitsPage from "../src/VisitsPage";
import BillingPage, { TodaySummary } from "../src/BillingPage";
import { cairoClock, cairoDayLabel, cairoDate } from "../src/lib/cairo";
import { choosePerspective, perspective, subscribe, snapshot, data, resetDemo, type Perspective } from "./state";
import "../src/index.css";
import "./portfolio.css";
const source = "https://github.com/MohanadMohamed/clinc-final";
function Notice() { return <aside className="demo-notice" aria-label="Portfolio demo notice"><strong dir="ltr">PORTFOLIO DEMO — SYNTHETIC DATA</strong><span>محاكاة تفاعلية فقط · لا توجد مصادقة أو حجوزات أو مدفوعات حقيقية. التغييرات مؤقتة وتُعاد عند تحديث الصفحة. لا تُدخل بيانات حقيقية.</span></aside>; }
function SourceLink() { return <a className="demo-source" href={source} target="_blank" rel="noreferrer"><ExternalLink size={18}/> <span dir="ltr">View Source on GitHub</span></a>; }
function Landing() {
    const qc = useQueryClient(), go = useNavigate(), location = useLocation();
    const explore = (role: Perspective) => { qc.clear(); choosePerspective(role); go(location.pathname); };
    return <div className="demo-landing"><Notice /><main className="demo-intro"><div className="demo-wordmark"><span className="brand-mark"><Activity /></span><b dir="ltr">Clinc Final</b><SourceLink /></div><section className="demo-hero"><div><p className="eyebrow">نظام عربي لإدارة عيادة طبيب واحد</p><h1>استكشف يوم العمل<br />داخل العيادة.</h1><p className="demo-lead">من استقبال المريض إلى الموعد والزيارة والتحصيل. جولة عملية في الواجهة العربية، باستخدام سجلات مصطنعة بالكامل.</p><div className="demo-entry"><button aria-label="Explore as Doctor" className="demo-doctor" onClick={() => explore("doctor")}><Activity size={22}/><span><strong lang="en">Explore as Doctor</strong><small>المرضى، المواعيد، الزيارات والفواتير</small></span><ArrowUpLeft /></button><button aria-label="Explore as Receptionist" onClick={() => explore("receptionist")}><Monitor size={22}/><span><strong lang="en">Explore as Receptionist</strong><small>الاستقبال والمواعيد والتحصيل</small></span><ArrowUpLeft /></button></div><p className="demo-explanation">اختيار منظور للعرض، وليس تسجيل دخول أو إثبات صلاحية. كل محتوى العرض متاح في ملفات الموقع الاصطناعي. نظام العيادة الحقيقي منفصل، ويطبق الصلاحيات في الخادم.</p></div><aside className="demo-tour"><h2>مسار تجربة مقترح</h2><ol><li><Users /><div><b>سجّل مريضاً اصطناعياً</b><p>ابحث، أضف وعدّل السجلات الإدارية.</p></div></li><li><CalendarDays /><div><b>احجز موعداً</b><p>جرّب إعادة الجدولة والتعامل مع التداخل.</p></div></li><li><ClipboardList /><div><b>أكمل الزيارة والتحصيل</b><p>حرّر مسودة اصطناعية، ثم استعرض إيصالاً.</p></div></li></ol><span>React · TypeScript · Arabic RTL</span></aside></section><footer>واجهة عرض للمحفظة المهنية · لا تتصل بخادم أو قاعدة بيانات · غير مخصصة للاستخدام الطبي</footer></main></div>;
}
const nav = [{ to: "/", text: "نظرة عامة", icon: Activity }, { to: "/patients", text: "المرضى", icon: Users }, { to: "/appointments", text: "المواعيد", icon: CalendarDays }, { to: "/workspace", text: "مساحة الطبيب", icon: ClipboardList }, { to: "/billing", text: "الفواتير", icon: ClipboardList }];
function Dashboard() {
    useSyncExternalStore(subscribe, snapshot);
    const appointments = data.appointments.filter(a => a.status === "scheduled" && cairoDate(new Date(a.start_at)) === cairoDate());
    return <><p className="eyebrow">{cairoDayLabel(cairoDate())}</p><h1>نظرة عامة على العيادة</h1><p className="subtle">هذه الأرقام محسوبة من سجلات العرض الاصطناعية. جرّب إجراءً في أحد الأقسام ثم عد إلى هنا.</p><div className="demo-statistics" aria-label="إحصاءات العرض"><div><Users /><strong>{data.patients.filter(p => p.active).length.toLocaleString("ar-EG")}</strong><span>مريض اصطناعي نشط</span></div><div><CalendarDays /><strong>{appointments.length.toLocaleString("ar-EG")}</strong><span>مواعيد مجدولة اليوم</span></div><div><ClipboardList /><strong>{data.invoices.filter(i => i.status !== "void").length.toLocaleString("ar-EG")}</strong><span>فواتير اصطناعية</span></div></div><section className="demo-agenda"><div><h2>مواعيد اليوم</h2><Link to="/appointments">فتح المواعيد <ArrowUpLeft size={16}/></Link></div>{appointments.length ? <ul>{appointments.map(a => <li key={a.id}><time>{cairoClock(new Date(a.start_at))}</time><b>{data.patients.find(p => p.id === a.patient_id)?.full_name}</b><span>{a.kind === "first_visit" ? "كشف أول" : "متابعة"}</span></li>)}</ul> : <p>لا توجد مواعيد اصطناعية مجدولة.</p>}</section><TodaySummary /></>;
}
function Shell({ role }: {
    role: Perspective;
}) {
    const [open, setOpen] = useState(false), qc = useQueryClient(), go = useNavigate();
    const change = () => { qc.clear(); choosePerspective(null); go("/"); };
    const reset = () => { if (window.confirm("إعادة سجلات العرض الاصطناعية إلى البداية؟")) {
        resetDemo();
        qc.clear();
        go("/");
    } };
    return <div className="demo-app shell"><aside className={`sidebar ${open ? "open" : ""}`}><div className="sidebrand"><span className="brand-mark"><Activity /></span><b>Clinc Final</b><button className="close" aria-label="إغلاق القائمة" onClick={() => setOpen(false)}><X /></button></div><p className="caption">منظور {role === "doctor" ? "الطبيب" : "الاستقبال"} · محاكاة</p><nav aria-label="التنقل الرئيسي">{nav.filter(n => n.to !== "/workspace" || role === "doctor").map(n => <NavLink key={n.to} to={n.to} end={n.to === "/"} onClick={() => setOpen(false)}><n.icon size={19}/>{n.text}</NavLink>)}</nav><div className="demo-side-footer"><SourceLink /><small>لا يوجد اتصال بخادم العيادة</small></div></aside>{open && <button className="scrim" aria-label="إغلاق القائمة" onClick={() => setOpen(false)}/>}<div className="main"><Notice /><header><button className="menu" aria-label="فتح القائمة" onClick={() => setOpen(true)}><Menu /></button><span>منظور {role === "doctor" ? "الطبيب" : "الاستقبال"} · عرض اصطناعي</span><div className="demo-tools"><button onClick={reset}><RotateCcw size={16}/>إعادة العرض</button><button onClick={change}>تغيير المنظور</button></div></header><main className="content"><Routes><Route path="/" element={<Dashboard />}/><Route path="/patients" element={<PatientsPage />}/><Route path="/appointments" element={<AppointmentsPage />}/><Route path="/workspace" element={role === "doctor" ? <VisitsPage /> : <Navigate to="/" replace/>}/><Route path="/billing" element={<BillingPage role={role}/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes></main></div></div>;
}
function DemoApp() { useSyncExternalStore(subscribe, snapshot); return perspective ? <Shell role={perspective}/> : <Landing />; }
const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false }, mutations: { retry: false, networkMode: "always" } } });
createRoot(document.getElementById("root")!).render(<StrictMode><QueryClientProvider client={queryClient}><HashRouter><DemoApp /></HashRouter></QueryClientProvider></StrictMode>);
