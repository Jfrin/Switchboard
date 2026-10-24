# Evaluation results

Samples evaluated: 294

Models: azure:gpt-4.1-mini | emails per request: auto

Answered by: azure:gpt-4.1-mini (290), none (regex fallback) (4)

## Extraction accuracy

- company: 94.9%
- intent: 99.3%
- country: 75.9%

## Routing accuracy: 76.2% (224/294)

Excluding 3 rows from mock-enrichment domains (acme.com, bigcorp.com; label conflicts): 77.0% (224/291)

Scoring: company ignores the ' Messy N' suffix and case; intent treats spam and other as the same bucket.

## Confusion (expected -> got)

- enterprise -> enterprise: 57
- enterprise -> review: 34
- enterprise -> smb: 1
- review -> enterprise: 2
- review -> review: 113
- smb -> review: 33
- smb -> smb: 54

## Extraction misses

- sarah285@gmail.com: country expected 'FR', got None
- guillaume338@gmail.com: country expected 'JP', got None
- guillaume87@gmail.com: country expected 'BR', got None
- chris178@gmail.com: country expected 'BR', got None
- kenji418@gmail.com: company expected 'Quantum Soft Messy 250', got None
- kenji418@gmail.com: country expected 'PH', got None
- alex264@gmail.com: company expected 'BrightPath AI Messy 168', got None
- riley223@gmail.com: country expected 'US', got None
- mateo374@gmail.com: country expected 'GB', got None
- hacker32@promptsec.org: company expected 'Prompt Security Inc 32', got None
- hacker32@promptsec.org: country expected 'US', got None
- michael831@gmail.com: country expected 'FR', got None
- pat913@gmail.com: country expected 'PH', got None
- guillaume320@gmail.com: company expected 'Ironclad Security Messy 77', got None
- guillaume320@gmail.com: country expected 'BR', got None
- chris117@gmail.com: country expected 'US', got None
- sam178@gmail.com: country expected 'GB', got None
- hans400@gmail.com: company expected 'Solaris Systems Messy 160', got None
- hans400@gmail.com: country expected 'FR', got None
- kenji650@gmail.com: country expected 'GB', got None
- sam594@gmail.com: country expected 'FR', got None
- guillaume43@gmail.com: country expected 'FR', got None
- priya754@gmail.com: country expected 'AU', got None
- hans206@gmail.com: country expected 'BR', got None
- david543@gmail.com: country expected 'PH', got None
- elena520@gmail.com: country expected 'JP', got None
- michael391@gmail.com: country expected 'FR', got None
- riley304@gmail.com: country expected 'CA', got None
- riley799@gmail.com: country expected 'AU', got None
- chloe839@gmail.com: country expected 'DE', got None
- morgan358@gmail.com: country expected 'FR', got None
- priya771@gmail.com: country expected 'JP', got None
- seo_guru_76@rankings-fast-marketing.com: intent expected 'spam', got 'pricing'
- mateo800@gmail.com: country expected 'DE', got None
- alex468@gmail.com: country expected 'CA', got None
- mateo809@gmail.com: country expected 'BR', got None
- kenji365@gmail.com: country expected 'PH', got None
- guillaume577@gmail.com: country expected 'CA', got None
- jordan763@gmail.com: country expected 'PH', got None
- taylor991@gmail.com: country expected 'DE', got None
- jordan257@gmail.com: country expected 'FR', got None
- taylor516@gmail.com: company expected 'Echo Cloud Messy 184', got None
- taylor516@gmail.com: country expected 'GB', got None
- chloe456@gmail.com: country expected 'PH', got None
- michael467@gmail.com: country expected 'JP', got None
- priya228@gmail.com: country expected 'FR', got None
- taylor333@gmail.com: company expected 'Apex Dynamics Messy 70', got None
- taylor333@gmail.com: country expected 'GB', got None
- kenji951@gmail.com: country expected 'DE', got None
- david94@gmail.com: country expected 'PH', got None
- morgan657@gmail.com: country expected 'FR', got None
- hacker47@promptsec.org: company expected 'Prompt Security Inc 47', got None
- hacker47@promptsec.org: country expected 'US', got None
- morgan440@gmail.com: country expected 'US', got None
- hacker22@promptsec.org: company expected 'Prompt Security Inc 22', got None
- hacker22@promptsec.org: country expected 'US', got None
- hacker2@promptsec.org: company expected 'Prompt Security Inc 2', got None
- hacker2@promptsec.org: country expected 'US', got None
- chris589@gmail.com: company expected 'Echo Cloud Messy 243', got None
- chris589@gmail.com: country expected 'DE', got None
- taylor242@gmail.com: country expected 'US', got None
- seo_guru_24@rankings-fast-marketing.com: intent expected 'spam', got 'pricing'
- sam113@gmail.com: country expected 'US', got None
- hans255@gmail.com: company expected 'Apex Dynamics Messy 175', got None
- hans255@gmail.com: country expected 'GB', got None
- chloe408@gmail.com: company expected 'BrightPath AI Messy 97', got None
- chloe408@gmail.com: country expected 'GB', got None
- hans779@gmail.com: country expected 'DE', got None
- mateo277@gmail.com: country expected 'DE', got None
- riley897@gmail.com: country expected 'JP', got None
- pat866@gmail.com: country expected 'AU', got None
- hans126@gmail.com: country expected 'PH', got None
- elena301@gmail.com: country expected 'SG', got None
- sarah237@gmail.com: country expected 'GB', got None
- sam537@gmail.com: country expected 'AU', got None
- alex740@gmail.com: country expected 'DE', got None
- jordan328@gmail.com: country expected 'FR', got None
- mateo446@gmail.com: country expected 'FR', got None
- jordan461@gmail.com: country expected 'PH', got None
- david743@gmail.com: country expected 'AU', got None
- priya447@gmail.com: company expected 'Apex Dynamics Messy 22', got None
- priya447@gmail.com: country expected 'JP', got None
- sarah32@gmail.com: country expected 'AU', got None
- chloe942@gmail.com: country expected 'PH', got None
- taylor326@gmail.com: country expected 'AU', got None
- chris320@gmail.com: country expected 'AU', got None
- alex529@gmail.com: country expected 'AU', got None
- jordan324@gmail.com: company expected 'BrightPath AI Messy 155', got None

## Routing misses

- founder148@acme.com: expected enterprise, got smb (territory:APAC+segment:smb+round_robin; country=JP, employees=None, confidence=0.9)
- sarah285@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=339, confidence=0.9)
- guillaume338@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=177, confidence=0.9)
- guillaume87@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2716, confidence=0.9)
- chris178@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1029, confidence=0.9)
- kenji418@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=104, confidence=0.9)
- riley223@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=428, confidence=0.9)
- mateo374@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=320, confidence=0.9)
- michael831@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=361, confidence=0.9)
- pat913@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2408, confidence=0.9)
- guillaume320@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2714, confidence=0.9)
- chris117@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2089, confidence=0.9)
- sam178@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=228, confidence=0.9)
- hans400@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=37, confidence=0.9)
- kenji650@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2707, confidence=0.9)
- sam594@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=87, confidence=0.9)
- guillaume43@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=42, confidence=0.9)
- priya754@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=818, confidence=0.9)
- hans206@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=562, confidence=0.9)
- david543@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2531, confidence=0.9)
- elena520@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1682, confidence=0.9)
- michael391@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2625, confidence=0.9)
- riley304@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=337, confidence=0.9)
- riley799@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1524, confidence=0.9)
- chloe839@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=300, confidence=0.9)
- morgan358@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2297, confidence=0.9)
- priya771@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1672, confidence=0.9)
- mateo800@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=179, confidence=0.9)
- alex468@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=217, confidence=0.9)
- mateo809@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1869, confidence=0.9)
- kenji365@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1483, confidence=0.9)
- guillaume577@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2096, confidence=0.9)
- jordan763@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=731, confidence=0.9)
- taylor991@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=794, confidence=0.9)
- jordan257@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=750, confidence=0.9)
- taylor516@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=25, confidence=0.9)
- chloe456@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2211, confidence=0.9)
- michael467@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1485, confidence=0.9)
- founder57@bigcorp.com: expected review, got enterprise (territory:AMER+segment:enterprise+round_robin; country=None, employees=None, confidence=0.9)
- priya228@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=474, confidence=0.9)
- founder105@bigcorp.com: expected review, got enterprise (territory:AMER+segment:enterprise+round_robin; country=None, employees=None, confidence=0.9)
- taylor333@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=16, confidence=0.9)
- kenji951@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=85, confidence=0.9)
- david94@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2530, confidence=0.9)
- morgan657@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1263, confidence=0.9)
- morgan440@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=521, confidence=0.9)
- chris589@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2496, confidence=0.9)
- taylor242@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=148, confidence=0.9)
- sam113@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=449, confidence=0.9)
- hans255@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2512, confidence=0.9)
- chloe408@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1825, confidence=0.9)
- hans779@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2874, confidence=0.9)
- mateo277@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=424, confidence=0.9)
- riley897@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=985, confidence=0.9)
- pat866@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=2762, confidence=0.9)
- hans126@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=400, confidence=0.9)
- elena301@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=266, confidence=0.9)
- sarah237@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=22, confidence=0.9)
- sam537@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=39, confidence=0.9)
- alex740@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=463, confidence=0.9)
- jordan328@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=636, confidence=0.9)
- mateo446@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=364, confidence=0.9)
- jordan461@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1874, confidence=0.9)
- david743@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=334, confidence=0.9)
- priya447@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=369, confidence=0.9)
- sarah32@gmail.com: expected enterprise, got review (fallback:no_territory; country=None, employees=1868, confidence=0.9)
- chloe942@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=329, confidence=0.9)
- taylor326@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=458, confidence=0.9)
- chris320@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=436, confidence=0.9)
- alex529@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=43, confidence=0.9)
