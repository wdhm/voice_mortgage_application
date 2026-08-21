import { useEffect, useRef, useState } from "react";
import {
  analyzeSample,
  getDocumentState,
  listSamples,
  previewUrl,
  reviewApprove,
  reviewEdit,
  reviewReject,
  uploadDocument,
  type DocumentProjection,
  type ExtractionField,
  type FieldName,
  type SampleMeta,
} from "../lib/api";
import type { AppRole } from "./Header";

const FIELD_LABELS: Record<FieldName, string> = {
  employer_name: "Employer",
  gross_salary_monthly: "Gross salary (monthly)",
  net_salary_monthly: "Net salary (monthly)",
  employment_type: "Employment type",
  pay_date: "Pay date",
};

const FIELD_ORDER: FieldName[] = [
  "employer_name",
  "gross_salary_monthly",
  "net_salary_monthly",
  "employment_type",
  "pay_date",
];

function pct(c: number | null): string {
  return c === null ? "—" : `${Math.round(c * 100)}%`;
}

function confClass(f: ExtractionField): string {
  if (f.provenance === "human-approved") return "ok";
  return f.passes ? "ok" : "low";
}

export function DocumentPanel({
  role,
  onContinue,
  refreshKey = 0,
}: {
  role: AppRole;
  onContinue?: () => void;
  refreshKey?: number;
}) {
  const [samples, setSamples] = useState<SampleMeta[]>([]);
  const [doc, setDoc] = useState<DocumentProjection | null>(null);
  const [busy, setBusy] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const uploadRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (role === "customer") listSamples().then(setSamples).catch(() => {});
  }, [role]);

  useEffect(() => {
    if (!busy) getDocumentState().then(setDoc).catch(() => {});
  }, [busy, refreshKey]);

  const state = doc?.document_state ?? "empty";
  const sampleKey = doc?.uploaded_document?.sample_key ?? null;

  const runSample = async (key: string) => {
    setBusy(true);
    setError(null);
    setDoc({ ...(doc as DocumentProjection), document_state: "analyzing" });
    try {
      setDoc(await analyzeSample(key));
    } finally {
      setBusy(false);
    }
  };

  const onUpload = async (file: File) => {
    setBusy(true);
    setError(null);
    setDoc((d) => (d ? { ...d, document_state: "analyzing" } : d));
    try {
      setDoc(await uploadDocument(file));
    } catch (e) {
      setError((e as Error).message);
      setDoc(await getDocumentState());
    } finally {
      setBusy(false);
    }
  };

  const saveEdit = async (field: FieldName) => {
    const value = drafts[field];
    if (value === undefined) return;
    setBusy(true);
    try {
      setDoc(await reviewEdit(field, value));
      setDrafts((d) => {
        const n = { ...d };
        delete n[field];
        return n;
      });
    } finally {
      setBusy(false);
    }
  };

  const approve = async () => {
    setBusy(true);
    setError(null);
    try {
      setDoc(await reviewApprove());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const reject = async () => {
    setBusy(true);
    try {
      setDoc(await reviewReject());
    } finally {
      setBusy(false);
    }
  };

  const accepted = state === "accepted_automatically" || state === "accepted_after_review";
  const fields = doc?.fields ?? null;
  const isAdvisor = role === "advisor";

  return (
    <div className="doc-panel">
      <div className="doc-head">
        <h2>{isAdvisor ? "Income evidence" : "Income verification"}</h2>
        <div className="doc-head-actions">
          {accepted && <span className="doc-status verified">✓ Income verified</span>}
          {!isAdvisor && (
            <>
              <input
                ref={uploadRef}
                className="visually-hidden"
                type="file"
                accept="application/pdf,image/png,image/jpeg,image/webp,image/tiff"
                disabled={busy}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onUpload(file);
                  e.target.value = "";
                }}
              />
              <button
                type="button"
                className="icon-btn upload-new"
                disabled={busy}
                onClick={() => uploadRef.current?.click()}
              >
                + Upload new document
              </button>
            </>
          )}
        </div>
      </div>
      <p className="doc-sub">
        {isAdvisor
          ? `Review extracted income evidence. Fields below ${Math.round((doc?.threshold ?? 0.85) * 100)}% confidence require a human decision.`
          : "Upload your latest payslip. We extract the income details and send uncertain fields to a Bank Alfa representative for review."}
      </p>

      {error && <div className="doc-error">{error}</div>}

      {doc?.uploaded_document && (
        <div className="upload-meta">
          <div>
            <span className="upload-file-icon" aria-hidden>PDF</span>
            <span>
              <strong>{doc.uploaded_document.filename}</strong>
              <small>Processed with {doc.provider === "foundry" ? "Microsoft Foundry" : "simulated document extraction"}</small>
            </span>
          </div>
          <span className={`provider-badge ${doc.provider}`}>{doc.provider}</span>
        </div>
      )}

      {doc?.provider === "simulated" && doc.uploaded_document?.sample_key === null && (
        <p className="simulation-note">
          Demo mode: structured values are simulated to demonstrate the extraction and human-review workflow.
        </p>
      )}

      {state === "empty" && !isAdvisor && (
        <div className="doc-intake">
          <div className="samples">
            <p className="pane-title">Payslips</p>
            {samples.map((s) => (
              <button key={s.key} className="sample-card" disabled={busy} onClick={() => runSample(s.key)}>
                <strong>{s.label}</strong>
                <span>{s.description}</span>
              </button>
            ))}
          </div>
          <label className="upload">
            <input
              type="file"
              accept="application/pdf,image/png,image/jpeg,image/webp,image/tiff"
              disabled={busy}
              onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
            />
            <span>Or upload a file (PDF / image, ≤10 MB)</span>
          </label>
        </div>
      )}

      {state === "empty" && isAdvisor && (
        <div className="doc-terminal">
          <p>Waiting for Emma to submit a payslip.</p>
        </div>
      )}

      {state === "analyzing" && (
        <div className="doc-analyzing">
          <div className="skeleton" />
          <div className="skeleton" />
          <div className="skeleton short" />
          <p>Analyzing payslip…</p>
        </div>
      )}

      {(accepted || state === "review_required") && fields && (
        <div className="doc-review">
          <div className="analysis">
            {state === "review_required" && isAdvisor && (
              <div className="review-banner">
                Human review required — correct the flagged fields, then approve.
              </div>
            )}
            {state === "review_required" && !isAdvisor && (
              <div className="review-banner customer-waiting">
                Your payslip is with a Bank Alfa representative for review. You can continue when it has been confirmed.
              </div>
            )}
            <table className="field-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Extracted value</th>
                  <th className="fconf">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {FIELD_ORDER.map((name) => {
                  const f = fields[name];
                  const editing = drafts[name] !== undefined;
                  const flagged = state === "review_required" && !f.passes && f.provenance !== "human-approved";
                  return (
                    <tr key={name} className={flagged ? "flagged" : ""}>
                      <td className="fname">{FIELD_LABELS[name]}</td>
                      <td className="fval">
                        {state === "review_required" && isAdvisor ? (
                          <input
                            value={editing ? drafts[name] : (f.value ?? "")}
                            onChange={(e) => setDrafts((d) => ({ ...d, [name]: e.target.value }))}
                            onBlur={() => editing && saveEdit(name)}
                            disabled={busy}
                          />
                        ) : (
                          <span>{f.value ?? "—"}</span>
                        )}
                        {f.original_value && f.original_value !== f.value && (
                          <span className="orig">was: {f.original_value}</span>
                        )}
                      </td>
                      <td className={`fconf ${confClass(f)}`}>
                        {!isAdvisor
                          ? f.passes || f.provenance === "human-approved" ? "Received" : "In review"
                          : f.provenance === "human-approved"
                          ? "Confirmed"
                          : confClass(f) === "ok"
                            ? `✓ ${pct(f.confidence)}`
                            : `${pct(f.confidence)} · review`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {state === "review_required" && isAdvisor && (
              <div className="review-actions">
                <button className="icon-btn primary" disabled={busy} onClick={approve}>
                  Approve income
                </button>
                <button className="icon-btn" disabled={busy} onClick={reject}>
                  Reject
                </button>
              </div>
            )}
            {accepted && !isAdvisor && (
              <div className="analysis-foot">
                <button className="icon-btn continue-next" onClick={onContinue}>
                  Continue →
                </button>
              </div>
            )}
          </div>
          {sampleKey && (
            <div className="preview">
              <p className="preview-label">Source document</p>
              <iframe title="Payslip preview" src={previewUrl(sampleKey)} />
            </div>
          )}
        </div>
      )}

      {state === "rejected_by_reviewer" && (
        <div className="doc-terminal">
          <p>Document rejected. Upload a new document to try again.</p>
        </div>
      )}
      {state === "analysis_failed" && (
        <div className="doc-terminal error">
          <p>Analysis failed. Upload a new document and retry.</p>
        </div>
      )}
    </div>
  );
}
