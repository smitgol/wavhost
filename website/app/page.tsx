import Link from "next/link";
import { Navigation } from "@/components/Navigation";
import { Footer } from "@/components/Footer";
import { CopyButton } from "@/components/CopyButton";

export default function Home() {
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <Navigation currentPath="/" />

      <main id="main">
        <section className="hero">
          <div className="wrap hero-inner">
            <h1>One API for every local model.</h1>
            <p className="lede">OpenAI-compatible speech. Named voices, saved locally.</p>
            <p className="cta-row">
              <a
                className="btn-pill"
                href="https://github.com/smitgol/wavhost"
                rel="noopener noreferrer"
              >
                GitHub
              </a>
            </p>
            <p className="cta-note">
              <a href="#quick-start">Quick start</a> · Apache-2.0
            </p>
          </div>
        </section>

        <section id="quick-start" className="install">
          <div className="wrap install-inner">
            <div className="install-chip-wrap">
              <div className="install-chip">
                <code data-copy>pip install wavhost</code>
                <CopyButton
                  text="pip install wavhost"
                  className="copy-btn copy-btn--chip"
                  label="Copy install command"
                />
              </div>
            </div>

            <div className="first-run" aria-label="First run">
              <div className="cmd-row">
                <span className="cmd-label">Pull</span>
                <code className="cmd-text" data-copy>
                  wavhost pull chatterbox-turbo
                </code>
                <CopyButton
                  text="wavhost pull chatterbox-turbo"
                  label="Copy pull command"
                />
              </div>
              <div className="cmd-row">
                <span className="cmd-label">Run</span>
                <code className="cmd-text" data-copy>
                  wavhost run chatterbox-turbo &quot;Hello from your machine.&quot; -o hello.wav
                </code>
                <CopyButton
                  text='wavhost run chatterbox-turbo "Hello from your machine." -o hello.wav'
                  label="Copy run command"
                />
              </div>
              <div className="cmd-row">
                <span className="cmd-label">Serve</span>
                <span className="cmd-body">
                  <code className="cmd-text" data-copy>
                    wavhost serve
                  </code>
                  <span className="cmd-note dim">:11435</span>
                </span>
                <CopyButton text="wavhost serve" label="Copy serve command" />
              </div>
            </div>

            <p className="hint">
              Models (Chatterbox + Qwen3-TTS), voices, and cache live under{" "}
              <code>~/.wavhost</code>. See <Link href="/models">Models</Link>. GPU recommended.
            </p>
          </div>
        </section>

        <section className="section" id="voices">
          <div className="wrap narrow">
            <h2>Named voices, saved locally</h2>
            <p>
              Create from short reference audio on the CLI or API, then reuse by name in{" "}
              <code>run</code> or <code>POST /v1/audio/speech</code>.
            </p>
            <div className="first-run" aria-label="Voice commands">
              <div className="cmd-row">
                <span className="cmd-label">Create</span>
                <code className="cmd-text" data-copy>
                  wavhost voice create my-voice --ref ./sample.wav
                </code>
                <CopyButton
                  text="wavhost voice create my-voice --ref ./sample.wav"
                  label="Copy voice create command"
                />
              </div>
              <div className="cmd-row">
                <span className="cmd-label">List</span>
                <code className="cmd-text" data-copy>
                  wavhost voice list
                </code>
                <CopyButton text="wavhost voice list" label="Copy voice list command" />
              </div>
              <div className="cmd-row">
                <span className="cmd-label">Run</span>
                <code className="cmd-text" data-copy>
                  wavhost run chatterbox-turbo &quot;Hello from Wavhost&quot; --voice my-voice -o
                  hello.wav
                </code>
                <CopyButton
                  text='wavhost run chatterbox-turbo "Hello from Wavhost" --voice my-voice -o hello.wav'
                  label="Copy run with voice command"
                />
              </div>
            </div>
            <p className="hint hint-left">
              Storage: <code>~/.wavhost/voices/</code>. Full CLI + API reference in{" "}
              <Link href="/docs">Docs</Link>.
            </p>
          </div>
        </section>

        <section className="section" id="api">
          <div className="wrap narrow">
            <h2>OpenAI-compatible API</h2>
            <p>
              Point a client at <code>http://localhost:11435/v1</code>. Pass a saved voice name, or{" "}
              <code>&quot;default&quot;</code>.
            </p>
            <div className="code-wrap">
              <CopyButton
                text={`curl http://localhost:11435/v1/audio/speech \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "chatterbox-turbo",
    "input": "Hello from Wavhost!",
    "voice": "my-voice"
  }' \\
  --output speech.mp3`}
                className="copy-btn copy-btn--block"
                label="Copy speech request"
              />
              <pre className="code">
                <code data-copy>
                  {`curl http://localhost:11435/v1/audio/speech \\
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
            <p className="hint hint-left">
              Voice CRUD: <code>POST/GET/DELETE /v1/voices</code> — see{" "}
              <Link href="/docs/api#voices">Docs</Link>.
            </p>
          </div>
        </section>

        <section className="section" id="local">
          <div className="wrap narrow">
            <h2>Local &amp; private</h2>
            <ul className="plain">
              <li>Runs on your machine — no API keys, no cloud account</li>
              <li>Text, audio, and saved voices stay put</li>
              <li>
                Model licenses printed on <code>pull</code> (Hugging Face)
              </li>
            </ul>
          </div>
        </section>

        <section className="section" id="scope">
          <div className="wrap narrow">
            <h2>What it isn&apos;t (v0)</h2>
            <ul className="plain">
              <li>Not cloud SaaS, marketplace, or voice sharing</li>
              <li>Not speech-to-text, fine-tuning, or streaming synthesis</li>
              <li>Not a web voice studio — CLI + local API only</li>
            </ul>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
