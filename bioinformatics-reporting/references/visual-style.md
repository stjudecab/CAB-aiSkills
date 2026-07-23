# Visual style

## Contents

- Design goals
- Color palette
- Typography and layout
- Figures and tables
- Report configuration

## Design goals

Use a modern scientific report aesthetic:

- neutral background,
- restrained color,
- accessible contrast,
- numbered figures/tables,
- compact metric cards for key QC values,
- callout boxes for warnings/limitations/key findings.

Avoid gradients, decorative animation, emoji, and marketing language.

## Color palette

| Role | Color | Usage |
|------|-------|-------|
| Primary | `#17365D` | headings, header, metric values |
| Accent | `#267F8E` | links, informational callouts |
| Warning | `#C97706` | limitations and tentative classifications |
| Danger | `#B42318` | severe failures only |

Use color-blind-safe categorical palettes for any newly generated plots. Do not restyle upstream figures unless explicitly requested.

## Typography and layout

- Body: system sans-serif stack (`Segoe UI`, `Helvetica Neue`, Arial, sans-serif)
- Max content width ~1100px for HTML
- Responsive tables with horizontal scroll
- Print-friendly page breaks for PDF via Sphinx LaTeX (`make latexpdf`)

## Figures and tables

- Preserve aspect ratio; cap width to container
- Include concise captions with source artifact paths
- Show only a useful table subset in the main report
- Explain row-selection criteria (`first N rows`, ranking column, supplied threshold)
- Link to full tables under `artifacts/`

## Report configuration

Override defaults through manifest `report`:

```yaml
report:
  title: "Integrated Epigenomics Report"
  subtitle: null
  author: null
  organization: null
  logo: ${skillLoc}/assets/CAB-aiSkills_bioinformatics-reporting.svg
  primary_color: "#17365D"
  accent_color: "#267F8E"
  include_toc: true
  self_contained_html: true
  render_pdf: true
```

HTML should remain readable without JavaScript wherever practical.
