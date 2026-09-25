# Finding: Unauthenticated AEM QueryBuilder servlet exposed on www.uc.edu

- **Severity:** Medium (potentially High — depends on which JCR paths anonymous can reach; see below)
- **Asset:** https://www.uc.edu  (Adobe Experience Manager, publish instance, behind Fastly/Dispatcher)
- **Class:** Security Misconfiguration / Information Exposure (OWASP A05:2021)
- **Date found:** 2026-07-13
- **Authorization ref:** <PASTE screenshot/link of supervisor approval + confirmed scope = www.uc.edu>

## Summary
The Adobe AEM QueryBuilder JSON servlet is reachable without authentication at
`/bin/querybuilder.json`. It returns structured repository (JCR) data and a total
node count, allowing an unauthenticated user to enumerate site content and — if
ACLs are weak — potentially search for sensitive nodes.

## Steps to reproduce
1. Request (GET), no auth:
   `https://www.uc.edu/bin/querybuilder.json?path=/content&type=cq:Page&p.limit=1&p.hits=selective&p.properties=jcr:path`
2. Response (minimal proof, limited to 1 hit on purpose):
   `{"success":true,"results":1,"total":42338,"more":false,"offset":0,"hits":[{"jcr:path":"/content/hoxworth/about/mission"}]}`
3. `total:42338` confirms the servlet will enumerate the whole content tree via paging (p.offset).

NOTE: Confirmation was deliberately limited to a single non-sensitive public page
path. No bulk export was performed, and no user/PII paths (e.g. /home/users) were
queried — that is a remediation-time decision, not something to prove by exfiltration.

## Impact
- Unauthenticated enumeration of repository structure (paths, page metadata).
- QueryBuilder is a common pivot: attackers use it to search for nodes/properties
  that leak data (author info, unpublished content, credentials-in-properties,
  profile nodes) when repository ACLs are permissive.
- At minimum this is reconnaissance value for an attacker; severity rises sharply
  if any sensitive tree is anonymously readable.

## Remediation (the fix)
Root cause: Dispatcher does not deny the QueryBuilder JSON/feed endpoints, and/or
the servlet is not access-restricted on publish.

Primary fix — deny at the Dispatcher (filters section of the vhost/dispatcher config):
```
/0100 { /type "deny"  /url "/bin/querybuilder.json*" }
/0101 { /type "deny"  /url "/bin/querybuilder.feed*" }
```
Defense in depth:
- Confirm anonymous (`anonymous` / `everyone`) has NO read on sensitive trees
  (`/home/users`, `/home/groups`, any app-specific PII nodes).
- Review the Dispatcher filter allow-list model (default-deny, only permit needed
  paths/selectors/extensions) per Adobe's Dispatcher Security Checklist.
- Confirm the same on all other AEM publish hosts in scope, not just www.

How to verify the fix: after change, `/bin/querybuilder.json?...` should return
403/404 from the internet.

## Notes
- Detected via AEM fingerprint (robots.txt /libs /apps /bin, x-vhost: publish, Fastly cache headers).
- Other classic AEM endpoints checked and correctly locked down: /crx/de (404),
  /crx/packmgr (403), /system/console (403), /content.infinity.json (404),
  gql.servlet (404). Good hardening overall — this one slipped through.
