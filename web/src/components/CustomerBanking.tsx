import { useEffect, useState } from "react";
import { getCase, type DemoCaseView } from "../lib/api";

export type CustomerService = "cards" | "mortgage" | "other";

const SERVICES: Array<{
  id: CustomerService;
  title: string;
  description: string;
  icon: string;
}> = [
  {
    id: "cards",
    title: "Cards",
    description: "View cards, limits and card support",
    icon: "▰",
  },
  {
    id: "mortgage",
    title: "Mortgage",
    description: "Apply for a mortgage or follow your case",
    icon: "⌂",
  },
  {
    id: "other",
    title: "Other",
    description: "Accounts, payments and more services",
    icon: "•••",
  },
];

const QUICK_ACTIONS = [
  { icon: "↗", label: "Make a transfer" },
  { icon: "▤", label: "Pay a bill" },
  { icon: "⌁", label: "Scan invoice" },
  { icon: "+", label: "Open an account" },
  { icon: "≡", label: "Statements" },
  { icon: "?", label: "Contact support" },
];

export function CustomerMenu({
  active,
  onSelect,
}: {
  active: CustomerService | null;
  onSelect: (service: CustomerService) => void;
}) {
  return (
    <aside className="customer-menu">
      <div className="customer-profile">
        <span className="avatar" aria-hidden>EL</span>
        <div>
          <strong>Emma Lindberg</strong>
          <span>Personal customer</span>
        </div>
      </div>
      <p className="menu-label">What would you like to do?</p>
      <nav aria-label="Banking services">
        {SERVICES.map((service) => (
          <button
            key={service.id}
            type="button"
            className={active === service.id ? "active" : ""}
            aria-current={active === service.id ? "page" : undefined}
            onClick={() => onSelect(service.id)}
          >
            <span className="menu-icon" aria-hidden>{service.icon}</span>
            <span className="menu-copy">
              <strong>{service.title}</strong>
              <small>{service.description}</small>
            </span>
            <span className="menu-arrow" aria-hidden>›</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}

export function BankingOverview({ onSelect }: { onSelect: (service: CustomerService) => void }) {
  return (
    <div className="banking-overview">
      <div className="welcome-row">
        <div>
          <p className="eyebrow">Friday, 21 August</p>
          <h1>Good morning, Emma</h1>
          <p>Here is an overview of your finances.</p>
        </div>
        <button className="notification-button" type="button" aria-label="Notifications">
          ♢<span>2</span>
        </button>
      </div>

      <section className="balance-card">
        <div>
          <span>Available across accounts</span>
          <strong>84 250,00 kr</strong>
          <small>Updated just now</small>
        </div>
        <div className="balance-account">
          <span>Salary account</span>
          <strong>•••• 1842</strong>
        </div>
      </section>

      <section className="quick-actions" aria-label="Quick actions">
        {QUICK_ACTIONS.map((action) => (
          <button type="button" key={action.label}>
            <span aria-hidden>{action.icon}</span>
            {action.label}
          </button>
        ))}
      </section>

      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Banking services</p>
            <h2>How can we help?</h2>
          </div>
        </div>
        <div className="service-grid">
          {SERVICES.map((service) => (
            <button key={service.id} type="button" onClick={() => onSelect(service.id)}>
              <span className="service-icon" aria-hidden>{service.icon}</span>
              <strong>{service.title}</strong>
              <small>{service.description}</small>
              <span className="service-link">Open {service.title.toLowerCase()} <span aria-hidden>→</span></span>
            </button>
          ))}
        </div>
      </section>

      <section className="recent-activity">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Latest</p>
            <h2>Recent activity</h2>
          </div>
          <button type="button">View all</button>
        </div>
        <div className="activity-row">
          <span className="activity-icon" aria-hidden>↓</span>
          <div><strong>Salary</strong><small>Nordic Tech AB · 25 Jul</small></div>
          <strong className="positive">+ 48 200,00 kr</strong>
        </div>
        <div className="activity-row">
          <span className="activity-icon" aria-hidden>◇</span>
          <div><strong>ICA Nära</strong><small>Card purchase · Yesterday</small></div>
          <strong>− 684,50 kr</strong>
        </div>
      </section>
    </div>
  );
}

export function CardsView({ refreshKey }: { refreshKey: number }) {
  const [demoCase, setDemoCase] = useState<DemoCaseView | null>(null);

  useEffect(() => {
    getCase().then(setDemoCase).catch(() => {});
  }, [refreshKey]);

  const card = demoCase?.cards[0];
  const blocked = card?.status === "blocked" || card?.status === "replacement_ordered";

  return (
    <div className="service-page">
      <p className="eyebrow">Cards</p>
      <h1>Your cards</h1>
      <p className="service-intro">View card details, spending and support options.</p>
      <div className="cards-layout">
        <div className={`bank-card ${blocked ? "blocked" : ""}`}>
          <span className="bank-card-brand">Bank Alfa</span>
          <span className="bank-card-chip" aria-hidden />
          <span className="bank-card-number">•••• •••• •••• {card?.last_four ?? "4471"}</span>
          <span className="bank-card-holder">EMMA LINDBERG</span>
          <strong>Mastercard</strong>
        </div>
        <div className="card-details">
          <span className={`card-state ${blocked ? "blocked" : ""}`}>
            {blocked ? "Card blocked" : "Card active"}
          </span>
          <h2>Bank Alfa Mastercard ·{card?.last_four ?? "4471"}</h2>
          <dl>
            <div><dt>Available credit</dt><dd>32 450 kr</dd></div>
            <div><dt>Monthly limit</dt><dd>50 000 kr</dd></div>
            <div><dt>Next invoice</dt><dd>4 180 kr</dd></div>
          </dl>
          <div className="card-actions">
            <button type="button">View PIN</button>
            <button type="button">Card settings</button>
            <button type="button" className="danger-action">Report a problem</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function OtherServicesView() {
  const items = ["Accounts", "Payments & transfers", "Savings", "Loans", "Documents", "Contact us"];
  return (
    <div className="service-page">
      <p className="eyebrow">Other</p>
      <h1>More banking services</h1>
      <p className="service-intro">Manage the rest of your everyday banking in one place.</p>
      <div className="other-services">
        {items.map((item, index) => (
          <button type="button" key={item}>
            <span aria-hidden>{["◎", "↗", "△", "□", "≡", "○"][index]}</span>
            <strong>{item}</strong>
            <small>Open service</small>
            <b aria-hidden>›</b>
          </button>
        ))}
      </div>
    </div>
  );
}
