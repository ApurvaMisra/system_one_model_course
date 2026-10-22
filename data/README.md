# Teaching fixtures

All tickets are original synthetic examples authored for this course, not real customer records. Screenshots are original code-rendered fictional UI fixtures. These fixture texts and images may be reused and modified with the course. No third-party screenshots or customer data are included.

## Annotation rules

- **billing:** existing payments, refunds, invoices, subscriptions.
- **technical:** malfunctioning application features or service errors.
- **account:** login, credentials, profiles, and membership.
- **other:** sales, suggestions, general questions, or insufficient evidence.
- Mixed intents: the reference team follows the first actionable issue; `review_expected=true` highlights that a single-team answer is incomplete.
- **Frustration 0:** neutral or positive. **1:** mild complaint/annoyance. **2:** clear or repeated frustration. **3:** intense anger or explicit outrage. This is tone, not urgency or business severity. Sarcasm is marked ambiguous.
- **refund_requested:** an explicit request for money back, including paraphrases; not merely a policy question, cancellation, or negated refund.

12 `dev` cases support prompt/threshold selection; 12 distinct `eval` cases are held out. Do not retune after seeing evaluation labels. These labels are authored examples, not independently adjudicated benchmark truth. Read `annotation_note` when examining mistakes; the small set cannot establish broad calibration or superiority.

For screenshot examples: category is payment/login/service/none; severity is 0 (no error), 1 (warning but work can continue), 2 (specific task blocked), or 3 (whole service blocked). Reference boxes enclose the banner. All image cases are illustrative evaluation examples; they are not used to tune image thresholds.

## Retrieval and extraction fixtures

`documents/search_passages.json` contains four authored snippets simulating retrieved search candidates. Their listed order is an input order, not a reference ranking or a real search result. The password-reset snippet is the expected best match for the default password-reset query.

`documents/invoice.txt` is an authored unstructured message. Reference fields for manual checking: supplier **Northwind Studio**, invoice **INV-2026-014**, total **USD 264.00**, due **2026-11-15**. The subtotal and tax are deliberate distractors. These reference values are not model outputs. Notebook 07 also reuses the original synthetic screenshots.
