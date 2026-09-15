import Link from "next/link";
import { Navigation } from "@/components/Navigation";
import { DocsLayout } from "@/components/DocsLayout";
import { CopyButton } from "@/components/CopyButton";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "API · Docs · Wavhost",
  description:
    "Wavhost API reference — speech, voices, models, health. OpenAI-compatible local server.",
};

export default function APIPage() {
  const toc = [
    { id: "speech", label: "Speech" },
    { id: "voices", label: "Voices" },
    { id: "models-health", label: "Models & health" },
    { id: "python", label: "Python client" },
  ];

  return (
    <div className="docs-app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <Navigation currentPath="/docs/api" variant="docs" />

      <DocsLayout breadcrumb="API" currentPath="/docs/api" toc={toc}>
        <h1>API reference</h1>
        <p className="docs-intro">
          Local OpenAI-compatible server. Base URL <code>http://localhost:11435</code>. No API key
          required.
        </p>

        <h2 id="speech">Speech</h2>

        <article className="endpoint" id="post-speech">
          <header className="endpoint-head">
            <span className="method method-post">POST</span>
            <code className="endpoint-path">/v1/audio/speech</code>
          </header>
          <p>Generate speech from text (OpenAI-compatible). Response is binary audio.</p>
          <div className="code-wrap">
            <CopyButton
              text={`curl http://localhost:11435/v1/audio/speech \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "chatterbox-turbo",
    "input": "Hello from Wavhost!",
    "voice": "my-voice",
    "response_format": "mp3"
  }' \\
  --output speech.mp3`}
              className="copy-btn copy-btn--block"
              label="Copy speech curl"
            />
            <pre className="code">
              <code data-copy>
                {`curl http://localhost:11435/v1/audio/speech \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "chatterbox-turbo",
    "input": "Hello from Wavhost!",
    "voice": "my-voice",
    "response_format": "mp3"
  }' \\
  --output speech.mp3`}
              </code>
            </pre>
          </div>
          <table className="docs-table">
            <thead>
              <tr>
                <th>Body</th>
                <th>Type</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <code>model</code>
                </td>
                <td>string</td>
                <td>
                  Required. e.g. <code>chatterbox-turbo</code>
                </td>
              </tr>
              <tr>
                <td>
                  <code>input</code>
                </td>
                <td>string</td>
                <td>Required. Text to synthesize (max 4096)</td>
              </tr>
              <tr>
                <td>
                  <code>voice</code>
                </td>
                <td>string</td>
                <td>
                  Optional. Saved voice name, or <code>default</code>
                </td>
              </tr>
              <tr>
                <td>
                  <code>response_format</code>
                </td>
                <td>string</td>
                <td>
                  Optional. Default <code>mp3</code>. Also <code>wav</code>, <code>opus</code>,{" "}
                  <code>flac</code>, <code>aac</code>, <code>pcm</code>, <code>pcm_16000</code>,{" "}
                  <code>pcm_22050</code>, <code>pcm_24000</code>, <code>pcm_44100</code>
                </td>
              </tr>
              <tr>
                <td>
                  <code>speed</code>
                </td>
                <td>float</td>
                <td>Optional 0.25–4.0 (not implemented yet)</td>
              </tr>
            </tbody>
          </table>
          <p className="docs-note">
            Errors: <code>400</code> unknown voice / bad params · <code>404</code> model not found
            · <code>500</code> generation failed.
          </p>
        </article>

        <h2 id="voices">Voices</h2>

        <article className="endpoint" id="post-voices">
          <header className="endpoint-head">
            <span className="method method-post">POST</span>
            <code className="endpoint-path">/v1/voices</code>
          </header>
          <p>
            Create a voice from reference audio (<code>multipart/form-data</code>).
          </p>
          <div className="code-wrap">
            <CopyButton
              text={`curl -X POST http://localhost:11435/v1/voices \\
  -F "name=narrator" \\
  -F "file=@reference.wav" \\
  -F "description=Professional narrator voice"`}
              className="copy-btn copy-btn--block"
              label="Copy create voice"
            />
            <pre className="code">
              <code data-copy>
                {`curl -X POST http://localhost:11435/v1/voices \\
  -F "name=narrator" \\
  -F "file=@reference.wav" \\
  -F "description=Professional narrator voice"`}
              </code>
            </pre>
          </div>
          <table className="docs-table">
            <thead>
              <tr>
                <th>Field</th>
                <th>Required</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <code>name</code>
                </td>
                <td>yes</td>
                <td>Voice name</td>
              </tr>
              <tr>
                <td>
                  <code>file</code>
                </td>
                <td>yes</td>
                <td>Reference audio file</td>
              </tr>
              <tr>
                <td>
                  <code>description</code>
                </td>
                <td>no</td>
                <td>Short description</td>
              </tr>
            </tbody>
          </table>
        </article>

        <article className="endpoint" id="get-voices">
          <header className="endpoint-head">
            <span className="method method-get">GET</span>
            <code className="endpoint-path">/v1/voices</code>
          </header>
          <p>List saved voices.</p>
          <div className="code-wrap">
            <CopyButton
              text="curl http://localhost:11435/v1/voices"
              className="copy-btn copy-btn--block"
              label="Copy list voices"
            />
            <pre className="code">
              <code data-copy>curl http://localhost:11435/v1/voices</code>
            </pre>
          </div>
        </article>

        <article className="endpoint" id="get-voice">
          <header className="endpoint-head">
            <span className="method method-get">GET</span>
            <code className="endpoint-path">/v1/voices/{"{name}"}</code>
          </header>
          <p>Get one voice&apos;s details.</p>
          <div className="code-wrap">
            <CopyButton
              text="curl http://localhost:11435/v1/voices/narrator"
              className="copy-btn copy-btn--block"
              label="Copy get voice"
            />
            <pre className="code">
              <code data-copy>curl http://localhost:11435/v1/voices/narrator</code>
            </pre>
          </div>
        </article>

        <article className="endpoint" id="delete-voice">
          <header className="endpoint-head">
            <span className="method method-delete">DELETE</span>
            <code className="endpoint-path">/v1/voices/{"{name}"}</code>
          </header>
          <p>Delete a saved voice.</p>
          <div className="code-wrap">
            <CopyButton
              text="curl -X DELETE http://localhost:11435/v1/voices/narrator"
              className="copy-btn copy-btn--block"
              label="Copy delete voice"
            />
            <pre className="code">
              <code data-copy>curl -X DELETE http://localhost:11435/v1/voices/narrator</code>
            </pre>
          </div>
        </article>

        <h2 id="models-health">Models &amp; health</h2>

        <article className="endpoint" id="get-models">
          <header className="endpoint-head">
            <span className="method method-get">GET</span>
            <code className="endpoint-path">/v1/models</code>
          </header>
          <p>List models (OpenAI-shaped).</p>
          <div className="code-wrap">
            <CopyButton
              text="curl http://localhost:11435/v1/models"
              className="copy-btn copy-btn--block"
              label="Copy models"
            />
            <pre className="code">
              <code data-copy>curl http://localhost:11435/v1/models</code>
            </pre>
          </div>
        </article>

        <article className="endpoint" id="get-health">
          <header className="endpoint-head">
            <span className="method method-get">GET</span>
            <code className="endpoint-path">/health</code>
          </header>
          <p>
            Health check. Returns <code>{`{"status":"ok"}`}</code>.
          </p>
          <div className="code-wrap">
            <CopyButton
              text="curl http://localhost:11435/health"
              className="copy-btn copy-btn--block"
              label="Copy health"
            />
            <pre className="code">
              <code data-copy>curl http://localhost:11435/health</code>
            </pre>
          </div>
        </article>

        <h2 id="python">Python client</h2>
        <div className="code-wrap">
          <CopyButton
            text={`from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11435/v1",
    api_key="not-needed",
)

speech = client.audio.speech.create(
    model="chatterbox-turbo",
    voice="my-voice",
    input="Hello from Wavhost!",
)
speech.write_to_file("hello.mp3")`}
            className="copy-btn copy-btn--block"
            label="Copy Python"
          />
          <pre className="code">
            <code data-copy>
              {`from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11435/v1",
    api_key="not-needed",
)

speech = client.audio.speech.create(
    model="chatterbox-turbo",
    voice="my-voice",
    input="Hello from Wavhost!",
)
speech.write_to_file("hello.mp3")`}
            </code>
          </pre>
        </div>

        <nav className="docs-pager" aria-label="Pagination">
          <Link className="docs-pager-prev" href="/docs/cli">
            <span className="docs-pager-label">Previous</span>
            <span className="docs-pager-title">CLI reference</span>
          </Link>
        </nav>
      </DocsLayout>
    </div>
  );
}
