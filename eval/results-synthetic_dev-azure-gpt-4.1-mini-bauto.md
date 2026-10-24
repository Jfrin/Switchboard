# Evaluation results

Samples evaluated: 686

Models: azure:gpt-4.1-mini | emails per request: auto

Answered by: azure:gpt-4.1-mini (679), refused:content_filter (7)
7 email(s) were refused by every model's content filter and sent to review (fallback:content_filtered); they count in the numbers below.

## Extraction accuracy

- company: 95.5%
- intent: 100.0%
- country: 97.1%

## Routing accuracy: 98.8% (678/686)

Excluding 7 rows from mock-enrichment domains (acme.com, bigcorp.com; label conflicts): 99.9% (678/679)

Scoring: company ignores the ' Messy N' suffix and case; intent treats spam and other as the same bucket.

## Confusion (expected -> got)

- enterprise -> enterprise: 211
- enterprise -> smb: 4
- review -> enterprise: 3
- review -> review: 264
- smb -> review: 1
- smb -> smb: 203

## Extraction misses

- morgan825@gmail.com: country expected 'PH', got None
- elena546@gmail.com: country expected 'DE', got 'SG'
- sales90@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- sales10@b2bleadlist-database.co: company expected None, got 'b2bleadlist-database.co'
- sales2@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database.co'
- sarah700@gmail.com: country expected 'CA', got 'SG'
- sales42@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- hacker17@promptsec.org: company expected 'Prompt Security Inc 17', got None
- hacker17@promptsec.org: country expected 'US', got None
- sales34@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- sales22@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- pat922@gmail.com: country expected 'JP', got 'SG'
- sales126@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- sales122@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- sales26@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- sam217@gmail.com: country expected 'PH', got 'BR'
- sales114@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- sales110@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- hacker27@promptsec.org: company expected 'Prompt Security Inc 27', got None
- hacker27@promptsec.org: country expected 'US', got None
- sales106@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- priya209@gmail.com: country expected 'CA', got 'BR'
- sarah842@gmail.com: country expected 'CA', got 'SG'
- jordan166@gmail.com: country expected 'FR', got 'BR'
- sales154@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- hacker7@promptsec.org: company expected 'Prompt Security Inc 7', got None
- hacker7@promptsec.org: country expected 'US', got None
- sam193@gmail.com: country expected 'PH', got 'SG'
- sales158@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- sales98@b2bleadlist-database.co: company expected None, got 'b2bleadlist-database'
- mateo909@gmail.com: country expected 'US', got 'SG'
- alex290@gmail.com: country expected 'CA', got 'SG'
- sales54@b2bleadlist-database.co: company expected None, got 'b2bleadlist-database.co'
- sales50@b2bleadlist-database.co: company expected None, got 'b2bleadlist-database.co'
- sales6@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- sales86@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- sales134@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- sales18@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- hacker12@promptsec.org: company expected 'Prompt Security Inc 12', got None
- hacker12@promptsec.org: country expected 'US', got None
- hacker52@promptsec.org: company expected 'Prompt Security Inc 52', got None
- hacker52@promptsec.org: country expected 'US', got None
- sales62@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- hacker42@promptsec.org: company expected 'Prompt Security Inc 42', got None
- hacker42@promptsec.org: country expected 'US', got None
- sales14@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'
- taylor792@gmail.com: country expected 'DE', got 'BR'
- priya77@gmail.com: country expected 'AU', got 'SG'
- hacker37@promptsec.org: company expected 'Prompt Security Inc 37', got None
- hacker37@promptsec.org: country expected 'US', got None
- sales142@b2bleadlist-database.co: company expected None, got 'B2BLeadList-Database'

## Routing misses

- morgan825@gmail.com: expected smb, got review (fallback:no_territory; country=None, employees=120, confidence=0.9)
- founder5@bigcorp.com: expected review, got enterprise (territory:AMER+segment:enterprise+round_robin; country=None, employees=None, confidence=0.9)
- founder140@acme.com: expected enterprise, got smb (territory:APAC+segment:smb+round_robin; country=PH, employees=None, confidence=0.9)
- founder125@bigcorp.com: expected review, got enterprise (territory:AMER+segment:enterprise+round_robin; country=None, employees=None, confidence=0.9)
- founder153@bigcorp.com: expected review, got enterprise (territory:AMER+segment:enterprise+round_robin; country=None, employees=None, confidence=0.9)
- founder4@acme.com: expected enterprise, got smb (territory:APAC+segment:smb+round_robin; country=PH, employees=None, confidence=0.9)
- founder16@acme.com: expected enterprise, got smb (territory:AMER+segment:smb+round_robin; country=CA, employees=None, confidence=0.9)
- founder28@acme.com: expected enterprise, got smb (territory:EMEA+segment:smb+round_robin; country=GB, employees=None, confidence=0.9)
