# DESIGN.md — T-ex Neutral Modern

SaaS control-plane visual language for T-ex LLM.

## 1. Purpose
Operator-grade clarity for multi-agent jobs. Calm surfaces, sharp hierarchy, motion that teaches paths—not decoration.

## 2. Palette
| Token | Hex | Use |
|-------|-----|-----|
| `--tex-bg` | `#070A12` | App background |
| `--tex-surface` | `#0F1524` | Cards / panels |
| `--tex-surface-2` | `#161E31` | Elevated |
| `--tex-border` | `#243049` | Hairlines |
| `--tex-text` | `#E8EEF9` | Primary text |
| `--tex-muted` | `#8B9BB8` | Secondary |
| `--tex-primary` | `#5B8CFF` | Actions / links |
| `--tex-accent` | `#3DDC97` | Success / agent pulse |
| `--tex-warn` | `#F5A524` | Review / retry |
| `--tex-danger` | `#FF6B7A` | Failed jobs |

## 3. Typography
- UI: `Inter`, system-ui, sans-serif
- Mono (handoffs/JSON): `JetBrains Mono`, ui-monospace
- Scale: 12 / 14 / 16 / 20 / 28 / 40
- Weight: 400 body, 500 labels, 600 titles

## 4. Layout
- Max content width 1280px
- Sidebar 260px, collapsible
- 8px spacing grid
- Radius: 10–16px (brand-overridable)
- Density: comfortable (default) / compact

## 5. Motion
- Page transitions: 220ms ease-out fade + 8px slide
- Onboarding stage: CSS 3D rotateY (respect reduced motion)
- Agent pulse: soft opacity loop on running jobs
- Never block interaction > 300ms

## 6. Components
- **Nav rail**: icons + labels, active pill
- **Job card**: status chip, goal, firmware pin
- **Brand drawer**: token controls, live preview
- **Command bar**: goal input + send (primary CTA)
- **Handoff timeline**: planner → executor → reviewer → integrator

## 7. Accessibility
- Contrast ≥ WCAG AA for text on surfaces
- Focus visible 2px primary ring
- Landmarks: `banner`, `navigation`, `main`, `complementary`
- Status chips use text + color (not color alone)

## 8. Brand overrides
All tokens overridable via Brand menu → CSS variables.

## 9. Anti-patterns
- No pure black pure white harsh pairs
- No autoplay audio
- No infinite confetti
- No trapping focus in onboarding without Skip
