More notes and questions in response to lessons_learned_answers_2026-09-27.md, organized per section.

1. Summary
- What are some good contract promises for a diagnostic? I don't think the ones you list are universally useful. What are some promises a diagnostic should keep? (Evidently Section 4 covers this.)

2. What was built, in numbers
- Each tool returns a JSON, and this is called "shape"
- Need to keep a stable data model. Database schema. API. Object definitions. Definitions of diagnostics. Model contracts. Definition of a diagnostic Result.

3. How control was lost
- What goes into "core"?

4. Testing components
- What is a typing.Protocol?
- I don't really know what the pyproject.toml does

8. APIs for LLMs
- what is the record format for traces and costs?