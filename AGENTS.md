## Design Context

### Users
Developers building production AI chatbots. They want a premium, professional interface for their LLM-powered applications — tools, function calling, streaming responses, and custom components. They are technical, value speed and simplicity, and want something that looks intentionally designed, not generic.

### Brand Personality
Premium, confident, simple, fast. The "Streamlit competitor" — better and simpler. Professional but with warmth and personality. Not clinical, not maximalist. Think a well-crafted developer tool that feels premium without being intimidating.

### Aesthetic Direction
- **Tone**: Editorial warmth meets technical precision. Serif display typography (Cormorant Garamond) for personality, clean sans-serif (Sora) for UI, monospace (JetBrains Mono) for code and technical labels.
- **Color**: OKLCH-based palettes with perceptually uniform steps. 9 themes (5 light, 4 dark). Each theme has a dominant accent color that owns 60% of colored elements, with semantic colors (success/error/warning) for state.
- **References**: Linear, Vercel dashboard, ChatGPT, Claude.ai — clean, confident, premium developer tools.
- **Anti-references**: Streamlit's default look (too utilitarian), generic AI chatbot UIs (purple-blue gradients, glassmorphism, neon on dark).

### Design Principles
1. **Confident restraint** — Every element should feel intentional. Remove anything that doesn't add meaning. Fewer borders, more breathing room, stronger hierarchy through typography rather than containers.
2. **Strategic color** — Color should communicate state, guide attention, and add warmth — never decorate. One dominant accent per theme, semantic colors for meaning, tinted neutrals for sophistication.
3. **Typography as hierarchy** — Use scale, weight, and family contrast to create visual hierarchy. Serif for moments of personality, sans for clarity, mono for precision.
4. **Purposeful motion** — Animations should convey state changes and provide feedback. Smooth deceleration (ease-out-quart), never bounce. Respect reduced-motion preferences.
5. **Accessible by default** — WCAG AA contrast, keyboard navigation, ARIA labels, screen reader support. Color never the only indicator.

### Anti-Patterns to Avoid
- Glassmorphism, blur effects, glow borders used decoratively
- Purple-to-blue gradients (AI slop)
- Gradient text on headings or metrics
- Cards inside cards (flatten the hierarchy)
- Same-sized card grids repeated endlessly
- Centered everything (use left-aligned asymmetry)
- Pure black (#000) or pure white (#fff) — always tint
- Gray text on colored backgrounds
- Monospace as lazy "developer" shorthand
- Rounded rectangles with generic drop shadows
