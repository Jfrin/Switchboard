# Evaluation results

Samples evaluated: 100

Answered by: gemini-3.1-flash-lite (98), gemini-3.5-flash-lite (2)

## Extraction accuracy

- company: 90.0%
- intent: 100.0%
- country: 100.0%

## Routing accuracy: 98.0%

## Confusion (expected -> got)

- enterprise -> enterprise: 32
- enterprise -> smb: 1
- review -> enterprise: 1
- review -> review: 33
- smb -> smb: 33

## Extraction misses

- morgan825@gmail.com: company expected 'AeroPulse Tech Messy 52', got None
- michael95@gmail.com: company expected 'Nexus Global Messy 14', got 'Nexus Global'
- guillaume485@gmail.com: company expected 'Apex Dynamics Messy 140', got 'Apex Dynamics'
- michael204@gmail.com: company expected 'Apex Dynamics Messy 108', got 'Apex Dynamics'
- riley999@gmail.com: company expected 'Tokyo Robotics Inc Messy 260', got 'Tokyo Robotics Inc'
- riley210@gmail.com: company expected 'Silverline Corp Messy 220', got 'Silverline Corp'
- seo_guru_84@rankings-fast-marketing.com: company expected None, got 'Rankings Fast Marketing'
- taylor185@gmail.com: company expected 'Velocity Labs Messy 55', got 'Velocity Labs'
- kenji264@gmail.com: company expected 'Ironclad Security Messy 40', got None
- seo_guru_72@rankings-fast-marketing.com: company expected None, got 'Rankings Fast Marketing'

## Routing misses

- founder5@bigcorp.com: expected review, got enterprise (territory:AMER+segment:enterprise+round_robin; country=None, employees=None, confidence=0.95)
- founder140@acme.com: expected enterprise, got smb (territory:APAC+segment:smb+round_robin; country=PH, employees=None, confidence=0.95)
