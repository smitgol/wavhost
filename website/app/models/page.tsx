import Link from "next/link";
import type { ReactNode } from "react";
import type { Metadata } from "next";
import { Navigation } from "@/components/Navigation";
import { Footer } from "@/components/Footer";
import { CopyButton } from "@/components/CopyButton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export const metadata: Metadata = {
  title: "Models · Wavhost",
  description:
    "Wavhost models — Chatterbox English + Multilingual (MIT) and Qwen3-TTS CustomVoice / Base (Apache-2.0).",
};

const CHATTERBOX_EN_LANGUAGES = ["English"] as const;

/** Official Chatterbox Multilingual language list (ISO codes → names). */
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

/** Qwen3-TTS 12Hz CustomVoice / Base (official): 10 languages. */
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
};

const CHATTERBOX_EN: ModelRow[] = [
  {
    id: "chatterbox-turbo",
    size: "350M",
    device: "GPU",
    notes: "Fast English — recommended default",
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

function LanguageBadges({ languages }: { languages: readonly string[] }) {
  return (
    <ul className="model-langs" aria-label="Supported languages">
      {languages.map((lang) => (
        <li key={lang}>
          <Badge variant="outline">{lang}</Badge>
        </li>
      ))}
    </ul>
  );
}

function PullChip({ modelId }: { modelId: string }) {
  const cmd = `wavhost pull ${modelId}`;
  return (
    <div className="model-pull">
      <code data-copy>{cmd}</code>
      <CopyButton
        text={cmd}
        className="copy-btn copy-btn--chip"
        label={`Copy ${cmd}`}
      />
    </div>
  );
}

function ModelEntry({ model }: { model: ModelRow }) {
  return (
    <article className="model-entry">
      <div className="model-entry-top">
        <h3 className="model-entry-id">
          <code>{model.id}</code>
        </h3>
        <p className="model-entry-meta">
          <span>{model.size}</span>
          <span aria-hidden="true">·</span>
          <span>{model.device}</span>
        </p>
      </div>
      <p className="model-entry-notes">{model.notes}</p>
      <PullChip modelId={model.id} />
    </article>
  );
}

function ModelFamily({
  title,
  badges,
  description,
  languages,
  models,
  footer,
}: {
  title: string;
  badges: ReactNode;
  description: ReactNode;
  languages: readonly string[];
  models: ModelRow[];
  footer?: ReactNode;
}) {
  return (
    <section className="model-family">
      <header className="model-family-head">
        <div className="model-family-title-row">
          <h2 className="model-family-title">{title}</h2>
          <div className="model-family-badges">{badges}</div>
        </div>
        <p className="model-family-desc">{description}</p>
        <div className="model-family-langs">
          <p className="model-family-langs-label">Supported languages</p>
          <LanguageBadges languages={languages} />
        </div>
      </header>

      <div className="model-entry-list">
        {models.map((m) => (
          <ModelEntry key={m.id} model={m} />
        ))}
      </div>

      {footer ? <div className="model-family-footer">{footer}</div> : null}
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
          <div className="wrap models-wrap">
            <h1 className="page-title">Models</h1>
            <p className="models-lede">
              Pull from Hugging Face into local storage. Licenses are shown at{" "}
              <code>wavhost pull</code> time. Engines install on demand.
            </p>
          </div>
        </section>

        <section className="section">
          <div className="wrap models-wrap models-stack">
            <ModelFamily
              title="Chatterbox · English"
              badges={
                <>
                  <Badge variant="secondary">MIT</Badge>
                  <Badge variant="outline">Resemble AI</Badge>
                </>
              }
              description="English TTS with built-in stock voice and reference-audio cloning."
              languages={CHATTERBOX_EN_LANGUAGES}
              models={CHATTERBOX_EN}
            />

            <ModelFamily
              title="Chatterbox · Multilingual"
              badges={
                <>
                  <Badge variant="secondary">MIT</Badge>
                  <Badge variant="outline">23 languages</Badge>
                </>
              }
              description={
                <>
                  Same engine family with multilingual weights. Pass an ISO
                  language code via <code>--language</code> / API{" "}
                  <code>language</code> (default <code>en</code>). Optional{" "}
                  <code>--voice</code> for cloning.
                </>
              }
              languages={CHATTERBOX_MTL_LANGUAGES}
              models={CHATTERBOX_MTL}
              footer={
                <div className="model-example">
                  <span className="model-example-label">Example</span>
                  <div className="model-pull">
                    <code data-copy>
                      wavhost run chatterbox-multilingual &quot;Bonjour&quot; -l
                      fr
                    </code>
                    <CopyButton
                      text='wavhost run chatterbox-multilingual "Bonjour" -l fr'
                      className="copy-btn copy-btn--chip"
                      label="Copy multilingual run"
                    />
                  </div>
                </div>
              }
            />

            <ModelFamily
              title="Qwen3-TTS"
              badges={
                <>
                  <Badge variant="secondary">Apache-2.0</Badge>
                  <Badge variant="outline">Alibaba</Badge>
                </>
              }
              description="Ten languages across CustomVoice and Base. Pulls stay separate — pick the checkpoint that matches your workflow."
              languages={QWEN_LANGUAGES}
              models={QWEN}
              footer={
                <>
                  <Alert>
                    <AlertTitle>CustomVoice vs Base</AlertTitle>
                    <AlertDescription>
                      <strong>CustomVoice</strong> uses nine named speakers (
                      <code>Ryan</code>, <code>Aiden</code>, <code>Vivian</code>
                      , <code>Serena</code>, <code>Uncle_Fu</code>,{" "}
                      <code>Dylan</code>, <code>Eric</code>,{" "}
                      <code>Ono_Anna</code>, <code>Sohee</code>). Default is
                      Ryan. Speakers have native languages (e.g. Ryan/Aiden
                      English; Vivian Chinese; Ono_Anna Japanese; Sohee Korean;
                      Dylan Beijing; Eric Sichuan) — cross-lingual still works,
                      native is best quality.
                      <br />
                      <strong>Base</strong> clones from <code>--voice</code>{" "}
                      (saved voice or audio file) in any of the ten languages.
                    </AlertDescription>
                  </Alert>

                  <div className="model-example">
                    <span className="model-example-label">Example</span>
                    <div className="model-pull">
                      <code data-copy>
                        wavhost run qwen-0.6-customvoice &quot;Hello&quot;
                        --voice Ryan
                      </code>
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

            <Separator />

            <p className="models-footer-note">
              Full CLI and API details:{" "}
              <Link href="/docs" className="underline underline-offset-2">
                Docs
              </Link>
              .
            </p>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
