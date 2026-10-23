# Evaluation results

Samples evaluated: 38 (skipped on LLM error: 0)

## Extraction accuracy

- company: 97.4%
- intent: 94.7%
- country: 100.0%

## Routing accuracy: 100.0%

## Confusion (expected -> got)

- enterprise -> enterprise: 10
- review -> review: 8
- smb -> smb: 20

## Extraction misses

- lee@fernhill.example: company expected 'Fernhill', got 'fernhill'
- qq@gmail.com: intent expected 'other', got 'spam'
- x@gmail.com: intent expected 'other', got 'spam'
