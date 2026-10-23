# Evaluation results

Samples evaluated: 96 (skipped on LLM error: 4)

## Extraction accuracy

- company: 87.5%
- intent: 95.8%
- country: 100.0%

## Routing accuracy: 97.9%

## Confusion (expected -> got)

- enterprise -> enterprise: 32
- enterprise -> smb: 1
- review -> review: 28
- review -> smb: 1
- smb -> smb: 34

## Extraction misses

- sarah285@gmail.com: company expected 'Berlin Biotech GmbH Messy 18', got 'Berlin Biotech GmbH'
- chris178@gmail.com: company expected 'Zenith Solutions Messy 53', got 'Zenith Solutions'
- kenji418@gmail.com: company expected 'Quantum Soft Messy 250', got None
- alex264@gmail.com: company expected 'BrightPath AI Messy 168', got 'BrightPath AI'
- mateo374@gmail.com: company expected 'Velocity Labs Messy 234', got 'Velocity Labs'
- hacker32@promptsec.org: company expected 'Prompt Security Inc 32', got 'Prompt Security Inc'
- unknown_sender_54@anonmail.net: intent expected 'other', got 'spam'
- unknown_sender_39@anonmail.net: intent expected 'other', got 'spam'
- hans400@gmail.com: company expected 'Solaris Systems Messy 160', got None
- kenji650@gmail.com: company expected 'Ironclad Security Messy 229', got None
- unknown_sender_9@anonmail.net: intent expected 'other', got 'spam'
- david543@gmail.com: company expected 'Kurogane Heavy Industries Messy 135', got 'Kurogane Heavy Industries'
- unknown_sender_49@anonmail.net: intent expected 'other', got 'spam'
- seo_guru_96@rankings-fast-marketing.com: company expected None, got 'rankings-fast-marketing'
- david422@gmail.com: company expected 'Velocity Labs Messy 54', got 'Velocity Labs'
- riley304@gmail.com: company expected 'Aussie Mining Ltd Messy 100', got 'Aussie Mining Ltd'

## Routing misses

- founder148@acme.com: expected enterprise, got smb (territory:APAC+segment:smb+round_robin; country=JP, employees=None, confidence=0.95)
- hacker32@promptsec.org: expected review, got smb (territory:AMER+segment:smb+round_robin; country=US, employees=12, confidence=0.9)
