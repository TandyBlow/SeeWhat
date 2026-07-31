"""
Pure-text analysis for formula detection: Unicode math-symbol density,
math region clustering over spans, and the Unicode→LaTeX symbol mapping.

No OCR, no I/O, no logging.
"""

from __future__ import annotations

from .span_extractor import Span

MATH_UNICODE_RANGES = [
    (0x2200, 0x22FF),   # Mathematical Operators
    (0x27C0, 0x27EF),   # Misc Math Symbols-A
    (0x2980, 0x29FF),   # Misc Math Symbols-B
    (0x2A00, 0x2AFF),   # Supplemental Math Operators
    (0x1D400, 0x1D7FF), # Mathematical Alphanumeric Symbols
    (0x2100, 0x214F),   # Letterlike Symbols
    (0x2308, 0x230B),   # Ceiling/floor brackets
]

GREEK_RANGE = (0x0370, 0x03FF)
INTEGRAL_CHARS = set('∫∬∭∮∯∰∱∲∳')
SUM_PROD_CHARS = set('∑∏∐')
MATH_OPERATORS = set('∂∇∞∈∉∋∌∏∐∑−∓∔∕∖∗∘∙√∛∜∝∞∟∠∡∢∣∤∥∦∧∨∩∪∴∵∶∷∸∹∺∻∼∽∾∿≀≁≂≃≄≅≆≇≈≉≊≋≌≍≎≏≐≑≒≓≔≕≖≗≘≙≚≛≜≝≞≟≠≡≢≣≤≥≦≧≨≩≪≫≬≭≮≯≰≱≲≳≴≵≶≷≸≹≺≻≼≽≾≿⊀⊃⊂⊄⊅⊆⊇⊈⊉⊊⊋⊌⊍⊎⊏⊐⊑⊒⊓⊔⊕⊖⊗⊘⊙⊚⊛⊜⊝⊞⊟⊢⊣⊤⊥⊦⊨⊩⊪⊫⊬⊭⊮⊯⊰⊱⊲⊳⊴⊵⊶⊷⊸⊹⊺⊻⊼⊽⊾⊿⋀⋁⋂⋃⋄⋅⋆⋇⋈⋉⋊⋋⋌⋍⋎⋏⋐⋑⋒⋓⋔⋕⋖⋗⋘⋙⋚⋛⋜⋝⋞⋟')


def _char_in_ranges(ch: str, ranges: list[tuple[int, int]]) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in ranges)

# Unicode → LaTeX mapping for inline math symbols
UNICODE_TO_LATEX = {
    'Ω': r'\Omega', 'Ω': r'\Omega',  # U+03A9 and U+2126
    'ω': r'\omega',
    'σ': r'\sigma', 'Σ': r'\Sigma',
    '∅': r'\emptyset', '∈': r'\in', '∉': r'\notin',
    '∪': r'\cup', '∩': r'\cap', '⊆': r'\subseteq',
    '⊂': r'\subset', '⊇': r'\supseteq', '⊃': r'\supset',
    '∀': r'\forall', '∃': r'\exists',
    '∂': r'\partial', '∇': r'\nabla',
    '∞': r'\infty', '∝': r'\propto',
    '≤': r'\leq', '≥': r'\geq', '≠': r'\neq',
    '≈': r'\approx', '≡': r'\equiv',
    '×': r'\times', '÷': r'\div',
    '±': r'\pm', '∓': r'\mp',
    '→': r'\rightarrow', '←': r'\leftarrow',
    '⇒': r'\Rightarrow', '⇐': r'\Leftarrow',
    '⇔': r'\Leftrightarrow',
    '∧': r'\wedge', '∨': r'\vee',
    '¬': r'\neg',
    '√': r'\sqrt',
    'α': r'\alpha', 'β': r'\beta', 'γ': r'\gamma',
    'δ': r'\delta', 'ε': r'\epsilon', 'ζ': r'\zeta',
    'η': r'\eta', 'θ': r'\theta', 'λ': r'\lambda',
    'μ': r'\mu', 'π': r'\pi', 'φ': r'\phi',
    'ψ': r'\psi', 'τ': r'\tau',
    'Γ': r'\Gamma', 'Δ': r'\Delta', 'Θ': r'\Theta',
    'Λ': r'\Lambda', 'Φ': r'\Phi', 'Ψ': r'\Psi',
    '∑': r'\sum', '∏': r'\prod', '∫': r'\int',
    '∎': r'\blacksquare',
}

def unicode_to_latex(text: str) -> str:
    """Replace Unicode math symbols with LaTeX equivalents."""
    result = []
    for ch in text:
        if ch in UNICODE_TO_LATEX:
            result.append(UNICODE_TO_LATEX[ch])
        else:
            result.append(ch)
    return ''.join(result)


def math_symbol_density(text: str) -> float:
    """Ratio of math-unicode characters to total non-whitespace characters."""
    if not text:
        return 0.0
    math_count = 0
    letter_count = 0
    for ch in text:
        if ch.isspace():
            continue
        letter_count += 1
        if _char_in_ranges(ch, MATH_UNICODE_RANGES):
            math_count += 1
        elif _char_in_ranges(ch, [GREEK_RANGE]):
            math_count += 1
        elif ch in INTEGRAL_CHARS or ch in SUM_PROD_CHARS or ch in MATH_OPERATORS:
            math_count += 1
    if letter_count == 0:
        return 0.0
    return math_count / letter_count


def detect_math_regions(
    spans: list[Span],
    density_threshold: float = 0.01,
    min_region_len: int = 1,
) -> list[tuple[int, int, float, list[Span]]]:
    """Find character ranges likely containing math based on Unicode density.

    Returns list of (char_start, char_end, density, matching_spans).

    Lower thresholds (0.01 density, min 1 char) to detect inline math
    symbols like Ω, σ, ∅ that appear as single-character spans.
    Adjacent math spans are merged into formula clusters.
    """
    if not spans:
        return []

    regions: list[tuple[int, int, float, list[Span]]] = []
    i = 0
    while i < len(spans):
        span = spans[i]
        density = math_symbol_density(span.text)
        if density >= density_threshold and len(span.text.strip()) >= min_region_len:
            region_spans = [span]
            start = span.char_start
            end = span.char_end
            densities = [density]
            last_accepted_idx = i
            j = i + 1
            while j < len(spans):
                next_density = math_symbol_density(spans[j].text)
                # Gap text only from spans between last_accepted and current candidate
                gap_text = "".join(s.text for s in spans[last_accepted_idx + 1:j])
                if next_density >= density_threshold:
                    region_spans.append(spans[j])
                    end = spans[j].char_end
                    densities.append(next_density)
                    last_accepted_idx = j
                    j += 1
                elif (j + 1 < len(spans) and
                      len(gap_text.strip()) <= 20 and
                      math_symbol_density(spans[j + 1].text) >= density_threshold):
                    # Bridge a small gap between two math spans
                    region_spans.append(spans[j])
                    region_spans.append(spans[j + 1])
                    end = spans[j + 1].char_end
                    last_accepted_idx = j + 1
                    j += 2
                else:
                    break
            avg_density = sum(densities) / len(densities)
            regions.append((start, end, avg_density, region_spans))
            i = j
        else:
            i += 1

    return regions
