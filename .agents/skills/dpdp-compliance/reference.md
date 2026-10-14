<!-- freshness: tracked · register entry `dpdp-compliance` in .agents/config/freshness.json -->

> ## ⚠️ Freshness gate — read before using this document
>
> **Content date: 26 July 2026. Review interval: 90 days.**
>
> This is a developer reference, not legal advice, and it describes law that is on a **staggered commencement schedule**. A provision appearing here may not yet be in force, and one recorded here as pending may since have commenced. Statutory windows, thresholds, and Rule numbering can change by amendment or corrigendum.
>
> Before shipping compliance-sensitive functionality, making a compliance claim, or answering a legal question:
>
> 1. Check `.agents/config/freshness.json` → entry `dpdp-compliance`. If `last_verified` is more than 90 days old, state that in your response before relying on this content.
> 2. Verify the current text **and commencement status** against authoritative sources: MeitY, the Gazette of India, India Code.
> 3. Route legal representations to qualified counsel. Never certify that a product "is DPDP compliant."
>
> Run `.agents/scripts/check-freshness.sh` to see whether this document is past due.

---

# DPDP Act & DPDP Rules 2025 — Practical Compliance Guide

> **For:** Software products, SaaS applications, ERP/CRM/HRMS/DMS, management systems, web apps and mobile apps operating in India  
> **Law:** Digital Personal Data Protection Act, 2023 (DPDP Act) + Digital Personal Data Protection Rules, 2025  
> **Version:** 1.0  
> **Prepared:** 26 July 2026  
> **Purpose:** Developer/product compliance reference. This is not legal advice.

---

## 1. Official status

The **Digital Personal Data Protection Act, 2023** was enacted on 11 August 2023.

The **Digital Personal Data Protection Rules, 2025** were notified through **G.S.R. 846(E)** in November 2025. MeitY lists the Rules as published on 14 November 2025. A corrigendum, **G.S.R. 892(E)**, was later issued in December 2025 to correct typographical errors.

The Rules use a **staggered commencement model**:

| Provision | Commencement |
|---|---|
| Rules 1, 2 and 17–21 | On publication in the Official Gazette |
| Rule 4 | One year after publication in the Official Gazette |
| Rules 3, 5–16, 22 and 23 | Eighteen months after publication in the Official Gazette |

The DPDP Act itself is also being brought into force in stages.

> **Important:** As of 26 July 2026, many of the operational compliance provisions are still within their statutory transition period. Product teams should nevertheless implement them in advance rather than wait for the effective date.

---

# 2. Core terminology

## 2.1 Personal Data

Any data about an individual who is identifiable by or in relation to that data.

Examples:

- Name
- Email address
- Mobile number
- Employee ID
- Student ID / PRN
- Customer ID
- IP address when linked to a person
- Device identifiers
- Address
- Photograph
- Date of birth
- Location
- Salary
- Attendance
- Documents
- Application history
- Financial details
- Support tickets linked to a person

---

## 2.2 Digital Personal Data

Personal data in digital form, including data:

- collected digitally; or
- collected offline and subsequently digitised.

---

## 2.3 Data Principal

The individual to whom the personal data relates.

Examples:

- Customer
- Employee
- Student
- Vendor representative
- Applicant
- User

For a child, the term includes the parent or lawful guardian where applicable.

---

## 2.4 Data Fiduciary

The person or organisation that determines:

1. **why** personal data is processed; and
2. **how** personal data is processed.

For most SaaS products, the organisation controlling the purpose and means of processing is the Data Fiduciary.

---

## 2.5 Data Processor

A person or organisation processing personal data **on behalf of a Data Fiduciary**.

Examples:

- Cloud hosting provider
- Email delivery provider
- SMS provider
- Support platform
- Analytics processor
- Backup provider
- Payroll processor

A Data Processor should be engaged under a valid contract.

---

## 2.6 Significant Data Fiduciary

The Central Government may notify a Data Fiduciary or class of Data Fiduciaries as a **Significant Data Fiduciary (SDF)** based on factors such as:

- volume and sensitivity of personal data;
- risk to Data Principal rights;
- sovereignty and integrity of India;
- electoral democracy;
- security of the State; and
- public order.

An organisation should not describe itself as an SDF merely because it is large; SDF status is based on Government notification.

---

## 2.7 Consent Manager

A registered entity that enables a Data Principal to give, manage, review or withdraw consent.

A normal SaaS application that collects consent for its own service is **not automatically a Consent Manager**.

---

# 3. Applicability

The DPDP Act applies to processing of digital personal data:

1. inside India where personal data is collected digitally or is digitised later; and
2. outside India where processing is connected with offering goods or services to individuals in India.

The Act does not apply to certain categories, including personal data processed by an individual for personal/domestic purposes and certain data made publicly available in circumstances covered by the Act.

---

# 4. Lawful basis for processing

Personal data may be processed for a lawful purpose based on:

- **consent**; or
- a **certain legitimate use** permitted by the Act.

Do not assume that every business purpose qualifies as a legitimate use.

---

# 5. Consent requirements

Consent must be:

- free;
- specific;
- informed;
- unconditional;
- unambiguous;
- given through clear affirmative action; and
- limited to personal data necessary for the specified purpose.

## Bad example

```text
☑ I agree to all terms, marketing, location tracking,
contacts access and third-party sharing.
```

Problems:

- bundled consent;
- unrelated purposes;
- potentially unnecessary data;
- no granular choice.

## Better example

```text
Purpose: Create and manage your employee account

Data:
- Full name
- Work email
- Mobile number
- Employee ID

[Continue]
```

Separate optional marketing consent:

```text
Receive product updates and promotional emails

[ ] Yes, send me marketing communications
```

---

# 6. Withdrawal of consent

A Data Principal must be able to withdraw consent.

The withdrawal mechanism should be **as easy as giving consent**.

Example:

```text
Settings
  → Privacy
    → Consent Preferences
      → Marketing Emails
        [Disable]
```

After withdrawal:

1. stop the consent-based processing within a reasonable time;
2. instruct relevant Data Processors to stop;
3. retain data only where another law requires or authorises retention.

---

# 7. DPDP Rule 3 — Privacy notice

The notice given by a Data Fiduciary should be independently understandable and written in clear and plain language.

At minimum, the notice should clearly state:

- what personal data is collected;
- the purpose or purposes;
- the relevant goods/services/use enabled by the processing;
- how consent can be withdrawn;
- how Data Principal rights can be exercised; and
- how a complaint can be made.

## Recommended notice structure

```markdown
# Privacy Notice

## Who we are
Company name and product name.

## Personal data we collect
- Name
- Email
- Phone
- Role
- Organisation
- Device/log information

## Why we collect it
### Account creation
Data: Name, email, phone
Purpose: Create and secure your account

### Support
Data: Contact details, ticket content
Purpose: Respond to support requests

## Sharing
List categories of processors/recipients.

## Retention
Describe retention criteria.

## Your rights
- Access
- Correction
- Update
- Erasure
- Grievance
- Nomination where applicable

## Withdraw consent
Explain the mechanism.

## Privacy contact
privacy@example.com
```

---

# 8. Data minimisation

Collect only the data that is necessary for the stated purpose.

## Example

For a project-management SaaS:

### Necessary

- name;
- work email;
- organisation;
- project role.

### Usually unnecessary for basic account creation

- Aadhaar;
- PAN;
- exact GPS coordinates;
- entire phone contact list;
- personal bank details.

Every input field should have a documented purpose.

---

# 9. Purpose limitation

Do not silently reuse personal data for a materially different purpose.

Example:

```text
Collected:
Employee mobile number

Original purpose:
Account verification

New purpose:
Promotional marketing
```

Do not automatically use it for marketing merely because it already exists in the database.

---

# 10. Data accuracy

Where personal data is likely to be:

- used to make a decision affecting the Data Principal; or
- disclosed to another Data Fiduciary,

the Data Fiduciary should ensure completeness, accuracy and consistency.

Recommended product features:

- edit profile;
- correction request;
- admin verification;
- change history;
- document versioning;
- validation rules.

---

# 11. Data Processor contracts

A Data Fiduciary may use a Data Processor only under a valid contract.

Examples:

- AWS / Azure / Google Cloud
- Hostinger
- Firebase
- SendGrid
- Mailgun
- Twilio
- SMS gateways
- CRM integrations
- backup vendors

A Data Processing Agreement should normally cover:

- processing instructions;
- confidentiality;
- security;
- breach notification;
- subprocessors;
- deletion/return of data;
- audit/cooperation;
- applicable retention;
- cross-border processing where relevant.

---

# 12. DPDP Rule 6 — Reasonable security safeguards

The Rules specify minimum types of safeguards.

A management system should implement, as applicable:

## 12.1 Protection of personal data

Use measures such as:

- encryption;
- obfuscation;
- masking;
- tokenisation.

### Recommended

```text
Transport:
HTTPS / TLS

Database:
Encryption at rest where supported

Passwords:
Argon2id or bcrypt hashes

Sensitive identifiers:
Mask in UI/logs where full display is unnecessary

Secrets:
Dedicated secret storage/environment configuration
```

---

## 12.2 Access controls

Implement:

- authentication;
- role-based access control;
- least privilege;
- privileged-admin controls;
- session management;
- MFA for administrators where appropriate;
- account deactivation;
- periodic permission review.

Example roles:

```text
Super Admin
Organisation Admin
Manager
Employee
Auditor
Support Agent
```

Do not rely only on hiding frontend buttons.

Backend APIs must enforce authorisation independently.

---

## 12.3 Logging, monitoring and review

Maintain logs that help detect and investigate unauthorised access.

Recommended events:

```text
LOGIN_SUCCESS
LOGIN_FAILURE
PASSWORD_CHANGE
MFA_CHANGE
USER_CREATED
USER_DISABLED
ROLE_CHANGED
PERMISSION_CHANGED
DATA_EXPORT
PERSONAL_DATA_VIEWED
PERSONAL_DATA_UPDATED
PERSONAL_DATA_DELETED
CONSENT_GIVEN
CONSENT_WITHDRAWN
ADMIN_IMPERSONATION
API_TOKEN_CREATED
API_TOKEN_REVOKED
```

Suggested fields:

```json
{
  "event": "PERSONAL_DATA_UPDATED",
  "actor_id": "U123",
  "subject_id": "U456",
  "organisation_id": "ORG20",
  "timestamp": "ISO-8601 timestamp",
  "source_ip": "masked-or-controlled-value",
  "resource": "employee_profile",
  "request_id": "request-id"
}
```

Avoid putting passwords, OTPs, authentication tokens or unnecessary personal data into logs.

---

## 12.4 Availability and recovery

Maintain reasonable controls for continued processing and recovery.

Recommended:

- automated backups;
- encrypted backups;
- off-site or logically isolated copies;
- restoration testing;
- disaster recovery plan;
- recovery time objective;
- recovery point objective.

A backup that has never been tested is not sufficient operational assurance.

---

## 12.5 Retention supporting breach detection

Rule 6 includes a one-year retention requirement for relevant logs and personal data used for enabling detection, investigation, remediation and continued processing, unless another applicable law requires otherwise.

Retention logic should be designed carefully to reconcile:

- deletion requirements;
- legal retention;
- security-log retention;
- sector-specific requirements.

Do not configure a universal `DELETE ALL USER DATA IMMEDIATELY` action without checking lawful retention requirements.

---

## 12.6 Processor security clauses

Contracts with Data Processors should contain appropriate security provisions.

---

## 12.7 Technical and organisational measures

Security is not only a software feature.

Maintain:

- policies;
- access reviews;
- incident-response procedures;
- employee awareness;
- vendor review;
- secure development process;
- patching;
- vulnerability management.

---

# 13. DPDP Rule 7 — Personal data breach

A **personal data breach** can include unauthorised processing or accidental disclosure, acquisition, sharing, use, alteration, destruction or loss of access that compromises confidentiality, integrity or availability.

Examples:

- database leak;
- exposed backup;
- stolen credentials;
- unauthorised admin access;
- ransomware;
- data sent to the wrong customer;
- public cloud bucket;
- accidental deletion affecting availability.

---

## 13.1 Notify affected Data Principals

On becoming aware of a personal data breach, the Data Fiduciary should notify each affected Data Principal **without delay**, in a concise, clear and plain manner.

The communication should cover:

- nature of breach;
- extent;
- timing;
- likely consequences;
- mitigation measures already implemented/being implemented;
- actions the Data Principal can take;
- business contact for questions.

---

## 13.2 Notify the Data Protection Board

On becoming aware of a breach:

### Without delay

Provide the Board with an initial description including:

- nature;
- extent;
- timing;
- location of occurrence;
- likely impact.

### Within 72 hours of becoming aware

Provide updated/detailed information, including:

- facts and circumstances;
- reasons leading to breach;
- mitigation;
- findings about the person who caused the breach, where available;
- remediation to prevent recurrence;
- report of notifications to affected Data Principals.

The Board may allow a longer period on a written request.

---

## 13.3 Incident response workflow

```text
Security Alert
    ↓
Validate Incident
    ↓
Contain
    ↓
Determine whether personal data is affected
    ↓
Create Breach Record
    ↓
Identify affected Data Principals
    ↓
Notify affected users without delay
    ↓
Initial Board notification
    ↓
Investigate + mitigate
    ↓
Detailed Board update within 72 hours
    ↓
Root-cause analysis
    ↓
Corrective action
    ↓
Close + retain evidence
```

---

## 13.4 Breach record schema

```text
incident_id
detected_at
awareness_at
reported_by
incident_type
affected_systems
affected_data_categories
affected_user_count
timeline
cause
risk
containment
mitigation
user_notification_at
board_initial_notification_at
board_detailed_notification_at
corrective_actions
owner
status
```

Keep **awareness_at** explicitly because statutory notification timing is linked to becoming aware of the breach.

---

# 14. DPDP Rule 8 — Retention and erasure

Personal data should not be kept indefinitely simply because storage is inexpensive.

The Act generally requires erasure when:

- consent is withdrawn; or
- it is reasonable to assume that the specified purpose is no longer being served,

whichever occurs earlier, unless retention is necessary under law.

Data Processors should also be instructed to erase data made available to them where erasure is required.

---

## 14.1 Rule 8 inactivity-based periods for specified large platforms

The Third Schedule sets a three-year period for certain large platforms.

| Category | Threshold | Period |
|---|---:|---|
| E-commerce entity | At least 2 crore registered users in India | 3 years |
| Online gaming intermediary | At least 50 lakh registered users in India | 3 years |
| Social media intermediary | At least 2 crore registered users in India | 3 years |

The period is measured using the criteria set out in the Third Schedule, including the Data Principal's last approach for the specified purpose/exercise of rights and commencement of the Rules.

Certain account access/token-related purposes are excluded from this deemed-purpose rule.

---

## 14.2 Advance erasure notice

For deletion under Rule 8's specified-period mechanism, the Data Principal should be informed at least **48 hours before** the period completes, unless the user logs in/contacts the Data Fiduciary or exercises rights in relation to the processing.

---

## 14.3 Product retention table

Create a retention matrix.

| Data | Purpose | Retention | Trigger | Legal override | Deletion method |
|---|---|---|---|---|---|
| Account profile | Service | While active + approved period | Account closure | Yes/No | Hard delete/anonymise |
| Login logs | Security | Defined policy / legal minimum | Log date | Yes | Secure purge |
| Audit logs | Accountability | Defined policy | Event date | Yes | Secure purge |
| Invoice data | Accounting | Per applicable tax law | Invoice date | Yes | Legal archive |
| Support ticket | Support | Defined period | Ticket closure | Maybe | Delete/anonymise |
| Consent record | Compliance | Evidence period | Consent event | Maybe | Archive/purge |

---

# 15. DPDP Rule 9 — Privacy contact

Every Data Fiduciary should prominently publish on its website/app, and include in responses related to Data Principal rights, business contact information of:

- the Data Protection Officer, where applicable; or
- another person authorised to answer questions about personal-data processing.

Recommended:

```text
Privacy Contact
Email: privacy@example.com
Support URL: https://example.com/privacy/request
```

---

# 16. Children

Under the DPDP Act, a **child is an individual under 18 years of age** unless a lawful notification changes the applicable position for a qualifying Data Fiduciary under the Act.

Before processing a child's personal data, a Data Fiduciary generally must obtain **verifiable parental consent**, subject to exemptions.

---

# 17. DPDP Rule 10 — Verifiable parental consent

The Data Fiduciary should adopt appropriate technical and organisational measures to:

1. obtain verifiable consent of the parent before processing a child's personal data; and
2. use due diligence to confirm that the person presenting as the parent is an identifiable adult.

Verification may rely on:

- reliable identity/age details already available to the Data Fiduciary; or
- identity/age information or an appropriate virtual token issued/made available through an authorised entity, as permitted by the Rules.

Design the system to avoid collecting excessive identity documents merely for age verification.

---

# 18. Children — restricted processing

The Act generally restricts:

- processing likely to cause detrimental effect on a child's well-being;
- tracking of children;
- behavioural monitoring of children; and
- targeted advertising directed at children,

subject to statutory exemptions.

---

# 19. DPDP Rule 12 — child-related exemptions

The Fourth Schedule provides limited exemptions for specified classes/purposes and only under defined conditions.

Examples include processing by or for:

- clinical establishments / healthcare professionals;
- allied healthcare professionals;
- educational institutions;
- childcare providers;
- transport providers for children,

where processing is restricted to specified health, education or safety purposes.

Other specified purposes include:

- duties exercised in the interest of a child under law;
- certain subsidies/benefits/services;
- creation of an email-only user account;
- real-time location for child safety/security;
- preventing access to information/services/advertising likely to harm a child;
- confirming that a Data Principal is not a child.

Do not treat these exemptions as a general permission to track students or children.

---

# 20. Person with disability who has lawful guardian

Where the Act requires consent from a lawful guardian, Rule 11 requires due diligence to verify that the guardian is lawfully appointed under the applicable legal framework.

This should be handled with accessibility and minimum-data principles.

---

# 21. Data Principal rights

A system should provide mechanisms for applicable rights including:

## 21.1 Access

A Data Principal may request information about personal data and processing, including a summary and applicable sharing information under the Act.

Recommended endpoint:

```http
POST /privacy/requests/access
```

---

## 21.2 Correction / completion / updating

Recommended:

```http
POST /privacy/requests/correction
```

Allow users to:

- correct inaccurate data;
- complete incomplete data;
- update outdated data.

---

## 21.3 Erasure

Recommended:

```http
POST /privacy/requests/erasure
```

The workflow must check:

```text
Can erase?
    ↓
No legal retention?
No active purpose requiring data?
No overriding statutory requirement?
    ↓
Erase / anonymise as appropriate
    ↓
Propagate instruction to processors
    ↓
Record completion
```

---

## 21.4 Grievance redressal

Provide a clear grievance mechanism.

Recommended:

```http
POST /privacy/grievances
GET  /privacy/grievances/{id}
```

Rule 14 requires the Data Fiduciary / Consent Manager to prominently publish the period for responding to grievances, which must be **reasonable and not exceed 90 days**.

A product team should set an internal target much shorter than the legal outer limit.

Example:

```text
Internal target: 7 business days
Published maximum: 30 days
Legal rule: published period must not exceed 90 days
```

---

## 21.5 Nomination

A Data Principal may nominate another individual to exercise rights in the event of death or incapacity, in accordance with the Act and applicable terms/process.

Consider:

```text
Settings → Privacy → Nominee
```

---

# 22. DPDP Rule 14 — rights interface

The Data Fiduciary should prominently publish:

- how Data Principals can submit requests; and
- identifiers/details reasonably needed to verify the person making the request.

Do not request excessive verification data.

Recommended privacy centre:

```text
/privacy
/privacy/request
/privacy/access
/privacy/correction
/privacy/delete
/privacy/consent
/privacy/grievance
/privacy/nomination
```

---

# 23. Significant Data Fiduciary obligations

If notified as an SDF, the Act requires additional obligations including:

- appoint a Data Protection Officer;
- DPO must be based in India;
- DPO must be responsible to the Board of Directors or similar governing body;
- appoint an independent data auditor;
- conduct periodic DPIAs;
- conduct periodic audits.

Rule 13 adds that an SDF should, among other requirements:

- conduct a DPIA and audit once every 12 months;
- cause the assessor/auditor to provide a report containing significant observations to the Board;
- perform due diligence on technical measures, including algorithmic software, so that they are not likely to pose a risk to Data Principal rights; and
- comply with notified restrictions on specified personal data/traffic data transfers outside India where applicable.

---

# 24. DPIA template

```markdown
# Data Protection Impact Assessment

## 1. Project
Name:
Owner:
Date:

## 2. Processing
Purpose:
Users:
Data categories:
Sources:
Recipients:
Processors:

## 3. Necessity
Why is each data field required?

## 4. Data flow
Collection → API → Database → Processor → Backup → Deletion

## 5. Risks
- Unauthorised access
- Excess collection
- Secondary use
- Re-identification
- Data leak
- Incorrect data
- Excessive retention
- Children's data risk
- Algorithmic impact

## 6. Controls
- Encryption
- RBAC
- MFA
- Logging
- Retention
- Consent
- Monitoring
- Processor contracts

## 7. Residual risk
Low / Medium / High

## 8. Approval
Privacy:
Security:
Product:
Management:
```

---

# 25. Cross-border transfer

The DPDP Act permits cross-border processing subject to restrictions notified by the Central Government and other applicable Indian laws that may impose a higher level of protection/restriction.

Rule 15 also enables the Central Government to specify requirements relating to making personal data available to:

- a foreign State; or
- a person/entity under the control of a foreign State.

Before selecting a foreign cloud region or processor, check:

- DPDP restrictions;
- sector-specific localisation rules;
- contractual obligations;
- customer requirements.

---

# 26. Research, archiving and statistics

Rule 16 provides an exemption for processing necessary for research, archiving or statistical purposes where the processing follows the standards in the Second Schedule.

The standards focus on principles such as:

- lawful processing;
- purpose limitation;
- data minimisation;
- accuracy;
- retention limitation;
- security; and
- accountability.

Do not label ordinary commercial analytics as "research" merely to avoid compliance.

---

# 27. Consent Manager — Rule 4

Consent Managers require registration with the Data Protection Board and must satisfy the First Schedule.

Key conditions include, among other things:

- company incorporated in India;
- technical, operational and financial capability;
- sound management;
- minimum net worth of **₹2 crore**;
- suitable governance;
- independently certified interoperable platform and relevant controls.

A Consent Manager has specialised obligations such as:

- enabling consent management;
- maintaining consent records;
- providing records to Data Principals;
- maintaining security;
- avoiding conflicts of interest;
- audit mechanisms.

This section does **not** mean every SaaS company needs to register as a Consent Manager.

---

# 28. Record of Processing Activities

Maintain an internal inventory.

| Field | Example |
|---|---|
| Process | Employee onboarding |
| Owner | HR |
| Data Principal | Employee |
| Data | Name, email, mobile, DOB |
| Purpose | Employment onboarding |
| Processing basis | Consent / applicable legitimate use / law |
| Source | Employee |
| Processor | Cloud provider |
| Sharing | Payroll vendor |
| Retention | Defined policy |
| Security | Encryption + RBAC |
| Child data | No |
| Cross-border | Yes/No |
| Deletion workflow | Defined |

---

# 29. Consent audit record

Recommended consent table:

```text
id
data_principal_id
purpose_code
purpose_version
notice_version
consent_status
consented_at
withdrawn_at
source
ip_or_context_if_appropriate
language
evidence_reference
created_at
updated_at
```

Example purpose codes:

```text
ACCOUNT_SERVICE
EMAIL_MARKETING
SMS_MARKETING
LOCATION_FEATURE
ANALYTICS_OPTIONAL
```

Never rely on one global boolean:

```text
consent = true
```

Consent should be linked to a **specific purpose and notice version**.

---

# 30. Privacy request schema

```text
request_id
data_principal_id
request_type
submitted_at
verified_at
status
owner
due_at
completed_at
rejection_reason
legal_retention_reason
processor_actions
evidence
```

Request types:

```text
ACCESS
CORRECTION
UPDATE
ERASURE
CONSENT_WITHDRAWAL
GRIEVANCE
NOMINATION
```

---

# 31. Data inventory

Create a data map before implementing privacy controls.

Example:

```text
users
 ├── name
 ├── email
 ├── mobile
 └── role

employees
 ├── employee_code
 ├── address
 ├── date_of_birth
 └── salary

documents
 ├── document_type
 ├── file_path
 └── owner_id

audit_logs
 ├── actor_id
 ├── action
 ├── resource
 └── timestamp
```

For each field answer:

```text
Why do we collect it?
Who can see it?
Where is it stored?
Who receives it?
How long is it retained?
How can it be corrected?
How will it be deleted?
Does it enter logs/backups?
```

---

# 32. Recommended product architecture

```text
                    ┌────────────────────┐
                    │    Web / Mobile    │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │ Authentication     │
                    │ MFA / Sessions     │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │ Authorisation/RBAC │
                    └─────────┬──────────┘
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
        ┌────────────────┐        ┌────────────────┐
        │ Application API│        │ Privacy Centre │
        └───────┬────────┘        └───────┬────────┘
                │                         │
                ▼                         ▼
        ┌────────────────┐        ┌────────────────┐
        │ Database       │        │ Rights Engine  │
        │ Encryption     │        │ Consent Engine │
        └───────┬────────┘        └────────────────┘
                │
        ┌───────┼───────────────┐
        ▼       ▼               ▼
    Audit     Backup        Processors
    Logs                    / Vendors
```

---

# 33. Multi-tenant SaaS requirements

For a multi-tenant management system:

```text
Tenant A must never access Tenant B data.
```

Implement tenant isolation at backend/database level.

Recommended:

- `tenant_id` scoped queries;
- middleware/policies;
- per-tenant RBAC;
- object-level authorisation;
- tests for cross-tenant access;
- tenant-scoped export/deletion;
- tenant-scoped audit logs.

Bad:

```sql
SELECT * FROM employees WHERE id = ?;
```

Better conceptually:

```sql
SELECT *
FROM employees
WHERE id = ?
  AND tenant_id = ?;
```

Every API that accesses tenant data should enforce tenant context.

---

# 34. API security checklist

- [ ] HTTPS only
- [ ] Authentication required where appropriate
- [ ] RBAC / ABAC
- [ ] Object-level authorisation
- [ ] Tenant isolation
- [ ] Rate limiting
- [ ] Input validation
- [ ] Output filtering
- [ ] No secrets in URLs
- [ ] No passwords/OTP/tokens in logs
- [ ] Secure token expiry
- [ ] Token revocation
- [ ] Audit important actions
- [ ] CORS configured narrowly
- [ ] File upload validation
- [ ] Malware scanning where appropriate
- [ ] Signed/controlled file access
- [ ] Error messages do not expose internals

---

# 35. Database checklist

- [ ] Personal-data inventory maintained
- [ ] Encryption at rest where appropriate
- [ ] Backup encryption
- [ ] Production DB not publicly exposed
- [ ] Strong credentials
- [ ] Least privilege DB users
- [ ] Separate production/non-production
- [ ] No production personal data copied to development without controls
- [ ] Retention jobs configured
- [ ] Secure deletion/anonymisation mechanism
- [ ] Audit history for sensitive admin operations

---

# 36. Frontend checklist

- [ ] Privacy notice accessible
- [ ] Purpose shown before data collection
- [ ] Required and optional fields distinguished
- [ ] Optional consent unchecked by default
- [ ] No deceptive consent design
- [ ] Withdrawal easy to find
- [ ] Data-access request available
- [ ] Correction mechanism available
- [ ] Account/data deletion request available
- [ ] Privacy contact visible
- [ ] Grievance mechanism visible
- [ ] Sensitive information masked
- [ ] Sessions expire appropriately
- [ ] No sensitive personal data in browser console
- [ ] No secrets in frontend bundles

---

# 37. Mobile app checklist

- [ ] Request permissions only when required
- [ ] Explain purpose before sensitive permissions
- [ ] Avoid collecting contact list unless essential
- [ ] Avoid background location unless essential
- [ ] Secure local storage
- [ ] Do not store authentication tokens in plain preferences
- [ ] Certificate/transport security configured
- [ ] Analytics SDKs inventoried
- [ ] Advertising SDKs reviewed
- [ ] Crash logs checked for personal data
- [ ] Account deletion/privacy request workflow available
- [ ] Child-user flows reviewed where relevant

---

# 38. File/document management checklist

For DMS/HRMS/ERP products:

- [ ] Private files not stored in public web directories
- [ ] Authenticated file access
- [ ] Object-level permission check
- [ ] Expiring signed URLs where appropriate
- [ ] File type validation
- [ ] Size limits
- [ ] Malware scanning where appropriate
- [ ] Document access audit
- [ ] Download audit for sensitive documents
- [ ] Retention classification
- [ ] Secure deletion
- [ ] Backups included in retention strategy

---

# 39. Vendor register

Maintain:

| Vendor | Purpose | Data | Location | Contract | Security reviewed | Deletion |
|---|---|---|---|---|---|---|
| Cloud host | Hosting | App/database | Region | Yes | Yes | Defined |
| Email provider | Transactional email | Email/name | Region | Yes | Yes | Defined |
| Analytics | Product analytics | Usage data | Region | Yes | Yes | Defined |

Review vendors before sending them personal data.

---

# 40. Privacy by design checklist

Before releasing a new feature ask:

```text
Does the feature collect personal data?
        ↓
Why?
        ↓
Can we collect less?
        ↓
What is the lawful processing basis?
        ↓
Was the user properly informed?
        ↓
Who can access it?
        ↓
Is it shared?
        ↓
How is it secured?
        ↓
How long is it needed?
        ↓
How can the user exercise rights?
        ↓
How will it be deleted?
```

---

# 41. Employee access

Internal staff access is also a privacy/security concern.

Use:

```text
Support Agent
    ↓
Customer data
    ↓
Only when required
    ↓
Authorised scope
    ↓
Logged access
```

For sensitive support access consider:

- reason-for-access;
- elevated permission request;
- temporary access;
- approval;
- audit logging.

---

# 42. Development and test environments

Avoid:

```text
Production DB dump
        ↓
Developer laptop
```

Prefer:

```text
Production data
        ↓
Anonymisation / synthetic data
        ↓
Test environment
```

Controls:

- separate credentials;
- separate cloud projects;
- restricted developers;
- short retention;
- no real OTP/email/SMS unless required;
- no public staging databases.

---

# 43. Account deletion workflow

Do not implement account deletion as only:

```sql
UPDATE users SET active = 0;
```

Recommended:

```text
Deletion Request
        ↓
Authenticate User
        ↓
Check Legal Retention
        ↓
Disable Account if appropriate
        ↓
Delete/Anonymise Eligible Personal Data
        ↓
Notify/Trigger Processor Deletion
        ↓
Handle Backups according to policy
        ↓
Create Compliance Record
        ↓
Confirm Completion
```

---

# 44. Data export

For an access request, provide information in a clear format.

Possible export:

```json
{
  "profile": {},
  "organisation_memberships": [],
  "activity": [],
  "consents": [],
  "documents": [],
  "sharing_summary": []
}
```

Before export:

- authenticate the requester;
- prevent access to other users' data;
- remove third-party confidential information where legally appropriate;
- use secure delivery;
- make download links expire.

---

# 45. Security incident policy

Minimum internal process:

```text
Detect
Triage
Contain
Preserve evidence
Assess personal-data impact
Escalate
Notify as applicable
Eradicate
Recover
Review
Prevent recurrence
```

Set internal severity:

```text
SEV-1 Critical
SEV-2 High
SEV-3 Medium
SEV-4 Low
```

Personal data breaches should trigger the privacy incident workflow immediately.

---

# 46. Required policy set for a management system

Recommended documentation:

```text
01_Privacy_Policy.md
02_Data_Protection_Policy.md
03_Data_Retention_and_Deletion_Policy.md
04_Information_Security_Policy.md
05_Access_Control_Policy.md
06_Password_and_Authentication_Policy.md
07_Incident_Response_and_Breach_Policy.md
08_Backup_and_Disaster_Recovery_Policy.md
09_Vendor_and_Processor_Management_Policy.md
10_Data_Principal_Rights_Procedure.md
11_Consent_Management_Procedure.md
12_Secure_Development_Policy.md
13_Logging_and_Monitoring_Policy.md
14_Child_Data_Procedure.md
15_Data_Classification_Policy.md
```

---

# 47. Recommended database tables

```text
privacy_notices
consent_purposes
user_consents
privacy_requests
privacy_grievances
privacy_nominations
data_inventory
processing_activities
data_processors
processor_contracts
retention_rules
deletion_jobs
security_incidents
breach_notifications
audit_logs
data_exports
```

---

# 48. Example consent tables

## consent_purposes

```sql
id
code
name
description
is_required
notice_version
active
created_at
updated_at
```

## user_consents

```sql
id
user_id
purpose_id
status
consented_at
withdrawn_at
evidence
created_at
updated_at
```

Status:

```text
GRANTED
WITHDRAWN
EXPIRED
NOT_REQUIRED
```

---

# 49. Example privacy-request workflow

```text
SUBMITTED
    ↓
IDENTITY_VERIFICATION
    ↓
IN_REVIEW
    ↓
PROCESSOR_ACTION_PENDING
    ↓
COMPLETED
```

Alternative:

```text
REJECTED
```

A rejection should have a documented reason.

---

# 50. Role-based privacy controls

Example:

| Permission | Employee | Manager | HR | Admin |
|---|:---:|:---:|:---:|:---:|
| View own profile | ✓ | ✓ | ✓ | ✓ |
| Edit own profile | ✓ | ✓ | ✓ | ✓ |
| View team basic data |  | ✓ | ✓ | ✓ |
| View salary | Own | Limited | ✓ | Controlled |
| Export employees |  |  | Controlled | Controlled |
| Change permissions |  |  |  | ✓ |
| View audit log |  |  | Limited | ✓ |

Never make "Admin" a universal bypass without logging and governance.

---

# 51. Logging rules

## Log

```text
Login
Logout
Failed authentication
Password reset
MFA changes
Role changes
Admin changes
Data exports
Document downloads where appropriate
Privacy requests
Consent changes
Deletion
Integration changes
API key actions
```

## Do not log

```text
Passwords
OTP values
Access tokens
Refresh tokens
Private keys
Full payment card data
Unnecessary identity-document contents
Sensitive request bodies without a clear need
```

---

# 52. Encryption

Recommended baseline:

```text
Browser
  ↓ TLS
API
  ↓ TLS/private network
Database
  → encryption at rest
Backup
  → encryption
```

For highly sensitive fields consider application-level encryption.

Encryption keys must not be hard-coded into source code.

---

# 53. Secrets management

Never commit:

```env
DB_PASSWORD=
JWT_SECRET=
AWS_SECRET=
RAZORPAY_SECRET=
SMTP_PASSWORD=
FIREBASE_PRIVATE_KEY=
```

into public/source repositories.

Use:

- secret stores;
- protected environment variables;
- restricted CI/CD secrets;
- rotation.

---

# 54. Authentication

Recommended:

- secure password hashing;
- password reset with short-lived tokens;
- session expiration;
- login throttling;
- MFA for privileged users;
- device/session revocation;
- secure cookies for web apps.

Cookies:

```text
Secure
HttpOnly
SameSite
```

as applicable.

---

# 55. Authorisation

Do not assume:

```text
Authenticated = authorised
```

Every protected object should be checked.

Example:

```text
User U1 requests /employees/200

System verifies:
1. U1 is authenticated
2. U1 belongs to the tenant
3. employee 200 belongs to the same tenant
4. U1 has permission to view employee 200
```

---

# 56. Backups and deletion

Backups complicate erasure.

Document:

- backup interval;
- retention;
- encryption;
- access;
- restore procedure;
- deletion lifecycle.

Do not make false promises such as:

> "All copies are permanently removed instantly"

unless the architecture truly guarantees it.

Use wording aligned with actual backup lifecycle and legal requirements.

---

# 57. Privacy notice versioning

Store notice versions:

```text
Privacy Notice v1.0
Effective: YYYY-MM-DD

Privacy Notice v1.1
Effective: YYYY-MM-DD
```

Consent evidence should be associated with the relevant notice/purpose version.

---

# 58. Data classification

Example:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
```

Possible mapping:

```text
Marketing website → PUBLIC
Internal procedure → INTERNAL
Customer profile → CONFIDENTIAL
Identity/financial document → RESTRICTED
```

Apply controls based on classification.

---

# 59. Significant changes

When introducing a feature that materially changes processing:

1. update data inventory;
2. update purpose;
3. reassess necessity;
4. review notice;
5. obtain fresh consent where required;
6. review processors;
7. perform security/privacy assessment;
8. update retention;
9. update audit events.

---

# 60. Management dashboard for privacy

Recommended admin module:

```text
Privacy & Compliance
├── Data Inventory
├── Consent Purposes
├── Consent Records
├── Data Requests
├── Grievances
├── Retention
├── Processors
├── Security Incidents
├── Breach Notifications
├── Audit Logs
└── Reports
```

Dashboard metrics:

```text
Open privacy requests
Overdue requests
Consent withdrawals
Deletion jobs pending
High-risk processors
Open incidents
Breach notification timer
Retention jobs failed
```

---

# 61. Compliance ownership

Recommended responsibility model:

| Area | Owner |
|---|---|
| Privacy policy | Legal/Privacy |
| Data inventory | Privacy + Product |
| Access controls | Engineering |
| Security | Security/Engineering |
| Retention | Privacy + Engineering |
| Processor contracts | Legal/Procurement |
| Incident response | Security + Privacy |
| Rights requests | Privacy/Support |
| Product notices | Product + Privacy |
| Audit evidence | Compliance |

For a small organisation, one person may hold multiple roles, but responsibilities should still be documented.

---

# 62. Compliance evidence

Do not only implement controls; retain evidence.

Examples:

```text
Consent records
Notice versions
Processor agreements
Access reviews
Security tests
Backup-restore tests
Privacy requests
Deletion evidence
Training records
Incident records
Breach notifications
Audit reports
DPIAs
Retention jobs
Change approvals
```

---

# 63. Penalties under the DPDP Act

The Act provides for monetary penalties for significant breaches.

The statutory Schedule includes maximum penalties such as:

| Breach category | Maximum |
|---|---:|
| Failure to take reasonable security safeguards | ₹250 crore |
| Failure to notify Board / affected Data Principal of breach | ₹200 crore |
| Failure regarding obligations relating to children | ₹200 crore |
| Failure of Significant Data Fiduciary obligations | ₹150 crore |
| Breach of Data Principal duties | ₹10,000 |
| Other breaches | ₹50 crore |

Penalty assessment depends on statutory factors such as:

- nature, gravity and duration;
- type/nature of affected data;
- repetition;
- gain/loss;
- mitigation;
- proportionality; and
- likely impact of the penalty.

---

# 64. Practical implementation priorities

## Phase 1 — Immediate

- [ ] Data inventory
- [ ] Privacy notice
- [ ] Purpose mapping
- [ ] RBAC
- [ ] HTTPS
- [ ] secure password storage
- [ ] processor/vendor list
- [ ] audit logging
- [ ] backup strategy

## Phase 2 — Privacy controls

- [ ] Consent engine
- [ ] Withdrawal
- [ ] Access request
- [ ] Correction request
- [ ] Erasure request
- [ ] Grievance workflow
- [ ] Privacy contact
- [ ] Retention matrix
- [ ] Automated deletion jobs

## Phase 3 — Security

- [ ] MFA for privileged accounts
- [ ] vulnerability testing
- [ ] penetration testing
- [ ] central monitoring
- [ ] incident response
- [ ] breach workflow
- [ ] restore testing
- [ ] vendor security review

## Phase 4 — Governance

- [ ] processing register
- [ ] processor agreements
- [ ] periodic access review
- [ ] privacy/security training
- [ ] DPIA process
- [ ] audit process
- [ ] compliance evidence repository

---

# 65. Go-live checklist

Do not release until critical items are addressed.

## Legal / Privacy

- [ ] Privacy notice approved
- [ ] Terms available
- [ ] Processing purposes documented
- [ ] Consent wording reviewed
- [ ] Privacy contact published
- [ ] Processor list complete

## Security

- [ ] HTTPS enabled
- [ ] passwords securely hashed
- [ ] RBAC tested
- [ ] tenant isolation tested
- [ ] file permissions tested
- [ ] secrets protected
- [ ] backups operational
- [ ] restore tested
- [ ] critical vulnerabilities resolved

## User rights

- [ ] Access workflow
- [ ] Correction workflow
- [ ] Erasure workflow
- [ ] Consent withdrawal
- [ ] Grievance workflow
- [ ] Nomination workflow where applicable

## Operations

- [ ] Incident contacts
- [ ] breach escalation
- [ ] notification templates
- [ ] retention jobs
- [ ] audit logs
- [ ] monitoring
- [ ] processor contacts

---

# 66. Breach notification template — affected user

```markdown
Subject: Notice regarding a personal data incident

We identified a personal data incident affecting your information.

## What happened
[Concise description]

## Information affected
[Categories of personal data]

## When it happened
[Known timing]

## Possible impact
[Relevant likely consequences]

## What we have done
[Containment and mitigation]

## What you should do
[Recommended safety steps]

## Contact
privacy@example.com
```

Have legal/privacy personnel review actual breach communications before sending.

---

# 67. Privacy request acknowledgement template

```markdown
Subject: We received your privacy request

Request type: [Access / Correction / Erasure / Other]
Reference: [Reference number]
Received: [Date]

We have received your request and will process it through our privacy request procedure.

We may contact you if additional information is reasonably necessary to verify the request.

Privacy Contact
privacy@example.com
```

---

# 68. Internal privacy feature definition

Every PRD for a feature processing personal data should contain:

```markdown
## Privacy

### Personal Data
What data is collected?

### Data Principal
Whose data?

### Purpose
Why is it needed?

### Processing Basis
Consent / applicable legitimate use / legal requirement

### Visibility
Who can view it?

### Processors
Is it sent externally?

### Retention
How long?

### User Rights
How can it be accessed/corrected/deleted?

### Security
Encryption / RBAC / logging

### Children
Does the feature involve users under 18?

### Cross-border
Does data leave India?

### DPIA
Required? Yes/No
```

---

# 69. Data deletion job example

Pseudo-flow:

```text
for each retention_rule:
    find records past retention threshold

    if legal_hold:
        skip

    if active_required_purpose:
        skip

    delete/anonymise eligible data

    propagate processor action where required

    record:
        policy
        records affected
        execution time
        status
```

Deletion jobs should be auditable without retaining unnecessary deleted content.

---

# 70. What DPDP does NOT automatically require

For an ordinary management software product, DPDP does not automatically mean that you must:

- obtain ISO 27001 before launch;
- obtain SOC 2 before launch;
- register every SaaS app with the Data Protection Board;
- become a registered Consent Manager;
- appoint a DPO unless the applicable obligation requires it;
- host every category of personal data only in India.

However, separate sector laws, contracts, Government notifications or customer requirements may impose additional obligations.

---

# 71. Product-level compliance baseline

For a typical B2B management SaaS, the minimum practical target should be:

```text
Privacy Notice
+
Purpose-based Consent
+
RBAC / Tenant Isolation
+
Encryption
+
Audit Logs
+
Retention Rules
+
User Rights Workflow
+
Processor Contracts
+
Breach Response
+
Backups / Recovery
+
Documented Compliance Evidence
```

---

# 72. Official references

Always check the latest official version before treating this guide as final legal interpretation.

## Digital Personal Data Protection Act, 2023

MeitY official PDF:

https://www.meity.gov.in/static/uploads/2024/06/2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf

## Digital Personal Data Protection Rules, 2025

MeitY official page:

https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa

Official Rules PDF listed by MeitY:

https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf

## DPDP enforcement timeline notification

Available from the MeitY DPDP Rules page:

https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa

## India Code

https://www.indiacode.nic.in/

Search for:

```text
Digital Personal Data Protection Act, 2023
```

and review the Rules, notifications and corrigenda listed under the Act.

---

# 73. Corrigendum note

A corrigendum to the DPDP Rules was issued in December 2025.

It corrects drafting/typographical issues including references in:

- Rule 1;
- Rule 13;
- Rule 23;
- First Schedule; and
- Fourth Schedule.

When comparing text from blogs or old copies, prefer the latest official Gazette/MeitY/India Code version.

---

# 74. Compliance review frequency

Recommended:

```text
Monthly
- Privacy requests
- Incidents
- Failed retention/deletion jobs

Quarterly
- User/role access
- Processors
- High-risk integrations

Every 6–12 months
- Data inventory
- Privacy notice
- Retention schedule
- Security controls
- Incident plan
- Product data flows

Before major releases
- Privacy review
- Security review
- Processor review
- DPIA where appropriate
```

For Significant Data Fiduciaries, statutory Rule 13 requirements apply in addition to internal schedules.

---

# 75. Final engineering rule

For every personal-data field, the team should be able to answer:

```text
1. What is it?
2. Whose data is it?
3. Why do we collect it?
4. What permits us to process it?
5. Did we inform the person properly?
6. Who can access it?
7. Where is it stored?
8. Who is it shared with?
9. How is it protected?
10. How long is it retained?
11. How can it be corrected?
12. How can it be deleted?
13. What happens after consent withdrawal?
14. What happens if it is breached?
15. What evidence proves our compliance?
```

If the team cannot answer these questions, the feature is not privacy-ready.

---

## Disclaimer

This document is a practical product and engineering guide based on the Digital Personal Data Protection Act, 2023 and the Digital Personal Data Protection Rules, 2025 as reviewed on 26 July 2026.

It is not a substitute for legal advice. Requirements may vary based on:

- organisation;
- industry;
- type of data;
- Government notifications;
- sector regulation;
- contracts;
- court decisions; and
- future amendments.

For production compliance, legal/privacy counsel should verify the latest Gazette notifications and sector-specific requirements.
