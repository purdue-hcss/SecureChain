import json

from openai import OpenAI


comparison_template = """
Analyze the compatibility between this GitHub profile and OpenAlex academic records. Evaluate through progressive reasoning using these dimensions:

GitHub Profile:
- Name: {name}
- Affiliation: {affiliation}
- Location: {location}
- Homepage: {homepage}
- Bio: {bio}
- Twitter: {twitter}

OpenAlex Candidate {index}:
- Display Name: {display_name}
- Name Variants: {aliases}
- Affiliations: {affiliation_names}
- Research Fields: {topics}
- Relevance Score: {relevance_score}

Evaluation Framework:
1. Name Compatibility:
   - Compare display name/variants with GitHub name
   - Account for abbreviations (e.g., Marc vs M.), hyphens, and diacritics
   - Identify possible name ordering differences

2. Institutional Alignment:
   - Match explicit organization names
   - Identify parent-child relationships between institutions
   - Recognize alternative naming conventions (e.g., "Sorbonne Université" vs "Paris-Sorbonne University")

3. Domain Consistency:
   - Map GitHub bio keywords to research topics
   - Identify implicit connections between technical domains
   - Evaluate thematic overlap using semantic understanding

4. Geographical Correlation:
   - Cross-reference institution locations with user's location
   - Consider multi-campus institutions and international branches

5. Supporting Evidence:
   - Analyze homepage content potential matches
   - Verify Twitter profile connections to academic work
   - Identify potential publications or projects in bio

6. Score Integration:
   - Weight OpenAlex's relevance_score as baseline (scale 0-3000)
   - Normalize all dimensions to 0-100 range
   - Apply penalty for conflicting evidence

Output Requirements:
- Final compatibility score (0-100)
- Top 3 matching evidences with confidence levels
- Critical mismatches (if any)
- Confidence rationale explaining scoring logic

Return only valid JSON format:
{{
  "score": [0-100],
  "evidences": [
    {{"type": "name|institution|domain|geo|support", 
      "description": string,
      "confidence": "high|medium|low"}},
    ...
  ],
  "mismatches": [strings],
  "rationale": string
}}
"""

client = OpenAI(
    api_key="<your_api_key>"
)


def find_best_match(github_profile, openalex_candidates):
    best_match = {"score": 0, "id": None, "reason": ""}

    for i, candidate in enumerate(openalex_candidates):
        prompt = comparison_template.format(
            index=i + 1,
            name=github_profile.get("name", ""),
            affiliation=github_profile.get("company", ""),
            location=github_profile.get("location", ""),
            homepage=github_profile.get("homepage", ""),
            bio=github_profile.get("bio", ""),
            twitter=github_profile.get("twitter", ""),
            display_name=candidate["display_name"],
            aliases=", ".join(candidate["display_name_alternatives"]),
            affiliation_names=", ".join(candidate["affiliation_names"]),
            topics=", ".join(candidate["topic_names"]),
            relevance_score=candidate["relevance_score"],
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
        )

        try:
            result = json.loads(response.choices[0].message.content)
            print(result)
            
            current_score = result["score"]
            if current_score > best_match["score"]:
                best_match = {
                    "id": candidate["id"],
                    "score": current_score,
                  #   "reason": f"得分 {current_score}，关键证据：{result['evidence']}，差异点：{result['differences']}",
                }
        except Exception as e:
            print(e)
            continue

    return best_match if best_match["id"] else None
