import Link from "next/link";
import type { ReactNode } from "react";
import { Navigation } from "@/components/Navigation";
import { DocsLayout } from "@/components/DocsLayout";
import { CopyButton } from "@/components/CopyButton";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "API · Docs · Wavhost",
  description:
    "Wavhost API reference — speech, voices, models, health. OpenAI-compatible local server.",
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
  type: string;
  children: ReactNode;
}) {
  return (
    <li className="docs-param">
      <div className="docs-param-name">
        <code>{name}</code>
        <span className="docs-param-type">{type}</span>
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

const SPEECH_CURL = `curl http://localhost:11435/v1/audio/speech \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "chatterbox-turbo",
    "input": "Hello from Wavhost!",
    "voice": "my-voice",
    "response_format": "mp3"
  }' \\
  --output speech.mp3`;

const STREAM_CURL = `curl http://127.0.0.1:11435/v1/audio/speech \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "chatterbox-nano",
    "input": "Hello",
    "voice": "default",
    "stream": true,
    "response_format": "pcm"
  }' \\
  --output out.pcm`;

const CREATE_VOICE_CURL = `curl -X POST http://localhost:11435/v1/voices \\
  -F "name=narrator" \\
  -F "file=@reference.wav" \\
  -F "description=Professional narrator voice"`;

const PYTHON_CLIENT = `from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11435/v1",
    api_key="not-needed",
)

speech = client.audio.speech.create(
    model="chatterbox-turbo",
    voice="my-voice",
    input="Hello from Wavhost!",
)
speech.write_to_file("hello.mp3")`;

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

      <DocsLayout
        breadcrumb="API"
        currentPath="/docs/api"
        toc={toc}
        articleClassName="docs-article--catalog"
      >
        <p className="docs-kicker">Reference</p>
        <h1>API</h1>
        <p className="docs-lede">
          Local OpenAI-compatible server at <code>http://localhost:11435</code>. No API key
          required. Binary audio responses; progressive download when{" "}
          <code>stream: true</code>.
        </p>
        <nav className="docs-jump" aria-label="On this page">
          <a href="#speech">Speech</a>
          <a href="#voices">Voices</a>
          <a href="#models-health">Models &amp; health</a>
          <a href="#python">Python</a>
        </nav>

        <div className="docs-stack">
          <p className="docs-section-label" id="speech">
            Speech
          </p>

          <article className="endpoint" id="post-speech" aria-labelledby="post-speech-title">
            <header className="endpoint-head">
              <span className="method method-post">POST</span>
              <code className="endpoint-path" id="post-speech-title">
                /v1/audio/speech
              </code>
            </header>
            <div className="endpoint-body">
              <p className="endpoint-desc">
                Generate speech from text. Response is binary audio (
                <code>audio/mpeg</code>, <code>audio/pcm</code>, …).
              </p>

              <p className="docs-example-label">Body</p>
              <ul className="docs-param-list">
                <Param name="model" type="string">
                  Required. e.g. <code>chatterbox-turbo</code>
                </Param>
                <Param name="input" type="string">
                  Required. Text to synthesize (max 4096)
                </Param>
                <Param name="voice" type="string">
                  Optional. Saved voice, Qwen speaker (<code>Ryan</code>, …), path, or{" "}
                  <code>default</code>
                </Param>
                <Param name="language" type="string">
                  Optional. Chatterbox Multilingual ISO (<code>fr</code>, <code>zh</code>, …) or
                  Qwen language name
                </Param>
                <Param name="response_format" type="string">
                  Optional. Default <code>mp3</code>. Also <code>wav</code>, <code>opus</code>,{" "}
                  <code>flac</code>, <code>aac</code>, <code>pcm</code>, <code>pcm_16000</code>,{" "}
                  <code>pcm_22050</code>, <code>pcm_24000</code>, <code>pcm_44100</code>
                </Param>
                <Param name="speed" type="float">
                  Optional 0.25–4.0 (not implemented yet)
                </Param>
                <Param name="stream" type="bool">
                  Optional. Default <code>false</code>. Progressive download; only{" "}
                  <code>mp3</code> and <code>pcm</code> / <code>pcm_*</code>
                </Param>
              </ul>

              <div className="model-note">
                <p>
                  <strong>Streaming</strong> — <code>stream: true</code> returns chunked bytes.
                  Allowed: <code>mp3</code>, <code>pcm</code>, <code>pcm_*</code>. Rejected with{" "}
                  <code>400</code>: <code>wav</code>, <code>opus</code>, <code>aac</code>,{" "}
                  <code>flac</code>. For <code>pcm</code>, Content-Type is <code>audio/pcm</code>{" "}
                  at the model&apos;s native sample rate.
                </p>
                <p>
                  Errors: <code>400</code> bad params / unsupported stream format ·{" "}
                  <code>404</code> model not found · <code>500</code> generation failed.
                </p>
              </div>

              <p className="docs-example-label">Example</p>
              <CodeBlock text={SPEECH_CURL} label="Copy speech curl" />

              <p className="docs-example-label">Streaming</p>
              <CodeBlock text={STREAM_CURL} label="Copy streaming curl" />
            </div>
          </article>

          <p className="docs-section-label" id="voices">
            Voices
          </p>

          <article className="endpoint" id="post-voices" aria-labelledby="post-voices-title">
            <header className="endpoint-head">
              <span className="method method-post">POST</span>
              <code className="endpoint-path" id="post-voices-title">
                /v1/voices
              </code>
            </header>
            <div className="endpoint-body">
              <p className="endpoint-desc">
                Create a voice from reference audio (<code>multipart/form-data</code>).
              </p>
              <ul className="docs-param-list">
                <Param name="name" type="string">
                  Required. Voice name
                </Param>
                <Param name="file" type="file">
                  Required. Reference audio file
                </Param>
                <Param name="description" type="string">
                  Optional. Short description
                </Param>
              </ul>
              <p className="docs-example-label">Example</p>
              <CodeBlock text={CREATE_VOICE_CURL} label="Copy create voice" />
            </div>
          </article>

          <ul className="endpoint-list" aria-label="Voice endpoints">
            <li className="endpoint-row" id="get-voices">
              <span className="method method-get">GET</span>
              <div className="endpoint-row-main">
                <code className="endpoint-row-path">/v1/voices</code>
                <p className="endpoint-row-notes">List saved voices</p>
              </div>
              <CommandChip
                text="curl http://localhost:11435/v1/voices"
                label="Copy list voices"
              />
            </li>
            <li className="endpoint-row" id="get-voice">
              <span className="method method-get">GET</span>
              <div className="endpoint-row-main">
                <code className="endpoint-row-path">/v1/voices/{"{name}"}</code>
                <p className="endpoint-row-notes">Get one voice&apos;s details</p>
              </div>
              <CommandChip
                text="curl http://localhost:11435/v1/voices/narrator"
                label="Copy get voice"
              />
            </li>
            <li className="endpoint-row" id="delete-voice">
              <span className="method method-delete">DELETE</span>
              <div className="endpoint-row-main">
                <code className="endpoint-row-path">/v1/voices/{"{name}"}</code>
                <p className="endpoint-row-notes">Delete a saved voice</p>
              </div>
              <CommandChip
                text="curl -X DELETE http://localhost:11435/v1/voices/narrator"
                label="Copy delete voice"
              />
            </li>
          </ul>

          <p className="docs-section-label" id="models-health">
            Models &amp; health
          </p>

          <ul className="endpoint-list" aria-label="Models and health">
            <li className="endpoint-row" id="get-models">
              <span className="method method-get">GET</span>
              <div className="endpoint-row-main">
                <code className="endpoint-row-path">/v1/models</code>
                <p className="endpoint-row-notes">List models (OpenAI-shaped)</p>
              </div>
              <CommandChip
                text="curl http://localhost:11435/v1/models"
                label="Copy models"
              />
            </li>
            <li className="endpoint-row" id="get-health">
              <span className="method method-get">GET</span>
              <div className="endpoint-row-main">
                <code className="endpoint-row-path">/health</code>
                <p className="endpoint-row-notes">
                  Health check → <code>{`{"status":"ok"}`}</code>
                </p>
              </div>
              <CommandChip text="curl http://localhost:11435/health" label="Copy health" />
            </li>
          </ul>

          <p className="docs-section-label" id="python">
            Python client
          </p>
          <CodeBlock text={PYTHON_CLIENT} label="Copy Python" />
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
