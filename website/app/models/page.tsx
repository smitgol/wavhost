import { Navigation } from "@/components/Navigation";
import { Footer } from "@/components/Footer";
import { CopyButton } from "@/components/CopyButton";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Models · Wavhost",
  description: "Wavhost models — Chatterbox TTS (Resemble AI). Pull from Hugging Face. MIT.",
};

export default function ModelsPage() {
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <Navigation currentPath="/models" />

      <main id="main">
        <section className="section models-hero">
          <div className="wrap narrow">
            <h1 className="page-title">Models</h1>
            <p>
              Wavhost v0 ships Resemble AI Chatterbox TTS (MIT). Models download from Hugging
              Face; the license is shown when you pull.
            </p>

            <div className="install-chip-wrap models-pull">
              <div className="install-chip">
                <code data-copy>wavhost pull chatterbox-turbo</code>
                <CopyButton
                  text="wavhost pull chatterbox-turbo"
                  className="copy-btn copy-btn--chip"
                  label="Copy pull command"
                />
              </div>
            </div>
          </div>
        </section>

        <section className="section">
          <div className="wrap narrow">
            <h2>Currently supported</h2>
            <div className="model-table" role="table" aria-label="Supported models">
              <div className="model-row model-row--head" role="row">
                <span role="columnheader">Model</span>
                <span role="columnheader">Size</span>
                <span role="columnheader">Device</span>
                <span role="columnheader">Notes</span>
              </div>
              <div className="model-row" role="row">
                <span role="cell">
                  <code>chatterbox-turbo</code>
                </span>
                <span role="cell">350M</span>
                <span role="cell">GPU</span>
                <span role="cell">Fast, high-quality English — recommended</span>
              </div>
              <div className="model-row" role="row">
                <span role="cell">
                  <code>chatterbox-nano</code>
                </span>
                <span role="cell">110M</span>
                <span role="cell">CPU/GPU</span>
                <span role="cell">Efficient, good on CPU</span>
              </div>
              <div className="model-row" role="row">
                <span role="cell">
                  <code>chatterbox-base</code>
                </span>
                <span role="cell">500M</span>
                <span role="cell">GPU</span>
                <span role="cell">Original high-quality</span>
              </div>
            </div>
          </div>
        </section>

        <section className="section">
          <div className="wrap narrow">
            <h2>Coming later</h2>
            <ul className="plain">
              <li>Qwen3-TTS — coming</li>
              <li>Additional TTS families — coming</li>
            </ul>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
