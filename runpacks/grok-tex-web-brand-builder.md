# T-Ex LLM — Web, Dashboard & Brand Builder (Grok Runpack)

Operating document for a **Grok agent** building T-Ex LLM's **own** web presence — the product's marketing site, its SaaS app dashboard, and its brand kit — as one premium, standalone build. Open a fresh folder on the target machine, start Grok, paste/load this as the agent's instructions. Build **standalone** (mocked data behind a typed layer); it stays independent until the owner confirms, then it wires into the T-Ex LLM runpack + platform. Do not brand it as anything but **T-Ex LLM**.

## 0. Identity & rules

You are building T-Ex LLM's flagship web product. Premium SaaS craft — this is the storefront and the cockpit, so it must look expensive and *work*. Hard rules:
1. **Standalone first.** Every data read goes through one typed data layer (`lib/data.ts`) returning mock data now; swapping to real APIs later is a one-file change. No backend secrets in this build — ever.
2. **Premium ≠ broken.** Every 3D scene and animation ships with a performance budget and a `prefers-reduced-motion` fallback (§8). A beautiful site that janks or fails a screen reader is a failed build.
3. **Two surfaces, one system.** Public marketing (SSR, indexable) and the app dashboard (auth-gated, `noindex`) share a design system and brand tokens but are separate route groups.
4. **Own the code.** shadcn/ui and Tremor are copy-in components — you own and brand them. No external UI lock-in.

## 1. Deliverables (three)

- **A — Marketing site** (public, unauthenticated): hero with 3D + motion, animated "how it works" workflow, features, MCP/API/Integrations, pricing & packages, API docs, PR/press + social kit, signup CTA.
- **B — App dashboard** (authenticated): overview, **agentic task board** (Todo → In Progress → Done → Shipped), checklists/todos, team & board directory, live agent-workflow animation, integrations (MCP/API), usage/credits + billing, account.
- **C — Brand kit**: logo + wordmark (SVG), color + type + spacing tokens, motion signature, favicon + OG images, social-post templates, one-page voice guide.

## 2. The vibe (premium SaaS aesthetic)

- **Direction:** deep, dark, high-contrast "mission-control for AI" — near-black layered surfaces, generous negative space, ONE confident accent (electric cyan or violet — pick one, commit). Depth comes from **real 3D and lighting**, not purple gradients or glassmorphism spam. Pick one aesthetic family and hold it across every screen (mixing families is the #1 "AI template" tell).
- **Type:** one distinctive display face for headlines + a clean UI sans + mono for code/IDs/commands (the terminal-native signal). Self-host all fonts.
- **Motion language:** purposeful and quick — 150–250ms on UI, 200–300ms on panels; a signature 3D hero scene; and the animated workflow (§6) as the centerpiece. Motion must mean something (direction = spatial model); never animate just to move.
- **Anti-generic gate:** no Inter/Roboto default stack, no stock-dashboard screenshots, no decorative widgets. Every element earns its place.

## 3. Stack & setup (shadcn install included)

Next.js (App Router) + TypeScript + Tailwind. Then:

```sh
# scaffold
npx create-next-app@latest tex-web --typescript --tailwind --app --eslint
cd tex-web
# shadcn/ui (the "scdn" install)
npx shadcn@latest init          # choose: default style, your accent as base color, CSS variables: yes
npx shadcn@latest add button card dialog dropdown-menu tabs table badge input sheet tooltip toast avatar progress skeleton
# charts / KPI tiles
npm i @tremor/react
# motion
npm i framer-motion            # UI orchestration + micro-interactions
npm i gsap                     # scroll-timeline + hero choreography
npm i lottie-react             # live workflow animations (pre-rendered JSON)
# 3D (hero + scenes)
npm i three @react-three/fiber @react-three/drei
# docs + payments front-end (no secret keys in this build)
npm i @stripe/stripe-js        # checkout redirect only; secret billing lives server-side later
```

Structure: `app/(marketing)/…` and `app/(app)/…` route groups; `components/ui/*` (shadcn), `components/brand/*`, `components/motion/*`, `lib/data.ts` (the typed mock layer), `lib/tokens.css` (brand tokens), `public/brand/*` (assets).

## 4. Marketing site — page spec (SSR, indexable)

| Section | Content | Motion |
|---|---|---|
| **Hero** | One-line value prop ("Your AI company, in one runpack"), sub-line, primary CTA (Start free) + secondary (Docs). | 3D scene (react-three-fiber): a slowly rotating abstract "agent constellation" or wireframe deck; GSAP intro; parallax on scroll. Lazy-loaded, static poster fallback. |
| **How it works** | The T-Ex flow made visible: Onboard → Build → Review gates → Ship. 3–4 steps. | The **live workflow animation** (§6) — nodes light up and hand off as a task flows. |
| **Features** | Agents & teams, 44 deep skills, native + web app dev, dashboards, fleet. Card grid. | Framer Motion stagger-in on scroll. |
| **MCP · API · Integrations** | Three tabs: MCP (Context7, Linear, Playwright…), REST API, integrations (Stripe, GitHub, n8n…). Logos + one-liners. | Tab crossfade; logo marquee. |
| **Pricing & packages** | The two tiers from the business model — **Credits** (packages with AI-usage credits) and **BYOK / Managed** (bring your own API key, flat subscription). Monthly/annual toggle, feature matrix, CTA→signup. | Toggle spring; recommended-plan glow. |
| **API docs** | A `/docs` route: rendered API reference (embed Scalar or Redoc against an OpenAPI spec, or MDX pages). Searchable, code samples, dark theme matched. | Minimal — docs prioritize legibility. |
| **PR & Press / Social** | `/press`: brand assets download (logo pack, OG images), boilerplate copy, and the social-post kit preview (§7). | Light. |
| **Footer + CTA** | Final signup CTA, links, status, socials. | — |

SEO: every marketing page has real `<title>`, meta description, OG image, and JSON-LD; SSR/SSG; LCP < 2.5s. This is the surface search + buyers judge — it must be crawlable HTML, never a client-only shell.

## 5. App dashboard — page spec (auth-gated, `noindex`)

Apply the `dashboard-design` doctrine: one intent per view, all four states, brand tokens, freshness on every number.

| View | Intent | Content |
|---|---|---|
| **Overview / Command deck** | monitor | Usage + credits balance, active tasks, recent activity feed, quick actions. Stat tiles (Tremor) with delta + freshness. |
| **Agentic Task Board** | act | **Kanban: Todo → In Progress → Done → Shipped.** Cards = tasks with title, owner + reviewer avatars, a **checklist** (progress bar), labels, and a status dot. Drag between columns. This is the product's heart. |
| **Checklists / To-do** | act | Per-task checklists and a personal to-do list; check-off with satisfying micro-interaction. |
| **Team & Board directory** | explore | Team members (the 9 teams / 53 agents as the "staff"), and boards/projects list; click → detail drawer. |
| **Live Workflow** | monitor | The §6 animation wired to (mock) live task state — watch agents pick up work, hand off through gates, and ship. |
| **Integrations** | act | MCP servers, API keys, connected services — connect/disconnect. (Key *entry* UI only; storage is the private backend later.) |
| **Billing & Packages** | act | Credits balance + burn chart, current package, upgrade, and BYOK key field (masked, "stored securely" — real vaulting is server-side later). |
| **Account / Settings** | act | Profile, org, theme, notifications. |

## 6. The live workflow animation (centerpiece)

The thing that makes it feel alive: a pipeline where **nodes (agents) light up and hand off** as a task moves Onboard → Build → Gate → Ship.

- **Build it data-driven:** `react-flow` (or a custom SVG) for the node graph + Framer Motion for the pulses/edges, fed by a task-state object from `lib/data.ts`. This lets the same animation run on real data later.
- **Or pre-rendered:** a **Lottie** JSON for the marketing hero version (lighter, no logic), and the data-driven version inside the app.
- Show: a card entering Todo, an owner node lighting, an edge animating to a reviewer node (the gate), a green "passed" pulse, then "Shipped". Loop on the marketing page; live-bind in the app.
- Respect reduced-motion: swap pulses for a static "current step" highlight.

## 7. Brand kit (deliverables in `public/brand/`)

- **Logo:** a wordmark "T-Ex LLM" + a compact mark/monogram (a "T-Ex" glyph or an abstract agent-node mark). Deliver as **SVG** (scalable, themeable), plus PNG exports at 512/256/64 and a monochrome variant.
- **Tokens:** `lib/tokens.css` — color scale (surfaces, accent, semantic), typography scale, spacing, radius, shadow — light + dark. Everything else references these.
- **Motion signature:** documented easing + durations so every animation feels like one brand.
- **Social kit:** templated post images (launch, feature, quote/testimonial) sized for X (1600×900), LinkedIn (1200×627), IG (1080×1080); an **OG image** template; **favicon** set. Build as React components you can screenshot, or exported PNGs.
- **Voice:** a one-page tone guide (confident, technical, execution-first — mirrors the T-Ex persona).
- **Honesty gate:** AI-generated logos and brand art are a strong *starting point*, not a finished trademarked identity — flag that a designer should refine the final mark before heavy commercial/legal use, and never imitate another company's identity.

## 8. Guardrails (premium but not broken)

- **Performance:** lazy-load 3D and Lottie (dynamic import, in-view trigger); poster/fallback images; keep marketing LCP < 2.5s; cap hero 3D draw calls. Test on a mid laptop, not just yours.
- **Accessibility:** WCAG AA contrast (both themes), full keyboard path, visible focus rings, `aria-label` on icon buttons, and **`prefers-reduced-motion` honored everywhere** (kill 3D auto-spin and pulses, keep opacity fades).
- **Responsive:** mobile-first; the 3D hero degrades to a static brand image on small/low-power devices; the kanban board scrolls horizontally on mobile.
- **SEO split:** marketing SSR + full meta/OG; the app is `noindex` behind auth. Never ship the app shell as the public site.
- **No secrets:** no API keys, no billing secrets, no customer data in this build. Stripe is checkout-redirect only; real billing/metering is the private platform.

## 9. Wiring later (standalone → T-Ex)

Everything reads `lib/data.ts` now. When the owner confirms, swap that layer to:
- The **T-Ex LLM runpack contract** (`GET /api/runpack`, `/api/active`, `/api/brain`, plus the events feed) for agents/skills/task state — see `runpacks/grok-dashboard-builder.md`.
- The **platform backend** (auth, packages, credit metering, BYOK vault) for signup, billing, and keys.

Keep the seam clean: UI never talks to a provider directly — it talks to your data layer, which talks to the backend.

## 10. Done-gates

- `npm run dev` serves; marketing and app both render with mock data.
- Marketing: Lighthouse **SEO ≥ 90** and good performance; real `<title>`/meta/OG on every page; hero 3D loads lazily with a working fallback.
- App: kanban drag works across all four columns; checklists check off; every view has loading/empty/error/live states; app routes are `noindex`.
- Motion: everything honors `prefers-reduced-motion` (verify by toggling the OS setting).
- Brand: logo exports (SVG + PNG), favicon, one OG image, and one social template render correctly; tokens drive the whole UI (zero hardcoded hex in components).
- Zero secrets anywhere in the repo; `lib/data.ts` is the single swap-point for real data.

---

**Is this possible?** Yes — all of it is standard for a capable coding agent: Next.js + shadcn + Tremor + Framer Motion/GSAP/Lottie + react-three-fiber cover the premium 3D and live-animation asks; the kanban/checklist/team-board and pricing/docs surfaces are ordinary app work; the brand kit is generatable as a starting point. The only honest limits: AI-made brand assets need a designer's final pass before trademark-grade use, real billing/metering/BYOK-key storage is the **private** backend (this build ships the front-end + checkout hooks, not the secret logic), and premium motion must stay inside the performance/accessibility budgets above.
