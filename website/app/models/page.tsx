import Link from "next/link";
import type { Metadata } from "next";
import { Navigation } from "@/components/Navigation";
import { Footer } from "@/components/Footer";
import { CopyButton } from "@/components/CopyButton";

export const metadata: Metadata = {
  title: "Models · Wavhost",
  description:
    "Wavhost models — Chatterbox English + Multilingual (MIT) and Qwen3-TTS CustomVoice / Base (Apache-2.0).",
};

const CHATTERBOX_EN_LANGUAGES = ["English"] as const;

const CHATTERBOX_MTL_LANGUAGES = [
  "Arabic",
  "Danish",
  "German",
  "Greek",
  "English",
  "Spanish",
  "Finnish",
  "French",
  "Hebrew",
  "Hindi",
  "Italian",
  "Japanese",
  "Korean",
  "Malay",
  "Dutch",
  "Norwegian",
  "Polish",
  "Portuguese",
  "Russian",
  "Swedish",
  "Swahili",
  "Turkish",
  "Chinese",
] as const;

const QWEN_LANGUAGES = [
  "Chinese",
  "English",
  "Japanese",
  "Korean",
  "German",
  "French",
  "Russian",
  "Portuguese",
  "Spanish",
  "Italian",
] as const;

type ModelRow = {
  id: string;
  size: string;
  device: string;
  notes: string;
  recommended?: boolean;
};

const CHATTERBOX_EN: ModelRow[] = [
  {
    id: "chatterbox-turbo",
    size: "350M",
    device: "GPU",
    notes: "Fast English",
    recommended: true,
  },
  {
    id: "chatterbox-nano",
    size: "110M",
    device: "CPU/GPU",
    notes: "Lightweight, strong on CPU",
  },
  {
    id: "chatterbox-base",
    size: "500M",
    device: "GPU",
    notes: "Original high-quality English",
  },
];

const CHATTERBOX_MTL: ModelRow[] = [
  {
    id: "chatterbox-multilingual",
    size: "500M",
    device: "GPU",
    notes: "23 languages; pass --language fr / zh / …",
  },
];

const QWEN: ModelRow[] = [
  {
    id: "qwen-0.6-customvoice",
    size: "600M",
    device: "GPU",
    notes: "Named speakers, default Ryan",
  },
  {
    id: "qwen-0.6-base",
    size: "600M",
    device: "GPU",
    notes: "Voice cloning from reference audio",
  },
  {
    id: "qwen-1.7-customvoice",
    size: "1.7B",
    device: "GPU",
    notes: "Named speakers + style instruct",
  },
  {
    id: "qwen-1.7-base",
    size: "1.7B",
    device: "GPU",
    notes: "Higher-quality voice cloning",
  },
];

function LanguageList({ languages }: { languages: readonly string[] }) {
  if (languages.length === 1) {
    return <span className="catalog-langs-inline">{languages[0]}</span>;
  }

  return (
    <details className="catalog-langs-details">
      <summary>
        {languages.length} {languages.length === 1 ? "language" : "languages"} — Show list
      </summary>
      <p className="catalog-langs-list">{languages.join(", ")}</p>
    </details>
  );
}

function ModelCatalogRow({ model }: { model: ModelRow }) {
  const cmd = `wavhost pull ${model.id}`;

  return (
    <div className="catalog-row">
      <div className="catalog-row-id">
        <code>{model.id}</code>
        {model.recommended && <span className="catalog-recommended">Recommended</span>}
      </div>
      <span className="catalog-row-size">{model.size}</span>
      <span className="catalog-row-device">{model.device}</span>
      <span className="catalog-row-notes">{model.notes}</span>
      <div className="catalog-row-pull">
        <code data-copy>{cmd}</code>
        <CopyButton text={cmd} className="copy-btn copy-btn--chip" label={`Copy ${cmd}`} />
      </div>
    </div>
  );
}

function ModelFamilySection({
  id,
  title,
  license,
  description,
  languages,
  models,
  footer,
}: {
  id: string;
  title: string;
  license: string;
  description: React.ReactNode;
  languages: readonly string[];
  models: ModelRow[];
  footer?: React.ReactNode;
}) {
  return (
    <section id={id} className="catalog-family">
      <header className="catalog-family-head">
        <div className="catalog-family-title-row">
          <h2 className="catalog-family-title">{title}</h2>
          <span className="catalog-license">{license}</span>
        </div>
        <p className="catalog-family-desc">{description}</p>
        <div className="catalog-langs-row">
          <LanguageList languages={languages} />
        </div>
      </header>

      <div className="catalog-rows">
        {models.map((m) => (
          <ModelCatalogRow key={m.id} model={m} />
        ))}
      </div>

      {footer && <div className="catalog-family-footer">{footer}</div>}
    </section>
  );
}

export default function ModelsPage() {
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <Navigation currentPath="/models" />

      <main id="main">
        <section className="section models-hero">
          <div className="wrap catalog-wrap">
            <h1 className="page-title">Models</h1>
            <p className="catalog-lede">
              Pull from Hugging Face into local storage. Licenses are shown at{" "}
              <code>wavhost pull</code> time. Engines install on demand.
            </p>

            <nav className="catalog-jump-nav" aria-label="Jump to model family">
              <a href="#chatterbox-english">Chatterbox English</a>
              <span aria-hidden="true">·</span>
              <a href="#chatterbox-multilingual">Multilingual</a>
              <span aria-hidden="true">·</span>
              <a href="#qwen3-tts">Qwen3-TTS</a>
            </nav>
          </div>
        </section>

        <section className="section">
          <div className="wrap catalog-wrap catalog-stack">
            <ModelFamilySection
              id="chatterbox-english"
              title="Chatterbox · English"
              license="MIT"
              description="English TTS with built-in stock voice and reference-audio cloning."
              languages={CHATTERBOX_EN_LANGUAGES}
              models={CHATTERBOX_EN}
            />

            <ModelFamilySection
              id="chatterbox-multilingual"
              title="Chatterbox · Multilingual"
              license="MIT"
              description={
                <>
                  Same engine family with multilingual weights. Pass an ISO language code via{" "}
                  <code>--language</code> / API <code>language</code> (default <code>en</code>).
                  Optional <code>--voice</code> for cloning.
                </>
              }
              languages={CHATTERBOX_MTL_LANGUAGES}
              models={CHATTERBOX_MTL}
              footer={
                <div className="catalog-example">
                  <span className="catalog-example-label">Example</span>
                  <div className="catalog-row-pull">
                    <code data-copy>wavhost run chatterbox-multilingual &quot;Bonjour&quot; -l fr</code>
                    <CopyButton
                      text='wavhost run chatterbox-multilingual "Bonjour" -l fr'
                      className="copy-btn copy-btn--chip"
                      label="Copy multilingual run"
                    />
                  </div>
                </div>
              }
            />

            <ModelFamilySection
              id="qwen3-tts"
              title="Qwen3-TTS"
              license="Apache-2.0"
              description="Ten languages across CustomVoice and Base. Pulls stay separate — pick the checkpoint that matches your workflow."
              languages={QWEN_LANGUAGES}
              models={QWEN}
              footer={
                <>
                  <div className="catalog-comparison">
                    <div className="catalog-comparison-col">
                      <h3 className="catalog-comparison-title">CustomVoice</h3>
                      <p className="catalog-comparison-desc">
                        Nine named speakers: <code>Ryan</code>, <code>Aiden</code>,{" "}
                        <code>Vivian</code>, <code>Serena</code>, <code>Uncle_Fu</code>,{" "}
                        <code>Dylan</code>, <code>Eric</code>, <code>Ono_Anna</code>,{" "}
                        <code>Sohee</code>. Default is Ryan.
                      </p>
                      <p className="catalog-comparison-note">
                        Speakers have native languages (e.g. Ryan/Aiden English; Vivian Chinese;
                        Ono_Anna Japanese; Sohee Korean) — cross-lingual works, native is best
                        quality.
                      </p>
                    </div>
                    <div className="catalog-comparison-col">
                      <h3 className="catalog-comparison-title">Base</h3>
                      <p className="catalog-comparison-desc">
                        Clone from <code>--voice</code> (saved voice or audio file) in any of the
                        ten languages.
                      </p>
                    </div>
                  </div>

                  <div className="catalog-example">
                    <span className="catalog-example-label">Example</span>
                    <div className="catalog-row-pull">
                      <code data-copy>wavhost run qwen-0.6-customvoice &quot;Hello&quot; --voice Ryan</code>
                      <CopyButton
                        text='wavhost run qwen-0.6-customvoice "Hello" --voice Ryan'
                        className="copy-btn copy-btn--chip"
                        label="Copy Qwen CustomVoice run"
                      />
                    </div>
                  </div>
                </>
              }
            />

            <div className="catalog-footer-note">
              <p>
                Full CLI and API details:{" "}
                <Link href="/docs">
                  Docs
                </Link>
                .
              </p>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
