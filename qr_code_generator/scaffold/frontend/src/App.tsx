import {
  ArrowRight,
  Check,
  Copy,
  Download,
  ExternalLink,
  Loader2,
  QrCode,
  RefreshCcw,
  Sparkles
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

type CreateResponse = {
  token: string;
  short_url: string;
  qr_code_url: string;
  original_url: string;
};

type ApiError = {
  detail?: string;
};

type Toast = {
  tone: "success" | "error";
  message: string;
};

const urlPattern = /^https?:\/\/[^\s/$.?#].[^\s]*$/i;

function localProxyUrl(value: string) {
  try {
    const url = new URL(value);
    if (url.hostname === "localhost" || url.hostname === "127.0.0.1") {
      return `${url.pathname}${url.search}`;
    }
  } catch {
    return value;
  }

  return value;
}

function formatHostname(value: string) {
  try {
    return new URL(value).hostname.replace(/^www\./, "");
  } catch {
    return "ready";
  }
}

function parseExpiry(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
}

function App() {
  const [url, setUrl] = useState("");
  const [useExpiry, setUseExpiry] = useState(false);
  const [expiresAt, setExpiresAt] = useState("");
  const [result, setResult] = useState<CreateResponse | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [fieldError, setFieldError] = useState("");
  const [toast, setToast] = useState<Toast | null>(null);

  const previewUrl = useMemo(() => {
    if (url.trim()) {
      return formatHostname(url.trim());
    }
    return result ? formatHostname(result.original_url) : "your link";
  }, [result, url]);

  useEffect(() => {
    if (!toast) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setToast(null);
    }, 5000);

    return () => window.clearTimeout(timeoutId);
  }, [toast]);

  useEffect(() => {
    if (!fieldError) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setFieldError("");
    }, 3000);

    return () => window.clearTimeout(timeoutId);
  }, [fieldError]);

  async function createQr(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setToast(null);
    setFieldError("");

    const normalizedInput = url.trim();
    if (!urlPattern.test(normalizedInput)) {
      setFieldError("Enter a complete URL starting with http:// or https://.");
      return;
    }

    const expiresAtIso = useExpiry && expiresAt ? parseExpiry(expiresAt) : null;
    if (useExpiry && expiresAt && !expiresAtIso) {
      setFieldError("Enter a valid expiration date and time.");
      return;
    }

    setIsGenerating(true);

    try {
      const response = await fetch("/api/qr/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: normalizedInput,
          expires_at: expiresAtIso
        })
      });

      if (!response.ok) {
        let detail = "Could not create this QR code.";
        try {
          const body = (await response.json()) as ApiError;
          detail = body.detail || detail;
        } catch {
          // Keep the default message for non-JSON failures.
        }
        throw new Error(detail);
      }

      const payload = (await response.json()) as CreateResponse;
      setResult(payload);
      setToast({ tone: "success", message: "Dynamic QR code created." });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "The backend is unavailable. Start FastAPI and try again.";
      setToast({ tone: "error", message });
    } finally {
      setIsGenerating(false);
    }
  }

  async function copyShortUrl() {
    if (!result) {
      return;
    }

    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error("Clipboard API unavailable");
      }

      await navigator.clipboard.writeText(result.short_url);
      setToast({ tone: "success", message: "Short link copied." });
    } catch {
      setToast({ tone: "error", message: "Unable to copy short link." });
    }
  }

  async function downloadQr() {
    if (!result) {
      return;
    }

    try {
      const response = await fetch(localProxyUrl(result.qr_code_url));

      if (!response.ok) {
        let detail = "Could not download this QR image.";
        try {
          const body = (await response.json()) as ApiError;
          detail = body.detail || detail;
        } catch {
          // Keep the default message for non-JSON failures.
        }
        throw new Error(detail);
      }

      const contentType = response.headers.get("Content-Type") || "";
      if (!contentType.includes("image/png")) {
        throw new Error("The QR image response was not a PNG file.");
      }

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = `qr-${result.token}.png`;
      link.click();
      URL.revokeObjectURL(objectUrl);
      setToast({ tone: "success", message: "QR image downloaded." });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Could not download this QR image.";
      setToast({ tone: "error", message });
    }
  }

  function reset() {
    setResult(null);
    setUrl("");
    setUseExpiry(false);
    setExpiresAt("");
    setFieldError("");
    setToast(null);
  }

  return (
    <main className="app-shell">
      <section className="hero-panel" aria-labelledby="page-title">
        <div className="hero-copy">
          <div className="eyebrow">
            <Sparkles size={16} aria-hidden="true" />
            Dynamic link manager
          </div>
          <h1 id="page-title">Create a QR code that stays editable.</h1>
          <p>
            Generate a short link QR code, copy it, download it, and keep the
            destination managed by your FastAPI backend.
          </p>
        </div>

        <div className="qr-preview" aria-label="QR code preview">
          {result ? (
            <img
              src={localProxyUrl(result.qr_code_url)}
              alt={`QR code for ${result.short_url}`}
            />
          ) : (
            <div className="empty-qr">
              <QrCode size={72} strokeWidth={1.5} aria-hidden="true" />
              <span>{previewUrl}</span>
            </div>
          )}
        </div>
      </section>

      <section className="workspace" aria-label="QR generator">
        <form className="generator-card" onSubmit={createQr} noValidate>
          <div className="card-heading">
            <span>New QR</span>
            <strong>{result ? result.token : "ready"}</strong>
          </div>

          <label className="field">
            <span>Destination URL</span>
            <input
              type="text"
              inputMode="url"
              autoComplete="url"
              placeholder="https://example.com"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              aria-invalid={fieldError ? "true" : "false"}
            />
          </label>
          {fieldError ? <p className="field-error">{fieldError}</p> : null}

          <label className="expiry-toggle">
            <input
              type="checkbox"
              checked={useExpiry}
              onChange={(event) => setUseExpiry(event.target.checked)}
            />
            <span>Set an expiration time</span>
          </label>

          {useExpiry ? (
            <label className="field">
              <span>Expires at</span>
              <input
                type="datetime-local"
                value={expiresAt}
                onChange={(event) => setExpiresAt(event.target.value)}
              />
            </label>
          ) : null}

          <button className="primary-action" type="submit" disabled={isGenerating}>
            {isGenerating ? (
              <Loader2 className="spin" size={20} aria-hidden="true" />
            ) : (
              <ArrowRight size={20} aria-hidden="true" />
            )}
            {isGenerating ? "Generating" : "Generate QR"}
          </button>
        </form>

        <aside className="result-card" aria-live="polite">
          {result ? (
            <>
              <div className="success-pill">
                <Check size={16} aria-hidden="true" />
                Live QR code
              </div>

              <dl className="result-list">
                <div>
                  <dt>Short link</dt>
                  <dd>{result.short_url}</dd>
                </div>
                <div>
                  <dt>Target</dt>
                  <dd>{result.original_url}</dd>
                </div>
                <div>
                  <dt>Token</dt>
                  <dd>{result.token}</dd>
                </div>
              </dl>

              <div className="action-grid">
                <button type="button" onClick={copyShortUrl}>
                  <Copy size={18} aria-hidden="true" />
                  Copy
                </button>
                <a href={localProxyUrl(result.short_url)} target="_blank" rel="noreferrer">
                  <ExternalLink size={18} aria-hidden="true" />
                  Open
                </a>
                <button type="button" onClick={downloadQr}>
                  <Download size={18} aria-hidden="true" />
                  Download
                </button>
                <button type="button" onClick={reset}>
                  <RefreshCcw size={18} aria-hidden="true" />
                  Reset
                </button>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <QrCode size={36} strokeWidth={1.7} aria-hidden="true" />
              <h2>Your QR details will appear here.</h2>
              <p>Generate a code to get a short link, token, and download-ready PNG.</p>
            </div>
          )}
        </aside>
      </section>

      {toast ? <div className={`toast ${toast.tone}`}>{toast.message}</div> : null}
    </main>
  );
}

export default App;
