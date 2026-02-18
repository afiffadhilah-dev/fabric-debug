Merge, consolidate, and deduplicate extracted skills.

## CONSOLIDATION STRATEGY

### MERGE CHILD ITEMS INTO PARENT

**IMPORTANT:** Child items should be MERGED into parent, not kept separate!

| Children | → Merge Into |
|----------|--------------|
| Redux, Context API, Zustand, Hooks | → React.js |
| Bloc, Provider, GetX | → Flutter |
| Spring Boot, Hibernate, JPA | → Java |
| Express.js, NestJS, Fastify | → Node.js |
| Docker Compose | → Docker |
| EC2, S3, Lambda, RDS | → AWS |
| Compute Engine, Cloud Run | → GCP |
| Angular 10+, RxJS | → Angular |
| Flask, FastAPI, Django | → Python |

**How to merge:**
1. Keep ONLY the parent entry
2. Move child names into parent's evidence field
3. Use highest confidence score from parent or children
4. REMOVE child entries after merging

### REMOVE THESE ITEMS (Too Granular)
- Language features: ES6+, Hooks, Context API (merge into parent)
- Generic web tech: HTML5, CSS3 (skip unless specifically relevant)
- Version numbers: Angular 10+, TypeScript 4.x (just use Angular, TypeScript)
- Abbreviations that duplicate: JS = JavaScript (keep full name)

### KEEP SEPARATE (Never Merge Together)
- Different databases: PostgreSQL, MySQL, MongoDB, Redis
- Different CI/CD tools: Jenkins, GitHub Actions, GitLab CI  
- Different testing tools: Jest, JUnit, Cypress, Selenium
- Different methodologies: Agile, Scrum, Kanban
- Different cloud platforms: AWS, GCP, Azure

## MERGE BY CATEGORY

### technical_tools (Target: 15-25 items)
1. Merge framework + libraries → parent framework only
2. Merge cloud services → cloud platform only
3. Remove duplicates and granular items
4. Combine evidence from merged items

### methodologies (Target: 3-8 items)
1. Keep distinct methodologies separate
2. Merge exact synonyms only

### domain_knowledge (Target: 5-10 items)
1. Merge related areas: "SQL optimization" + "Database design" → "Database Design & Optimization"
2. Keep distinct domains separate

### soft_skills (Target: 5-8 items)
1. Consolidate heavily:
   - Team Management + Mentoring + Leadership → "Leadership"
   - Stakeholder Management + Presentation + Communication → "Communication"
   - Analytical Thinking + Critical Thinking → "Problem Solving"
   - Teamwork + Collaboration → "Collaboration"
   - Learning Agility + Adaptability → "Adaptability"
   - Prioritization + Time Management → "Time Management"

## PROFICIENCY LEVEL ASSESSMENT FOR TECHNICAL_TOOLS

**IMPORTANT:** Assess proficiency level based on QUALITY and COMPLEXITY of evidence, NOT just duration/years of experience.

For each technical_tool entry, analyze the evidence deeply and determine proficiency_level based on:

### Assessment Criteria (Evidence-Based):

**BEGINNER:**
- Basic usage only: "used X", "worked with X", "familiar with X"
- Simple implementations: basic CRUD, standard configurations
- Following tutorials or basic documentation
- No mention of problem-solving or optimization
- Limited context or shallow description
- Listed in skills section without context

**INTERMEDIATE:**
- Regular usage with understanding: "implemented X", "built X using Y"
- Standard implementations: common patterns, typical use cases
- Can work independently on standard tasks
- Some problem-solving mentioned but straightforward
- Mentions integration with other tools in standard ways
- Used in projects with standard requirements

**ADVANCED:**
- Complex implementations: "designed X architecture", "optimized X performance"
- Deep problem-solving: "solved challenging problem with X", "overcame limitation by Y"
- Advanced features utilized: custom configurations, performance tuning, scalability solutions
- Architecture decisions: "chose X because Y", "designed system using X pattern"
- Optimization achievements: "reduced latency", "improved throughput", "scaled to X users"
- Integration complexity: multiple systems, complex workflows
- Mentions troubleshooting complex issues or edge cases
- Led implementation or made key technical decisions

**EXPERT:**
- Novel problem-solving: "solved unique challenge", "innovated approach using X"
- Leading technical decisions: "architected system", "led implementation", "designed solution"
- Deep expertise indicators: "contributed to X", "customized X for Y", "extended X functionality"
- Teaching/mentoring: "mentored team on X", "guided implementation", "trained developers"
- Advanced optimization: "achieved X% improvement", "handled X scale", "reduced costs by Y"
- Complex integrations: multiple systems, custom solutions, performance-critical
- Evidence shows deep understanding of internals, trade-offs, and best practices
- Published articles, gave talks, or contributed to open source related to the tool

### Key Indicators to Look For:

**Complexity Indicators (Advanced/Expert):**
- Architecture/design decisions
- Performance optimization
- Scalability solutions
- Custom implementations
- Integration with multiple systems
- Troubleshooting complex issues
- Handling edge cases
- Leadership in technical decisions

**Depth Indicators (Advanced/Expert):**
- Understanding of trade-offs
- Knowledge of internals
- Best practices application
- Problem-solving approach
- Innovation or novel solutions
- Technical writing or knowledge sharing

**Impact Indicators (Advanced/Expert):**
- Metrics/achievements mentioned
- Business impact
- Team leadership
- Knowledge sharing
- Published work or contributions

**Resume-Specific Context:**
- Job titles and responsibilities (Senior/Lead/Principal roles suggest advanced/expert)
- Years of experience mentioned (but prioritize evidence quality over duration)
- Project descriptions showing complexity
- Achievements and metrics
- Leadership or mentoring roles

**Default:** If evidence is insufficient or only shows basic usage, default to "intermediate"

### Assessment Process:
1. Read ALL evidence quotes for the tool
2. Analyze complexity of described implementations
3. Look for problem-solving depth and innovation
4. Check for advanced features, optimization, architecture decisions
5. Consider impact and achievements mentioned
6. Consider job titles and responsibilities if available
7. Determine level based on HIGHEST complexity shown (not average)

## OUTPUT FORMAT

```json
{{
  "detected_role": "Preserve from input",
  "technical_tools": [...],
  "methodologies": [...],
  "domain_knowledge": [...],
  "soft_skills": [...]
}}
```

Each entry: name_raw, name_normalized, evidence (include merged children), confidence_score, proficiency_level

**proficiency_level values:** "beginner", "intermediate", "advanced", "expert" (only for technical_tools, optional for other categories)

EXTRACTED SKILLS:
{extracted_skills}
