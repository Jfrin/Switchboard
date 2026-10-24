# Evaluation results

Samples evaluated: 686

Models: azure:gpt-4.1-mini | emails per request: 20

Answered by: azure:gpt-4.1-mini (686)

## Extraction accuracy

- company: 99.9%
- intent: 99.0%
- country: 91.1%

## Routing accuracy: 89.2% (612/686)

Excluding 7 rows from mock-enrichment domains (acme.com, bigcorp.com; label conflicts): 90.1% (612/679)

Scoring: company ignores the ' Messy N' suffix and case; intent treats spam and other as the same bucket.

## Confusion (expected -> got)

- enterprise -> enterprise: 180
- enterprise -> review: 31
- enterprise -> smb: 4
- review -> enterprise: 3
- review -> review: 257
- review -> smb: 7
- smb -> review: 29
- smb -> smb: 175

## Extraction misses

- morgan825@gmail.com: country expected 'PH', got None
- michael95@gmail.com: country expected 'JP', got None
- guillaume485@gmail.com: country expected 'GB', got None
- mateo985@gmail.com: country expected 'AU', got None
- elena546@gmail.com: country expected 'DE', got None
- michael204@gmail.com: country expected 'GB', got None
- elena731@gmail.com: country expected 'AU', got None
- guillaume704@gmail.com: country expected 'SG', got None
- morgan49@gmail.com: country expected 'AU', got None
- kenji875@gmail.com: country expected 'BR', got None
- hacker17@promptsec.org: intent expected 'other', got 'demo'
- sarah.fernandez@londonfintec.com: country expected 'AU', got None
- founder50@startup50.io: country expected 'AU', got None
- elena.johnson@aussiemining.com: country expected 'AU', got None
- michael.silva@crestviewhol.com: country expected 'PH', got None
- jordan636@gmail.com: country expected 'PH', got None
- chris579@gmail.com: country expected 'PH', got None
- alex.mueller@berlinbiotec.com: country expected 'CA', got None
- sam217@gmail.com: country expected 'PH', got None
- pat811@gmail.com: country expected 'PH', got None
- hacker27@promptsec.org: intent expected 'other', got 'demo'
- mateo946@gmail.com: country expected 'CA', got None
- alex.kowalski@singaporedig.com: country expected 'PH', got None
- sam.johnson@apexdynamics.com: country expected 'PH', got None
- priya209@gmail.com: country expected 'CA', got None
- david825@gmail.com: country expected 'DE', got None
- morgan174@gmail.com: country expected 'JP', got None
- pat514@gmail.com: country expected 'JP', got None
- sarah343@gmail.com: country expected 'JP', got None
- sarah842@gmail.com: country expected 'CA', got None
- morgan843@gmail.com: country expected 'AU', got None
- jordan166@gmail.com: country expected 'FR', got None
- guillaume134@gmail.com: country expected 'BR', got None
- global_procurement3@synergyhq.com: country expected 'JP', got None
- chloe463@gmail.com: country expected 'BR', got None
- guillaume423@gmail.com: country expected 'AU', got None
- riley890@gmail.com: country expected 'JP', got None
- hacker7@promptsec.org: intent expected 'other', got 'demo'
- elena814@gmail.com: country expected 'JP', got None
- hans719@gmail.com: company expected 'Echo Cloud Messy 117', got None
- hans719@gmail.com: country expected 'CA', got None
- chris.patel@pinnaclelogi.com: country expected 'AU', got None
- chloe781@gmail.com: country expected 'DE', got None
- riley664@gmail.com: country expected 'PH', got None
- jordan693@gmail.com: country expected 'AU', got None
- chloe37@gmail.com: country expected 'GB', got None
- mateo909@gmail.com: country expected 'US', got None
- sarah132@gmail.com: country expected 'US', got None
- morgan.kowalski@blueskycapit.com: country expected 'PH', got None
- chris.kim@horizonmedia.com: country expected 'PH', got None
- morgan330@gmail.com: country expected 'CA', got None
- alex746@gmail.com: country expected 'FR', got None
- riley621@gmail.com: country expected 'DE', got None
- michael565@gmail.com: country expected 'DE', got None
- sarah263@gmail.com: country expected 'AU', got None
- hacker12@promptsec.org: intent expected 'other', got 'demo'
- hacker52@promptsec.org: intent expected 'other', got 'demo'
- taylor621@gmail.com: country expected 'CA', got None
- michael160@gmail.com: country expected 'AU', got None
- pat552@gmail.com: country expected 'JP', got None
- michael734@gmail.com: country expected 'FR', got None
- hacker42@promptsec.org: intent expected 'other', got 'demo'
- elena80@gmail.com: country expected 'DE', got None
- priya.kim@singaporedig.com: country expected 'AU', got None
- taylor792@gmail.com: country expected 'DE', got None
- david686@gmail.com: country expected 'DE', got None
- pat22@gmail.com: country expected 'GB', got None
- hacker37@promptsec.org: intent expected 'other', got 'demo'
- elena910@gmail.com: country expected 'BR', got None

## Routing misses

- morgan825@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=120, confidence=0.9)
- michael95@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=140, confidence=0.9)
- guillaume485@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=248, confidence=0.9)
- mateo985@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=193, confidence=0.9)
- elena546@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2866, confidence=0.85)
- michael204@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=297, confidence=0.85)
- elena731@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=427, confidence=0.85)
- guillaume704@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=469, confidence=0.85)
- founder5@bigcorp.com: expected review, got enterprise (territory:AMER+segment:enterprise+round_robin; country=None, employees=None, confidence=0.8)
- morgan49@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2938, confidence=0.85)
- kenji875@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2456, confidence=0.85)
- founder140@acme.com: expected enterprise, got smb (territory:APAC+segment:smb+round_robin; country=PH, employees=None, confidence=0.8)
- hacker17@promptsec.org: expected review, got smb (territory:AMER+segment:smb+round_robin; country=US, employees=12, confidence=0.9)
- sarah.fernandez@londonfintec.com: expected enterprise, got review (fallback:no_territory; country=None, employees=12680, confidence=0.95)
- elena.johnson@aussiemining.com: expected enterprise, got review (fallback:no_territory; country=None, employees=7493, confidence=0.95)
- michael.silva@crestviewhol.com: expected smb, got review (fallback:no_territory; country=None, employees=493, confidence=0.95)
- jordan636@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1182, confidence=0.9)
- chris579@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=475, confidence=0.9)
- alex.mueller@berlinbiotec.com: expected enterprise, got review (fallback:no_territory; country=None, employees=3852, confidence=0.95)
- sam217@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1259, confidence=0.85)
- pat811@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=447, confidence=0.85)
- founder125@bigcorp.com: expected review, got enterprise (territory:AMER+segment:enterprise+round_robin; country=None, employees=None, confidence=0.85)
- hacker27@promptsec.org: expected review, got smb (territory:AMER+segment:smb+round_robin; country=US, employees=12, confidence=0.9)
- mateo946@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=471, confidence=0.85)
- alex.kowalski@singaporedig.com: expected enterprise, got review (fallback:no_territory; country=None, employees=11395, confidence=0.95)
- sam.johnson@apexdynamics.com: expected enterprise, got review (fallback:no_territory; country=None, employees=13008, confidence=0.95)
- priya209@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1883, confidence=0.85)
- david825@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1826, confidence=0.85)
- morgan174@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=92, confidence=0.85)
- pat514@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=348, confidence=0.85)
- sarah343@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=289, confidence=0.85)
- sarah842@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1995, confidence=0.85)
- morgan843@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=469, confidence=0.85)
- jordan166@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1339, confidence=0.85)
- guillaume134@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1935, confidence=0.85)
- founder153@bigcorp.com: expected review, got enterprise (territory:AMER+segment:enterprise+round_robin; country=None, employees=None, confidence=0.8)
- global_procurement3@synergyhq.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1200, confidence=0.9)
- chloe463@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1690, confidence=0.85)
- guillaume423@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=217, confidence=0.85)
- riley890@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=543, confidence=0.85)
- hacker7@promptsec.org: expected review, got smb (territory:AMER+segment:smb+round_robin; country=US, employees=12, confidence=0.95)
- elena814@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2338, confidence=0.85)
- founder4@acme.com: expected enterprise, got smb (territory:APAC+segment:smb+round_robin; country=PH, employees=None, confidence=0.8)
- hans719@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1249, confidence=0.9)
- chris.patel@pinnaclelogi.com: expected smb, got review (fallback:no_territory; country=None, employees=469, confidence=0.95)
- chloe781@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=380, confidence=0.9)
- riley664@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=708, confidence=0.85)
- jordan693@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=322, confidence=0.85)
- chloe37@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2887, confidence=0.85)
- mateo909@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=87, confidence=0.85)
- sarah132@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=357, confidence=0.85)
- morgan.kowalski@blueskycapit.com: expected smb, got review (fallback:no_territory; country=None, employees=29, confidence=0.95)
- chris.kim@horizonmedia.com: expected enterprise, got review (fallback:no_territory; country=None, employees=9926, confidence=0.95)
- morgan330@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=731, confidence=0.85)
- alex746@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=404, confidence=0.9)
- riley621@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=385, confidence=0.9)
- michael565@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1220, confidence=0.9)
- founder16@acme.com: expected enterprise, got smb (territory:AMER+segment:smb+round_robin; country=CA, employees=None, confidence=0.85)
- sarah263@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2283, confidence=0.85)
- hacker12@promptsec.org: expected review, got smb (territory:AMER+segment:smb+round_robin; country=US, employees=12, confidence=0.9)
- founder28@acme.com: expected enterprise, got smb (territory:EMEA+segment:smb+round_robin; country=GB, employees=None, confidence=0.9)
- hacker52@promptsec.org: expected review, got smb (territory:AMER+segment:smb+round_robin; country=US, employees=12, confidence=0.9)
- taylor621@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=123, confidence=0.85)
- michael160@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=266, confidence=0.85)
- pat552@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2544, confidence=0.85)
- michael734@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=65, confidence=0.85)
- hacker42@promptsec.org: expected review, got smb (territory:AMER+segment:smb+round_robin; country=US, employees=12, confidence=0.9)
- elena80@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1412, confidence=0.85)
- priya.kim@singaporedig.com: expected enterprise, got review (fallback:no_territory; country=None, employees=5442, confidence=0.95)
- taylor792@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=302, confidence=0.9)
- david686@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1750, confidence=0.9)
- pat22@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2937, confidence=0.9)
- hacker37@promptsec.org: expected review, got smb (territory:AMER+segment:smb+round_robin; country=US, employees=12, confidence=0.9)
- elena910@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=248, confidence=0.85)
