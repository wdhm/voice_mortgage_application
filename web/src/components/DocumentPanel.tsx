import { useEffect, useRef, useState } from "react";
import {
  getDocumentState,
  getExtractionJson,
  previewUrl,
  removeDocument,
  reviewApprove,
  reviewEdit,
  reviewReject,
  uploadDocument,
  uploadedPreviewUrl,
  type DocumentProjection,
  type ExtractionField,
  type FieldName,
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

const ACCEPTED_TYPES = "application/pdf,image/png,image/jpeg,image/webp,image/tiff";

function pct(c: number | null): string {
  return c === null ? "—" : `${Math.round(c * 100)}%`;
}

function confClass(f: ExtractionField): string {
  if (f.provenance === "human-approved") return "ok";
  return f.passes ? "ok" : "low";
}

export function DocumentPanel({
  role,
  refreshKey = 0,
  onContinue,
}: {
  role: AppRole;
  refreshKey?: number;
  onContinue?: () => void;
}) {
  const [doc, setDoc] = useState<DocumentProjection | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isAdvisor = role === "advisor";

  useEffect(() => {
    if (!busy) getDocumentState().then(setDoc).catch(() => {});
  }, [busy, refreshKey]);

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

  const onRemove = async () => {
    setBusy(true);
    setError(null);
    try {
      setDoc(await removeDocument());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return isAdvisor ? (
    <AdvisorPanel doc={doc} setDoc={setDoc} busy={busy} setBusy={setBusy} error={error} setError={setError} />
  ) : (
    <CustomerUpload
      doc={doc}
      busy={busy}
      error={error}
      onUpload={onUpload}
      onRemove={onRemove}
      onContinue={onContinue}
    />
  );
}

/* ------------------------------------------------------------------ */
/* Customer: upload plus a clear summary of the required and extracted data. */
/* ------------------------------------------------------------------ */

function CustomerUpload({
  doc,
  busy,
  error,
  onUpload,
  onRemove,
  onContinue,
}: {
  doc: DocumentProjection | null;
  busy: boolean;
  error: string | null;
  onUpload: (file: File) => void;
  onRemove: () => void;
  onContinue?: () => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const state = doc?.document_state ?? "empty";
  const uploaded = doc?.uploaded_document ?? null;
  const analyzing = state === "analyzing";
  const submitted = uploaded !== null && !analyzing;
  const fields = doc?.fields ?? null;
  const approved = state === "accepted_automatically" || state === "accepted_after_review";
  const rejected = state === "analysis_failed" || state === "rejected_by_reviewer";

  const pick = () => !busy && inputRef.current?.click();

  const receipt = (() => {
    switch (state) {
      case "accepted_automatically":
      case "accepted_after_review":
        return { tone: "ok", text: "Payslip received — your income has been verified." };
      case "rejected_by_reviewer":
        return { tone: "warn", text: "This document couldn't be used. Please upload a new payslip." };
      case "analysis_failed":
        return { tone: "warn", text: "We couldn't process that file. Please upload a new payslip." };
      case "review_required":
        return {
          tone: "review",
          text: "Automated checks passed. Your payslip is waiting for an advisor to approve it.",
        };
      default:
        return { tone: "ok", text: "Payslip received. Bank Alfa is reviewing your income." };
    }
  })();

  return (
    <div className="doc-panel">
      <div className="doc-head">
        <h2>Income verification</h2>
        {approved && <span className="doc-status verified">✓ Approved</span>}
        {state === "review_required" && <span className="doc-status review">Awaiting advisor</span>}
      </div>
      <p className="doc-sub">
        Upload your latest payslip. We will read the five required income details below and show you
        what was found.
      </p>

      {error && <div className="doc-error">{error}</div>}

      <input
        ref={inputRef}
        className="visually-hidden"
        type="file"
        accept={ACCEPTED_TYPES}
        disabled={busy}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onUpload(file);
          e.target.value = "";
        }}
      />

      {rejected && (
        <section className="payslip-rejected-card" role="alert">
          <div className="payslip-rejected-head">
            <span className="payslip-rejected-icon" aria-hidden>▲</span>
            <div>
              <strong>We couldn’t process your payslip</strong>
              <p>
                We weren’t able to process this payslip automatically. Please upload it again. If
                you need any help, contact us and we’ll be glad to assist.
              </p>
            </div>
          </div>
          {uploaded && <p className="payslip-rejected-file">Rejected file: {uploaded.filename}</p>}
          <div className="payslip-rejected-actions">
            <button type="button" className="icon-btn primary" onClick={pick} disabled={busy}>
              Re-upload payslip
            </button>
            <button type="button" className="icon-btn remove-upload" onClick={onRemove} disabled={busy}>
              Remove
            </button>
          </div>
        </section>
      )}

      {analyzing && (
        <div className="ocr-progress" role="status">
          <div className="ocr-progress-head">
            <span className="upload-file-icon" aria-hidden>OCR</span>
            <div>
              <strong>Reading your new payslip…</strong>
              <small>Extracting employer, salary, employment type, and pay date.</small>
            </div>
          </div>
          <div className="ocr-progress-track" aria-hidden><span /></div>
          <p>Running automated document checks</p>
        </div>
      )}

      {!analyzing && !submitted && (
        <button
          type="button"
          className={`upload-dropzone ${dragOver ? "drag" : ""}`}
          onClick={pick}
          disabled={busy}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files?.[0];
            if (file) onUpload(file);
          }}
        >
          <span className="upload-dropzone-icon" aria-hidden>↑</span>
          <strong>Upload your payslip</strong>
          <span className="upload-dropzone-hint">Click to choose a file, or drag &amp; drop it here</span>
          <span className="upload-dropzone-meta">PDF or image (PNG, JPEG, WEBP, TIFF) · up to 10 MB</span>
        </button>
      )}

      {submitted && !rejected && (
        <>
          {approved && (
            <div className="income-approved">
              <div>
                <strong>Income verification approved</strong>
                <span>All required payslip information was found and accepted.</span>
              </div>
              {onContinue && (
                <button type="button" className="icon-btn primary" onClick={onContinue}>
                  Continue to appointment →
                </button>
              )}
            </div>
          )}
          {state === "review_required" && (
            <div className="income-review-pending">
              <div>
                <strong>Automated review complete</strong>
                <span>Your payslip was read successfully and is waiting for a Bank Alfa advisor.</span>
              </div>
              <span className="doc-status review">Manual approval needed</span>
            </div>
          )}
          <div className={`upload-receipt ${receipt.tone}`}>
            <span className="upload-file-icon" aria-hidden>
              {uploaded?.content_type === "application/pdf" ? "PDF" : "DOC"}
            </span>
            <div>
              <strong>{uploaded?.filename}</strong>
              <small>{receipt.text}</small>
            </div>
          </div>
          <div className="upload-actions">
            <button type="button" className="icon-btn" onClick={pick} disabled={busy}>
              Upload a different file
            </button>
            <button type="button" className="icon-btn remove-upload" onClick={onRemove} disabled={busy}>
              Remove
            </button>
          </div>
        </>
      )}

      <div className="customer-extraction">
        <div className="customer-extraction-head">
          <h3>{fields ? "Information autofilled from your payslip" : "Information we will autofill"}</h3>
          <span>{fields ? "Extracted from your PDF" : "After upload"}</span>
        </div>
        <table className="field-table">
          <thead>
            <tr>
              <th>Payslip information</th>
              <th>{fields ? "Autofilled value" : "Status"}</th>
              {fields && <th className="fconf">Result</th>}
            </tr>
          </thead>
          <tbody>
            {FIELD_ORDER.map((name) => {
              const field = fields?.[name];
              return (
                <tr key={name} className={field && !field.passes ? "flagged" : ""}>
                  <td className="fname">{FIELD_LABELS[name]}</td>
                  <td className="fval">{field ? field.value ?? "Not found" : "Required"}</td>
                  {fields && (
                    <td className={`fconf ${field?.passes ? "ok" : "low"}`}>
                      {field?.passes ? "✓ Found" : "Needs review"}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
        {state === "review_required" && (
          <p className="customer-review-note">
            All required details were found. A Bank Alfa advisor now needs to approve the extracted
            information before your income is verified.
          </p>
        )}
        {doc?.provider === "simulated" && fields && (
          <p className="simulation-note">
            Demo mode: this local preview uses simulated extraction. Set DOCUMENT_PROVIDER=foundry for live
            Microsoft Foundry OCR.
          </p>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Advisor: full Content Understanding processing — extracted fields,   */
/* human review, the structured JSON contract, and the source preview.  */
/* ------------------------------------------------------------------ */

function AdvisorPanel({
  doc,
  setDoc,
  busy,
  setBusy,
  error,
  setError,
}: {
  doc: DocumentProjection | null;
  setDoc: React.Dispatch<React.SetStateAction<DocumentProjection | null>>;
  busy: boolean;
  setBusy: React.Dispatch<React.SetStateAction<boolean>>;
  error: string | null;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
}) {
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [extraction, setExtraction] = useState<Record<string, unknown> | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (doc?.fields) {
      getExtractionJson().then(setExtraction).catch(() => setExtraction(null));
    } else {
      setExtraction(null);
    }
  }, [doc]);

  const state = doc?.document_state ?? "empty";
  const fields = doc?.fields ?? null;
  const accepted = state === "accepted_automatically" || state === "accepted_after_review";

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

  const prettyJson = extraction ? JSON.stringify(extraction, null, 2) : "";

  const copyJson = async () => {
    if (!prettyJson) return;
    try {
      await navigator.clipboard.writeText(prettyJson);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  const downloadJson = () => {
    if (!prettyJson) return;
    const blob = new Blob([prettyJson], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "income-extraction.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const up = doc?.uploaded_document ?? null;
  const previewCT = up?.content_type ?? "";
  const canPreview = !!up && (!!up.sample_key || previewCT === "application/pdf" || previewCT.startsWith("image/"));
  const previewSrc = up
    ? up.sample_key
      ? previewUrl(up.sample_key)
      : `${uploadedPreviewUrl}?ts=${encodeURIComponent(up.uploaded_at)}`
    : "";

  return (
    <div className="doc-panel">
      <div className="doc-head">
        <h2>Income evidence</h2>
        <div className="doc-head-actions">
          {accepted && <span className="doc-status verified">✓ Income verified</span>}
        </div>
      </div>
      <p className="doc-sub">
        Review extracted income evidence. Fields below {Math.round((doc?.threshold ?? 0.85) * 100)}% confidence
        require a human decision.
      </p>

      {error && <div className="doc-error">{error}</div>}

      {up && (
        <div className="upload-meta">
          <div>
            <span className="upload-file-icon" aria-hidden>
              {previewCT === "application/pdf" ? "PDF" : "DOC"}
            </span>
            <span>
              <strong>{up.filename}</strong>
              <small>
                Processed with {doc?.provider === "foundry" ? "Microsoft Foundry" : "simulated document extraction"}
              </small>
            </span>
          </div>
          <span className={`provider-badge ${doc?.provider}`}>{doc?.provider}</span>
        </div>
      )}

      {doc?.provider === "simulated" && up && up.sample_key === null && (
        <p className="simulation-note">
          Demo mode: structured values are simulated to demonstrate the extraction and human-review workflow.
        </p>
      )}

      {state === "empty" && (
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

            {extraction && (
              <div className="extraction-json">
                <div className="extraction-json-head">
                  <div>
                    <p className="pane-title">Structured extraction</p>
                    <span className="extraction-json-sub">
                      Reusable JSON contract — normalized values, confidence and analyzer metadata.
                    </span>
                  </div>
                  <div className="extraction-json-actions">
                    <button type="button" className="icon-btn" onClick={copyJson}>
                      {copied ? "Copied ✓" : "Copy"}
                    </button>
                    <button type="button" className="icon-btn" onClick={downloadJson}>
                      Download .json
                    </button>
                  </div>
                </div>
                <pre className="extraction-json-body">
                  <code>{prettyJson}</code>
                </pre>
              </div>
            )}
          </div>
          {canPreview && (
            <div className="preview">
              <p className="preview-label">Source document</p>
              <iframe title="Payslip preview" src={previewSrc} />
            </div>
          )}
        </div>
      )}

      {state === "rejected_by_reviewer" && (
        <div className="doc-terminal">
          <p>Document rejected. Waiting for Emma to upload a new document.</p>
        </div>
      )}
      {state === "analysis_failed" && (
        <div className="doc-terminal error">
          <p>Analysis failed. Waiting for a new document.</p>
        </div>
      )}
    </div>
  );
}
