# Evaluation results

Samples evaluated: 100

Models: azure:gpt-4.1-mini | emails per request: auto

Answered by: azure:gpt-4.1-mini (100)

## Extraction accuracy

- company: 96.0%
- intent: 100.0%
- country: 97.0%

## Routing accuracy: 97.0% (97/100)

Excluding 2 rows from mock-enrichment domains (acme.com, bigcorp.com; label conflicts): 99.0% (97/98)

Scoring: company ignores the ' Messy N' suffix and case; intent treats spam and other as the same bucket.

## Confusion (expected -> got)

- enterprise -> enterprise: 32
- enterprise -> smb: 1
- review -> enterprise: 1
- review -> review: 33
- smb -> review: 1
- smb -> smb: 32

## Extraction misses

- morgan825@gmail.com: country expected 'PH', got None
- elena546@gmail.com: country expected 'DE', got 'SG'
- sales90@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- sales10@b2bleadlist-database.co: company expected None, got 'b2bleadlist-database.co'
- sales2@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database.co'
- sarah700@gmail.com: country expected 'CA', got 'SG'
- sales42@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'

## Routing misses

- morgan825@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=120, confidence=0.9)
- founder5@bigcorp.com: expected review, got enterprise (territory:AMER+segment:enterprise+round_robin; country=None, employees=None, confidence=0.9)
- founder140@acme.com: expected enterprise, got smb (territory:APAC+segment:smb+round_robin; country=PH, employees=None, confidence=0.9)
