# Evaluation results

Samples evaluated: 100

Models: gemini-3.1-flash-lite | emails per request: 100

Answered by: gemini-3.1-flash-lite (100)

## Extraction accuracy

- company: 100.0%
- intent: 100.0%
- country: 100.0%

## Routing accuracy: 98.0% (98/100)

Excluding 2 rows from mock-enrichment domains (acme.com, bigcorp.com; label conflicts): 100.0% (98/98)

Scoring: company ignores the ' Messy N' suffix and case; intent treats spam and other as the same bucket.

## Confusion (expected -> got)

- enterprise -> enterprise: 32
- enterprise -> smb: 1
- review -> enterprise: 1
- review -> review: 33
- smb -> smb: 33

## Routing misses

- founder5@bigcorp.com: expected review, got enterprise (territory:AMER+segment:enterprise+round_robin; country=None, employees=None, confidence=1.0)
- founder140@acme.com: expected enterprise, got smb (territory:APAC+segment:smb+round_robin; country=PH, employees=None, confidence=1.0)
