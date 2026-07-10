import { NavLink, Link, Outlet } from "react-router-dom";

function Logo() {
  return (
    <Link to="/" className="ca-logo">
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden>
        <circle cx="11" cy="11" r="10" stroke="currentColor" strokeWidth="1.4" />
        <path d="M11 4 L17 11 L11 18 L5 11 Z" stroke="currentColor" strokeWidth="1.4" fill="none" />
        <circle cx="11" cy="11" r="2.4" fill="var(--accent)" />
      </svg>
      CryptoAcademy
    </Link>
  );
}

const NAV = [
  { to: "/today", label: "Today's Signal" },
  { to: "/brief", label: "Daily Brief" },
  { to: "/learn", label: "Learn" },
];

export function Nav() {
  return (
    <header className="ca-nav">
      <div className="ca-container ca-nav-inner">
        <Logo />
        <nav className="ca-nav-links" aria-label="Main">
          {NAV.map((l) => (
            <NavLink key={l.to} to={l.to} className={({ isActive }) => (isActive ? "active" : "")}>
              {l.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="ca-footer">
      <div className="ca-container">
        <div className="ca-footer-row">
          <span>CryptoAcademy · 2026</span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <span className="ca-dot" />
            Signals refresh daily · 07:00 UTC
          </span>
        </div>
        <p className="ca-footer-disclaimer">
          CryptoAcademy is an educational platform. Nothing on this site is financial
          advice, a recommendation, or a solicitation to trade. Signals are produced by a
          machine-learning model and can be wrong, late, or stale — on most days the
          honest answer is “no clear edge.” Crypto markets are volatile and trading
          carries substantial risk of loss. Never trade money you cannot afford to lose,
          and always do your own research.
        </p>
      </div>
    </footer>
  );
}

export default function Layout() {
  return (
    <>
      <Nav />
      <main className="ca-main">
        <Outlet />
      </main>
      <Footer />
    </>
  );
}
