# Lecture Notes Population — Design Spec
Date: 2026-06-10

## Context

Two lecture files in the CU Quiz App lack educational content:

1. `courses/Econs/week1/lecture1.catsoop` — 61 lines; contains CSS and live-file JS panel but zero lecture body. Topic: **Law of Demand and Supply**.
2. `courses/Physics/week4/` — no `lecture4.catsoop` exists at all. Topic: **Kinetic Theory of Gases**.

All other lectures (Finance wk1, History wk1, Physics wk1–3, Programming wk1–3, Sports wk1–3) are fully populated at ~230–280 lines each.

## Approach

Comprehensive content (Option A): ~240–280 lines each, matching the quality, structure, and style of existing Physics wk2/wk3 lectures. This includes:
- `<style>` block with `.highlight`, `.formula`, `.worked` CSS classes
- Headings (`h1`, `h2`, `h3`)
- Highlight boxes for key concepts
- Formula boxes for equations
- Worked example panels
- Summary tables
- Nigerian/local context where appropriate

## File 1 — Econs/week1/lecture1.catsoop

**Edit type:** Insert HTML content between the existing `<style>` block and the existing live-file panel `<div>`. The `<python>` header, CSS, and live-file JS are preserved unchanged.

**Sections:**
1. What is a Market? — buyer/seller framing, price mechanism
2. The Law of Demand — definition, demand schedule table, Nigerian tomato/petrol examples
3. Factors that Shift the Demand Curve — table: income, tastes, substitutes, complements, expectations
4. The Law of Supply — definition, supply schedule table, upward-sloping relationship
5. Factors that Shift the Supply Curve — table: input costs, technology, number of sellers
6. Market Equilibrium — Qd = Qs formula box; surplus vs. shortage explanation
7. Price Elasticity of Demand — PED = %ΔQd / %ΔP formula box; elastic vs. inelastic table; worked example calculating PED for a Nigerian good
8. Summary — key takeaways bullet list

## File 2 — Physics/week4/lecture4.catsoop

**Edit type:** Create new file. Must match Physics wk2 structure exactly: `<python>` header → `<style>` → HTML content → live-file panel.

The live-file panel JS must use the same API base as other Physics weeks (`http://172.31.184.39:8000`).

**Sections:**
1. What is the Kinetic Theory? — 5 assumptions of ideal gas (highlight box)
2. Gas Pressure from Molecular View — pressure as momentum transfer; P = F/A
3. Boyle's Law — P₁V₁ = P₂V₂ at constant T; table + worked example (syringe)
4. Charles' Law — V/T = constant at constant P; worked example (gas heated in piston)
5. Gay-Lussac's Law — P/T = constant at constant V; tyre pressure example
6. The Ideal Gas Law — PV = nRT; constants table (R = 8.314 J/mol·K); worked example (moles of air in a room)
7. Temperature and Kinetic Energy — KE = (3/2)kT; RMS speed formula; comparison table (O₂, N₂, H₂)
8. Real vs. Ideal Gases — van der Waals deviations; when the ideal assumption breaks down
9. Summary — laws table (Boyle, Charles, Gay-Lussac, Ideal Gas) with formulas

## Verification

1. Visit `http://localhost:7667/Econs/week1/lecture1` — confirm lecture body renders with all sections, tables, and formula boxes visible
2. Visit `http://localhost:7667/Physics/week4/lecture4` — confirm new file renders correctly
3. Ensure live-file panel appears (hidden until a file is uploaded — correct behaviour)
4. No changes to quiz, example_questions, or gamification files needed
