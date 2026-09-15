import Link from "next/link";
import { Navigation } from "@/components/Navigation";
import { DocsLayout } from "@/components/DocsLayout";
import { CopyButton } from "@/components/CopyButton";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Getting started · Docs · Wavhost",
  description: "Wavhost getting started — install, pull, first speech, voices, serve.",
};

export default function DocsPage() {
  const toc = [
    { id: "install", label: "Install" },
    { id: "pull", label: "Pull a model" },
    { id: "run", label: "Generate speech" },
    { id: "voice", label: "Save a voice" },
    { id: "serve", label: "Start the API" },
  ];

  return (
    <div className="docs-app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <Navigation currentPath="/docs" variant="docs" />

      <DocsLayout breadcrumb="Getting started" currentPath="/docs" toc={toc}>
        <h1>Getting started</h1>
        <p className="docs-intro">
          From install to first WAV and a named local voice. About five minutes if you already have
          a GPU-friendly Python env.
        </p>

        <h2 id="install">1. Install</h2>
        <div className="code-wrap">
          <CopyButton
            text="pip install wavhost"
            className="copy-btn copy-btn--block"
            label="Copy install"
          />
          <pre className="code">
            <code data-copy>pip install wavhost</code>
          </pre>
        </div>
        <p>
          This installs the runtime and PyTorch. TTS engines are pulled with the model — not
          bundled in the base package.
        </p>
        <aside className="docs-callout">
          <strong>GPU tip.</strong> After <code>pull</code>, if PyTorch is CPU-only on an NVIDIA
          machine, Wavhost prints the exact <code>pip install torch==…+cu124</code> line to run.
          Use the printed pin; don&apos;t invent a CUDA tag.
        </aside>

        <h2 id="pull">2. Pull a model</h2>
        <div className="code-wrap">
          <CopyButton
            text="wavhost pull chatterbox-turbo"
            className="copy-btn copy-btn--block"
            label="Copy pull"
          />
          <pre className="code">
            <code data-copy>wavhost pull chatterbox-turbo</code>
          </pre>
        </div>
        <p>
          Shows the license, installs the Chatterbox engine if needed, and downloads weights into{" "}
          <code>~/.wavhost</code>.
        </p>

        <h2 id="run">3. Generate speech</h2>
        <div className="code-wrap">
          <CopyButton
            text='wavhost run chatterbox-turbo "Hello world, this is Wavhost!" -o output.wav'
            className="copy-btn copy-btn--block"
            label="Copy run"
          />
          <pre className="code">
            <code data-copy>
              wavhost run chatterbox-turbo &quot;Hello world, this is Wavhost!&quot; -o output.wav
            </code>
          </pre>
        </div>

        <h2 id="voice">4. Save a voice (optional)</h2>
        <div className="code-wrap">
          <CopyButton
            text={`wavhost voice create my-voice --ref reference.wav --desc "My custom voice"
wavhost run chatterbox-turbo "Hello from my voice!" --voice my-voice -o output.wav`}
            className="copy-btn copy-btn--block"
            label="Copy voice create and run"
          />
          <pre className="code">
            <code data-copy>
              {`wavhost voice create my-voice --ref reference.wav --desc "My custom voice"
wavhost run chatterbox-turbo "Hello from my voice!" --voice my-voice -o output.wav`}
            </code>
          </pre>
        </div>
        <p>
          Voices live under <code>~/.wavhost/voices/</code>. You can also create them over HTTP
          once the server is up — see <Link href="/docs/api#post-voices">API · Voices</Link>.
        </p>

        <h2 id="serve">5. Start the API</h2>
        <div className="code-wrap">
          <CopyButton
            text={`wavhost serve

curl http://localhost:11435/v1/audio/speech \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "chatterbox-turbo",
    "input": "Hello from Wavhost!",
    "voice": "my-voice"
  }' \\
  --output speech.mp3`}
            className="copy-btn copy-btn--block"
            label="Copy serve and speech"
          />
          <pre className="code">
            <code data-copy>
              {`wavhost serve

curl http://localhost:11435/v1/audio/speech \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "chatterbox-turbo",
    "input": "Hello from Wavhost!",
    "voice": "my-voice"
  }' \\
  --output speech.mp3`}
            </code>
          </pre>
        </div>
        <p>
          Default listen address is <code>http://localhost:11435</code>. Use{" "}
          <code>&quot;voice&quot;: &quot;default&quot;</code> for the built-in stock voice.
        </p>

        <nav className="docs-pager" aria-label="Next page">
          <Link className="docs-pager-next" href="/docs/cli">
            <span className="docs-pager-label">Next</span>
            <span className="docs-pager-title">CLI reference</span>
          </Link>
        </nav>
      </DocsLayout>
    </div>
  );
}
