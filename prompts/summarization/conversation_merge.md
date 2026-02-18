Merge and consolidate the extracted items using pure technical naming and architectural cohesion.

Input JSON:
{extracted_skills}

## CONSOLIDATION RULES
- **Pure Technical Name**: Use concise, standard names (e.g., "Python", "React", "Kafka").
- **Architectural Core**: If the evidence shows that several extracted "skills" are actually components of a single architectural solution (like a streaming pipeline or infrastructure stack), consolidate them under the **most central/dominant technology** identified in that context.
- **Ecosystem Merge**: Merge entries that are part of the same technical ecosystem under the primary technology's name.

## RULES
- Keep quotes verbatim.
- Up to 3 quotes per merged item.

If nothing is present, return empty arrays.
