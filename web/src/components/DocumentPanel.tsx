import { useEffect, useState } from "react";
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

export function DocumentPanel({ onContinue }: { onContinue: () => void }) {
  const [samples, setSamples] = useState<SampleMeta[]>([]);
  const [doc, setDoc] = useState<DocumentProjection | null>(null);
  const [busy, setBusy] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSamples().then(setSamples).catch(() => {});
    getDocumentState().then(setDoc).catch(() => {});
  }, []);

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

  return (
    <div className="doc-panel">
      <div className="doc-head">
        <h2>Income verification</h2>
        {accepted && <span className="doc-status verified">✓ Income verified</span>}
      </div>
      <p className="doc-sub">
        The payslip is read automatically. Any field below {Math.round((doc?.threshold ?? 0.85) * 100)}% confidence is
        flagged for the advisor to confirm before it is used.
      </p>

      {error && <div className="doc-error">{error}</div>}

      {state === "empty" && (
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
            {state === "review_required" && (
              <div className="review-banner">
                Human review required — correct the flagged fields, then approve.
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
                        {state === "review_required" ? (
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
                        {f.provenance === "human-approved"
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

            {state === "review_required" && (
              <div className="review-actions">
                <button className="icon-btn primary" disabled={busy} onClick={approve}>
                  Approve income
                </button>
                <button className="icon-btn" disabled={busy} onClick={reject}>
                  Reject
                </button>
              </div>
            )}
            {accepted && (
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
          <p>Document rejected. Reset the demo to try another payslip.</p>
        </div>
      )}
      {state === "analysis_failed" && (
        <div className="doc-terminal error">
          <p>Analysis failed. Reset the demo and retry.</p>
        </div>
      )}
    </div>
  );
}
