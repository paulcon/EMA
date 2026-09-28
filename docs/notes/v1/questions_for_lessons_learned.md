Here are questions I have about the report lessons_learned_2026-09-27.md by section.

1. Summary
- What does "runs belong to a model version and are cached" mean?
- What is a contract? And what is the contract suite?

2. What was built, in numbers
- What is churn?
- What is the Agent surface?
- What is ALTER TABLE?

3. How control was lost
- How can I ensure that interpretation and advice stay out of the main diagnostic reports and only appears in a separate section labeled "experimental"?
- What are the rules that should stay? What's the right way to design rules? Should I try to envision all of them or derive them from bugs?

4. Testing components
- I'm confused about the contrast suite. What is a contract? How does a contract ensure that every diagnostic gets a set of checks? What might those checks be? How do I design a contract? What are some design principles for the contracts?
- What are snapshot comparisons?
- What are the degenerate inputs I should consider?
- How do I define a contract for every component interface?
- How do I generate degenerate cases?
- How would I design and implement fast and slow tiers
- What is a golden report? And what is shape-pinning?

5. Database structure
- What was the run cache?
- What does provenance mean here?
- How might I design the database to manage models with multiple outputs?
- What does "Designs are not first class" mean?
- What is a JSON blob? 
- What does it mean for state to not be split between database and files? What is state and how should I manage it?
- What is a version hash?
- How do I store arrays as arrays in a database?
- How do I design the written spec for the schema? What does schema mean in this context?

6. User interface
- What is a JSON data card?
- How do I structure the code to design a layered interface (API, CLI, agent)?

7. Agent reliability
- What is an example of "give the agent jobs whose correctness is structural"?
- How do I ensure the harness renders every number?
- What do you mean by "scenarios" in the context of the gate?

8. The API for LLMs (the tool surface)
I have not designed tools before and I know very little about them.
- What are all these tools? Where did they come from? What do they do? Why did I need them?
- What do you mean by "Result shapes"?
- Should I not couple to Anthropic throughout?
- What are the tools describe_model, propose_model, estimate, run_diagnostic, get_result, get_figure? Should these call the API layer?
- What is a result envelope for a tool? 
- How would I ship as an MCP server? How can I learn more about developing tools for an MCP server? What would this approach buy me? How might I structure the tools for an MCP server? How could I use a chatbot to call the tools as an MCP server?

9. Dependencies
- What does "pin lower bounds" mean?

10. Cost
- Is it easy to develop with OpenRouter in mind from the start?

11. Workflows
- How should status live if not in memory notes?
- How should CLAUDE.md be distinct from an architecture document?
- What's the difference between "rules in code and tests" and "principles and commands"?
- What is a "decision record" committed to the repository? What is its purpose? What goes in this record?

12. Other lessons
- What is "no data, no claims"? Give an example.
- What is a trust boundary? What does approval.py do? 
