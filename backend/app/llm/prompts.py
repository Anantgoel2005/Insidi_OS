from __future__ import annotations

ORCHESTRATOR_SYSTEM_PROMPT = """You are Insidi_OS, an AI security assistant for insider-threat investigations, honeypots, canary tokens, and controlled cyber deception tactics.

Your capabilities:
- Analyze attacker TTPs (Tactics, Techniques, Procedures) and map them to MITRE ATT&CK
- Decide engagement strategies: passive monitoring, delay, mislead, gather intel, or deploy countermeasures
- Generate structured JSON responses for automated execution
- Prioritize safety: never enable real exploitation, never exfiltrate real data

Respond in valid JSON only unless asked for narrative analysis."""


TTP_ANALYSIS_PROMPT = """Analyze the following attack events and return a JSON object:

{{
  "techniques": ["TXXXX", ...],
  "tactics": ["tactic_name", ...],
  "threat_actor_type": "opportunistic|targeted|insider|unknown",
  "estimated_skill_level": "novice|intermediate|advanced|nation-state",
  "likely_goal": "description",
  "risk_assessment": "low|medium|high|critical",
  "recommendation": "passive|delay|mislead|gather|escalate",
  "summary": "brief analysis of the attack chain"
}}

Events:
{events}"""


ALERT_ANALYSIS_PROMPT = """Analyze this security alert and provide a detailed investigation recommendation:

Alert Title: {title}
Description: {description}
Severity: {severity}
Event Data: {event_data}

Provide:
1. What likely happened
2. Recommended investigation steps
3. If this is a false positive
4. Suggested remediation or engagement action"""


ENGAGEMENT_DECISION_PROMPT = """Based on the following attack analysis, decide what engagement action to take.

Return JSON:
{{
  "action": "passive|delay|mislead|gather|escalate|withdraw",
  "reason": "why this action was chosen",
  "params": {{}}
}}

Analysis:
{analysis}"""


MITRE_MAPPING_PROMPT = """Map this attacker activity to MITRE ATT&CK techniques. Return JSON:

{{
  "technique_id": "TXXXX",
  "technique_name": "exact name",
  "tactic": "tactic name",
  "confidence": 0.0-1.0
}}

Command: {command}
Log: {log}"""


INCIDENT_REPORT_PROMPT = """Generate a structured cybersecurity incident report in markdown format.

Title: {title}
Generated: {generated_at}

Attack Events:
{events}

Alerts:
{alerts}

Include:
1. Executive Summary
2. Attack Timeline
3. TTP Analysis with MITRE ATT&CK mappings
4. Indicators of Compromise (IOCs)
5. Impact Assessment
6. Recommendations"""
