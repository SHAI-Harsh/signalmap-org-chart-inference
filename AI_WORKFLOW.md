# AI-assisted development log

The task described an AI-native workflow. This prototype was implemented with an AI coding assistant, with executable feedback rather than an unverified generated answer. No external model is called by the app or data pipeline, and no claim is made that a real company hierarchy was discovered.

## Working loop

1. Translate the brief into separate observed-roster and hidden-truth contracts, a company-level evaluation split, explicit abstention, and a static reviewer-facing explorer.
2. Generate imperfect hierarchies first, then remove managers and corrupt observed fields. Implement readable title rules and a simple baseline.
3. Run inference, fit monotone confidence on the calibration companies, and measure precision, coverage, recall and error counts on different test companies. Examine the precision/coverage tradeoff rather than optimizing for a full-looking chart.
4. Add behavioral tests for ambiguous titles, tied candidates, absent managers and cross-company contamination. A graph invariant test exposed that the CEO and other executives initially shared the same numeric seniority. The implementation was corrected to make the CEO rank strictly higher and the baseline was recalculated.
5. Exercise the UI in a browser: select a person and inspect evidence; search for and switch to a different company. Visual inspection also caught confidence rounding that displayed 99.97% as 100%; the display and stored precision were corrected.

The assistant produced the code and draft documentation, then used program execution and browser inspection to check its own work. This is not independent human review. In particular, the generator and inference were co-designed, so a held-out company split is necessary but not sufficient evidence of generalization. No fabricated prompts, model evaluations, or production accuracy claims are included.
