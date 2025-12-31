Design Compliance Enforcement: The Combine Templates
Date: December 14, 2025
Artifacts: project_detail.html, project_new.html, project_collapsed.html, project_expanded.html, project_list.html, architecture_view.html
Governing Documents: The Combine Design Manifesto, Design Constitution & Design Tokens v1.0

Section 1 — Violations
Violation 1
Rule Violated: "Use one primary accent color (restrained blue) for primary actions and selection states." — Quiet Palette
Evidence: project_detail.html line 24: class="bg-blue-100 text-blue-800" (project ID badge)
Required Change: Replace bg-blue-100 text-blue-800 with bg-gray-100 text-gray-700

Violation 2
Rule Violated: "Do not introduce secondary accent palettes per feature." — Quiet Palette
Evidence: project_detail.html line 34: class="mb-8 bg-purple-50 rounded-lg border-2 border-purple-200 p-6" (High Level Architecture section)
Required Change: Replace bg-purple-50 with bg-gray-50 and border-purple-200 with border-gray-200

Violation 3
Rule Violated: "Do not introduce secondary accent palettes per feature." — Quiet Palette
Evidence: project_detail.html line 36: class="w-6 h-6 mr-3 text-purple-600" (icon color)
Required Change: Replace text-purple-600 with text-gray-600

Violation 4
Rule Violated: "Do not introduce secondary accent palettes per feature." — Quiet Palette
Evidence: project_detail.html line 46: class="mb-8 bg-indigo-50 rounded-lg border-2 border-indigo-200 p-6" (Detailed Architecture section)
Required Change: Replace bg-indigo-50 with bg-gray-50 and border-indigo-200 with border-gray-200

Violation 5
Rule Violated: "Do not introduce secondary accent palettes per feature." — Quiet Palette
Evidence: project_detail.html line 48: class="w-6 h-6 mr-3 text-indigo-600" (icon color)
Required Change: Replace text-indigo-600 with text-gray-600

Violation 6
Rule Violated: "Use one primary accent color (restrained blue) for primary actions." — Quiet Palette
Evidence: project_detail.html line 66: class="... bg-purple-600 text-white ... hover:bg-purple-700 ..."
Required Change: Replace bg-purple-600 with bg-blue-600 and hover:bg-purple-700 with hover:bg-blue-700

Violation 7
Rule Violated: "Use one primary accent color (restrained blue) for primary actions." — Quiet Palette
Evidence: project_detail.html line 86: class="... bg-indigo-600 text-white ... hover:bg-indigo-700 ..."
Required Change: Replace bg-indigo-600 with bg-blue-600 and hover:bg-indigo-700 with hover:bg-blue-700

Violation 8
Rule Violated: "Button labels use explicit verbs: Generate, Review, Approve, Advance." — Boring Buttons
Evidence: project_detail.html line 69: <span>Preliminary Architecture</span> (noun-based label)
Required Change: Replace with <span>Generate High-Level Architecture</span>

Violation 9
Rule Violated: "Button labels use explicit verbs: Generate, Review, Approve, Advance." — Boring Buttons
Evidence: project_detail.html line 79: <span>Start PM</span> (vague action)
Required Change: Replace with <span>Generate Epics</span>

Violation 10
Rule Violated: "Button labels use explicit verbs: Generate, Review, Approve, Advance." — Boring Buttons
Evidence: project_detail.html line 89: <span>Detailed Architecture</span> (noun-based label)
Required Change: Replace with <span>Generate Detailed Architecture</span>

Violation 11
Rule Violated: "Green: complete, validated, or safe." — Status Color Meaning
Evidence: project_detail.html line 119: class="... bg-green-600 text-white ... hover:bg-green-700 ..." (Begin Work button)
Required Change: Replace bg-green-600 with bg-blue-600 and hover:bg-green-700 with hover:bg-blue-700

Violation 12
Rule Violated: "Button labels use explicit verbs: Generate, Review, Approve, Advance." — Boring Buttons
Evidence: project_detail.html line 121: Begin Work (vague action)
Required Change: Replace with Generate Stories

Violation 13
Rule Violated: "No gradients." — Design Manifesto, What We Never Do
Evidence: project_detail.html line 107: class="bg-gradient-to-r from-blue-50 to-indigo-50 p-4" (Epic header)
Required Change: Replace bg-gradient-to-r from-blue-50 to-indigo-50 with bg-gray-50

Violation 14
Rule Violated: "Button labels use explicit verbs: Generate, Review, Approve, Advance." — Boring Buttons
Evidence: project_detail.html line 152: <span>Create First Epic</span>
Required Change: Replace with <span>Generate First Epic</span>

Violation 15
Rule Violated: "Do not introduce secondary accent palettes per feature." — Quiet Palette
Evidence: project_expanded.html line 27: class="w-4 h-4 text-purple-500 flex-shrink-0" (Architecture icon)
Required Change: Replace text-purple-500 with text-gray-500


Section 2 — Post-Fix Validation
After applying all required changes:
TokenStatusQuiet PaletteCompliantAnchored PanelsCompliantStructured Negative SpaceCompliantStatus Color MeaningCompliantBoring ButtonsCompliantDense but LegibleCompliant

Section 3 — Final Verdict
Approved — implementation is fully compliant.