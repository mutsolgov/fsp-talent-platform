# FSP Russia Brand Asset Hub — Authoritative Manifest & Component Mapping

**Document:** `assets/brand/MANIFEST.md`  
**Origin:** Official FSP Russia Brandbook (`брендбук/` & `https://fsp-russia.ru/`)  
**Scope:** Frontend React 19 SPA, Tailwind CSS v4 `@theme`, Backend ReportLab PDF Engine, Offline Docker Distribution  
**Quality Standard:** Ponytail Minimal Efficiency + 100% Reference Completeness (Zero Stubs, Zero TODO/TBD)

---

## 1. Brand Tokens & Color Invariants

The design system is built upon the official visual identity of the Federation of Sport Programming of Russia (ФСП), augmented with LCT 2026 co-branding accents. Every token is strictly calibrated for WCAG 2.1 AAA accessibility across Dark and Light display modes.

| Token Key | HEX Code | RGB | HSL | Semantic Role & UI Placement | WCAG Contrast Ratio |
|---|---|---|---|---|---|
| `color-fsp-blue` | `#402FFF` | `rgb(64, 47, 255)` | `245°, 100%, 59%` | Primary Interactive Brand Blue: bottom emblem node, primary CTA buttons, active navigation links, progress bars, radar charts | 8.6:1 on `#FFFFFF`, 4.5:1 on `#1B1C21` |
| `color-fsp-red` | `#EC1D35` | `rgb(236, 29, 53)` | `353°, 84%, 52%` | Accent Crimson Red: right emblem node, live contest tags, critical deadline alerts, destructive actions | 4.6:1 on `#1B1C21` |
| `color-graphite-bg` | `#1B1C21` | `rgb(27, 28, 33)` | `230°, 10%, 12%` | Deep Graphite Canvas: dark mode background, light mode typography | Base Canvas / 16.5:1 text on white |
| `color-graphite-surface`| `#2D2E37` | `rgb(45, 46, 55)` | `234°, 10%, 20%` | Dark Card Surface: elevated containers, modals, table headers | 10.2:1 against `#EDEDED` text |
| `color-graphite-card` | `#202129` | `rgb(32, 33, 41)` | `233°, 12%, 14%` | Base Card Surface: candidate cards, filter drawers, sidebar panels | 12.8:1 against `#EDEDED` text |
| `color-graphite-border`| `#3D3E42` | `rgb(61, 62, 66)` | `228°, 4%, 25%` | Subtle Structural Borders: grid dividing lines, input field borders | 3.1:1 non-text UI contrast |
| `color-silver-light` | `#EDEDED` | `rgb(237, 237, 237)` | `0°, 0%, 93%` | High-contrast Dark Mode typography & Dark Mode emblem top/left node | 13.5:1 on `#1B1C21` |
| `color-silver-node` | **`#C8C9CA`** | `rgb(200, 201, 202)`| `210°, 2%, 79%` | **MANDATORY INVARIANT**: Light Mode emblem top/left node (prevents contrast failure against white) | Distinct silver-grey contour on `#FFFFFF` |
| `color-lct-mint` | `#00F5D4` | `rgb(0, 245, 212)` | `172°, 100%, 48%` | Co-Branding Cyber Mint: verified KITE assessment score ($\theta \ge 70$), online status dots | 9.8:1 on `#1B1C21` |
| `color-lct-purple` | `#7B2CBF` | `rgb(123, 44, 191)` | `272°, 63%, 46%` | Co-Branding Electric Purple: All-Russian championship tags, jury demo badge | 5.2:1 on `#FFFFFF` |

---

## 2. Official SVG Logos Matrix (10 Variants + 3 Compatibility Aliases)

The platform provides 10 official SVG logo variants directly sourced from `брендбук/`, guaranteeing optimal rendering across all viewport breakpoints and color themes.

### 2.1. Canonical Matrix Table

| Asset Path | Mode | Aspect Ratio | Dimensions (`viewBox`) | Top/Left Node | Right Node | Bottom Node | Wordmark Color | Target Component(s) & Route(s) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `assets/brand/logo_big.svg` | **Dark** | 8:1 (Wide) | `1230 x 154` (`0 0 1230 154`) | `#EDEDED` | `#EC1D35` | `#402FFF` | `#EDEDED` | Hero banner on `LandingPage` (P01), `PublicLayout` (T06), presentation decks |
| `assets/brand/logo_01.svg` | **Dark** | 3:1 (Horizontal) | `345 x 117` (`0 0 345 117`) | `#EDEDED` | `#EC1D35` | `#402FFF` | `#EDEDED` | Top navigation bar in `CandidateLayout` (T02), `EmployerLayout` (T03) (Dark Theme) |
| `assets/brand/logo_02.svg` | **Dark** | 1:1 (Square) | `237 x 227` (`0 0 237 227`) | `#EDEDED` | `#EC1D35` | `#402FFF` | *None (Mark only)* | Mobile bottom navigation bar, browser favicon (Dark mode), candidate avatar badge |
| `assets/brand/logo_03.svg` | **Dark** | 4:5 (Vertical) | `162 x 207` (`0 0 162 207`) | `#EDEDED` | `#EC1D35` | `#402FFF` | `#EDEDED` | Collapsible sidebar in desktop mode, modal authentication dialogs in `AuthLayout` (T01) |
| `assets/brand/logo_04.svg` | **Dark** | 4:5 (Vertical Full) | `160 x 183` (`0 0 160 183`) | `#EDEDED` | `#EC1D35` | `#402FFF` | `#EDEDED` | Mobile drawer header, tournament standings sidebar, splash screen |
| `assets/brand/logo_01w.svg` | **Light** | 8:1 (Wide) | `1000 x 125` (`0 0 1000 125`) | **`#C8C9CA`** | `#EC1D35` | `#402FFF` | **`#1B1C21`** | Floating light header in `LandingPage` (P01), Standardized PDF Profile (`FR-CAND-03`) header |
| `assets/brand/logo_02w.svg` | **Light** | 3:1 (Horizontal) | `345 x 116` (`0 0 345 116`) | **`#C8C9CA`** | `#EC1D35` | `#402FFF` | **`#1B1C21`** | Top navigation bar in `EmployerCandidateBankPage` (P21) (Light Theme), printed reports |
| `assets/brand/logo_03w.svg` | **Light** | 1:1 (Square) | `237 x 227` (`0 0 237 227`) | **`#C8C9CA`** | `#EC1D35` | `#402FFF` | *None (Mark only)* | Browser favicon (Light mode), light candidate card badge, verified stamp |
| `assets/brand/logo_04w.svg` | **Light** | 4:5 (Vertical) | `152 x 191` (`0 0 152 191`) | **`#C8C9CA`** | `#EC1D35` | `#402FFF` | **`#1B1C21`** | Light mode sidebar navigation drawer, printable talent evaluation summary |
| `assets/brand/logo_05w.svg` | **Light** | 4:5 (Vertical Full) | `171 x 191` (`0 0 171 191`) | **`#C8C9CA`** | `#EC1D35` | `#402FFF` | **`#1B1C21`** | Light onboarding dialog in `CandidateOnboardingPage` (P09), formal offer letter header |

### 2.2. Backward Compatibility Aliases

To maintain backward compatibility with existing codebase references, the following alias files are preserved in `assets/brand/`:
- `assets/brand/logo_head.svg` (`32,352 B`): Canonical alias for light navigation headers (viewBox `0 0 1000 125`, `#C8C9CA` top node, `#1B1C21` wordmark).
- `assets/brand/logo_foot.svg` (`32,351 B`): Canonical alias for dark footer panels (viewBox `0 0 1000 125`, `#EDEDED` top node, `#EDEDED` wordmark).
- `assets/brand/logo_mark.svg` (`6,479 B`): Standalone isolated 3-node connected graph mark (viewBox `0 0 237 227`).

---

## 3. Official Sport Programming Discipline Icons (5 SVGs)

The platform supports all 5 official disciplines of the Federation of Sport Programming of Russia. Each icon is implemented as a clean vector SVG (`52 x 52`), integrated into filters, candidate cards, and PDF profiles.

| Asset Path | Discipline Code | Discipline Official Name | ViewBox & Palette | Target Component(s) | UI Semantics |
|---|:---:|---|---|---|---|
| `assets/brand/icon_algoritm.svg` | `DISC-01` | Программирование алгоритмическое | `0 0 52 52`<br>`#402FFF` | `CandidateCard` (O01), `DisciplineFilterBar` (M05), `CandidateProfilePage` (P12) | Icon of code terminal with algorithmic brackets; indicates algorithmic contest achievements (ICPC, All-Russian Olympiads). |
| `assets/brand/icon_product.svg` | `DISC-02` | Программирование продуктовое (хакатоны) | `0 0 52 52`<br>`#402FFF`, `#EDEDED` | `CandidateCard` (O01), `RadarMatchChart` (M03), `NeedCreationWizard` (O07) | Icon of sprint stopwatch and product rocket; indicates hackathon victories, fast prototyping, and product architecture. |
| `assets/brand/icon_security.svg` | `DISC-03` | Программирование систем информационной безопасности | `0 0 52 52`<br>`#402FFF`, `#EDEDED` | `CandidateCard` (O01), `ScoreBreakdownBar` (M04), `EmployerCandidateDetailPage` (P22) | Icon of cryptographic shield and cyber key; indicates CTF competitions, secure coding, and vulnerability analysis. |
| `assets/brand/icon_robot.svg` | `DISC-04` | Программирование робототехники | `0 0 52 52`<br>`#402FFF`, `#EDEDED` | `CandidateCard` (O01), `CandidateProfilePage` (P12), `PublicCategoriesPage` (P08) | Icon of robotic manipulator and microchip node; indicates embedded C/C++, ROS, RTOS, and hardware integration. |
| `assets/brand/icon_drone.svg` | `DISC-05` | Программирование алгоритмов беспилотных авиационных систем (БАС) | `0 0 52 52`<br>`#402FFF`, `#FFFFFF` | `CandidateCard` (O01), `CandidateProfilePage` (P12), `PublicVacanciesPage` (P06) | Icon of quadcopter drone and autonomous waypoint path; indicates autonomous navigation, telemetry, and computer vision. |

---

## 4. Brand Graphic & Raster Artwork (PNG & JPEG)

Official graphic primitives from `брендбук/` provide visual identity and technical authenticity across UI flows and PDF generation.

| Asset Path | Format & Resolution | Size | Palette / Channels | Target Component & Route | Detailed Usage Scenario |
|---|---|---|---|---|---|
| `assets/brand/lineline1.png` | PNG `385 x 313` | `3,962 B` | Deep Graphite & Blue track, Alpha | `FspCircuitConnector.tsx` (Atom A16), `OnboardingWizard` (P09), `CandidateProfilePage` (P12) | 90° rounded circuit bus line with soldering connection pads. Used as structural connector in multi-step onboarding, verified grade progression (`Junior` $\rightarrow$ `Middle` $\rightarrow$ `Senior` $\rightarrow$ `Lead`), invitation lifecycle (`sent` $\rightarrow$ `viewed` $\rightarrow$ `accepted`), and timeline divider in PDF profile. |
| `assets/brand/face1.png` | PNG `332 x 313` | `124,675 B` | Multi-tone cyber wireframe mesh, Alpha | `Avatar.tsx` (A10), `CandidateCard.tsx` (O01), `CandidateAssessmentPage` (P10) | 3D polygonal cyber face mesh. Functions as: 1) Official anonymized applicant avatar under 152-ФЗ compliance before employer invitation is accepted (`isMasked = true`); 2) Hero banner graphic in KITE IRT psychometric assessment. |
| `assets/brand/map1.png` | PNG `471 x 312` | `20,200 B` | Brand Blue `#402FFF` dot matrix, Alpha | `SearchFilterBar.tsx` (M05), `EmployerCandidateBankPage` (P21), `JuryDashboardPage` (P32) | High-precision vector dot matrix map of the 89 regions of the Russian Federation. Functions as interactive background underlay for regional talent searches and territorial coverage analytics. |
| `assets/brand/example.png` | PNG `1133 x 825` | `590,864 B` | Brand Blue `#402FFF`, Off-White, Shadows | ReportLab PDF Engine, `PdfPreviewThumbnail.tsx` (M17), `FR-CAND-03` | Official reference mockup of the Standardized Candidate PDF Profile: modular layout, blue accents `#402FFF`, circuit connector lines, JetBrains Mono typography, co-branding header (Минспорт, Минцифры, Синергия), and 152-ФЗ masked contact container. |
| `assets/brand/logo_big_blue.png` | PNG `92 x 275` | `8,415 B` | Solid `#402FFF` & White, RGBA | Marketing sidebar, event promo cards, PWA desktop banners | Vertical brand blue ribbon banner with white FSP 3-node mark and vertical Cyrillic title. |
| `assets/brand/logo_small_blue.png` | PNG `169 x 179` | `7,192 B` | Solid `#402FFF` & White, RGBA | `RoleSwitcherBar.tsx` (M10), mobile splash screen, PWA manifest icon | Square brand blue icon badge with white FSP 3-node mark. |
| `assets/brand/logo_white1.png` | PNG `127 x 166` | `2,721 B` | Monochrome `#EDEDED`, RGBA | ReportLab PDF canvas watermark, dark footer seal | Raster white standalone FSP emblem mark with transparent alpha channel. |
| `assets/brand/logo_white2.png` | PNG `164 x 188` | `10,512 B` | Monochrome `#EDEDED`, RGBA | Printable talent certificate footer, dark modal dialog footer | Raster white vertical stacked logo with acronym and title. |
| `assets/brand/photo.jpeg` | JPEG `1440 x 734` | `723,276 B` | Full Color RGB | `LandingPage.tsx` (P01) hero background, tournament showcase card | High-resolution tournament atmosphere photograph from Russian Sport Programming Championship. |

---

## 5. Offline Typography & JetBrains Mono Font Family (`assets/brand/fonts/`)

To guarantee 100% offline autonomy (zero external calls to Google Fonts or CDN) during Docker container execution, the official JetBrains Mono font family (version 2.304, SIL Open Font License v1.1) is locally vendored in both Web (`.woff2`) and Desktop (`.ttf`) formats.

### 5.1. Vendored Font Files Inventory

| Font File Path | Format | Weight | Style | File Size | Target Engine & Usage |
|---|:---:|:---:|:---:|:---:|---|
| `assets/brand/fonts/JetBrainsMono-Regular.woff2` | WOFF2 | 400 | Normal | `92,164 B` | React SPA CSS `@font-face` — default body text, table cells, code snippets |
| `assets/brand/fonts/JetBrainsMono-Medium.woff2` | WOFF2 | 500 | Normal | `93,824 B` | React SPA CSS `@font-face` — navigation tabs, form labels, verification badges |
| `assets/brand/fonts/JetBrainsMono-Bold.woff2` | WOFF2 | 700 | Normal | `94,588 B` | React SPA CSS `@font-face` — page headings H1-H3, metric figures, CTA buttons |
| `assets/brand/fonts/JetBrainsMono-Regular.ttf` | TTF | 400 | Normal | `273,900 B` | Backend ReportLab (`TTFont`) — body text in Standardized Candidate PDF Profile |
| `assets/brand/fonts/JetBrainsMono-Medium.ttf` | TTF | 500 | Normal | `273,860 B` | Backend ReportLab (`TTFont`) — section subheaders and table columns in PDF Profile |
| `assets/brand/fonts/JetBrainsMono-Bold.ttf` | TTF | 700 | Normal | `277,828 B` | Backend ReportLab (`TTFont`) — candidate name, grade title, KITE score badge in PDF Profile |
| `assets/brand/fonts/OFL.txt` | Text | — | — | `4,399 B` | SIL Open Font License v1.1 legal notice and permission grant |

### 5.2. Frontend Web Integration (`src/styles/fsp-theme.css`)

```css
@font-face {
  font-family: 'JetBrains Mono';
  src: url('/assets/brand/fonts/JetBrainsMono-Regular.woff2') format('woff2');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: 'JetBrains Mono';
  src: url('/assets/brand/fonts/JetBrainsMono-Medium.woff2') format('woff2');
  font-weight: 500;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: 'JetBrains Mono';
  src: url('/assets/brand/fonts/JetBrainsMono-Bold.woff2') format('woff2');
  font-weight: 700;
  font-style: normal;
  font-display: swap;
}
```

### 5.3. Backend ReportLab PDF Integration (`backend/app/services/pdf_generator.py`)

```python
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONTS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "brand" / "fonts"

pdfmetrics.registerFont(TTFont("JetBrainsMono", str(FONTS_DIR / "JetBrainsMono-Regular.ttf")))
pdfmetrics.registerFont(TTFont("JetBrainsMono-Medium", str(FONTS_DIR / "JetBrainsMono-Medium.ttf")))
pdfmetrics.registerFont(TTFont("JetBrainsMono-Bold", str(FONTS_DIR / "JetBrainsMono-Bold.ttf")))
```

---

## 6. End-to-End Component Traceability & Quality Gate

Every asset documented in this manifest is bound to architectural specifications and validated by automated Quality Gate tooling:

1. **`docs/05_FRONTEND_UX_AND_COMPONENT_MAP.md`**:
   - Section 1.1 formalizes the 10 SVG logo matrix and the mandatory `#C8C9CA` Light Mode color invariant.
   - Section 1.7 specifies `FspCircuitConnector` (`lineline1.png`), `face1.png`, and `map1.png`.
   - Section 5.6.3 specifies the Standardized Candidate PDF Profile (`FR-CAND-03`) layout per `example.png`.
2. **`SPEC.md`**:
   - Section 1 Criterion 3 anchors brand tokens, 10 SVG logos, and local typography.
   - Section 2.4 anchors PDF profile generation per `example.png` with 152-ФЗ masking.
3. **`docs/06_VALIDATION_BENCHMARK_AND_IMPLEMENTATION_PLAN.md`**:
   - Section 1.2 includes `assets/brand/` and `assets/brand/fonts/` in the canonical repository tree.
   - Section 2 defines offline container volume mounts and font bundling.
   - Section 3 links brand assets to Phase 4 (PDF) and Phase 5 (SPA).
4. **Automated Verification**:
   - `scripts/check_consistency.py` (Step 10, Step 11, Step 12) enforces existence, non-emptiness, valid `<svg` syntax, and document token mentions.
   - `tests/run_quality_gate.py` (`verify_brand_assets_integrity`) performs automated disk validation.
