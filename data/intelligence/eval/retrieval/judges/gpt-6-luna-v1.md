# GPT-6 Luna relevance grading prompt — v1.1 incremental pool

You are judging development-set query/document relevance. Judge only the information shown for the query and artifact. The record identity fields (`query_id`, `artifact_id`) are for returning your answer and are not relevance evidence.

Assign exactly one relevance grade:

- **0 — Irrelevant:** the artifact does not answer the query or materially help investigate it.
- **1 — Relevant/useful:** the artifact contributes useful context, evidence, a method, or a source to follow.
- **2 — Directly important:** the artifact directly addresses the query or is a central result or example for it.

Assess the artifact against the query, category, and specificity. Do not award relevance because an artifact is recent, popular, from a prestigious source, written by a familiar author, or associated with a well-known model or organization. Do not infer content that is absent from the supplied metadata. You will not be given the retrieval route, rank, or score; do not seek or infer them.

Choose `quality_issue` independently of relevance. Use `insufficient_metadata` when the supplied title, type, URL, date, and summary excerpt do not provide enough information to assess the artifact. This flag does not force grade 0: assign the best-supported grade from the available evidence. Otherwise use `none`, except when the visible record clearly has a broken URL, suspected duplicate identity, or identity problem.

Return one JSON object with schema `bubblevan/retrieval-model-judgment/v1`, echoing the supplied `benchmark_hash`, `corpus_hash`, and `prompt_hash`. Its `judgments` array must contain exactly one row for every supplied pair and no other rows. Each row must contain exactly `query_id`, `artifact_id`, integer `grade` (0, 1, or 2), and `quality_issue` (one of `none`, `insufficient_metadata`, `broken_url`, `suspected_duplicate`, `identity_problem`). Do not add explanations or other fields.

These are explicit model-judged development relevance judgments for regression and product diagnosis. They are not human judgments or objective ground truth.
