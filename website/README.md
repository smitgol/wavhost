# Wavhost Website

Next.js App Router site for [Wavhost](https://github.com/smitgol/wavhost) — local-first TTS runtime.

Ported from static HTML to Next.js while preserving the grayscale design and README-homepage restraint.

## Local Development

```bash
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)

## Production Build

```bash
npm run build
npm start
```

## Vercel Deployment

This site is designed to be deployed from the `website/` directory.

**Vercel Project Settings:**
- Framework Preset: Next.js
- Root Directory: `website`
- Build Command: `npm run build`
- Output Directory: `.next`

The site will automatically deploy when changes are pushed to the configured branch.

## Routes

- `/` — Homepage
- `/models` — Supported models
- `/docs` — Getting started guide
- `/docs/cli` — CLI reference
- `/docs/api` — API reference

## Design

- **shadcn/ui** (Radix + Tailwind v4) for buttons, tables, cards, badges, alerts
- **Grayscale palette:** Paper white / warm charcoal, black/light ink, neutral grays
- **Theme toggle:** Respects `prefers-color-scheme`, persists in localStorage (`data-theme` + `.dark`)
- **Copy buttons:** Every code block and command has a copy-to-clipboard control
- **Docs layout:** Three-column shell with left sidebar, article, and right TOC

Models documented: Chatterbox (MIT) and Qwen3-TTS CustomVoice / Base (Apache-2.0).

All GitHub links point to `https://github.com/smitgol/wavhost`.
