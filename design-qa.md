# OlGal Hearth design QA

## Comparison target

- Source visual truth: `docs/assets/hearth-quiet-switchboard-reference.webp`
- Shipped browser preview: `docs/assets/olgal-hearth-preview.webp`
- Final browser-rendered implementation: `design-qa-evidence/implementation-pass-3.jpg`
- Combined final comparison: `design-qa-evidence/comparison-pass-3.png`
- State: owner home with a trusted AI call request, one voice letter, and one quiet request in the explicit `preview=hearth` visual-fixture mode.
- CSS viewport: 390 x 844 px.
- Browser device pixel ratio: 1.
- Source pixels: 853 x 1844; normalized to 390 x 844 for comparison.
- Implementation pixels: 390 x 844; no density conversion required.

## Full-view comparison evidence

The final side-by-side comparison confirms the selected composition: compact wordmark and line
state, copper rule, caller identity and intent, paired consent actions, chronological waiting area,
and persistent three-item navigation. Major region boundaries and the bottom navigation align at
the target viewport without overflow.

## Focused-region evidence

The caller and waiting regions were inspected separately during browser interaction testing. The
identity mark, name, intent, voice state, Answer and Later affordances, Phosphor icons, queue copy,
relative time, and row separators remain legible at 390 px. No further crop was needed because all
important type and controls are clearly readable in the 1:1 final comparison.

## Required fidelity surfaces

- Fonts and typography: the implementation uses an iPhone-friendly old-style serif stack and a
  humanist system sans stack. Hierarchy, italic intent copy, letter spacing, weight, wrapping, and
  line height match the source closely. Optical differences from the generated source font are
  acceptable and remain P3.
- Spacing and layout rhythm: header, call region, waiting list, and navigation fit exactly within
  390 x 844 with no scroll overflow. Avatar and button proportions closely match the target.
- Colors and visual tokens: near-black forest, parchment, moss, and restrained copper match the
  selected palette with sufficient foreground separation.
- Image quality and asset fidelity: the generated matte Hearth background is shipped as a crisp
  1170 x 2532 WebP. All visible interface icons come from the MIT-licensed Phosphor library rather
  than handcrafted substitutes.
- Copy and content: source identity and intent copy are preserved in preview mode. Production mode
  deliberately uses generic, truthful purpose copy because private reasons are not stored.

## Interaction and browser checks

- Home and Letters navigation tested.
- Settings dialog open, focus, close, connection controls, and technical-details disclosure tested.
- Answer state tested without requesting a real microphone in preview mode.
- Accepted state exposes a distinct End call action; preview hang-up was tested through to the
  quiet state, and the accepted-call layout remains balanced at phone and desktop widths.
- The final privacy review confirmed that pending or live audio pins its caller on screen; choosing
  another view, opening Settings, changing access, or losing the session tears capture down first.
- Later tested as a visible deferred queue state.
- Browser console checked in the current implementation; no current-page errors were observed.
- Live owner inbox checked separately with its real capability; it returned a non-cacheable empty
  snapshot without exposing private reasons or transport data.

## Comparison history

1. Pass 1 was blocked because a pre-existing service worker served the old developer interface.
   The stylesheet and script URLs were versioned so the selected design loaded deterministically.
2. Pass 1b found a P2 vertical-rhythm mismatch: the header and call area pushed navigation below
   the 844 px viewport. Padding, display scale, call copy, and waiting-area proportions were tuned.
3. Pass 2 fit the viewport and resolved the layout issue. It found one P2 copy issue: the preview
   voice-letter subtitle repeated the caller name. Dynamic subtitle composition was corrected.
4. Pass 3 shows no actionable P0, P1, or P2 mismatch.
5. The release-control pass added owner hang-up and microphone teardown without changing the
   selected incoming-call composition. Answer, End call, return-to-quiet, and a clean browser
   console were rechecked after the change.

## Follow-up polish

- P3: the source uses ornamental radio arcs around the caller mark; the implementation keeps the
  identity mark quieter to avoid adding a decorative non-library drawing.
- P3: the generated source has a denser waveform than the bundled Phosphor waveform icon.

final result: passed
