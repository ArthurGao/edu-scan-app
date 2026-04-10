"""Seed K12 knowledge base concepts

Revision ID: 014_seed_knowledge_base
Revises: 015_create_knowledge_base
Create Date: 2026-03-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "014_seed_knowledge_base"
down_revision: Union[str, None] = "015_create_knowledge_base"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    kb_table = sa.table(
        "knowledge_base",
        sa.column("title", sa.String),
        sa.column("content", sa.Text),
        sa.column("subject", sa.String),
        sa.column("category", sa.String),
        sa.column("grade_levels", postgresql.ARRAY(sa.String)),
        sa.column("source", sa.String),
    )

    op.bulk_insert(
        kb_table,
        [
            # ==================== MATH: ALGEBRA ====================
            {
                "title": "Linear Equations",
                "content": (
                    "A linear equation is an equation where the highest power of the variable is 1, taking the form ax + b = c. "
                    "To solve, isolate the variable by performing inverse operations on both sides: subtract constants, then divide by the coefficient. "
                    "Graphically, a linear equation in two variables (y = mx + b) produces a straight line, where m is the slope and b is the y-intercept. "
                    "Common mistakes include forgetting to apply operations to both sides, and sign errors when moving terms across the equals sign."
                ),
                "subject": "math",
                "category": "Algebra",
                "grade_levels": ["grade-7", "grade-8", "grade-9"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Quadratic Equations",
                "content": (
                    "A quadratic equation has the form ax² + bx + c = 0 where a ≠ 0. "
                    "It can be solved by: (1) factoring — find two numbers that multiply to ac and add to b; "
                    "(2) completing the square — rewrite as (x + p)² = q; "
                    "(3) the quadratic formula: x = (-b ± √(b²-4ac)) / 2a. "
                    "The discriminant b²-4ac determines the nature of roots: positive → 2 real roots, zero → 1 repeated root, negative → no real roots. "
                    "The vertex of the parabola is at x = -b/2a."
                ),
                "subject": "math",
                "category": "Algebra",
                "grade_levels": ["grade-8", "grade-9", "grade-10"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Systems of Linear Equations",
                "content": (
                    "A system of linear equations is two or more equations with the same variables solved simultaneously. "
                    "Three solution methods: (1) substitution — solve one equation for a variable, substitute into the other; "
                    "(2) elimination — add or subtract equations to cancel one variable; "
                    "(3) graphical — find the intersection point. "
                    "A system has one solution (intersecting lines), no solution (parallel lines), or infinitely many solutions (same line). "
                    "For 3-variable systems, use elimination to reduce to 2 variables, then solve."
                ),
                "subject": "math",
                "category": "Algebra",
                "grade_levels": ["grade-8", "grade-9", "grade-10"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Exponent Rules",
                "content": (
                    "Exponent rules govern how to simplify expressions with powers. "
                    "Key rules: product rule: aᵐ × aⁿ = aᵐ⁺ⁿ; quotient rule: aᵐ ÷ aⁿ = aᵐ⁻ⁿ; power rule: (aᵐ)ⁿ = aᵐⁿ; "
                    "zero exponent: a⁰ = 1 (a ≠ 0); negative exponent: a⁻ⁿ = 1/aⁿ; fractional exponent: a^(m/n) = ⁿ√(aᵐ). "
                    "When multiplying expressions with the same base, add exponents. When raising a power to a power, multiply exponents. "
                    "These rules also apply to algebraic expressions: (2x²y)³ = 8x⁶y³."
                ),
                "subject": "math",
                "category": "Algebra",
                "grade_levels": ["grade-7", "grade-8", "grade-9"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Logarithms",
                "content": (
                    "A logarithm is the inverse of exponentiation: log_b(x) = y means bʸ = x. "
                    "Key properties: log(mn) = log m + log n (product rule); log(m/n) = log m - log n (quotient rule); "
                    "log(mⁿ) = n·log m (power rule); change of base: log_b(x) = log(x)/log(b). "
                    "Common bases: log₁₀ (common log, written 'log'), log_e (natural log, written 'ln'). "
                    "Logarithms are used to solve exponential equations: take log of both sides to bring the exponent down. "
                    "Domain of log_b(x) requires x > 0 and b > 0, b ≠ 1."
                ),
                "subject": "math",
                "category": "Algebra",
                "grade_levels": ["grade-10", "grade-11", "grade-12"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Polynomials and Factoring",
                "content": (
                    "A polynomial is an expression with multiple terms of the form aₙxⁿ + ... + a₁x + a₀. "
                    "Factoring methods: (1) GCF — factor out the greatest common factor first; "
                    "(2) difference of squares: a² - b² = (a+b)(a-b); "
                    "(3) perfect square trinomial: a² ± 2ab + b² = (a ± b)²; "
                    "(4) trinomial factoring: find two numbers multiplying to ac and adding to b for ax² + bx + c; "
                    "(5) grouping — for 4-term polynomials, group pairs and factor each. "
                    "Always check by expanding to verify the factored form is correct."
                ),
                "subject": "math",
                "category": "Algebra",
                "grade_levels": ["grade-8", "grade-9", "grade-10"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Sequences and Series",
                "content": (
                    "An arithmetic sequence has a constant difference d between terms: aₙ = a₁ + (n-1)d. "
                    "The sum of n terms of an arithmetic series: Sₙ = n/2 × (a₁ + aₙ) = n/2 × (2a₁ + (n-1)d). "
                    "A geometric sequence has a constant ratio r between terms: aₙ = a₁ × rⁿ⁻¹. "
                    "The sum of n terms of a geometric series: Sₙ = a₁(1 - rⁿ)/(1 - r) when r ≠ 1. "
                    "For an infinite geometric series to converge, |r| < 1, and S∞ = a₁/(1-r). "
                    "Key skill: identify whether a sequence is arithmetic or geometric by checking if differences or ratios are constant."
                ),
                "subject": "math",
                "category": "Algebra",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Functions and Transformations",
                "content": (
                    "A function f(x) maps each input x to exactly one output; tested by the vertical line test on a graph. "
                    "Key transformations from f(x): f(x) + k shifts up k units; f(x) - k shifts down; f(x + h) shifts left h; f(x - h) shifts right h; "
                    "-f(x) reflects over x-axis; f(-x) reflects over y-axis; af(x) stretches vertically by factor a; f(bx) compresses horizontally. "
                    "Composite functions: (f∘g)(x) = f(g(x)) — apply g first, then f. "
                    "Inverse functions f⁻¹ undo f: f(f⁻¹(x)) = x. To find f⁻¹, swap x and y then solve for y."
                ),
                "subject": "math",
                "category": "Algebra",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            # ==================== MATH: GEOMETRY ====================
            {
                "title": "Angles and Parallel Lines",
                "content": (
                    "When a transversal crosses two parallel lines, it creates pairs of special angles. "
                    "Corresponding angles are equal (same position at each intersection). "
                    "Alternate interior angles are equal (between the lines, on opposite sides of the transversal). "
                    "Co-interior (same-side interior) angles are supplementary (sum to 180°). "
                    "Vertically opposite angles are always equal. "
                    "To prove lines are parallel, show that any of these angle relationships hold. "
                    "Common proof technique: angles on a straight line sum to 180°; angles around a point sum to 360°."
                ),
                "subject": "math",
                "category": "Geometry",
                "grade_levels": ["grade-7", "grade-8", "grade-9"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Triangle Properties and Congruence",
                "content": (
                    "The interior angles of any triangle sum to 180°. The exterior angle equals the sum of the two non-adjacent interior angles. "
                    "Congruence criteria (triangles are identical in shape and size): SSS, SAS, ASA, AAS, RHS. "
                    "Similarity criteria (same shape, different size): AA, SAS, SSS (with equal ratios). "
                    "In a right triangle: the side opposite the right angle is the hypotenuse (longest side). "
                    "Special triangles: 30-60-90 (sides in ratio 1 : √3 : 2) and 45-45-90 (sides in ratio 1 : 1 : √2). "
                    "The triangle inequality states that the sum of any two sides must be greater than the third side."
                ),
                "subject": "math",
                "category": "Geometry",
                "grade_levels": ["grade-7", "grade-8", "grade-9"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Circle Theorems",
                "content": (
                    "Key circle theorems: (1) The angle at the centre is twice the angle at the circumference subtended by the same arc. "
                    "(2) Angles in the same segment are equal. "
                    "(3) The angle in a semicircle is 90° (angle subtended by a diameter). "
                    "(4) Opposite angles of a cyclic quadrilateral sum to 180°. "
                    "(5) The tangent to a circle is perpendicular to the radius at the point of contact. "
                    "(6) Tangents from an external point are equal in length. "
                    "Arc length = (θ/360°) × 2πr; Sector area = (θ/360°) × πr²."
                ),
                "subject": "math",
                "category": "Geometry",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Coordinate Geometry",
                "content": (
                    "The coordinate plane uses (x, y) pairs to locate points. "
                    "Gradient (slope) between two points: m = (y₂ - y₁)/(x₂ - x₁). "
                    "Distance formula: d = √((x₂-x₁)² + (y₂-y₁)²). "
                    "Midpoint formula: M = ((x₁+x₂)/2, (y₁+y₂)/2). "
                    "Equation of a line: y = mx + c (slope-intercept); y - y₁ = m(x - x₁) (point-slope). "
                    "Parallel lines have equal gradients; perpendicular lines have gradients that are negative reciprocals (m₁ × m₂ = -1). "
                    "The equation of a circle with centre (a, b) and radius r: (x-a)² + (y-b)² = r²."
                ),
                "subject": "math",
                "category": "Geometry",
                "grade_levels": ["grade-8", "grade-9", "grade-10"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Area, Perimeter, Surface Area and Volume",
                "content": (
                    "2D shapes: Rectangle area = lw, perimeter = 2(l+w); Triangle area = ½bh; Circle area = πr², circumference = 2πr; "
                    "Trapezoid area = ½(a+b)h. "
                    "3D shapes: Cube volume = a³, surface area = 6a²; Cuboid V = lwh, SA = 2(lw + lh + wh); "
                    "Cylinder V = πr²h, SA = 2πr² + 2πrh; Sphere V = (4/3)πr³, SA = 4πr²; "
                    "Cone V = (1/3)πr²h, slant height l, SA = πr² + πrl; Pyramid V = (1/3) × base area × height. "
                    "Always check units: area uses square units, volume uses cubic units."
                ),
                "subject": "math",
                "category": "Geometry",
                "grade_levels": ["grade-6", "grade-7", "grade-8", "grade-9"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Vectors",
                "content": (
                    "A vector has both magnitude and direction, written as a column vector (x, y) or bold letter. "
                    "Vector addition: add corresponding components; subtraction: subtract components. "
                    "Scalar multiplication: multiply each component by the scalar, changing magnitude but not direction. "
                    "Magnitude: |v| = √(x² + y²). Unit vector: v̂ = v / |v|. "
                    "Position vector of midpoint M of AB: OM = ½(OA + OB). "
                    "To show vectors are parallel: one must be a scalar multiple of the other. "
                    "Dot product: a·b = |a||b|cosθ = a₁b₁ + a₂b₂; vectors are perpendicular when a·b = 0."
                ),
                "subject": "math",
                "category": "Geometry",
                "grade_levels": ["grade-10", "grade-11", "grade-12"],
                "source": "K12 Core Curriculum",
            },
            # ==================== MATH: TRIGONOMETRY ====================
            {
                "title": "Trigonometric Ratios (SOHCAHTOA)",
                "content": (
                    "In a right-angled triangle, the three basic trig ratios relate angles to side lengths: "
                    "sin θ = opposite/hypotenuse; cos θ = adjacent/hypotenuse; tan θ = opposite/adjacent. "
                    "Mnemonic: SOH-CAH-TOA. "
                    "To find a missing side: multiply the known side by the trig ratio. "
                    "To find a missing angle: use the inverse function (sin⁻¹, cos⁻¹, tan⁻¹). "
                    "Special values to memorize: sin 30° = 0.5, cos 30° = √3/2, tan 30° = 1/√3; "
                    "sin 45° = cos 45° = √2/2, tan 45° = 1; sin 60° = √3/2, cos 60° = 0.5, tan 60° = √3."
                ),
                "subject": "math",
                "category": "Trigonometry",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Sine Rule and Cosine Rule",
                "content": (
                    "The Sine Rule applies to any triangle (not just right-angled): a/sinA = b/sinB = c/sinC. "
                    "Use the Sine Rule when you know: two angles and one side (AAS/ASA), or two sides and a non-included angle (SSA — check for ambiguous case). "
                    "The Cosine Rule: a² = b² + c² - 2bc·cosA (or rearranged: cosA = (b²+c²-a²)/2bc). "
                    "Use the Cosine Rule when you know: two sides and the included angle (SAS), or all three sides (SSS). "
                    "The area of any triangle: Area = ½ab·sinC. "
                    "Ambiguous case (SSA): there may be 0, 1, or 2 possible triangles — always check both solutions."
                ),
                "subject": "math",
                "category": "Trigonometry",
                "grade_levels": ["grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Trigonometric Identities",
                "content": (
                    "Fundamental identities: sin²θ + cos²θ = 1; tanθ = sinθ/cosθ; "
                    "1 + tan²θ = sec²θ; 1 + cot²θ = csc²θ. "
                    "Double angle formulas: sin 2θ = 2sinθcosθ; cos 2θ = cos²θ - sin²θ = 1 - 2sin²θ = 2cos²θ - 1; "
                    "tan 2θ = 2tanθ/(1 - tan²θ). "
                    "Sum and difference: sin(A±B) = sinAcosB ± cosAsinB; cos(A±B) = cosAcosB ∓ sinAsinB. "
                    "To prove identities: work on one side only, use known identities to simplify until it matches the other side. "
                    "Never cross-multiply or assume equality before proving it."
                ),
                "subject": "math",
                "category": "Trigonometry",
                "grade_levels": ["grade-10", "grade-11", "grade-12"],
                "source": "K12 Core Curriculum",
            },
            # ==================== MATH: CALCULUS ====================
            {
                "title": "Limits and Continuity",
                "content": (
                    "The limit lim(x→a) f(x) = L means f(x) approaches L as x approaches a (but x ≠ a). "
                    "Limit laws: limits of sums, products, and quotients follow algebraic rules. "
                    "For indeterminate forms (0/0, ∞/∞), use: factoring and cancelling, L'Hôpital's Rule (differentiate numerator and denominator), or rationalizing. "
                    "A function is continuous at a if: f(a) exists, lim f(x) exists, and they are equal. "
                    "One-sided limits: left-hand limit lim(x→a⁻) and right-hand limit lim(x→a⁺) must both exist and be equal for the limit to exist."
                ),
                "subject": "math",
                "category": "Calculus",
                "grade_levels": ["grade-11", "grade-12"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Differentiation Rules",
                "content": (
                    "The derivative f'(x) = lim(h→0) [f(x+h) - f(x)] / h represents the instantaneous rate of change. "
                    "Key rules: power rule: d/dx(xⁿ) = nxⁿ⁻¹; constant rule: d/dx(c) = 0; "
                    "sum rule: (f+g)' = f' + g'; product rule: (fg)' = f'g + fg'; "
                    "quotient rule: (f/g)' = (f'g - fg')/g²; chain rule: d/dx[f(g(x))] = f'(g(x))·g'(x). "
                    "Standard derivatives: d/dx(eˣ) = eˣ; d/dx(ln x) = 1/x; d/dx(sin x) = cos x; d/dx(cos x) = -sin x. "
                    "Geometric interpretation: the derivative at a point is the slope of the tangent line."
                ),
                "subject": "math",
                "category": "Calculus",
                "grade_levels": ["grade-11", "grade-12"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Applications of Derivatives",
                "content": (
                    "Finding turning points (maxima/minima): set f'(x) = 0 to find critical points; "
                    "use the second derivative test: f''(x) > 0 → local minimum; f''(x) < 0 → local maximum; f''(x) = 0 → inconclusive. "
                    "Increasing/decreasing: f'(x) > 0 → increasing; f'(x) < 0 → decreasing. "
                    "Inflection points: where f''(x) = 0 and the concavity changes. "
                    "Optimization problems: set up the objective function, differentiate, set equal to zero, verify it's a max or min. "
                    "Related rates: differentiate both sides of an equation with respect to time, then substitute known values."
                ),
                "subject": "math",
                "category": "Calculus",
                "grade_levels": ["grade-11", "grade-12"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Integration",
                "content": (
                    "Integration is the reverse of differentiation (antiderivative). "
                    "Power rule for integration: ∫xⁿ dx = xⁿ⁺¹/(n+1) + C (n ≠ -1); ∫1/x dx = ln|x| + C. "
                    "Standard integrals: ∫eˣ dx = eˣ + C; ∫cos x dx = sin x + C; ∫sin x dx = -cos x + C. "
                    "The definite integral ∫ₐᵇ f(x) dx gives the net area between f(x) and the x-axis from a to b. "
                    "Fundamental theorem of calculus: ∫ₐᵇ f(x) dx = F(b) - F(a), where F is any antiderivative of f. "
                    "For area between curves: ∫ₐᵇ [f(x) - g(x)] dx where f(x) ≥ g(x) on [a, b]."
                ),
                "subject": "math",
                "category": "Calculus",
                "grade_levels": ["grade-11", "grade-12"],
                "source": "K12 Core Curriculum",
            },
            # ==================== PHYSICS: MECHANICS ====================
            {
                "title": "Kinematics: SUVAT Equations",
                "content": (
                    "Kinematics describes motion using five variables: s (displacement), u (initial velocity), v (final velocity), a (acceleration), t (time). "
                    "The four SUVAT equations (for constant acceleration): "
                    "v = u + at; s = ut + ½at²; v² = u² + 2as; s = ½(u+v)t. "
                    "Choose the equation that contains the unknown and three known quantities. "
                    "For objects in free fall: a = g ≈ 9.8 m/s² (downward). Take downward as positive or negative — be consistent. "
                    "For projectile motion: horizontal and vertical components are independent. "
                    "Horizontal: constant velocity (a = 0). Vertical: constant acceleration g downward."
                ),
                "subject": "physics",
                "category": "Mechanics",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Newton's Laws of Motion",
                "content": (
                    "Newton's First Law (inertia): An object stays at rest or moves at constant velocity unless acted on by a net force. "
                    "Newton's Second Law: F = ma — net force equals mass times acceleration. "
                    "The net force is the vector sum of all forces; acceleration is in the same direction as the net force. "
                    "Newton's Third Law: For every action there is an equal and opposite reaction (forces act on different objects). "
                    "Free body diagrams: draw all forces acting on the object as arrows. Common forces: weight (W = mg downward), normal force (perpendicular to surface), friction, tension. "
                    "On an incline: resolve forces parallel and perpendicular to the slope."
                ),
                "subject": "physics",
                "category": "Mechanics",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Work, Energy and Power",
                "content": (
                    "Work done by a force: W = Fs cosθ, where θ is the angle between force and displacement. "
                    "Kinetic energy: KE = ½mv²; Gravitational potential energy: GPE = mgh. "
                    "Conservation of mechanical energy: KE + GPE = constant (when no non-conservative forces act). "
                    "Work-energy theorem: net work done on an object equals its change in KE: W_net = ΔKE. "
                    "Power is the rate of doing work: P = W/t = Fv. Units: Watts (W) = J/s. "
                    "Efficiency = (useful energy output / total energy input) × 100%. "
                    "Energy is always conserved overall, but may be converted to heat by friction."
                ),
                "subject": "physics",
                "category": "Mechanics",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Momentum and Impulse",
                "content": (
                    "Momentum: p = mv (vector quantity, same direction as velocity). Units: kg·m/s. "
                    "Impulse: J = FΔt = Δp (change in momentum). A large force over a short time equals a small force over a long time. "
                    "Law of conservation of momentum: in a closed system (no external forces), total momentum before = total momentum after. "
                    "Elastic collision: both momentum and kinetic energy are conserved. "
                    "Inelastic collision: only momentum is conserved; KE is lost (converted to heat/sound). "
                    "Perfectly inelastic collision: objects stick together after impact. "
                    "For explosions (reverse collision): total initial momentum = 0, so the two pieces move in opposite directions."
                ),
                "subject": "physics",
                "category": "Mechanics",
                "grade_levels": ["grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Circular Motion",
                "content": (
                    "An object in uniform circular motion moves at constant speed but changing direction — it is accelerating toward the centre. "
                    "Centripetal acceleration: a = v²/r = ω²r (directed toward centre). "
                    "Centripetal force: F = mv²/r = mω²r. This is not a new force — it is the net inward force (gravity, tension, normal, friction). "
                    "Period T = 2πr/v; Frequency f = 1/T; Angular velocity ω = 2πf = v/r. "
                    "In a vertical circle: at the top, F_net = mg + T = mv²/r (minimum speed when T = 0: v_min = √(gr)). "
                    "In a banked curve, the horizontal component of normal force provides centripetal force."
                ),
                "subject": "physics",
                "category": "Mechanics",
                "grade_levels": ["grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            # ==================== PHYSICS: WAVES ====================
            {
                "title": "Wave Properties",
                "content": (
                    "A wave transfers energy without transferring matter. "
                    "Transverse waves: oscillation perpendicular to direction of travel (e.g., light, water waves). "
                    "Longitudinal waves: oscillation parallel to direction of travel (e.g., sound — compressions and rarefactions). "
                    "Key quantities: wavelength λ (m), frequency f (Hz), period T = 1/f (s), amplitude A, speed v. "
                    "Wave equation: v = fλ. "
                    "Superposition: when waves meet, their displacements add (constructive interference: in phase; destructive: out of phase). "
                    "Standing waves form between two fixed points: nodes (no displacement), antinodes (maximum displacement)."
                ),
                "subject": "physics",
                "category": "Waves",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Light, Refraction and Optics",
                "content": (
                    "The law of reflection: angle of incidence = angle of reflection (measured from the normal). "
                    "Refraction occurs when light passes between media of different optical densities; it bends toward the normal when slowing down. "
                    "Snell's law: n₁ sinθ₁ = n₂ sinθ₂, where n is the refractive index (n = c/v). "
                    "Total internal reflection occurs when the angle of incidence exceeds the critical angle: sinθ_c = n₂/n₁. "
                    "Converging (convex) lenses bring parallel rays to a focus; diverging (concave) lenses spread them. "
                    "Lens formula: 1/f = 1/v + 1/u; Magnification: m = v/u. "
                    "Real images (light actually converges) are inverted; virtual images appear upright."
                ),
                "subject": "physics",
                "category": "Waves",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            # ==================== PHYSICS: ELECTRICITY ====================
            {
                "title": "Ohm's Law and Electric Circuits",
                "content": (
                    "Ohm's Law: V = IR (Voltage = Current × Resistance). Units: V (volts), A (amperes), Ω (ohms). "
                    "Series circuit: same current throughout; total resistance R_T = R₁ + R₂ + ...; voltages add: V_T = V₁ + V₂ + ... "
                    "Parallel circuit: same voltage across each branch; 1/R_T = 1/R₁ + 1/R₂ + ...; currents add: I_T = I₁ + I₂ + ... "
                    "Kirchhoff's laws: (1) Current law — sum of currents at a junction = 0; (2) Voltage law — sum of EMFs = sum of voltage drops around a loop. "
                    "Internal resistance: terminal voltage = EMF - Ir. When current is zero, terminal voltage = EMF."
                ),
                "subject": "physics",
                "category": "Electricity",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Electric Power and Energy",
                "content": (
                    "Electric power: P = IV = I²R = V²/R. Units: Watts (W). "
                    "Electrical energy: E = Pt = IVt. Units: Joules (J) or kilowatt-hours (kWh). "
                    "1 kWh = 3.6 × 10⁶ J. Cost of electricity = energy used (kWh) × price per unit. "
                    "Fuses and circuit breakers protect against excessive current that could cause overheating. "
                    "A fuse rating should be just above the normal operating current of the device. "
                    "The heating effect of current (Joule heating): Q = I²Rt — used in electric heaters, toasters. "
                    "Resistors in circuits: choose resistor values to give the correct current or voltage drop."
                ),
                "subject": "physics",
                "category": "Electricity",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Electromagnetic Induction and Transformers",
                "content": (
                    "Faraday's law: an EMF is induced when the magnetic flux through a circuit changes. "
                    "Lenz's law: the induced current opposes the change causing it. "
                    "EMF = -dΦ/dt, where magnetic flux Φ = BAcosθ. "
                    "A generator converts mechanical energy to electrical energy using electromagnetic induction. "
                    "A transformer uses a changing magnetic field in a core to change AC voltages: "
                    "V_s/V_p = N_s/N_p (voltage ratio = turns ratio). "
                    "Ideal transformer power conservation: I_p V_p = I_s V_s (so more turns on secondary = higher voltage but lower current). "
                    "Step-up transformers increase voltage (used for power transmission to reduce energy loss)."
                ),
                "subject": "physics",
                "category": "Electricity",
                "grade_levels": ["grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            # ==================== PHYSICS: THERMODYNAMICS ====================
            {
                "title": "Ideal Gas Law and Thermodynamics",
                "content": (
                    "Ideal gas law: PV = nRT, where P = pressure (Pa), V = volume (m³), n = moles, R = 8.314 J/mol·K, T = temperature (Kelvin). "
                    "Boyle's law (constant T): P₁V₁ = P₂V₂. Charles' law (constant P): V₁/T₁ = V₂/T₂. "
                    "Gay-Lussac's law (constant V): P₁/T₁ = P₂/T₂. "
                    "Temperature in Kelvin: T(K) = T(°C) + 273. "
                    "First law of thermodynamics: ΔU = Q - W (change in internal energy = heat added - work done by gas). "
                    "Internal energy of an ideal gas depends only on temperature. "
                    "Heat transfer methods: conduction (through solids), convection (through fluids), radiation (electromagnetic waves)."
                ),
                "subject": "physics",
                "category": "Thermodynamics",
                "grade_levels": ["grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            # ==================== CHEMISTRY ====================
            {
                "title": "Atomic Structure and Electron Configuration",
                "content": (
                    "An atom consists of a nucleus (protons + neutrons) surrounded by electrons in shells/orbitals. "
                    "Atomic number Z = number of protons = number of electrons (neutral atom). "
                    "Mass number A = protons + neutrons. Isotopes have the same Z but different A. "
                    "Electron configuration fills orbitals in order: 1s, 2s, 2p, 3s, 3p, 4s, 3d... "
                    "Shorthand: use noble gas core + remaining electrons, e.g., Na = [Ne] 3s¹. "
                    "Valence electrons (outermost shell) determine chemical properties. "
                    "Ions: losing electrons → cation (+charge); gaining electrons → anion (-charge)."
                ),
                "subject": "chemistry",
                "category": "Atomic Structure",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Periodic Table Trends",
                "content": (
                    "Moving across a period (left to right): atomic radius decreases (more protons pulling electrons closer); "
                    "electronegativity increases; ionization energy increases; metallic character decreases. "
                    "Moving down a group: atomic radius increases (more electron shells); "
                    "electronegativity decreases; ionization energy decreases; metallic character increases. "
                    "First ionization energy: energy to remove the first electron from a gaseous atom. "
                    "Electronegativity measures attraction for bonding electrons (Pauling scale; F = 4.0 is highest). "
                    "Transition metals (groups 3-12) have incomplete d-subshells and form variable-valency ions."
                ),
                "subject": "chemistry",
                "category": "Periodic Table",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Chemical Bonding",
                "content": (
                    "Ionic bonding: transfer of electrons from metal to non-metal; results in oppositely charged ions held by electrostatic attraction. "
                    "High melting point, conducts electricity when molten or dissolved. "
                    "Covalent bonding: sharing of electrons between non-metals. Simple molecular covalent: low melting point, poor conductor. "
                    "Giant covalent (diamond, SiO₂): very high melting point. "
                    "Metallic bonding: positive metal ions in a sea of delocalised electrons; conducts electricity, malleable. "
                    "VSEPR theory: electron pairs repel each other, determining molecular shape. "
                    "Bond polarity: if electronegativity difference > 0.5, the bond is polar covalent; > 1.7 ionic."
                ),
                "subject": "chemistry",
                "category": "Bonding",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Mole Concept and Stoichiometry",
                "content": (
                    "One mole = 6.022 × 10²³ particles (Avogadro's number, Nₐ). "
                    "Molar mass = mass per mole of substance (g/mol), equal to relative atomic/molecular mass. "
                    "Moles = mass / molar mass; moles = volume (L) × concentration (mol/L). "
                    "Stoichiometry uses the mole ratio from balanced equations to relate amounts of reactants and products. "
                    "Limiting reagent: the reactant that runs out first, determining the maximum yield. "
                    "Percentage yield = (actual yield / theoretical yield) × 100%. "
                    "Percentage purity = (mass of pure substance / total mass of sample) × 100%."
                ),
                "subject": "chemistry",
                "category": "Stoichiometry",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Acids, Bases and pH",
                "content": (
                    "Brønsted-Lowry definition: acid = proton (H⁺) donor; base = proton acceptor. "
                    "Strong acids fully dissociate (HCl, HNO₃, H₂SO₄); weak acids partially dissociate (CH₃COOH). "
                    "pH = -log[H⁺]; neutral pH = 7, acidic < 7, basic > 7. "
                    "Neutralization: acid + base → salt + water. "
                    "Titration is used to find the concentration of an acid or base. "
                    "At the equivalence point: moles of acid × acid valency = moles of base × base valency. "
                    "Buffer solutions resist pH change: contain a weak acid and its conjugate base (e.g., CH₃COOH/CH₃COO⁻)."
                ),
                "subject": "chemistry",
                "category": "Acids and Bases",
                "grade_levels": ["grade-9", "grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Balancing Chemical Equations and Reaction Types",
                "content": (
                    "Chemical equations must be balanced: same number of each atom on both sides (conservation of mass). "
                    "Steps: write formulas, count atoms, adjust coefficients (never change subscripts). "
                    "Main reaction types: combination (A + B → AB); decomposition (AB → A + B); "
                    "single displacement (A + BC → AC + B); double displacement (AB + CD → AD + CB); combustion (fuel + O₂ → CO₂ + H₂O). "
                    "Oxidation-reduction (redox) reactions involve electron transfer. "
                    "Oxidation = loss of electrons (OIL); reduction = gain of electrons (RIG). OIL RIG. "
                    "Oxidation state rules: O is usually -2; H is usually +1; sum of oxidation states = charge of species."
                ),
                "subject": "chemistry",
                "category": "Stoichiometry",
                "grade_levels": ["grade-8", "grade-9", "grade-10"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Electrochemistry and Redox",
                "content": (
                    "Electrochemical cells convert chemical energy to electrical energy (galvanic) or vice versa (electrolytic). "
                    "In a galvanic cell: oxidation at the anode (negative); reduction at the cathode (positive). "
                    "Cell voltage (EMF) = E°_cathode - E°_anode (using standard electrode potentials). "
                    "The standard hydrogen electrode (SHE) has E° = 0 V by definition. "
                    "More positive E° = stronger oxidising agent. "
                    "In electrolysis: external current drives non-spontaneous reactions. "
                    "Faraday's laws: mass deposited ∝ charge passed; Q = It; moles of electrons = Q/F (F = 96500 C/mol). "
                    "Electrolysis of brine produces Cl₂ at anode, H₂ at cathode, NaOH in solution."
                ),
                "subject": "chemistry",
                "category": "Electrochemistry",
                "grade_levels": ["grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Thermochemistry and Enthalpy",
                "content": (
                    "Enthalpy change ΔH = heat energy change at constant pressure. Exothermic: ΔH < 0 (releases heat); endothermic: ΔH > 0 (absorbs heat). "
                    "Standard enthalpy of combustion: ΔH°_c (per mole of substance burned completely). "
                    "Standard enthalpy of formation ΔH°_f: forming 1 mole of compound from its elements in standard states. "
                    "Hess's law: ΔH for a reaction is independent of the route taken. "
                    "ΔH°_reaction = Σ ΔH°_f(products) - Σ ΔH°_f(reactants). "
                    "Bond enthalpies: ΔH ≈ Σ(bonds broken) - Σ(bonds formed). "
                    "Calorimetry: q = mcΔT (q = heat, m = mass, c = specific heat capacity, ΔT = temperature change)."
                ),
                "subject": "chemistry",
                "category": "Thermochemistry",
                "grade_levels": ["grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Chemical Equilibrium",
                "content": (
                    "Dynamic equilibrium: the rate of the forward reaction equals the rate of the reverse reaction; concentrations remain constant. "
                    "Equilibrium constant Kc = [products]^n / [reactants]^m (concentrations raised to stoichiometric powers; pure solids/liquids excluded). "
                    "Le Chatelier's principle: if a system at equilibrium is disturbed, it shifts to counteract the change. "
                    "Increasing concentration of a reactant → equilibrium shifts right (toward products). "
                    "Increasing temperature → shifts in the endothermic direction. "
                    "Increasing pressure → shifts toward the side with fewer moles of gas. "
                    "A catalyst increases the rate of both forward and reverse reactions equally — it does not change the position of equilibrium."
                ),
                "subject": "chemistry",
                "category": "Equilibrium",
                "grade_levels": ["grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
            {
                "title": "Reaction Rates and Catalysis",
                "content": (
                    "Reaction rate = change in concentration / time. Measured by monitoring reactant consumption or product formation. "
                    "Factors affecting rate: temperature (higher T → more frequent, energetic collisions); "
                    "concentration/pressure (more particles → more frequent collisions); "
                    "surface area (more exposed particles for heterogeneous reactions); "
                    "catalyst (lowers activation energy, providing an alternative reaction pathway). "
                    "Activation energy Eₐ: minimum energy required for a successful collision. "
                    "Maxwell-Boltzmann distribution shows the spread of molecular energies; higher T shifts the curve right. "
                    "Enzymes are biological catalysts; inhibitors reduce enzyme activity."
                ),
                "subject": "chemistry",
                "category": "Kinetics",
                "grade_levels": ["grade-10", "grade-11"],
                "source": "K12 Core Curriculum",
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM knowledge_base WHERE source = 'K12 Core Curriculum'")
