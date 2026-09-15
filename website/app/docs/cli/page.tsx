import Link from "next/link";
import { Navigation } from "@/components/Navigation";
import { DocsLayout } from "@/components/DocsLayout";
import { CopyButton } from "@/components/CopyButton";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "CLI · Docs · Wavhost",
  description: "Wavhost CLI reference — pull, run, voice, serve, list, rm, uninstall.",
};

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

      <DocsLayout breadcrumb="CLI" currentPath="/docs/cli" toc={toc}>
        <h1>CLI reference</h1>
        <p className="docs-intro">Commands for models, speech, voices, and the local server.</p>

        <h2 id="pull">
          <code>wavhost pull</code>
        </h2>
        <p>
          Download weight layers into local storage and register the model, installing its backend
          engine if needed.
        </p>
        <div className="code-wrap">
          <CopyButton
            text={`wavhost pull chatterbox-turbo
wavhost pull chatterbox-multilingual
wavhost pull qwen-0.6-customvoice
wavhost pull qwen-0.6-base --force
wavhost pull chatterbox-turbo --skip-deps`}
            className="copy-btn copy-btn--block"
            label="Copy pull"
          />
          <pre className="code">
            <code data-copy>
              {`wavhost pull chatterbox-turbo
wavhost pull chatterbox-multilingual
wavhost pull qwen-0.6-customvoice
wavhost pull qwen-0.6-base --force
wavhost pull chatterbox-turbo --skip-deps`}
            </code>
          </pre>
        </div>
        <table className="docs-table">
          <thead>
            <tr>
              <th>Flag</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <code>--force</code>
              </td>
              <td>Pull even if already installed (resumes existing blobs)</td>
            </tr>
            <tr>
              <td>
                <code>--skip-deps</code>
              </td>
              <td>Don&apos;t install the backend engine</td>
            </tr>
          </tbody>
        </table>

        <h2 id="run">
          <code>wavhost run</code>
        </h2>
        <p>Generate speech from text using a local model.</p>
        <div className="code-wrap">
          <CopyButton
            text={`wavhost run chatterbox-turbo "Welcome to Wavhost" -o welcome.wav
wavhost run chatterbox-turbo "Hello" --voice my-voice -o hello.wav
wavhost run chatterbox-turbo "Hello" --voice /path/to/audio.wav -o hello.wav
wavhost run qwen-0.6-customvoice "Hello" --voice Ryan -o qwen.wav
wavhost run qwen-0.6-base "Hello" --voice /path/to/audio.wav -o clone.wav
wavhost run chatterbox-multilingual "Bonjour" --language fr -o fr.wav`}
            className="copy-btn copy-btn--block"
            label="Copy run"
          />
          <pre className="code">
            <code data-copy>
              {`wavhost run chatterbox-turbo "Welcome to Wavhost" -o welcome.wav
wavhost run chatterbox-turbo "Hello" --voice my-voice -o hello.wav
wavhost run chatterbox-turbo "Hello" --voice /path/to/audio.wav -o hello.wav
wavhost run qwen-0.6-customvoice "Hello" --voice Ryan -o qwen.wav
wavhost run qwen-0.6-base "Hello" --voice /path/to/audio.wav -o clone.wav
wavhost run chatterbox-multilingual "Bonjour" --language fr -o fr.wav`}
            </code>
          </pre>
        </div>
        <table className="docs-table">
          <thead>
            <tr>
              <th>Flag</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <code>-o, --output</code>
              </td>
              <td>
                Output WAV path (default <code>output.wav</code>)
              </td>
            </tr>
            <tr>
              <td>
                <code>--voice</code>
              </td>
              <td>
                Saved voice, reference audio path, or Qwen CustomVoice speaker (
                <code>Ryan</code>, <code>Aiden</code>, …)
              </td>
            </tr>
            <tr>
              <td>
                <code>--language, -l</code>
              </td>
              <td>
                Language for Multilingual (ISO: <code>en</code>, <code>fr</code>,{" "}
                <code>zh</code>, …) or Qwen names (<code>English</code>, …)
              </td>
            </tr>
            <tr>
              <td>
                <code>--device</code>
              </td>
              <td>
                <code>cuda</code>, <code>cpu</code>, or <code>mps</code>
              </td>
            </tr>
          </tbody>
        </table>

        <h2 id="voice">Voice commands</h2>
        <h3 id="voice-create">
          <code>wavhost voice create</code>
        </h3>
        <div className="code-wrap">
          <CopyButton
            text='wavhost voice create narrator --ref voice.wav --desc "Professional narrator"'
            className="copy-btn copy-btn--block"
            label="Copy voice create"
          />
          <pre className="code">
            <code data-copy>
              wavhost voice create narrator --ref voice.wav --desc &quot;Professional
              narrator&quot;
            </code>
          </pre>
        </div>
        <table className="docs-table">
          <thead>
            <tr>
              <th>Flag</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <code>--ref</code>
              </td>
              <td>Required. Path to reference audio</td>
            </tr>
            <tr>
              <td>
                <code>--desc</code>
              </td>
              <td>Optional description</td>
            </tr>
          </tbody>
        </table>

        <h3 id="voice-list">
          <code>list</code> · <code>show</code> · <code>rm</code>
        </h3>
        <div className="code-wrap">
          <CopyButton
            text={`wavhost voice list
wavhost voice show narrator
wavhost voice rm narrator
wavhost voice rm narrator -y`}
            className="copy-btn copy-btn--block"
            label="Copy voice manage"
          />
          <pre className="code">
            <code data-copy>
              {`wavhost voice list
wavhost voice show narrator
wavhost voice rm narrator
wavhost voice rm narrator -y`}
            </code>
          </pre>
        </div>

        <h2 id="serve">
          <code>wavhost serve</code>
        </h2>
        <div className="code-wrap">
          <CopyButton
            text={`wavhost serve
wavhost serve --host 0.0.0.0 --port 8000 --reload`}
            className="copy-btn copy-btn--block"
            label="Copy serve"
          />
          <pre className="code">
            <code data-copy>
              {`wavhost serve
wavhost serve --host 0.0.0.0 --port 8000 --reload`}
            </code>
          </pre>
        </div>
        <table className="docs-table">
          <thead>
            <tr>
              <th>Flag</th>
              <th>Default</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <code>--host</code>
              </td>
              <td>
                <code>localhost</code>
              </td>
            </tr>
            <tr>
              <td>
                <code>--port</code>
              </td>
              <td>
                <code>11435</code>
              </td>
            </tr>
            <tr>
              <td>
                <code>--reload</code>
              </td>
              <td>off</td>
            </tr>
          </tbody>
        </table>

        <h2 id="models">Models &amp; uninstall</h2>
        <div className="code-wrap">
          <CopyButton
            text={`wavhost list
wavhost rm chatterbox-turbo -y
wavhost uninstall
pip uninstall wavhost
# optional engines:
# pip uninstall chatterbox-tts qwen-tts`}
            className="copy-btn copy-btn--block"
            label="Copy model commands"
          />
          <pre className="code">
            <code data-copy>
              {`wavhost list
wavhost rm chatterbox-turbo -y
wavhost uninstall
pip uninstall wavhost
# optional engines:
# pip uninstall chatterbox-tts qwen-tts`}
            </code>
          </pre>
        </div>
        <p>
          <code>uninstall</code> supports <code>--purge-data</code> /{" "}
          <code>--keep-data</code> (default purge) and <code>-y</code>.
        </p>

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
