import Link from "next/link";
import type { ReactNode } from "react";
import type { Metadata } from "next";
import { Navigation } from "@/components/Navigation";
import { Footer } from "@/components/Footer";
import { CopyButton } from "@/components/CopyButton";

export const metadata: Metadata = {
  title: "Models · Wavhost",
  description:
    "Wavhost models — Chatterbox (MIT), Qwen3-TTS CustomVoice / Base, and Kokoro-82M (Apache-2.0).",
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

const KOKORO_LANGUAGES = [
  "English",
  "Japanese",
  "Chinese",
  "Spanish",
  "French",
  "Hindi",
  "Italian",
  "Portuguese",
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
    notes: "23 languages via --language",
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
    notes: "Clone from reference audio",
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

const KOKORO: ModelRow[] = [
  {
    id: "kokoro",
    size: "82M",
    device: "CPU/GPU",
    notes: "54 named voices, default af_heart",
  },
];

function LanguageList({ languages }: { languages: readonly string[] }) {
  return (
    <ul className="model-langs" aria-label="Supported languages">
      {languages.map((lang) => (
        <li key={lang}>
          <span className="model-lang-pill">{lang}</span>
        </li>
      ))}
    </ul>
  );
}

function CommandChip({
  text,
  label,
}: {
  text: string;
  label: string;
}) {
  return (
    <div className="model-cmd">
      <code data-copy>{text}</code>
      <CopyButton
        text={text}
        className="copy-btn copy-btn--chip"
        label={label}
      />
    </div>
  );
}

function ModelEntry({ model }: { model: ModelRow }) {
  const cmd = `wavhost pull ${model.id}`;
  return (
    <li className="model-entry">
      <div className="model-entry-main">
        <div className="model-entry-idrow">
          <code className="model-entry-id">{model.id}</code>
          <span className="model-entry-meta">
            {model.size}
            <span aria-hidden="true"> · </span>
            {model.device}
          </span>
        </div>
        <p className="model-entry-notes">{model.notes}</p>
      </div>
      <CommandChip text={cmd} label={`Copy ${cmd}`} />
    </li>
  );
}

function ModelFamily({
  id,
  eyebrow,
  title,
  tags,
  description,
  languages,
  models,
  aside,
}: {
  id: string;
  eyebrow: string;
  title: string;
  tags: string[];
  description: ReactNode;
  languages: readonly string[];
  models: ModelRow[];
  aside?: ReactNode;
}) {
  return (
    <section className="model-family" id={id} aria-labelledby={`${id}-title`}>
      <header className="model-family-head">
        <div className="model-family-heading">
          <p className="model-family-eyebrow">{eyebrow}</p>
          <div className="model-family-title-row">
            <h2 className="model-family-title" id={`${id}-title`}>
              {title}
            </h2>
            <ul className="model-family-tags">
              {tags.map((tag) => (
                <li key={tag}>
                  <span className="model-tag">{tag}</span>
                </li>
              ))}
            </ul>
          </div>
          <p className="model-family-desc">{description}</p>
        </div>
        <div className="model-family-langs">
          <span className="model-family-langs-label">Languages</span>
          <LanguageList languages={languages} />
        </div>
      </header>

      <ul className="model-entry-list">
        {models.map((m) => (
          <ModelEntry key={m.id} model={m} />
        ))}
      </ul>

      {aside ? <aside className="model-family-aside">{aside}</aside> : null}
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

      <main id="main" className="models-page">
        <header className="models-hero">
          <div className="wrap models-wrap">
            <p className="models-kicker">Catalog</p>
            <h1 className="page-title">Models</h1>
            <p className="models-lede">
              Pull checkpoints from Hugging Face into local storage. Licenses
              appear at <code>wavhost pull</code> time; engines install on
              demand.
            </p>
            <nav className="models-toc" aria-label="Model families">
              <a href="#chatterbox-english">Chatterbox English</a>
              <a href="#chatterbox-multilingual">Multilingual</a>
              <a href="#qwen3-tts">Qwen3-TTS</a>
              <a href="#kokoro">Kokoro</a>
            </nav>
          </div>
        </header>

        <div className="wrap models-wrap models-stack">
          <ModelFamily
            id="chatterbox-english"
            eyebrow="Resemble AI"
            title="Chatterbox English"
            tags={["MIT", "English"]}
            description="Stock voice plus reference-audio cloning. Turbo is the usual default."
            languages={CHATTERBOX_EN_LANGUAGES}
            models={CHATTERBOX_EN}
          />

          <ModelFamily
            id="chatterbox-multilingual"
            eyebrow="Resemble AI"
            title="Chatterbox Multilingual"
            tags={["MIT", "23 languages"]}
            description={
              <>
                Same family with multilingual weights. Pass an ISO code with{" "}
                <code>--language</code> / API <code>language</code> (default{" "}
                <code>en</code>). Optional <code>--voice</code> for cloning.
              </>
            }
            languages={CHATTERBOX_MTL_LANGUAGES}
            models={CHATTERBOX_MTL}
            aside={
              <div className="model-aside-row">
                <span className="model-aside-label">Try</span>
                <CommandChip
                  text='wavhost run chatterbox-multilingual "Bonjour" -l fr'
                  label="Copy multilingual run"
                />
              </div>
            }
          />

          <ModelFamily
            id="qwen3-tts"
            eyebrow="Alibaba"
            title="Qwen3-TTS"
            tags={["Apache-2.0", "10 languages"]}
            description="CustomVoice (named speakers) and Base (clone from audio) stay as separate pulls."
            languages={QWEN_LANGUAGES}
            models={QWEN}
            aside={
              <>
                <div className="model-note">
                  <p>
                    <strong>CustomVoice</strong> — nine speakers (
                    <code>Ryan</code>, <code>Aiden</code>, <code>Vivian</code>,{" "}
                    <code>Serena</code>, <code>Uncle_Fu</code>,{" "}
                    <code>Dylan</code>, <code>Eric</code>,{" "}
                    <code>Ono_Anna</code>, <code>Sohee</code>). Default Ryan.
                    Native-language speakers sound best; cross-lingual still
                    works.
                  </p>
                  <p>
                    <strong>Base</strong> — clone with <code>--voice</code>{" "}
                    (saved voice or audio file) in any supported language.
                  </p>
                </div>
                <div className="model-aside-row">
                  <span className="model-aside-label">Try</span>
                  <CommandChip
                    text='wavhost run qwen-0.6-customvoice "Hello" --voice Ryan'
                    label="Copy Qwen CustomVoice run"
                  />
                </div>
              </>
            }
          />

          <ModelFamily
            id="kokoro"
            eyebrow="hexgrad"
            title="Kokoro"
            tags={["Apache-2.0", "8 languages"]}
            description="Lightweight 82M StyleTTS 2 model with 54 named voicepacks. No reference-audio cloning — pick a speaker name."
            languages={KOKORO_LANGUAGES}
            models={KOKORO}
            aside={
              <>
                <div className="model-note">
                  <p>
                    Default voice is <code>af_heart</code>. List every pack with{" "}
                    <code>wavhost show kokoro</code>. Prefix is language + gender (
                    <code>a</code> American, <code>b</code> British, <code>j</code> Japanese,{" "}
                    <code>z</code> Mandarin, <code>e</code> Spanish, <code>f</code> French,{" "}
                    <code>h</code> Hindi, <code>i</code> Italian, <code>p</code> Portuguese).
                  </p>
                  <p>
                    English works out of the box. Spanish, French, Hindi, Italian, and Portuguese
                    need <code>espeak-ng</code> on PATH. Japanese and Chinese need{" "}
                    <code>pip install &apos;misaki[ja]&apos;</code> /{" "}
                    <code>&apos;misaki[zh]&apos;</code>.
                  </p>
                </div>
                <div className="model-aside-row">
                  <span className="model-aside-label">Try</span>
                  <CommandChip
                    text='wavhost run kokoro "Hello from Kokoro" --voice af_heart'
                    label="Copy Kokoro run"
                  />
                </div>
              </>
            }
          />

          <p className="models-footer-note">
            CLI and API reference in the{" "}
            <Link href="/docs">docs</Link>.
          </p>
        </div>
      </main>

      <Footer />
    </>
  );
}
