import Link from "next/link";
import type { ReactNode } from "react";
import { Navigation } from "@/components/Navigation";
import { DocsLayout } from "@/components/DocsLayout";
import { CopyButton } from "@/components/CopyButton";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "CLI · Docs · Wavhost",
  description: "Wavhost CLI reference — pull, run, voice, serve, list, rm, uninstall.",
};

function CommandChip({ text, label }: { text: string; label: string }) {
  return (
    <div className="model-cmd">
      <code data-copy>{text}</code>
      <CopyButton text={text} className="copy-btn copy-btn--chip" label={label} />
    </div>
  );
}

function Param({
  name,
  type,
  children,
}: {
  name: string;
  type?: string;
  children: ReactNode;
}) {
  return (
    <li className="docs-param">
      <div className="docs-param-name">
        <code>{name}</code>
        {type ? <span className="docs-param-type">{type}</span> : null}
      </div>
      <p className="docs-param-desc">{children}</p>
    </li>
  );
}

function CodeBlock({ text, label }: { text: string; label: string }) {
  return (
    <div className="code-wrap">
      <CopyButton text={text} className="copy-btn copy-btn--block" label={label} />
      <pre className="code">
        <code data-copy>{text}</code>
      </pre>
    </div>
  );
}

function CommandPanel({
  id,
  title,
  description,
  children,
}: {
  id: string;
  title: string;
  description?: ReactNode;
  children: ReactNode;
}) {
  return (
    <article className="endpoint" id={id} aria-labelledby={`${id}-title`}>
      <header className="endpoint-head">
        <code className="endpoint-path" id={`${id}-title`}>
          {title}
        </code>
      </header>
      <div className="endpoint-body">
        {description ? <p className="endpoint-desc">{description}</p> : null}
        {children}
      </div>
    </article>
  );
}

const PULL_EXAMPLES = `wavhost pull chatterbox-turbo
wavhost pull chatterbox-multilingual
wavhost pull qwen-0.6-customvoice
wavhost pull qwen-0.6-base --force
wavhost pull chatterbox-turbo --skip-deps`;

const RUN_EXAMPLES = `wavhost run chatterbox-turbo "Welcome to Wavhost" -o welcome.wav
wavhost run chatterbox-turbo "Hello" --voice my-voice -o hello.wav
wavhost run chatterbox-turbo "Hello" --voice /path/to/audio.wav -o hello.wav
wavhost run qwen-0.6-customvoice "Hello" --voice Ryan -o qwen.wav
wavhost run qwen-0.6-base "Hello" --voice /path/to/audio.wav -o clone.wav
wavhost run chatterbox-multilingual "Bonjour" --language fr -o fr.wav`;

export default function CLIPage() {
  const toc = [
    { id: "pull", label: "pull" },
    { id: "run", label: "run" },
    { id: "voice", label: "voice" },
    { id: "serve", label: "serve" },
    { id: "models", label: "models & uninstall" },
  ];

  return (
    <div className="docs-app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <Navigation currentPath="/docs/cli" variant="docs" />

      <DocsLayout
        breadcrumb="CLI"
        currentPath="/docs/cli"
        toc={toc}
        articleClassName="docs-article--catalog"
      >
        <p className="docs-kicker">Reference</p>
        <h1>CLI</h1>
        <p className="docs-lede">
          Commands for models, speech, voices, and the local server. Start with{" "}
          <code>wavhost pull</code>, then <code>run</code> or <code>serve</code>.
        </p>
        <nav className="docs-jump" aria-label="On this page">
          <a href="#pull">pull</a>
          <a href="#run">run</a>
          <a href="#voice">voice</a>
          <a href="#serve">serve</a>
          <a href="#models">models</a>
        </nav>

        <div className="docs-stack">
          <CommandPanel
            id="pull"
            title="wavhost pull"
            description="Download weight layers into local storage and register the model, installing its backend engine if needed."
          >
            <ul className="docs-param-list">
              <Param name="--force">Pull even if already installed (resumes existing blobs)</Param>
              <Param name="--skip-deps">Don&apos;t install the backend engine</Param>
            </ul>
            <p className="docs-example-label">Examples</p>
            <CodeBlock text={PULL_EXAMPLES} label="Copy pull" />
          </CommandPanel>

          <CommandPanel
            id="run"
            title="wavhost run"
            description="Generate speech from text using a local model."
          >
            <ul className="docs-param-list">
              <Param name="-o, --output">
                Output WAV path (default <code>output.wav</code>)
              </Param>
              <Param name="--voice">
                Saved voice, reference audio path, or Qwen CustomVoice speaker (
                <code>Ryan</code>, <code>Aiden</code>, …)
              </Param>
              <Param name="--language, -l">
                Multilingual ISO (<code>en</code>, <code>fr</code>, <code>zh</code>, …) or Qwen
                names (<code>English</code>, …)
              </Param>
              <Param name="--device">
                <code>cuda</code>, <code>cpu</code>, or <code>mps</code>
              </Param>
            </ul>
            <p className="docs-example-label">Examples</p>
            <CodeBlock text={RUN_EXAMPLES} label="Copy run" />
          </CommandPanel>

          <p className="docs-section-label" id="voice">
            Voice
          </p>

          <CommandPanel
            id="voice-create"
            title="wavhost voice create"
            description="Create a saved voice from reference audio."
          >
            <ul className="docs-param-list">
              <Param name="--ref">Required. Path to reference audio</Param>
              <Param name="--desc">Optional description</Param>
            </ul>
            <p className="docs-example-label">Example</p>
            <div className="model-aside-row">
              <span className="model-aside-label">Try</span>
              <CommandChip
                text='wavhost voice create narrator --ref voice.wav --desc "Professional narrator"'
                label="Copy voice create"
              />
            </div>
          </CommandPanel>

          <ul className="endpoint-list" aria-label="Voice management">
            <li className="endpoint-row endpoint-row--plain">
              <div className="endpoint-row-main">
                <code className="endpoint-row-path">voice list</code>
                <p className="endpoint-row-notes">List saved voices</p>
              </div>
              <CommandChip text="wavhost voice list" label="Copy voice list" />
            </li>
            <li className="endpoint-row endpoint-row--plain">
              <div className="endpoint-row-main">
                <code className="endpoint-row-path">voice show</code>
                <p className="endpoint-row-notes">Show voice details</p>
              </div>
              <CommandChip text="wavhost voice show narrator" label="Copy voice show" />
            </li>
            <li className="endpoint-row endpoint-row--plain">
              <div className="endpoint-row-main">
                <code className="endpoint-row-path">voice rm</code>
                <p className="endpoint-row-notes">
                  Remove a voice (<code>-y</code> skips confirm)
                </p>
              </div>
              <CommandChip text="wavhost voice rm narrator -y" label="Copy voice rm" />
            </li>
          </ul>

          <CommandPanel id="serve" title="wavhost serve" description="Start the local API server.">
            <ul className="docs-param-list">
              <Param name="--host" type="default localhost">
                Bind address
              </Param>
              <Param name="--port" type="default 11435">
                Bind port
              </Param>
              <Param name="--reload" type="off">
                Auto-reload for development
              </Param>
            </ul>
            <p className="docs-example-label">Examples</p>
            <CodeBlock
              text={`wavhost serve
wavhost serve --host 0.0.0.0 --port 8000 --reload`}
              label="Copy serve"
            />
          </CommandPanel>

          <p className="docs-section-label" id="models">
            Models &amp; uninstall
          </p>

          <ul className="endpoint-list" aria-label="Model management">
            <li className="endpoint-row endpoint-row--plain">
              <div className="endpoint-row-main">
                <code className="endpoint-row-path">list</code>
                <p className="endpoint-row-notes">Installed models + registry</p>
              </div>
              <CommandChip text="wavhost list" label="Copy list" />
            </li>
            <li className="endpoint-row endpoint-row--plain">
              <div className="endpoint-row-main">
                <code className="endpoint-row-path">rm</code>
                <p className="endpoint-row-notes">Remove a pulled model</p>
              </div>
              <CommandChip text="wavhost rm chatterbox-turbo -y" label="Copy rm" />
            </li>
            <li className="endpoint-row endpoint-row--plain">
              <div className="endpoint-row-main">
                <code className="endpoint-row-path">uninstall</code>
                <p className="endpoint-row-notes">
                  Purge <code>~/.wavhost</code> (<code>--keep-data</code> / <code>-y</code>)
                </p>
              </div>
              <CommandChip text="wavhost uninstall -y" label="Copy uninstall" />
            </li>
          </ul>

          <div className="model-note">
            <p>
              Remove the package with <code>pip uninstall wavhost</code>. Optional engines:{" "}
              <code>pip uninstall chatterbox-tts qwen-tts</code>.
            </p>
          </div>
        </div>

        <nav className="docs-pager" aria-label="Pagination">
          <Link className="docs-pager-prev" href="/docs">
            <span className="docs-pager-label">Previous</span>
            <span className="docs-pager-title">Getting started</span>
          </Link>
          <Link className="docs-pager-next" href="/docs/api">
            <span className="docs-pager-label">Next</span>
            <span className="docs-pager-title">API reference</span>
          </Link>
        </nav>
      </DocsLayout>
    </div>
  );
}
