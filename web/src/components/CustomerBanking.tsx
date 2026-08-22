import { useEffect, useState } from "react";
import { getCase, type CaseCard, type DemoCaseView } from "../lib/api";

export type CustomerService = "profile" | "cards" | "mortgage" | "other";

const SERVICES: Array<{
  id: CustomerService;
  title: string;
  description: string;
  icon: string;
}> = [
  {
    id: "profile",
    title: "Personal information",
    description: "Contact details, address and preferences",
    icon: "●",
  },
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
          </button>
        ))}
      </nav>
    </aside>
  );
}

export function PersonalInfoView({
  refreshKey,
  phoneUpdated,
}: {
  refreshKey: number;
  phoneUpdated: boolean;
}) {
  const [demoCase, setDemoCase] = useState<DemoCaseView | null>(null);

  useEffect(() => {
    getCase().then(setDemoCase).catch(() => {});
  }, [refreshKey]);

  const profile = demoCase?.customer_profile;
  const updatedAt = profile?.contact_details_updated_at
    ? new Intl.DateTimeFormat("en-GB", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(profile.contact_details_updated_at))
    : null;

  return (
    <div className="service-page personal-info-page">
      <p className="eyebrow">Personal information</p>
      <h1>Your details</h1>
      <p className="service-intro">
        Review the information Bank Alfa uses to contact you and provide your services.
      </p>

      {phoneUpdated && (
        <div className="profile-update-banner" role="status">
          <span aria-hidden>✓</span>
          <div>
            <strong>Phone number updated</strong>
            <p>The voice assistant saved your confirmed number to your customer profile.</p>
          </div>
        </div>
      )}

      <section className="profile-details-card" aria-label="Emma's personal details">
        <div className="profile-card-heading">
          <span className="profile-large-avatar" aria-hidden>EL</span>
          <div>
            <h2>{profile?.display_name ?? "Emma Lindberg"}</h2>
            <span>Personal customer</span>
          </div>
        </div>
        <dl className="profile-detail-list">
          <div>
            <dt>Phone number</dt>
            <dd className={phoneUpdated ? "recently-updated" : ""}>
              {profile?.phone_number ?? "Loading…"}
              {updatedAt && <small>Updated {updatedAt} by {profile?.contact_details_updated_by}</small>}
            </dd>
          </div>
          <div><dt>Email</dt><dd>{profile?.email ?? "Loading…"}</dd></div>
          <div>
            <dt>Home address</dt>
            <dd>
              {profile
                ? <>{profile.street_address}<br />{profile.postal_code} {profile.city}<br />{profile.country}</>
                : "Loading…"}
            </dd>
          </div>
          <div><dt>Preferred language</dt><dd>{profile?.preferred_language ?? "Loading…"}</dd></div>
          <div>
            <dt>Customer since</dt>
            <dd>{profile ? new Date(profile.customer_since).getFullYear() : "Loading…"}</dd>
          </div>
          <div><dt>Customer number</dt><dd>{profile?.customer_number ?? "Loading…"}</dd></div>
        </dl>
      </section>
    </div>
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

  const defaultCards: CaseCard[] = [
    {
      card_id: "card-mc-4471",
      card_type: "Bank Alfa Mastercard",
      last_four: "4471",
      status: "active",
    },
    {
      card_id: "card-visa-1842",
      card_type: "Bank Alfa Everyday Debit",
      last_four: "1842",
      status: "active",
    },
  ];
  const cards = defaultCards.map(
    (defaultCard) =>
      demoCase?.cards.find((card) => card.card_id === defaultCard.card_id) ?? defaultCard,
  );

  return (
    <div className="service-page">
      <p className="eyebrow">Cards</p>
      <h1>Your cards</h1>
      <p className="service-intro">View card details, spending and support options.</p>
      <div className="card-list">
        {cards.map((card) => {
          const isDebit = card.card_type.includes("Debit");
          const blocked = card.status === "blocked" || card.status === "replacement_ordered";

          return (
            <div className="cards-layout" key={card.card_id}>
              <div className={`bank-card ${isDebit ? "debit" : ""} ${blocked ? "blocked" : ""}`}>
                <span className="bank-card-brand">Bank Alfa</span>
                <span className="bank-card-chip" aria-hidden />
                <span className="bank-card-number">•••• •••• •••• {card.last_four}</span>
                <span className="bank-card-holder">EMMA LINDBERG</span>
                <strong>{isDebit ? "VISA" : "Mastercard"}</strong>
              </div>
              <div className="card-details">
                <span className={`card-state ${blocked ? "blocked" : ""}`}>
                  {blocked ? "Card blocked" : "Card active"}
                </span>
                <h2>{card.card_type} ·{card.last_four}</h2>
                <dl>
                  {isDebit ? (
                    <>
                      <div><dt>Linked account</dt><dd>Salary account ·1842</dd></div>
                      <div><dt>Available balance</dt><dd>84 250 kr</dd></div>
                      <div><dt>Daily purchase limit</dt><dd>20 000 kr</dd></div>
                    </>
                  ) : (
                    <>
                      <div><dt>Available credit</dt><dd>32 450 kr</dd></div>
                      <div><dt>Monthly limit</dt><dd>50 000 kr</dd></div>
                      <div><dt>Next invoice</dt><dd>4 180 kr</dd></div>
                    </>
                  )}
                </dl>
                <div className="card-actions">
                  <button type="button">View PIN</button>
                  <button type="button">Card settings</button>
                  <button type="button" className="danger-action">Report a problem</button>
                </div>
              </div>
            </div>
          );
        })}
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
