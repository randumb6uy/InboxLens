import { useEffect, useMemo, useState, useCallback } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Activity, ArrowRight, ArrowUpRight, CalendarDays, Check,
  ChevronLeft, CreditCard, ExternalLink, Inbox, LayoutDashboard,
  Loader2, Mail, Menu, Search, Sparkles, TrendingUp, Users, Wallet, X, Zap
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis, Bar, BarChart,
} from "recharts";
import { api, OverviewResponse } from "@/lib/api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "IndexLens — Inbox Intelligence" },
      { name: "description", content: "Minimalist black & orange intelligence for inbox spending, subscriptions, and schedule." },
    ],
  }),
  component: IndexLens,
});

type Section = "Overview" | "Spend" | "Subscriptions" | "Newsletters" | "Contacts" | "Schedule";

type Signal = {
  title: string;
  sender: string;
  date: string;
  amount?: string;
  category?: string;
  text: string;
  icon: string;
};

export interface TransactionItem {
  merchant: string;
  detail: string;
  category: string;
  method: string;
  date: string;
  amount: string;
  icon: string;
  subject: string;
  sender: string;
  snippet: string;
}

export interface SubscriptionItem {
  name: string;
  icon: string;
  amount: string;
  cycle: string;
  renewal: string;
  note: string;
  hasPriceAlert?: boolean;
}

export interface NewsletterItem {
  name: string;
  sender: string;
  frequency: string;
  last: string;
  count: string;
  icon: string;
  unsubUrl: string;
}

export interface ContactItem {
  name: string;
  role: string;
  email: string;
  subject: string;
  date: string;
  status: string;
  initials: string;
}

export interface DeadlineItem {
  title: string;
  desc: string;
  date: string;
  priority: string;
  kind: string;
}

export interface CategoryItem {
  name: string;
  value: number;
  amount: string;
  color: string;
}

export interface SpendTrendItem {
  month: string;
  spend: number;
}

const NAV_ITEMS: { label: Section; icon: typeof LayoutDashboard }[] = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Spend", icon: Wallet },
  { label: "Subscriptions", icon: CreditCard },
  { label: "Newsletters", icon: Mail },
  { label: "Contacts", icon: Users },
  { label: "Schedule", icon: CalendarDays },
];

const ORANGE_PALETTE = ["#ff6a00", "#f97316", "#ea580c", "#c2410c", "#7c2d12", "#383842"];

function IndexLens() {
  const [section, setSection] = useState<Section>("Overview");
  const [drawer, setDrawer] = useState<Signal | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [searching, setSearching] = useState(false);
  const [answerSources, setAnswerSources] = useState<string[]>([]);
  const [answerModel, setAnswerModel] = useState("");
  const [resolvingLlm, setResolvingLlm] = useState(false);
  const [resolveMessage, setResolveMessage] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [synced, setSynced] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [vipModal, setVipModal] = useState(false);
  const [vipName, setVipName] = useState("");
  const [vipEmail, setVipEmail] = useState("");
  const [unsubscribed, setUnsubscribed] = useState<string[]>([]);

  const [overviewData, setOverviewData] = useState<OverviewResponse | null>(null);
  const [transactionsState, setTransactionsState] = useState<TransactionItem[]>([]);
  const [subscriptionsState, setSubscriptionsState] = useState<SubscriptionItem[]>([]);
  const [newslettersState, setNewslettersState] = useState<NewsletterItem[]>([]);
  const [contactsState, setContactsState] = useState<ContactItem[]>([]);
  const [deadlinesState, setDeadlinesState] = useState<DeadlineItem[]>([]);
  const [spendCategories, setSpendCategories] = useState<CategoryItem[]>([]);
  const [spendTrendState, setSpendTrendState] = useState<SpendTrendItem[]>([]);

  const loadBackendData = useCallback(async () => {
    try {
      const [ov, sp, sub, nl, ct, sc] = await Promise.allSettled([
        api.getOverview(),
        api.getSpend(),
        api.getSubscriptions(),
        api.getNewsletters(),
        api.getImportantContacts(),
        api.getSchedule(),
      ]);

      if (ov.status === "fulfilled" && ov.value) {
        setOverviewData(ov.value);
        if (ov.value.classification?.breakdown) {
          const total = ov.value.classification.total || 1;
          const mappedCats: CategoryItem[] = Object.entries(ov.value.classification.breakdown).map(([k, v], idx) => ({
            name: k,
            value: Math.round((v / total) * 100),
            amount: `${v} emails`,
            color: ORANGE_PALETTE[idx % ORANGE_PALETTE.length],
          }));
          setSpendCategories(mappedCats);
        }
      }

      if (sp.status === "fulfilled" && sp.value) {
        if (sp.value.transactions) {
          const mappedTxs: TransactionItem[] = sp.value.transactions.map((t) => ({
            merchant: t.vendor || "Unknown Vendor",
            detail: t.subject ? (t.subject.length > 34 ? t.subject.slice(0, 34) + "..." : t.subject) : (t.category || "Receipt"),
            category: t.category ? t.category.charAt(0).toUpperCase() + t.category.slice(1) : "Expense",
            method: "Electronic",
            date: t.date || "Recent",
            amount: `−${t.currency === "USD" ? "$" : "₹"}${t.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`,
            icon: (t.vendor?.[0] || "R").toUpperCase(),
            subject: t.subject || `Receipt from ${t.vendor}`,
            sender: t.sender || t.vendor,
            snippet: t.snippet || `Transaction for ${t.vendor}: ${t.currency} ${t.amount}`,
          }));
          setTransactionsState(mappedTxs);
        }
        if (sp.value.spend_trend) {
          setSpendTrendState(sp.value.spend_trend);
        }
      }

      if (sub.status === "fulfilled" && sub.value) {
        const mappedSubs: SubscriptionItem[] = sub.value.map((s) => ({
          name: s.vendor,
          icon: s.vendor.slice(0, 2).toUpperCase(),
          amount: `${s.currency === "USD" ? "$" : "₹"}${s.last_amount}`,
          cycle: `/ ${s.cadence || "mo"}`,
          renewal: s.next_expected_date || "Upcoming",
          note: s.price_change_alert || "Active",
          hasPriceAlert: Boolean(s.price_change_alert),
        }));
        setSubscriptionsState(mappedSubs);
      }

      if (nl.status === "fulfilled" && nl.value) {
        const mappedNls: NewsletterItem[] = nl.value.map((n) => ({
          name: n.name,
          sender: n.email,
          frequency: n.frequency || "Weekly",
          last: n.last_received ? n.last_received.slice(0, 10) : "Recent",
          count: `${n.volume_count}`,
          icon: (n.name?.[0] || "N").toUpperCase(),
          unsubUrl: n.unsubscribe_url,
        }));
        setNewslettersState(mappedNls);
      }

      if (ct.status === "fulfilled" && ct.value?.recent_threads) {
        const mappedContacts: ContactItem[] = ct.value.recent_threads.map((c) => {
          const senderName = c.sender.split("<")[0].trim().replace(/['"]/g, "") || c.sender;
          const emailAddr = c.sender.includes("<") ? c.sender.split("<")[1].replace(">", "").trim() : c.sender;
          const initials = senderName.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase() || "VIP";
          return {
            name: senderName,
            role: "VIP",
            email: emailAddr,
            subject: c.subject,
            date: c.date ? c.date.slice(0, 10) : "Recent",
            status: "Action needed",
            initials,
          };
        });
        setContactsState(mappedContacts);
      }

      if (sc.status === "fulfilled" && sc.value) {
        const combined: DeadlineItem[] = [
          ...(sc.value.meetings || []).map((m) => ({
            title: m.title,
            desc: m.location_or_link || m.organizer || "Calendar event",
            date: m.datetime_start ? m.datetime_start.slice(0, 10) : "Upcoming",
            priority: "Scheduled",
            kind: "Meeting",
          })),
          ...(sc.value.deadlines || []).map((d) => ({
            title: d.description,
            desc: d.source_context ? (d.source_context.length > 50 ? d.source_context.slice(0, 50) + "..." : d.source_context) : "Action required",
            date: d.due_date || "Upcoming",
            priority: d.urgency || "Due soon",
            kind: "Bill",
          })),
        ];
        setDeadlinesState(combined);
      }
    } catch (err) {
      console.warn("Backend API not reachable:", err);
    }
  }, []);

  useEffect(() => {
    loadBackendData();
  }, [loadBackendData]);

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
      }
      if (event.key === "Escape") {
        setSearchOpen(false);
        setDrawer(null);
        setVipModal(false);
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const runSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setAnswer("");
    setAnswerSources([]);
    setAnswerModel("");
    try {
      const res = await api.askQuestion(query.trim());
      setAnswer(res.answer);
      setAnswerSources(res.sources || []);
      setAnswerModel(res.model || "");
    } catch (err) {
      console.warn("AI QA call failed, using heuristic fallback:", err);
      const q = query.toLowerCase();
      const totalSpend = overviewData?.metrics?.total_spend_this_month ?? 0;
      const subsCount = subscriptionsState.length;
      if (q.includes("spend") || q.includes("food") || q.includes("money") || q.includes("cost") || q.includes("total")) {
        const topVendors = Array.from(new Set(transactionsState.map((t) => t.merchant))).slice(0, 4).join(", ");
        setAnswer(`Tracked spend: ₹${totalSpend.toLocaleString("en-IN", { minimumFractionDigits: 2 })} across ${transactionsState.length} receipts${topVendors ? ` (${topVendors})` : ""}.`);
      } else if (q.includes("sub") || q.includes("recurring") || q.includes("netflix")) {
        const subList = subscriptionsState.slice(0, 4).map((s) => `${s.name} (${s.amount})`).join(", ");
        setAnswer(`${subsCount} active subscriptions found${subList ? `: ${subList}` : ""}.`);
      } else if (q.includes("deadline") || q.includes("bill") || q.includes("meeting") || q.includes("due")) {
        const topItems = deadlinesState.slice(0, 3).map((d) => `${d.title} (${d.date || "Upcoming"})`).join(", ");
        setAnswer(`${deadlinesState.length} upcoming items${topItems ? `: ${topItems}` : ""}.`);
      } else {
        const total = overviewData?.classification?.total ?? 0;
        setAnswer(`Indexed ${total} emails with deterministic entity extraction in local SQLite.`);
      }
    } finally {
      setSearching(false);
    }
  };

  const handleResolveLlm = async () => {
    setResolvingLlm(true);
    setResolveMessage("");
    try {
      const res = await api.extractEntities(100);
      await loadBackendData();
      const resolved = res.results?.resolved_llm_count ?? 0;
      setResolveMessage(`Successfully processed emails with LLM! (Resolved ${resolved} ambiguous email(s))`);
      window.setTimeout(() => setResolveMessage(""), 5000);
    } catch (err) {
      console.error("LLM extraction failed:", err);
      setResolveMessage("LLM extraction call failed. Check OpenRouter credentials.");
    } finally {
      setResolvingLlm(false);
    }
  };

  const syncInbox = async () => {
    setSyncing(true);
    setSynced(false);
    try {
      await api.syncInbox(100, false, true);
      await loadBackendData();
      setSynced(true);
      window.setTimeout(() => setSynced(false), 2500);
    } catch {
      window.setTimeout(() => { setSynced(true); window.setTimeout(() => setSynced(false), 2000); }, 1000);
    } finally {
      setSyncing(false);
    }
  };

  const handleAddVip = async () => {
    if (vipEmail.trim() || vipName.trim()) {
      const email = vipEmail.trim() || `${vipName.toLowerCase().replace(/\s+/g, ".")}@example.com`;
      try {
        await api.addImportantContact(email, vipName.trim(), "VIP contact");
        await loadBackendData();
      } catch (err) {
        console.error("Failed to add VIP contact:", err);
      }
      setContactsState([
        {
          name: vipName || email.split("@")[0],
          role: "VIP",
          email: email,
          subject: "Direct thread",
          date: "Today",
          status: "Action needed",
          initials: (vipName || email).slice(0, 2).toUpperCase(),
        },
        ...contactsState,
      ]);
    }
    setVipModal(false);
    setVipName("");
    setVipEmail("");
  };

  const signalFromTransaction = (tx: TransactionItem): Signal => ({
    title: tx.subject,
    sender: tx.sender,
    date: tx.date,
    amount: tx.amount,
    category: tx.category,
    text: tx.snippet,
    icon: tx.icon,
  });

  const totalSpendFormatted = `₹${(overviewData?.metrics?.total_spend_this_month ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 0 })}`;
  const totalEmailsCount = overviewData?.classification?.total ?? 0;
  const activeSubsCount = overviewData?.metrics?.active_subscriptions_count ?? subscriptionsState.length;
  const upcomingDeadlinesCount = overviewData?.metrics?.upcoming_deadlines_count ?? deadlinesState.length;

  return (
    <div className="app-frame">
      {/* Sidebar: Minimalist Obsidian Bar with Orange Accents */}
      <aside className={`sidebar ${collapsed ? "sidebar-collapsed" : ""} ${mobileNav ? "sidebar-mobile-open" : ""}`}>
        <div className="brand-row">
          <div className="brand-mark">
            <Activity size={16} strokeWidth={2.5} />
          </div>
          {!collapsed && <span className="brand-name">INDEXLENS</span>}
          <button
            className="collapse-btn"
            onClick={() => setCollapsed(!collapsed)}
            aria-label="Toggle sidebar"
          >
            <ChevronLeft size={14} className={collapsed ? "rotate-180" : ""} />
          </button>
        </div>

        <nav className="side-nav">
          {NAV_ITEMS.map(({ label, icon: Icon }) => (
            <button
              key={label}
              className={`nav-item ${section === label ? "nav-item-active" : ""}`}
              onClick={() => { setSection(label); setMobileNav(false); }}
              title={collapsed ? label : undefined}
            >
              <Icon size={16} />
              <span>{label}</span>
              {label === "Contacts" && contactsState.length > 0 && <span className="nav-badge">{contactsState.length}</span>}
              {label === "Schedule" && deadlinesState.length > 0 && <span className="nav-badge">{deadlinesState.length}</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-spacer" />

        <button className="sync-btn" onClick={syncInbox} disabled={syncing}>
          <Inbox size={14} className={syncing ? "spin" : ""} />
          {!collapsed && <span>{syncing ? "Syncing..." : synced ? "Synced" : "Sync Inbox"}</span>}
        </button>
      </aside>

      {mobileNav && <div className="mobile-scrim" onClick={() => setMobileNav(false)} />}

      {/* Main Panel */}
      <main className="main-panel">
        <header className="topbar">
          <div className="topbar-left">
            <button className="mobile-toggle" aria-label="Open menu" onClick={() => setMobileNav(true)}>
              <Menu size={18} />
            </button>
            <h1 className="section-title">{section}</h1>
          </div>

          <div className="topbar-actions">
            <button className="search-pill" onClick={() => { setSearchOpen(true); setAnswer(""); }}>
              <Search size={13} />
              <span>Search inbox...</span>
              <kbd>⌘K</kbd>
            </button>
            <div className="live-indicator">
              <span className="live-dot" />
              <span>Live</span>
            </div>
          </div>
        </header>

        <div className="content-area">
          {section === "Overview" && (
            <Overview
              spendThisMonth={totalSpendFormatted}
              activeSubs={activeSubsCount}
              upcomingDeadlines={upcomingDeadlinesCount}
              totalEmails={totalEmailsCount}
              needsLlmCount={overviewData?.classification?.needs_llm_count ?? 0}
              categories={spendCategories}
              spendData={spendTrendState}
              transactions={transactionsState}
              deadlines={deadlinesState}
              subscriptions={subscriptionsState}
              onNavigate={(s) => setSection(s)}
              onTransaction={(item) => setDrawer(signalFromTransaction(item))}
              onDeadline={(item) => setDrawer({ title: item.title, sender: "Alerts", date: item.date, category: item.kind, text: item.desc, icon: "C" })}
              onResolveLlm={handleResolveLlm}
              resolvingLlm={resolvingLlm}
              resolveMessage={resolveMessage}
            />
          )}

          {section === "Spend" && (
            <Spend
              transactions={transactionsState}
              categories={spendCategories}
              spendData={spendTrendState}
              totalSpend={totalSpendFormatted}
              onTransaction={(item) => setDrawer(signalFromTransaction(item))}
            />
          )}

          {section === "Subscriptions" && (
            <Subscriptions subscriptions={subscriptionsState} />
          )}

          {section === "Newsletters" && (
            <Newsletters
              newsletters={newslettersState}
              unsubscribed={unsubscribed}
              onUnsubscribe={(name) => setUnsubscribed([...unsubscribed, name])}
            />
          )}

          {section === "Contacts" && (
            <Contacts
              contacts={contactsState}
              onAdd={() => setVipModal(true)}
              onOpen={(person) => setDrawer({ title: person.subject, sender: person.email, date: person.date, category: person.role, text: `${person.name}: ${person.subject}`, icon: person.initials })}
            />
          )}

          {section === "Schedule" && (
            <Schedule
              deadlines={deadlinesState}
              onOpen={(item) => setDrawer({ title: item.title, sender: item.kind === "Meeting" ? "Calendar" : "Alert", date: item.date, category: item.kind, text: item.desc, icon: item.kind === "Meeting" ? "M" : "B" })}
            />
          )}
        </div>
      </main>

      {/* Command Palette / Search Modal */}
      {searchOpen && (
        <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) setSearchOpen(false); }}>
          <section className="search-dialog" role="dialog" aria-modal="true">
            <div className="search-input-wrap">
              <Search size={16} className="search-icon-orange" />
              <input
                autoFocus
                placeholder="Ask about spend, subscriptions, landlord, deadlines..."
                value={query}
                onChange={(e) => { setQuery(e.target.value); setAnswer(""); setAnswerSources([]); }}
                onKeyDown={(e) => { if (e.key === "Enter") runSearch(); }}
              />
              <button className="search-enter-btn" onClick={runSearch} disabled={searching} aria-label="Submit">
                {searching ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
              </button>
            </div>

            {searching ? (
              <div className="search-answer" style={{ display: "flex", alignItems: "center", gap: "10px", padding: "16px" }}>
                <Loader2 size={16} className="animate-spin" style={{ color: "#ff6a00" }} />
                <span style={{ fontSize: "13px", color: "rgba(255,255,255,0.7)" }}>IndexLens AI is reasoning over your inbox...</span>
              </div>
            ) : answer ? (
              <div className="search-answer">
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
                  <Sparkles size={13} style={{ color: "#ff6a00" }} />
                  <span style={{ fontSize: "11px", fontWeight: 600, color: "#ff6a00", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                    IndexLens AI Answer {answerModel ? `(${answerModel.split("/").pop()})` : ""}
                  </span>
                </div>
                <p style={{ lineHeight: 1.6 }}>{answer}</p>
                {answerSources.length > 0 && (
                  <div style={{ marginTop: "12px", paddingTop: "10px", borderTop: "1px solid rgba(255,255,255,0.08)", fontSize: "11px", color: "rgba(255,255,255,0.5)" }}>
                    <span style={{ fontWeight: 600, color: "#ff6a00", marginRight: "6px" }}>CITED SOURCES:</span>
                    {answerSources.join(" • ")}
                  </div>
                )}
              </div>
            ) : (
              <div className="search-prompts">
                {[
                  "How much did I spend this month?",
                  "What active subscriptions do I have?",
                  "What did my landlord say about the lease?",
                  "What deadlines or meetings are upcoming?"
                ].map((q) => (
                  <button key={q} onClick={() => { setQuery(q); setAnswer(""); }}>
                    <span>{q}</span>
                    <ArrowRight size={12} />
                  </button>
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      {/* Detail Drawer */}
      {drawer && (
        <div className="drawer-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) setDrawer(null); }}>
          <aside className="detail-drawer">
            <div className="drawer-header">
              <span className="drawer-tag">DETAIL</span>
              <button className="icon-btn" onClick={() => setDrawer(null)} aria-label="Close">
                <X size={16} />
              </button>
            </div>

            <div className="drawer-entity">
              <div className="entity-avatar">{drawer.icon.slice(0, 2)}</div>
              <div>
                <h3>{drawer.title}</h3>
                <span>{drawer.category ?? "Inbox item"}</span>
              </div>
            </div>

            <div className="drawer-meta-grid">
              <div><span>SENDER</span><strong>{drawer.sender}</strong></div>
              <div><span>DATE</span><strong>{drawer.date}</strong></div>
              {drawer.amount && <div><span>AMOUNT</span><strong className="text-orange">{drawer.amount}</strong></div>}
            </div>

            <div className="drawer-body">
              <p>{drawer.text}</p>
            </div>

            <div className="drawer-footer">
              <button className="primary-btn" onClick={() => setDrawer(null)}>
                Dismiss
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* Add VIP Contact Modal */}
      {vipModal && (
        <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) setVipModal(false); }}>
          <section className="dialog-box">
            <div className="dialog-head">
              <strong>Add VIP Contact</strong>
              <button className="icon-btn" onClick={() => setVipModal(false)}><X size={16} /></button>
            </div>
            <div className="dialog-inputs">
              <label>
                NAME
                <input value={vipName} onChange={(e) => setVipName(e.target.value)} placeholder="Full name" autoFocus />
              </label>
              <label>
                EMAIL
                <input value={vipEmail} onChange={(e) => setVipEmail(e.target.value)} placeholder="name@domain.com" />
              </label>
            </div>
            <div className="dialog-actions">
              <button className="ghost-btn" onClick={() => setVipModal(false)}>Cancel</button>
              <button className="primary-btn" onClick={handleAddVip}>Save Contact</button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, icon: Icon }: { label: string; value: string; icon: typeof Wallet }) {
  return (
    <article className="metric-box">
      <div className="metric-header">
        <span className="metric-title">{label}</span>
        <span className="metric-icon"><Icon size={14} /></span>
      </div>
      <div className="metric-digit">{value}</div>
    </article>
  );
}

function Overview({
  spendThisMonth, activeSubs, upcomingDeadlines, totalEmails, needsLlmCount,
  categories, spendData, transactions, deadlines, subscriptions,
  onNavigate, onTransaction, onDeadline, onResolveLlm, resolvingLlm, resolveMessage,
}: {
  spendThisMonth: string;
  activeSubs: number;
  upcomingDeadlines: number;
  totalEmails: number;
  needsLlmCount: number;
  categories: CategoryItem[];
  spendData: SpendTrendItem[];
  transactions: TransactionItem[];
  deadlines: DeadlineItem[];
  subscriptions: SubscriptionItem[];
  onNavigate: (section: Section) => void;
  onTransaction: (item: TransactionItem) => void;
  onDeadline: (item: DeadlineItem) => void;
  onResolveLlm: () => void;
  resolvingLlm: boolean;
  resolveMessage: string;
}) {
  const alertSub = useMemo(() => subscriptions.find((s) => s.hasPriceAlert), [subscriptions]);

  return (
    <>
      {needsLlmCount > 0 && (
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 18px",
          marginBottom: "16px",
          background: "linear-gradient(90deg, rgba(255, 106, 0, 0.12) 0%, rgba(255, 106, 0, 0.04) 100%)",
          border: "1px solid rgba(255, 106, 0, 0.35)",
          borderRadius: "8px",
          gap: "12px",
          flexWrap: "wrap"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "16px" }}>⚡</span>
            <div>
              <div style={{ fontWeight: 600, fontSize: "13px", color: "#fff" }}>
                {needsLlmCount} Ambiguous Email{needsLlmCount > 1 ? "s" : ""} Pending LLM Resolution
              </div>
              <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.6)", marginTop: "2px" }}>
                Non-deterministic emails requiring AI schema extraction. Click to extract receipts, schedule, and opportunities.
              </div>
            </div>
          </div>
          <button
            className="primary-btn"
            style={{ fontSize: "12px", padding: "6px 14px", display: "inline-flex", alignItems: "center", gap: "6px" }}
            onClick={onResolveLlm}
            disabled={resolvingLlm}
          >
            {resolvingLlm ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
            <span>{resolvingLlm ? "Resolving with LLM..." : "Resolve with LLM"}</span>
          </button>
        </div>
      )}

      {resolveMessage && (
        <div style={{
          padding: "10px 16px",
          marginBottom: "16px",
          background: "rgba(34, 197, 94, 0.1)",
          border: "1px solid rgba(34, 197, 94, 0.3)",
          borderRadius: "6px",
          color: "#4ade80",
          fontSize: "12px",
          display: "flex",
          alignItems: "center",
          gap: "8px"
        }}>
          <Check size={14} />
          <span>{resolveMessage}</span>
        </div>
      )}

      <div className="metric-strip">
        <Metric label="INBOX VOLUME" value={String(totalEmails)} icon={Inbox} />
        <Metric label="SCHEDULED" value={String(upcomingDeadlines)} icon={CalendarDays} />
        <Metric label="SUBSCRIPTIONS" value={String(activeSubs)} icon={CreditCard} />
        <Metric label="MONTHLY SPEND" value={spendThisMonth} icon={Wallet} />
      </div>

      <div className="two-col-grid">
        {/* Category Breakdown Donut */}
        <section className="card-panel">
          <div className="panel-title-row">
            <h3>Category Distribution</h3>
          </div>
          <div className="donut-section">
            {categories.length === 0 ? (
              <div className="empty-panel">No classified emails yet</div>
            ) : (
              <>
                <div className="donut-chart-holder">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={categories} dataKey="value" nameKey="name" innerRadius="70%" outerRadius="92%" paddingAngle={3} stroke="none">
                        {categories.map((item) => <Cell key={item.name} fill={item.color} />)}
                      </Pie>
                      <Tooltip
                        contentStyle={{ background: "#0a0a0c", border: "1px solid rgba(255,106,0,0.3)", borderRadius: 6, color: "#fff", fontSize: 11 }}
                        formatter={(val) => [`${val}%`, "Share"]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="donut-center-stat">
                    <strong>{totalEmails}</strong>
                    <span>emails</span>
                  </div>
                </div>

                <div className="category-legend">
                  {categories.map((c) => (
                    <div className="legend-entry" key={c.name}>
                      <span className="entry-dot" style={{ backgroundColor: c.color }} />
                      <span className="entry-name">{c.name}</span>
                      <strong className="entry-val">{c.value}%</strong>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </section>

        {/* Spend Trend */}
        <section className="card-panel">
          <div className="panel-title-row">
            <h3>Spend Trend</h3>
            <span className="header-stat">{spendThisMonth}</span>
          </div>
          <div className="area-chart-holder">
            {spendData.length === 0 ? (
              <div className="empty-panel">No spending trends detected</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={spendData} margin={{ top: 12, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="orangeGlow" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#ff6a00" stopOpacity={0.28} />
                      <stop offset="100%" stopColor="#ff6a00" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.03)" strokeDasharray="3 3" />
                  <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: "#71717a", fontSize: 11 }} dy={8} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: "#71717a", fontSize: 10 }} tickFormatter={(v) => `₹${v / 1000}k`} />
                  <Tooltip
                    contentStyle={{ background: "#0a0a0c", border: "1px solid rgba(255,106,0,0.3)", borderRadius: 6, color: "#fff", fontSize: 11 }}
                    formatter={(v) => [`₹${Number(v).toLocaleString("en-IN")}`, "Spend"]}
                  />
                  <Area type="monotone" dataKey="spend" stroke="#ff6a00" strokeWidth={2} fill="url(#orangeGlow)" activeDot={{ r: 4, fill: "#ff6a00", stroke: "#000", strokeWidth: 2 }} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>
      </div>

      <div className="two-col-grid">
        {/* Recent Receipts */}
        <section className="card-panel">
          <div className="panel-title-row">
            <h3>Recent Receipts</h3>
            <button className="link-action" onClick={() => onNavigate("Spend")}>
              View All <ArrowRight size={12} />
            </button>
          </div>
          <div className="row-list">
            {transactions.length === 0 ? (
              <div className="empty-panel">No recent receipts</div>
            ) : (
              transactions.slice(0, 4).map((tx, idx) => (
                <button className="interactive-row" key={tx.merchant + idx} onClick={() => onTransaction(tx)}>
                  <div className="item-monogram">{tx.icon}</div>
                  <div className="item-details">
                    <strong>{tx.merchant}</strong>
                    <span>{tx.detail}</span>
                  </div>
                  <span className="item-date">{tx.date}</span>
                  <strong className="item-amount">{tx.amount}</strong>
                </button>
              ))
            )}
          </div>
        </section>

        {/* Coming Up */}
        <section className="card-panel">
          <div className="panel-title-row">
            <h3>Upcoming Schedule</h3>
            <button className="link-action" onClick={() => onNavigate("Schedule")}>
              View All <ArrowRight size={12} />
            </button>
          </div>
          <div className="row-list">
            {deadlines.length === 0 ? (
              <div className="empty-panel">No upcoming events or bills</div>
            ) : (
              deadlines.slice(0, 4).map((d, idx) => (
                <button className="interactive-row" key={d.title + idx} onClick={() => onDeadline(d)}>
                  <div className="date-tile-orange">
                    <span>{d.date ? d.date.split("-")[1] || "DATE" : "DATE"}</span>
                    <strong>{d.date ? d.date.split("-")[2] || "—" : "—"}</strong>
                  </div>
                  <div className="item-details">
                    <strong>{d.title}</strong>
                    <span>{d.desc}</span>
                  </div>
                  <span className="tag-orange-subtle">{d.priority}</span>
                </button>
              ))
            )}
          </div>
        </section>
      </div>

      {alertSub && (
        <div className="alert-strip">
          <Zap size={15} className="text-orange" />
          <span>Subscription price alert: <strong>{alertSub.name}</strong> renewed ({alertSub.note}).</span>
          <button onClick={() => onNavigate("Subscriptions")}>Review <ArrowRight size={12} /></button>
        </div>
      )}
    </>
  );
}

function Spend({
  transactions, categories, spendData, totalSpend, onTransaction,
}: {
  transactions: TransactionItem[];
  categories: CategoryItem[];
  spendData: SpendTrendItem[];
  totalSpend: string;
  onTransaction: (item: TransactionItem) => void;
}) {
  const largestCat = useMemo(() => {
    if (!categories.length) return "N/A";
    const sorted = [...categories].sort((a, b) => b.value - a.value);
    return sorted[0].name;
  }, [categories]);

  return (
    <>
      <div className="metric-strip">
        <Metric label="TOTAL SPEND" value={totalSpend} icon={Wallet} />
        <Metric label="RECEIPTS" value={String(transactions.length)} icon={Activity} />
        <Metric label="TOP CATEGORY" value={largestCat} icon={TrendingUp} />
      </div>

      <div className="two-col-grid">
        <section className="card-panel">
          <div className="panel-title-row">
            <h3>Spend Trend</h3>
          </div>
          <div className="area-chart-holder">
            {spendData.length === 0 ? (
              <div className="empty-panel">No spend data</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={spendData} margin={{ top: 12, right: 10, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="finGlow" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#ff6a00" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#ff6a00" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.03)" strokeDasharray="3 3" />
                  <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: "#71717a", fontSize: 11 }} dy={8} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: "#71717a", fontSize: 10 }} tickFormatter={(v) => `₹${v / 1000}k`} />
                  <Tooltip
                    contentStyle={{ background: "#0a0a0c", border: "1px solid rgba(255,106,0,0.3)", borderRadius: 6, color: "#fff", fontSize: 11 }}
                    formatter={(v) => [`₹${Number(v).toLocaleString("en-IN")}`, "Spend"]}
                  />
                  <Area type="monotone" dataKey="spend" stroke="#ff6a00" strokeWidth={2} fill="url(#finGlow)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <section className="card-panel">
          <div className="panel-title-row">
            <h3>Category Breakdown</h3>
          </div>
          <div className="area-chart-holder">
            {categories.length === 0 ? (
              <div className="empty-panel">No categories found</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categories} layout="vertical" margin={{ top: 8, right: 16, left: 10, bottom: 0 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#e4e4e7", fontSize: 11 }} width={90} />
                  <Tooltip
                    contentStyle={{ background: "#0a0a0c", border: "1px solid rgba(255,106,0,0.3)", borderRadius: 6, color: "#fff", fontSize: 11 }}
                    formatter={(v) => [`${v}%`, "Share"]}
                  />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={10}>
                    {categories.map((c) => <Cell key={c.name} fill={c.color} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>
      </div>

      <section className="card-panel">
        <div className="panel-title-row">
          <h3>Extracted Transactions</h3>
        </div>
        {transactions.length === 0 ? (
          <div className="empty-panel">No receipts detected</div>
        ) : (
          <div className="table-wrap">
            <table className="sleek-table">
              <thead>
                <tr>
                  <th>MERCHANT</th>
                  <th>CATEGORY</th>
                  <th>METHOD</th>
                  <th>DATE</th>
                  <th className="align-right">AMOUNT</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx, idx) => (
                  <tr key={tx.merchant + idx} onClick={() => onTransaction(tx)}>
                    <td>
                      <div className="table-merchant-cell">
                        <span className="item-monogram-small">{tx.icon}</span>
                        <div>
                          <strong>{tx.merchant}</strong>
                          <span>{tx.detail}</span>
                        </div>
                      </div>
                    </td>
                    <td><span className="tag-neutral">{tx.category}</span></td>
                    <td><span className="cell-muted">{tx.method}</span></td>
                    <td><span className="cell-mono">{tx.date}</span></td>
                    <td className="align-right"><strong className="cell-amount">{tx.amount}</strong></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

function Subscriptions({ subscriptions }: { subscriptions: SubscriptionItem[] }) {
  const monthlyRecurring = useMemo(() => {
    return subscriptions.reduce((sum, s) => {
      const num = parseFloat(s.amount.replace(/[^0-9.]/g, "") || "0");
      return sum + (isNaN(num) ? 0 : num);
    }, 0);
  }, [subscriptions]);
  const annualCost = monthlyRecurring * 12;

  return (
    <>
      <div className="metric-strip">
        <Metric label="MONTHLY OUTFLOW" value={`₹${Math.round(monthlyRecurring).toLocaleString("en-IN")}`} icon={CreditCard} />
        <Metric label="ANNUAL RUN-RATE" value={`₹${Math.round(annualCost).toLocaleString("en-IN")}`} icon={TrendingUp} />
        <Metric label="ACTIVE SERVICES" value={String(subscriptions.length)} icon={Check} />
      </div>

      {subscriptions.length === 0 ? (
        <div className="card-panel empty-panel-large">No active subscriptions detected</div>
      ) : (
        <div className="grid-cards-3">
          {subscriptions.map((sub) => (
            <article className="sub-card" key={sub.name}>
              <div className="sub-card-top">
                <span className="sub-avatar">{sub.icon}</span>
                <span className={sub.hasPriceAlert ? "tag-orange" : "tag-neutral"}>
                  {sub.hasPriceAlert ? "Price Alert" : "Active"}
                </span>
              </div>
              <strong className="sub-name">{sub.name}</strong>
              <div className="sub-amount">
                {sub.amount}
                <span>{sub.cycle}</span>
              </div>
              <div className="sub-footer">
                <span>Renewal</span>
                <strong>{sub.renewal}</strong>
              </div>
            </article>
          ))}
        </div>
      )}
    </>
  );
}

function Newsletters({
  newsletters, unsubscribed, onUnsubscribe,
}: {
  newsletters: NewsletterItem[];
  unsubscribed: string[];
  onUnsubscribe: (name: string) => void;
}) {
  const list = newsletters.filter((n) => !unsubscribed.includes(n.name));

  return (
    <>
      <div className="newsletter-banner">
        <div>
          <strong>{list.length} Newsletters Detected</strong>
          <span>Surfaced automatically from email headers</span>
        </div>
      </div>

      {list.length === 0 ? (
        <div className="card-panel empty-panel-large">No newsletters in mailbox</div>
      ) : (
        <div className="card-panel">
          <div className="row-list">
            {list.map((n) => (
              <div className="interactive-row-static" key={n.name}>
                <div className="item-monogram">{n.icon}</div>
                <div className="item-details">
                  <strong>{n.name}</strong>
                  <span>{n.sender}</span>
                </div>
                <span className="tag-neutral">{n.frequency}</span>
                <span className="cell-muted">{n.count} received</span>
                <span className="cell-mono">{n.last}</span>
                <button
                  className="ghost-btn-orange"
                  onClick={() => {
                    if (n.unsubUrl) window.open(n.unsubUrl, "_blank");
                    onUnsubscribe(n.name);
                  }}
                >
                  <ExternalLink size={12} />
                  <span>Unsubscribe</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function Contacts({
  contacts, onAdd, onOpen,
}: {
  contacts: ContactItem[];
  onAdd: () => void;
  onOpen: (item: ContactItem) => void;
}) {
  return (
    <>
      <div className="action-strip-row">
        <div className="metric-strip compact-strip">
          <Metric label="VIP CONTACTS" value={String(contacts.length)} icon={Users} />
          <Metric label="ACTION NEEDED" value={String(contacts.filter((c) => c.status === "Action needed").length)} icon={Mail} />
        </div>
        <button className="primary-btn" onClick={onAdd}>
          + Add VIP
        </button>
      </div>

      {contacts.length === 0 ? (
        <div className="card-panel empty-panel-large">No VIP contacts configured</div>
      ) : (
        <div className="card-panel">
          <div className="row-list">
            {contacts.map((c, idx) => (
              <button className="interactive-row" key={c.email + idx} onClick={() => onOpen(c)}>
                <div className="contact-avatar-pill">{c.initials}</div>
                <div className="item-details">
                  <strong>{c.name}</strong>
                  <span>{c.email}</span>
                </div>
                <div className="subject-preview">
                  <strong>{c.subject}</strong>
                </div>
                <span className="cell-mono">{c.date}</span>
                <span className="tag-orange-subtle">{c.status}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function Schedule({
  deadlines, onOpen,
}: {
  deadlines: DeadlineItem[];
  onOpen: (item: DeadlineItem) => void;
}) {
  return (
    <>
      <div className="metric-strip">
        <Metric label="UPCOMING EVENTS" value={String(deadlines.length)} icon={CalendarDays} />
        <Metric label="ATTENTION DUE" value={String(deadlines.filter((d) => d.priority?.toLowerCase().includes("due") || d.priority?.toLowerCase().includes("urgent")).length)} icon={Zap} />
      </div>

      {deadlines.length === 0 ? (
        <div className="card-panel empty-panel-large">No upcoming events or bills</div>
      ) : (
        <section className="card-panel">
          <div className="row-list">
            {deadlines.map((d, idx) => (
              <button className="interactive-row" key={d.title + idx} onClick={() => onOpen(d)}>
                <div className="date-tile-orange">
                  <span>{d.date ? d.date.split("-")[1] || "DATE" : "DATE"}</span>
                  <strong>{d.date ? d.date.split("-")[2] || "—" : "—"}</strong>
                </div>
                <div className="item-details">
                  <strong>{d.title}</strong>
                  <span>{d.desc}</span>
                </div>
                <span className="tag-neutral">{d.kind}</span>
                <span className="tag-orange-subtle">{d.priority}</span>
              </button>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
