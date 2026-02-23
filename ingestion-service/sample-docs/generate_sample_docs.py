#!/usr/bin/env python3
"""
Generate 100+ realistic sample documents across categories.

Since we can't include 1,500 actual client PDFs, this script generates
realistic markdown/text documents that demonstrate the full ingestion
pipeline — varied lengths, categories, dates, and structures.

Categories:
  - Company policies (HR, IT, finance, travel)
  - Product documentation (features, specs, troubleshooting)
  - Meeting notes (quarterly reviews, project updates)
  - Knowledge base articles (how-tos, FAQs)

Usage:
    python generate_sample_docs.py           # Generate to ./generated/
    python generate_sample_docs.py --count 200  # Generate 200 docs
"""

import argparse
import random
from pathlib import Path

# ── Content Templates ──────────────────────────────────────

HR_POLICIES = [
    {
        "title": "Employee Leave Policy",
        "content": """# Employee Leave Policy

## Overview
This policy outlines the types of leave available to all full-time employees and the procedures for requesting time off. Compliance with this policy is mandatory for all staff members.

## Types of Leave

### Annual Leave
All full-time employees are entitled to {days} days of paid annual leave per calendar year. Leave accrues on a monthly basis at a rate of {monthly:.1f} days per month. Unused leave may be carried over to the following year, up to a maximum of {carryover} days. Any leave beyond the carryover limit will be forfeited unless approved by the department head.

### Sick Leave
Employees receive {sick_days} days of paid sick leave per year. A medical certificate is required for absences exceeding {cert_days} consecutive working days. Chronic illness accommodations are available through the HR department. Employees must notify their direct supervisor before 9:00 AM on the first day of absence.

### Parental Leave
Primary caregivers are entitled to {parental_weeks} weeks of paid parental leave. Secondary caregivers receive {secondary_weeks} weeks of paid leave. Leave must commence within {start_months} months of the birth or adoption date. Part-time return arrangements can be negotiated with your department head.

### Bereavement Leave
Employees may take up to {bereavement_days} days of paid bereavement leave for the death of an immediate family member. Immediate family includes spouse, children, parents, siblings, grandparents, and in-laws. Additional unpaid leave may be granted at the manager's discretion.

## Request Procedure
1. Submit leave requests through the HR portal at least {notice_days} business days in advance
2. Requests are reviewed by your direct supervisor within 2 business days
3. Approved requests generate an automatic calendar block
4. Emergency leave requests should be communicated directly to your supervisor

## Policy Violations
Failure to follow proper leave request procedures may result in the absence being recorded as unpaid leave. Repeated violations may lead to disciplinary action as outlined in the Employee Handbook Section 7.3.
""",
    },
    {
        "title": "Remote Work Policy",
        "content": """# Remote Work Policy

## Eligibility
Employees who have completed their {probation_months}-month probation period may apply for remote work arrangements. Eligibility is determined by role requirements, performance history, and team needs.

## Work-From-Home Guidelines

### Equipment
The company provides the following equipment for remote workers:
- Laptop with company-standard configuration
- External monitor (upon request)
- Keyboard and mouse set
- Headset for video conferencing

Employees are responsible for maintaining a reliable internet connection with a minimum speed of {min_speed} Mbps download and {min_upload} Mbps upload.

### Working Hours
Remote employees must be available during core hours ({core_start} to {core_end}). Flexible scheduling outside core hours is permitted with manager approval. All meetings should be attended via video with cameras on unless otherwise specified.

### Security Requirements
- All work must be performed on company-provided devices
- VPN connection is required when accessing internal systems
- Screen lock must be enabled with a maximum {lock_timeout}-minute timeout
- Work should not be performed in public spaces where screens are visible to others
- Confidential documents must not be printed at home

### Communication
- Respond to messages within {response_time} minutes during core hours
- Update your status in Slack/Teams when stepping away
- Attend all scheduled team meetings
- Provide daily standup updates by {standup_time}

## Hybrid Schedule
Employees on hybrid arrangements must be in-office a minimum of {office_days} days per week. In-office days should be coordinated with your team to maximize collaboration.

## Performance Monitoring
Remote work privileges may be revoked if performance metrics decline below acceptable thresholds. Quarterly reviews will assess remote work effectiveness.
""",
    },
    {
        "title": "Code of Conduct",
        "content": """# Code of Conduct

## Purpose
This Code of Conduct establishes the standards of behavior expected from all employees, contractors, and representatives of the organization. It applies to all work-related activities, including those conducted remotely.

## Professional Behavior
All employees are expected to:
- Treat colleagues, clients, and partners with respect and dignity
- Maintain professional communication in all channels
- Support an inclusive and diverse workplace
- Report concerns through appropriate channels without fear of retaliation

## Anti-Discrimination Policy
The company prohibits discrimination based on race, color, religion, sex, national origin, age, disability, genetic information, sexual orientation, gender identity, or any other protected characteristic. This applies to hiring, promotion, compensation, training, and all other aspects of employment.

## Conflict of Interest
Employees must disclose any actual or potential conflicts of interest to their supervisor and the Ethics Committee. This includes:
- Financial interests in competitors or suppliers
- Outside employment that may interfere with job duties
- Personal relationships with subordinates or vendors
- Gifts or hospitality exceeding ${gift_limit} in value

## Confidentiality
All proprietary information, trade secrets, and client data must be handled in accordance with the Data Classification Policy. Unauthorized disclosure of confidential information is grounds for immediate termination and may result in legal action.

## Reporting Violations
Employees who witness or suspect violations of this Code should report them through:
1. Direct supervisor (if appropriate)
2. HR department
3. Anonymous ethics hotline: {hotline_number}
4. Online reporting portal: ethics.company.com

All reports are investigated confidentially. Retaliation against good-faith reporters is strictly prohibited and will result in disciplinary action.

## Consequences
Violations of this Code may result in disciplinary action ranging from a written warning to termination, depending on the severity and frequency of the violation.
""",
    },
    {
        "title": "Performance Review Process",
        "content": """# Performance Review Process

## Overview
Performance reviews are conducted {review_frequency} to assess employee contributions, set goals, and identify development opportunities. The process is designed to be transparent, fair, and growth-oriented.

## Review Timeline
- **Self-Assessment**: Due by the {self_due}th of the review month
- **Manager Assessment**: Completed by the {manager_due}th
- **Peer Feedback**: Collected during the first {peer_days} days of the review period
- **Calibration Meeting**: Department heads align on ratings during week {calibration_week}
- **Review Meeting**: Scheduled between manager and employee by month-end

## Rating Scale
1. **Exceptional** — Consistently exceeds expectations; demonstrates leadership beyond role
2. **Exceeds Expectations** — Regularly delivers above what is required
3. **Meets Expectations** — Consistently delivers solid, reliable work
4. **Needs Improvement** — Performance gaps exist that require a development plan
5. **Unsatisfactory** — Significant performance issues; may lead to a PIP

## Goal Setting
Each employee sets {goal_count} goals per review period:
- At least {business_goals} must be directly tied to business objectives
- At least {development_goals} must focus on personal/professional development
- Goals must follow the SMART framework (Specific, Measurable, Achievable, Relevant, Time-bound)

## Compensation Impact
Performance ratings directly influence:
- Annual merit increases (typically {merit_min}% to {merit_max}%)
- Bonus calculations
- Promotion eligibility
- Stock option grants (for eligible roles)

## Appeals Process
Employees who disagree with their rating may submit a written appeal to HR within {appeal_days} business days of receiving their review. Appeals are reviewed by a committee of senior leaders.
""",
    },
    {
        "title": "Onboarding Guide for New Employees",
        "content": """# Onboarding Guide for New Employees

## Welcome
Welcome to the team! This guide covers everything you need to know during your first {onboarding_weeks} weeks. Your onboarding buddy ({buddy_name}) is your go-to person for any questions not covered here.

## First Day Checklist
- [ ] Collect your laptop and access badge from IT (Room {it_room})
- [ ] Complete mandatory security training module (takes ~{security_training_mins} minutes)
- [ ] Set up your email, Slack, and calendar
- [ ] Review and sign the Employee Handbook acknowledgment
- [ ] Schedule a 1:1 with your direct manager
- [ ] Join the #new-hires Slack channel

## First Week
- Attend the New Hire Orientation session ({orientation_day})
- Complete all required compliance training modules
- Set up your development environment (see IT Setup Guide)
- Meet with your onboarding buddy for a team overview
- Shadow at least {shadow_meetings} team meetings

## First Month
- Complete your 30-day onboarding plan (provided by your manager)
- Deliver your first small project or contribution
- Attend at least one company social event
- Complete the benefits enrollment process
- Schedule introductory meetings with key cross-functional partners

## Key Systems
| System | URL | Purpose |
|--------|-----|---------|
| HR Portal | hr.company.com | Leave, benefits, reviews |
| Confluence | wiki.company.com | Internal documentation |
| Jira | jira.company.com | Project tracking |
| Slack | company.slack.com | Communication |
| GitHub | github.com/company | Source code |

## Benefits Enrollment
You have {benefits_deadline} days from your start date to enroll in benefits. Key options include:
- Health insurance (3 plan options)
- Dental and vision coverage
- 401(k) with {match_percent}% company match
- Life insurance (1x salary, free)
- Employee assistance program (EAP)

## Questions?
Contact HR at hr@company.com or your onboarding buddy. We're here to help!
""",
    },
]

IT_POLICIES = [
    {
        "title": "Information Security Policy",
        "content": """# Information Security Policy

## Purpose
This policy establishes the security standards for protecting company information assets, systems, and data. All employees, contractors, and third-party users must comply with these requirements.

## Password Requirements
- Minimum {min_length} characters
- Must include uppercase, lowercase, numbers, and special characters
- Passwords expire every {expiry_days} days
- Cannot reuse the last {history_count} passwords
- Multi-factor authentication (MFA) is required for all systems

## Data Classification
### Level 1 — Public
Information approved for public release. No special handling required.

### Level 2 — Internal
General business information. Share only with employees and authorized contractors. Do not post externally.

### Level 3 — Confidential
Sensitive business data including financial reports, strategic plans, and employee records. Access restricted to authorized personnel only. Must be encrypted in transit and at rest.

### Level 4 — Restricted
Highly sensitive data including PII, payment card data, and trade secrets. Requires explicit authorization for each access. Full audit logging required. Breach notification within {breach_hours} hours.

## Acceptable Use
Company IT resources may be used for business purposes. Limited personal use is permitted provided it does not:
- Interfere with work duties
- Consume excessive bandwidth
- Violate any law or company policy
- Introduce security risks

## Incident Reporting
Report all security incidents immediately to:
- Security Operations: security@company.com
- Emergency hotline: {security_phone}
- In Slack: #security-incidents

## Device Management
- All company devices must be enrolled in the MDM system
- Automatic OS and security updates must remain enabled
- Lost or stolen devices must be reported within {report_hours} hours
- Personal devices accessing company data must comply with BYOD policy
""",
    },
    {
        "title": "VPN and Remote Access Policy",
        "content": """# VPN and Remote Access Policy

## Scope
This policy governs all remote connections to the company network. It applies to employees, contractors, and vendors requiring access to internal systems from outside the corporate network.

## VPN Requirements
All remote access to internal systems must use the company-approved VPN client. The VPN uses {vpn_protocol} encryption with {key_length}-bit keys. Split tunneling is disabled to ensure all traffic routes through the corporate network.

## Connection Procedures
1. Install the approved VPN client from the IT portal
2. Configure using your corporate credentials
3. Complete MFA verification on each connection
4. VPN sessions automatically disconnect after {timeout_minutes} minutes of inactivity
5. Maximum concurrent sessions per user: {max_sessions}

## Access Levels
| Level | Description | Approval Required |
|-------|-------------|-------------------|
| Basic | Email, calendar, Slack | Automatic for all employees |
| Standard | Basic + internal apps, wikis | Manager approval |
| Developer | Standard + code repos, CI/CD | Manager + IT approval |
| Admin | Full network access | VP + CISO approval |

## Prohibited Activities
While connected to the VPN:
- Do not download unauthorized software
- Do not share your VPN credentials
- Do not leave your session unattended without locking your screen
- Do not connect from public WiFi without additional precautions
- Do not use VPN for personal browsing

## Monitoring
All VPN connections are logged and monitored for anomalous activity. Logs include connection time, duration, source IP, and bandwidth usage. Anomalies are flagged for security review.

## Troubleshooting
Common issues and resolutions:
1. **Connection timeout**: Check your internet connection; try a different network
2. **MFA failure**: Ensure your authenticator app time is synced
3. **Slow performance**: Disconnect and reconnect to get assigned to a closer gateway
4. **Access denied**: Verify your access level with IT support

Contact IT Help Desk: helpdesk@company.com or ext. {helpdesk_ext}
""",
    },
    {
        "title": "Software Development Standards",
        "content": """# Software Development Standards

## Purpose
These standards ensure code quality, security, and maintainability across all development teams. They apply to all code written for production systems.

## Version Control
- All code must be stored in Git repositories
- The default branch is `main` — direct commits are prohibited
- All changes go through pull requests with at least {min_reviewers} reviewer(s)
- Branch naming: `feature/TICKET-description`, `bugfix/TICKET-description`, `hotfix/TICKET-description`
- Commits must reference a ticket number

## Code Review Standards
Every pull request must:
- Pass all automated tests (unit, integration, linting)
- Include relevant test cases for new functionality (minimum {coverage_threshold}% coverage)
- Have a clear description of changes and their purpose
- Be reviewed within {review_sla} business hours
- Address all reviewer comments before merging

## Testing Requirements
| Test Type | Minimum Coverage | Run Frequency |
|-----------|-----------------|---------------|
| Unit Tests | {unit_coverage}% | Every commit |
| Integration Tests | {integration_coverage}% | Every PR |
| E2E Tests | Critical paths | Nightly |
| Performance Tests | Key endpoints | Weekly |
| Security Scans | All code | Every PR |

## Deployment Process
1. Code merged to `main` triggers CI/CD pipeline
2. Automated tests run in staging environment
3. QA team conducts manual verification for major releases
4. Production deployment via blue-green strategy
5. Automated rollback if error rate exceeds {error_threshold}%
6. Post-deployment monitoring for {monitoring_hours} hours

## Documentation
- All public APIs must have OpenAPI/Swagger documentation
- Complex business logic requires inline comments explaining "why"
- Architecture decisions documented in ADRs (Architecture Decision Records)
- README.md required for every repository

## Security Practices
- Never commit secrets, API keys, or credentials to version control
- Use environment variables or secrets management (Vault/AWS Secrets Manager)
- Input validation required on all external-facing endpoints
- SQL queries must use parameterized statements — no string concatenation
- Dependencies scanned weekly for known vulnerabilities
""",
    },
]

FINANCE_POLICIES = [
    {
        "title": "Expense Reimbursement Policy",
        "content": """# Expense Reimbursement Policy

## Scope
This policy covers all business-related expenses incurred by employees. Expenses must be necessary, reasonable, and directly related to company business.

## Expense Categories and Limits

### Travel
- Airfare: Economy class for flights under {flight_hours} hours; business class for longer flights requires VP approval
- Hotels: Maximum ${hotel_max}/night in standard markets; ${hotel_max_premium}/night in premium markets (NYC, SF, London)
- Meals while traveling: ${meal_limit}/day inclusive of tips
- Ground transportation: Taxi/rideshare preferred; rental car requires pre-approval

### Client Entertainment
- Meals with clients: ${client_meal_limit} per person maximum
- Event tickets: Up to ${event_limit} per person with director approval
- All client entertainment requires documentation of business purpose and attendees

### Office Supplies
- Individual purchases under ${supply_limit}: Manager approval
- Purchases over ${supply_limit}: Procurement process required
- Recurring subscriptions require annual budget allocation

## Submission Process
1. Submit expenses within {submit_days} days of incurring them
2. Attach original receipts for all expenses over ${receipt_threshold}
3. Include business justification for all expenses
4. Expenses are reviewed by your manager within {approval_days} business days
5. Approved expenses are reimbursed in the next payroll cycle

## Non-Reimbursable Expenses
- Personal entertainment or personal travel extensions
- Fines, penalties, or late fees
- Clothing (unless specifically required for the role)
- Home office furniture (covered under separate Remote Work Equipment policy)
- Alcohol (except when part of approved client entertainment)

## Audit
The finance team audits {audit_percent}% of expense reports monthly. Fraudulent claims will result in termination and potential legal action.
""",
    },
    {
        "title": "Procurement Policy",
        "content": """# Procurement Policy

## Purpose
This policy establishes the procedures for purchasing goods and services to ensure cost-effectiveness, transparency, and compliance with company standards.

## Approval Thresholds
| Amount | Approval Required |
|--------|-------------------|
| Under ${threshold_1:,} | Manager |
| ${threshold_1:,} — ${threshold_2:,} | Director |
| ${threshold_2:,} — ${threshold_3:,} | VP + Procurement |
| Over ${threshold_3:,} | CFO |

## Vendor Selection
For purchases over ${competitive_bid:,}:
- Minimum {min_bids} competitive bids required
- Bids evaluated on: price ({price_weight}%), quality ({quality_weight}%), support ({support_weight}%)
- Preferred vendor list maintained by Procurement team
- New vendors require security assessment and financial stability review

## Purchase Order Process
1. Submit purchase request in the procurement system
2. Attach vendor quotes and business justification
3. Approval routed based on amount thresholds
4. Purchase order issued upon approval
5. Goods/services received and verified
6. Invoice matched to PO and processed for payment

## Contract Requirements
All contracts over ${contract_threshold:,} must be reviewed by Legal. Key terms to negotiate:
- Payment terms: Net {payment_terms} preferred
- Liability caps and indemnification
- Data protection and security requirements
- Termination clause with {notice_period}-day notice
- SLA commitments with penalty clauses

## Emergency Purchases
In urgent situations, purchases up to ${emergency_limit:,} may be approved by any VP. Retroactive PO must be submitted within {retro_days} business days. Emergency purchase usage is tracked and reported monthly.
""",
    },
]

TRAVEL_POLICIES = [
    {
        "title": "Business Travel Policy",
        "content": """# Business Travel Policy

## Booking Procedures
All business travel must be booked through the company travel portal (travel.company.com) or the designated travel agency. Personal bookings are not reimbursable unless the portal/agency was unavailable and prior approval was obtained.

## Air Travel
- Book at least {advance_days} days in advance when possible
- Economy class is standard for all domestic flights
- Business class permitted for international flights over {international_hours} hours
- Preferred airlines: {airlines}
- Loyalty program points earned during business travel belong to the employee

## Ground Transportation
- Airport transfers: Taxi or rideshare (economy tier)
- Local transportation: Public transit preferred; rideshare for efficiency
- Rental cars: Compact/intermediate class; upgrades require justification
- Personal vehicle: Reimbursed at ${mileage_rate}/mile (IRS standard rate)

## Accommodation
- Book through the company portal for negotiated rates
- Standard room in a business-class hotel
- Room rate limits:
  - Domestic standard: ${domestic_rate}/night
  - Domestic premium markets: ${premium_rate}/night
  - International: Market-dependent, approved case-by-case

## Per Diem
Instead of itemizing meal expenses while traveling, employees may opt for the per diem allowance:
- Domestic: ${domestic_per_diem}/day
- International: Varies by country (see travel portal)
- Per diem covers meals and incidental expenses only
- Receipts not required when using per diem

## Travel Safety
- Register all international trips with the security team
- Download the company safety app before traveling
- Keep copies of important documents (passport, insurance) in the secure portal
- In case of emergency abroad: Call {emergency_number} (24/7)

## Cancellations and Changes
- Cancel bookings as soon as trip plans change
- Non-refundable bookings require manager pre-approval
- Unused tickets/credits must be reported to the travel coordinator
""",
    },
]

PRODUCT_DOCS = [
    {
        "title": "API Reference — Authentication",
        "content": """# API Reference — Authentication

## Overview
All API requests must be authenticated using OAuth 2.0 bearer tokens. This document covers the authentication flow, token management, and common error handling.

## Authentication Flow

### 1. Obtain Client Credentials
Register your application in the Developer Portal to receive:
- `client_id`: Your application's unique identifier
- `client_secret`: Your application's secret key (keep this secure!)

### 2. Request an Access Token
```
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=YOUR_CLIENT_ID
&client_secret=YOUR_CLIENT_SECRET
&scope=read write
```

### 3. Use the Token
Include the token in the Authorization header:
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

## Token Lifecycle
- Access tokens expire after {token_expiry} minutes
- Refresh tokens are valid for {refresh_expiry} days
- Tokens can be revoked via `POST /oauth/revoke`
- Rate limit: {rate_limit} requests per minute per token

## Scopes
| Scope | Description |
|-------|-------------|
| `read` | Read-only access to resources |
| `write` | Create and update resources |
| `delete` | Delete resources |
| `admin` | Full administrative access |

## Error Responses
| Status | Code | Description |
|--------|------|-------------|
| 401 | `invalid_token` | Token is expired or malformed |
| 401 | `insufficient_scope` | Token doesn't have required scope |
| 429 | `rate_limited` | Too many requests; retry after {retry_seconds}s |
| 403 | `forbidden` | Account doesn't have access to this resource |

## Best Practices
- Store tokens securely (never in client-side code or version control)
- Implement token refresh before expiry to avoid service interruption
- Use the minimum required scopes for each integration
- Rotate client secrets every {rotation_days} days
- Monitor token usage via the Developer Portal dashboard
""",
    },
    {
        "title": "Product Feature — Search Engine",
        "content": """# Product Feature — Search Engine

## Overview
The search engine provides full-text search across all indexed content with support for filters, facets, and relevance ranking. It processes approximately {daily_queries:,} queries per day with a P95 latency of {p95_latency}ms.

## Search Syntax

### Basic Search
Simple keyword search matches against all indexed fields:
```
GET /search?q=quarterly+revenue+report
```

### Phrase Search
Use quotes for exact phrase matching:
```
GET /search?q="quarterly revenue report"
```

### Field-Specific Search
Target specific fields using the `field:value` syntax:
```
GET /search?q=author:smith+type:report
```

### Boolean Operators
Combine terms with AND, OR, NOT:
```
GET /search?q=(revenue OR profit) AND Q4 NOT draft
```

## Filters
| Filter | Type | Example |
|--------|------|---------|
| `date_from` | ISO date | `2024-01-01` |
| `date_to` | ISO date | `2024-12-31` |
| `category` | String | `finance,hr` |
| `author` | String | `john.smith` |
| `status` | Enum | `published,draft,archived` |

## Relevance Ranking
Results are ranked using a combination of:
1. **TF-IDF score** ({tfidf_weight}% weight) — how well the query terms match
2. **Recency boost** ({recency_weight}% weight) — newer documents rank higher
3. **Popularity signal** ({popularity_weight}% weight) — frequently accessed documents
4. **Exact match bonus** — phrase matches get a {exact_boost}x multiplier

## Pagination
- Default page size: {page_size} results
- Maximum page size: {max_page_size} results
- Use `offset` and `limit` for pagination
- Total result count returned in response headers

## Performance
- Average query latency: {avg_latency}ms
- P95 latency: {p95_latency}ms
- Index size: {index_size_gb}GB across {index_docs:,} documents
- Reindexing frequency: Every {reindex_hours} hours
""",
    },
    {
        "title": "Troubleshooting — Common API Errors",
        "content": """# Troubleshooting — Common API Errors

## Error Response Format
All API errors follow a consistent format:
```json
{{
    "error": {{
        "code": "ERROR_CODE",
        "message": "Human-readable description",
        "details": {{}},
        "request_id": "req_abc123"
    }}
}}
```

Always include the `request_id` when contacting support — it helps us trace the exact request through our systems.

## Common Errors

### 400 Bad Request
**Cause**: Invalid request parameters or malformed request body.

**Common fixes**:
- Check that required fields are present
- Verify data types match the API schema
- Ensure dates are in ISO 8601 format
- Check string length limits (max {max_string_length} characters for most fields)

### 401 Unauthorized
**Cause**: Missing, expired, or invalid authentication token.

**Common fixes**:
- Verify your token hasn't expired (tokens last {token_minutes} minutes)
- Check for typos in the Authorization header format
- Ensure you're using `Bearer` (capital B) as the auth scheme
- Try refreshing your token

### 404 Not Found
**Cause**: The requested resource doesn't exist.

**Common fixes**:
- Verify the resource ID is correct
- Check if the resource was recently deleted
- Ensure you're calling the correct API version (`/v{api_version}/...`)
- Confirm your account has access to the resource's workspace

### 429 Rate Limited
**Cause**: Too many requests in a short period.

**Current limits**:
- Standard tier: {standard_rpm} requests/minute
- Professional tier: {pro_rpm} requests/minute
- Enterprise tier: {enterprise_rpm} requests/minute

**How to handle**:
- Check the `Retry-After` header for when to retry
- Implement exponential backoff in your client
- Consider caching responses that don't change frequently
- Upgrade your plan if you consistently hit limits

### 500 Internal Server Error
**Cause**: An unexpected error on our side.

**What to do**:
1. Retry the request after {retry_wait} seconds
2. If the error persists, check our status page: status.company.com
3. Contact support with the `request_id` from the error response

## Debugging Tips
- Use the `X-Debug: true` header in non-production environments for verbose errors
- Check the API changelog for recent breaking changes
- Test with the API sandbox before deploying to production
- Enable webhook delivery logs for async operations
""",
    },
]

MEETING_NOTES = [
    {
        "title": "Q{quarter} {year} Business Review",
        "content": """# Q{quarter} {year} Business Review — Meeting Notes

**Date**: {date}
**Attendees**: {attendees}
**Duration**: {duration} minutes

## Revenue Summary
- Total revenue: ${revenue:,.0f} ({revenue_growth:+.1f}% vs. previous quarter)
- Recurring revenue: ${arr:,.0f} ({arr_pct:.0f}% of total)
- New customer revenue: ${new_revenue:,.0f}
- Churn rate: {churn:.1f}%

## Key Highlights
1. Successfully launched {product_launches} new product features
2. Customer satisfaction score improved to {csat}/100 (up from {prev_csat}/100)
3. Engineering team velocity increased by {velocity_increase}% after adopting sprint planning
4. Opened new office in {new_office} — {new_hires} employees hired

## Challenges
- Customer onboarding time averaging {onboarding_days} days (target: {target_onboarding} days)
- Support ticket volume increased {ticket_increase}% — investigating root causes
- Two key competitors launched similar features — need differentiation strategy
- Infrastructure costs {cost_direction} by {cost_change}% — optimization project initiated

## Action Items
| Owner | Action | Due Date |
|-------|--------|----------|
| {owner_1} | Reduce onboarding time to {target_onboarding} days | {due_1} |
| {owner_2} | Complete competitive analysis report | {due_2} |
| {owner_3} | Present infrastructure cost optimization plan | {due_3} |
| {owner_4} | Launch customer feedback program | {due_4} |

## Next Quarter Priorities
1. Achieve ${next_target:,.0f} in total revenue
2. Reduce churn to below {target_churn:.1f}%
3. Complete platform migration to new infrastructure
4. Hire {hiring_target} additional engineers

## Budget Allocation
- Engineering: {eng_pct}%
- Sales & Marketing: {sales_pct}%
- Operations: {ops_pct}%
- R&D: {rd_pct}%
""",
    },
]

KB_ARTICLES = [
    {
        "title": "How to Set Up Your Development Environment",
        "content": """# How to Set Up Your Development Environment

## Prerequisites
Before starting, ensure you have:
- macOS {macos_version}+ or Ubuntu {ubuntu_version}+
- Admin access to your machine
- Company GitHub account (request from IT if needed)

## Step 1: Install Core Tools

### Package Manager
**macOS**: Install Homebrew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Ubuntu**: Update apt
```bash
sudo apt update && sudo apt upgrade -y
```

### Git
```bash
# macOS
brew install git

# Ubuntu
sudo apt install git -y
```

Configure Git:
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@company.com"
git config --global core.editor "code --wait"
```

### Node.js
Install via nvm (Node Version Manager):
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v{nvm_version}/install.sh | bash
nvm install {node_version}
nvm use {node_version}
```

### Python
```bash
# macOS
brew install python@{python_version}

# Ubuntu
sudo apt install python{python_version} python{python_version}-venv -y
```

## Step 2: Clone Repositories
```bash
mkdir -p ~/projects
cd ~/projects
git clone git@github.com:company/main-app.git
git clone git@github.com:company/shared-libs.git
git clone git@github.com:company/infrastructure.git
```

## Step 3: IDE Setup
We recommend VS Code with these extensions:
- ESLint
- Prettier
- Python
- GitLens
- Docker

Import the team settings:
```bash
cp ~/projects/main-app/.vscode/settings.recommended.json ~/projects/main-app/.vscode/settings.json
```

## Step 4: Docker
Install Docker Desktop from https://docker.com. After installation:
```bash
docker compose up -d  # Start local dependencies (DB, Redis, etc.)
```

## Step 5: Verify Setup
```bash
cd ~/projects/main-app
npm install
npm run test  # Should pass all tests
npm run dev   # Should start on localhost:{dev_port}
```

## Common Issues
- **Permission denied (publickey)**: Add your SSH key to GitHub
- **Port already in use**: Check `lsof -i :{dev_port}` and kill the process
- **Docker not starting**: Ensure virtualization is enabled in BIOS
- **npm install fails**: Clear cache with `npm cache clean --force`
""",
    },
    {
        "title": "How to Deploy to Production",
        "content": """# How to Deploy to Production

## Overview
Production deployments follow a blue-green strategy with automatic rollback. The process is automated via CI/CD but requires manual approval for the final promotion step.

## Pre-Deployment Checklist
- [ ] All tests passing on the release branch
- [ ] Code review approved by at least {min_approvers} reviewers
- [ ] QA sign-off completed
- [ ] Release notes written and approved
- [ ] Database migrations tested in staging
- [ ] Performance benchmarks within acceptable thresholds
- [ ] Security scan clean (no critical/high findings)

## Deployment Steps

### 1. Create Release Branch
```bash
git checkout main
git pull origin main
git checkout -b release/v{version}
git push origin release/v{version}
```

### 2. Run Staging Deployment
The CI/CD pipeline automatically deploys to staging when a release branch is pushed. Monitor the deployment:
```bash
kubectl get pods -n staging --watch
```

### 3. Staging Verification
- Run smoke tests: `npm run test:smoke -- --env staging`
- Verify key user flows manually
- Check error rates in monitoring dashboard
- Confirm database migrations applied correctly

### 4. Production Promotion
After staging verification:
1. Go to the CI/CD dashboard
2. Navigate to the release pipeline
3. Click "Promote to Production"
4. Enter the approval code from your authenticator app
5. Monitor the rollout (takes approximately {rollout_minutes} minutes)

### 5. Post-Deployment Verification
- Monitor error rates for {monitoring_minutes} minutes
- Verify key API endpoints respond correctly
- Check database connection pool health
- Confirm CDN cache invalidation completed
- Run production smoke tests

## Rollback Procedure
If issues are detected:
1. **Automatic rollback**: Triggers if error rate exceeds {error_threshold}% within {auto_rollback_minutes} minutes
2. **Manual rollback**: Run `kubectl rollout undo deployment/main-app -n production`
3. **Database rollback**: Only if migration caused data issues — coordinate with DBA team

## Emergency Contacts
- On-call engineer: Check PagerDuty rotation
- Platform team: #platform-support in Slack
- Database team: #dba-support in Slack
- Security: security@company.com
""",
    },
    {
        "title": "FAQ — Benefits and Compensation",
        "content": """# FAQ — Benefits and Compensation

## Health Insurance

**Q: When does my health insurance coverage start?**
A: Coverage begins on the first day of the month following your start date. If you start on the 1st of a month, coverage begins immediately.

**Q: What are the plan options?**
A: We offer three plans:
1. **Basic**: ${basic_monthly}/month — ${basic_deductible:,} deductible, {basic_coverage}% coverage after deductible
2. **Standard**: ${standard_monthly}/month — ${standard_deductible:,} deductible, {standard_coverage}% coverage after deductible
3. **Premium**: ${premium_monthly}/month — ${premium_deductible:,} deductible, {premium_coverage}% coverage after deductible

**Q: Can I add dependents?**
A: Yes. Spouse/partner: +${spouse_cost}/month. Each child: +${child_cost}/month.

**Q: Is dental and vision included?**
A: Dental and vision are separate plans. Dental: ${dental_cost}/month. Vision: ${vision_cost}/month.

## 401(k) Retirement Plan

**Q: When can I start contributing?**
A: You're eligible to contribute from day one. Company matching starts after {matching_months} months of employment.

**Q: What's the company match?**
A: The company matches {match_percent}% of your contribution, up to {match_limit}% of your salary.

**Q: What are the investment options?**
A: We offer {fund_count} funds through {provider}, including:
- Target-date funds
- Index funds (S&P 500, Total Market, International)
- Bond funds
- Company stock (for eligible employees)

## Paid Time Off

**Q: How much PTO do I get?**
A:
- Years 0-2: {pto_tier1} days/year
- Years 3-5: {pto_tier2} days/year
- Years 6+: {pto_tier3} days/year
Plus {holidays} company holidays per year.

**Q: Can I cash out unused PTO?**
A: You may cash out up to {cashout_days} unused days per year at your current daily rate. Remaining days carry over (max {carryover_days} days).

## Stock Options

**Q: Am I eligible for stock options?**
A: Stock options are granted to employees at the {stock_level} level and above. New hire grants vest over {vesting_years} years with a {cliff_months}-month cliff.

**Q: What happens to my options if I leave?**
A: Vested options must be exercised within {exercise_days} days of your last day. Unvested options are forfeited.
""",
    },
]


def _fill_template(template: str, **kwargs) -> str:
    """Fill a template with random values, ignoring missing keys."""
    try:
        return template.format(**kwargs)
    except KeyError:
        # For any missing keys, use a simple default
        import re
        result = template
        for match in re.finditer(r'\{(\w+)(?::[^}]*)?\}', template):
            key = match.group(1)
            if key not in kwargs:
                # Replace with a reasonable default
                kwargs[key] = random.choice(["TBD", "N/A", "Various", "2024", "30"])
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return result


def _random_hr_params() -> dict:
    return {
        "days": random.choice([15, 20, 25]),
        "monthly": random.choice([15, 20, 25]) / 12,
        "carryover": random.choice([5, 10]),
        "sick_days": random.choice([10, 12, 15]),
        "cert_days": random.choice([2, 3]),
        "parental_weeks": random.choice([12, 16, 20]),
        "secondary_weeks": random.choice([2, 4, 6]),
        "start_months": random.choice([6, 12]),
        "bereavement_days": random.choice([3, 5]),
        "notice_days": random.choice([5, 10, 14]),
        "probation_months": random.choice([3, 6]),
        "min_speed": random.choice([25, 50, 100]),
        "min_upload": random.choice([5, 10, 20]),
        "core_start": random.choice(["9:00 AM", "10:00 AM"]),
        "core_end": random.choice(["3:00 PM", "4:00 PM"]),
        "lock_timeout": random.choice([3, 5]),
        "response_time": random.choice([15, 30]),
        "standup_time": random.choice(["9:30 AM", "10:00 AM"]),
        "office_days": random.choice([2, 3]),
        "review_frequency": random.choice(["quarterly", "semi-annually", "annually"]),
        "self_due": random.choice([5, 10, 15]),
        "manager_due": random.choice([15, 20]),
        "peer_days": random.choice([5, 7, 10]),
        "calibration_week": random.choice([3, 4]),
        "goal_count": random.choice([3, 5]),
        "business_goals": random.choice([2, 3]),
        "development_goals": random.choice([1, 2]),
        "merit_min": random.choice([2, 3]),
        "merit_max": random.choice([8, 10, 12]),
        "appeal_days": random.choice([10, 14, 30]),
        "onboarding_weeks": random.choice([4, 6, 8]),
        "buddy_name": random.choice(["Sarah", "Mike", "Alex", "Jamie"]),
        "it_room": random.choice(["201", "305", "118"]),
        "security_training_mins": random.choice([30, 45, 60]),
        "orientation_day": random.choice(["Monday", "Tuesday", "Wednesday"]),
        "shadow_meetings": random.choice([2, 3, 5]),
        "benefits_deadline": random.choice([30, 60]),
        "match_percent": random.choice([4, 5, 6]),
        "gift_limit": random.choice([50, 100, 250]),
        "hotline_number": f"1-800-{random.randint(100,999)}-{random.randint(1000,9999)}",
    }


def _random_it_params() -> dict:
    return {
        "min_length": random.choice([12, 14, 16]),
        "expiry_days": random.choice([60, 90]),
        "history_count": random.choice([10, 12, 24]),
        "breach_hours": random.choice([24, 48, 72]),
        "security_phone": f"ext. {random.randint(1000, 9999)}",
        "report_hours": random.choice([1, 2, 4]),
        "vpn_protocol": random.choice(["WireGuard", "IKEv2", "OpenVPN"]),
        "key_length": random.choice([256, 384]),
        "timeout_minutes": random.choice([15, 30]),
        "max_sessions": random.choice([2, 3, 5]),
        "helpdesk_ext": str(random.randint(1000, 9999)),
        "min_reviewers": random.choice([1, 2]),
        "coverage_threshold": random.choice([80, 85, 90]),
        "review_sla": random.choice([24, 48]),
        "unit_coverage": random.choice([80, 85, 90]),
        "integration_coverage": random.choice([60, 70, 75]),
        "error_threshold": random.choice([1, 2, 5]),
        "monitoring_hours": random.choice([2, 4, 8]),
    }


def _random_finance_params() -> dict:
    return {
        "flight_hours": random.choice([4, 5, 6]),
        "hotel_max": random.choice([150, 200, 250]),
        "hotel_max_premium": random.choice([300, 350, 400]),
        "meal_limit": random.choice([50, 75, 100]),
        "client_meal_limit": random.choice([75, 100, 150]),
        "event_limit": random.choice([200, 300, 500]),
        "supply_limit": random.choice([50, 100, 200]),
        "submit_days": random.choice([14, 30, 60]),
        "receipt_threshold": random.choice([25, 50]),
        "approval_days": random.choice([3, 5, 7]),
        "audit_percent": random.choice([5, 10, 15]),
        "threshold_1": random.choice([1000, 2500, 5000]),
        "threshold_2": random.choice([10000, 25000]),
        "threshold_3": random.choice([50000, 100000]),
        "competitive_bid": random.choice([5000, 10000]),
        "min_bids": random.choice([3, 5]),
        "price_weight": 40,
        "quality_weight": 35,
        "support_weight": 25,
        "contract_threshold": random.choice([10000, 25000]),
        "payment_terms": random.choice([30, 45, 60]),
        "notice_period": random.choice([30, 60, 90]),
        "emergency_limit": random.choice([5000, 10000]),
        "retro_days": random.choice([3, 5]),
    }


def _random_travel_params() -> dict:
    return {
        "advance_days": random.choice([7, 14, 21]),
        "international_hours": random.choice([5, 6, 8]),
        "airlines": random.choice([
            "United, Delta, American",
            "Delta, Southwest, JetBlue",
            "United, Alaska, Delta",
        ]),
        "mileage_rate": random.choice([0.655, 0.67]),
        "domestic_rate": random.choice([150, 200]),
        "premium_rate": random.choice([300, 350]),
        "domestic_per_diem": random.choice([59, 75, 100]),
        "emergency_number": f"+1-800-{random.randint(100,999)}-{random.randint(1000,9999)}",
    }


def _random_product_params() -> dict:
    return {
        "token_expiry": random.choice([15, 30, 60]),
        "refresh_expiry": random.choice([7, 14, 30]),
        "rate_limit": random.choice([60, 100, 300, 1000]),
        "retry_seconds": random.choice([30, 60]),
        "rotation_days": random.choice([90, 180, 365]),
        "daily_queries": random.randint(50000, 500000),
        "p95_latency": random.choice([45, 75, 120, 200]),
        "avg_latency": random.choice([20, 35, 50, 80]),
        "tfidf_weight": 50,
        "recency_weight": 25,
        "popularity_weight": 25,
        "exact_boost": random.choice([2, 3, 5]),
        "page_size": random.choice([10, 20, 25]),
        "max_page_size": random.choice([100, 200]),
        "index_size_gb": random.choice([5, 12, 25]),
        "index_docs": random.randint(100000, 1000000),
        "reindex_hours": random.choice([4, 6, 12, 24]),
        "max_string_length": random.choice([1000, 5000, 10000]),
        "token_minutes": random.choice([15, 30, 60]),
        "api_version": random.choice([1, 2, 3]),
        "standard_rpm": random.choice([60, 100]),
        "pro_rpm": random.choice([300, 500]),
        "enterprise_rpm": random.choice([1000, 5000]),
        "retry_wait": random.choice([5, 10, 30]),
    }


def _random_meeting_params(quarter: int, year: int) -> dict:
    months = {1: "January", 2: "April", 3: "July", 4: "October"}
    names = [
        "Sarah Chen", "Mike Johnson", "Alex Rivera", "Jamie Park",
        "Chris Taylor", "Dana Kim", "Jordan Lee", "Morgan Smith",
        "Riley Adams", "Casey Brown", "Taylor Davis", "Avery Wilson",
    ]
    return {
        "quarter": quarter,
        "year": year,
        "date": f"{months[quarter]} {random.randint(10,28)}, {year}",
        "attendees": ", ".join(random.sample(names, random.randint(4, 8))),
        "duration": random.choice([60, 90, 120]),
        "revenue": random.uniform(2_000_000, 20_000_000),
        "revenue_growth": random.uniform(-5, 25),
        "arr": random.uniform(1_500_000, 15_000_000),
        "arr_pct": random.uniform(60, 85),
        "new_revenue": random.uniform(200_000, 2_000_000),
        "churn": random.uniform(1, 8),
        "product_launches": random.randint(1, 5),
        "csat": random.randint(75, 95),
        "prev_csat": random.randint(70, 90),
        "velocity_increase": random.randint(5, 30),
        "new_office": random.choice(["Austin", "Denver", "Berlin", "Toronto", "Singapore"]),
        "new_hires": random.randint(5, 30),
        "onboarding_days": random.randint(14, 45),
        "target_onboarding": random.choice([7, 10, 14]),
        "ticket_increase": random.randint(10, 50),
        "cost_direction": random.choice(["increased", "decreased"]),
        "cost_change": random.randint(5, 25),
        "owner_1": random.choice(names),
        "owner_2": random.choice(names),
        "owner_3": random.choice(names),
        "owner_4": random.choice(names),
        "due_1": f"{random.choice(['February', 'May', 'August', 'November'])} {random.randint(1,28)}, {year}",
        "due_2": f"{random.choice(['February', 'May', 'August', 'November'])} {random.randint(1,28)}, {year}",
        "due_3": f"{random.choice(['March', 'June', 'September', 'December'])} {random.randint(1,28)}, {year}",
        "due_4": f"{random.choice(['March', 'June', 'September', 'December'])} {random.randint(1,28)}, {year}",
        "next_target": random.uniform(2_500_000, 22_000_000),
        "target_churn": random.uniform(2, 5),
        "hiring_target": random.randint(5, 20),
        "eng_pct": 40,
        "sales_pct": 25,
        "ops_pct": 20,
        "rd_pct": 15,
    }


def _random_kb_params() -> dict:
    return {
        "macos_version": random.choice(["13", "14"]),
        "ubuntu_version": random.choice(["22.04", "24.04"]),
        "nvm_version": random.choice(["0.39.7", "0.40.0"]),
        "node_version": random.choice(["18", "20", "22"]),
        "python_version": random.choice(["3.11", "3.12"]),
        "dev_port": random.choice([3000, 8000, 8080]),
        "min_approvers": random.choice([1, 2]),
        "version": f"{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,20)}",
        "rollout_minutes": random.choice([5, 10, 15]),
        "monitoring_minutes": random.choice([15, 30, 60]),
        "error_threshold": random.choice([1, 2, 5]),
        "auto_rollback_minutes": random.choice([5, 10]),
        "basic_monthly": random.choice([50, 75, 100]),
        "basic_deductible": random.choice([3000, 5000]),
        "basic_coverage": random.choice([70, 80]),
        "standard_monthly": random.choice([150, 200]),
        "standard_deductible": random.choice([1500, 2000]),
        "standard_coverage": random.choice([80, 85]),
        "premium_monthly": random.choice([300, 400]),
        "premium_deductible": random.choice([500, 1000]),
        "premium_coverage": random.choice([90, 95]),
        "spouse_cost": random.choice([100, 150, 200]),
        "child_cost": random.choice([50, 75, 100]),
        "dental_cost": random.choice([25, 40, 50]),
        "vision_cost": random.choice([10, 15, 20]),
        "matching_months": random.choice([3, 6]),
        "match_percent": random.choice([50, 100]),
        "match_limit": random.choice([4, 5, 6]),
        "fund_count": random.choice([20, 30, 40]),
        "provider": random.choice(["Fidelity", "Vanguard", "Charles Schwab"]),
        "pto_tier1": random.choice([15, 18, 20]),
        "pto_tier2": random.choice([20, 22, 25]),
        "pto_tier3": random.choice([25, 28, 30]),
        "holidays": random.choice([10, 11, 12]),
        "cashout_days": random.choice([5, 10]),
        "carryover_days": random.choice([5, 10, 15]),
        "stock_level": random.choice(["Senior", "Staff", "Principal"]),
        "vesting_years": random.choice([3, 4]),
        "cliff_months": random.choice([6, 12]),
        "exercise_days": random.choice([30, 60, 90]),
    }


def generate_documents(output_dir: Path, count: int = 120) -> list[Path]:
    """Generate sample documents across all categories."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    # Distribute documents across categories
    # Aim for: 25 HR, 20 IT, 15 Finance, 10 Travel, 20 Product, 15 Meeting, 15 KB
    categories = []

    # HR Policies — generate variations
    for i in range(min(25, count // 5)):
        template = random.choice(HR_POLICIES)
        params = _random_hr_params()
        title = template["title"]
        if i > 0:
            title = f"{title} v{random.randint(1,5)}.{random.randint(0,9)}"
        content = _fill_template(template["content"], **params)
        filename = f"hr-{title.lower().replace(' ', '-').replace('/', '-')}-{i:03d}.md"
        path = output_dir / filename
        path.write_text(f"# {title}\n\n{content}", encoding="utf-8")
        generated.append(path)
        categories.append("hr_policy")

    # IT Policies
    for i in range(min(20, count // 6)):
        template = random.choice(IT_POLICIES)
        params = _random_it_params()
        title = template["title"]
        if i > 0:
            title = f"{title} — Rev {random.randint(1,10)}"
        content = _fill_template(template["content"], **params)
        filename = f"it-{title.lower().replace(' ', '-').replace('/', '-').replace('—', '').strip('-')}-{i:03d}.md"
        path = output_dir / filename
        path.write_text(f"# {title}\n\n{content}", encoding="utf-8")
        generated.append(path)
        categories.append("it_policy")

    # Finance Policies
    for i in range(min(15, count // 8)):
        template = random.choice(FINANCE_POLICIES)
        params = _random_finance_params()
        title = template["title"]
        if i > 0:
            title = f"{title} — FY{random.randint(2022, 2025)}"
        content = _fill_template(template["content"], **params)
        filename = f"finance-{title.lower().replace(' ', '-').replace('/', '-').replace('—', '').strip('-')}-{i:03d}.md"
        path = output_dir / filename
        path.write_text(f"# {title}\n\n{content}", encoding="utf-8")
        generated.append(path)
        categories.append("finance")

    # Travel Policies
    for i in range(min(10, count // 12)):
        template = random.choice(TRAVEL_POLICIES)
        params = _random_travel_params()
        title = template["title"]
        if i > 0:
            title = f"{title} — {random.choice(['Americas', 'EMEA', 'APAC'])} Region"
        content = _fill_template(template["content"], **params)
        filename = f"travel-{title.lower().replace(' ', '-').replace('/', '-').replace('—', '').strip('-')}-{i:03d}.md"
        path = output_dir / filename
        path.write_text(f"# {title}\n\n{content}", encoding="utf-8")
        generated.append(path)
        categories.append("travel")

    # Product Documentation
    for i in range(min(20, count // 6)):
        template = random.choice(PRODUCT_DOCS)
        params = _random_product_params()
        title = template["title"]
        if i > 0:
            title = f"{title} — v{random.randint(1,4)}.{random.randint(0,9)}"
        content = _fill_template(template["content"], **params)
        filename = f"product-{title.lower().replace(' ', '-').replace('/', '-').replace('—', '').strip('-')}-{i:03d}.md"
        path = output_dir / filename
        path.write_text(f"# {title}\n\n{content}", encoding="utf-8")
        generated.append(path)
        categories.append("product")

    # Meeting Notes — quarterly reviews for multiple years
    for year in [2023, 2024, 2025]:
        for quarter in [1, 2, 3, 4]:
            if len(generated) >= count:
                break
            template = MEETING_NOTES[0]
            params = _random_meeting_params(quarter, year)
            title = f"Q{quarter} {year} Business Review"
            content = _fill_template(template["content"], **params)
            filename = f"meeting-q{quarter}-{year}-business-review.md"
            path = output_dir / filename
            path.write_text(f"# {title}\n\n{content}", encoding="utf-8")
            generated.append(path)
            categories.append("meeting_notes")

    # Knowledge Base Articles
    for i in range(min(15, count // 8)):
        template = random.choice(KB_ARTICLES)
        params = _random_kb_params()
        title = template["title"]
        if i > 0:
            suffixes = ["(Updated)", "(Linux)", "(Windows)", "(Advanced)", "(Quick Start)"]
            title = f"{title} {random.choice(suffixes)}"
        content = _fill_template(template["content"], **params)
        filename = f"kb-{title.lower().replace(' ', '-').replace('/', '-').replace('(', '').replace(')', '')}-{i:03d}.md"
        path = output_dir / filename
        path.write_text(f"# {title}\n\n{content}", encoding="utf-8")
        generated.append(path)
        categories.append("knowledge_base")

    # Fill remaining with additional variations
    all_templates = HR_POLICIES + IT_POLICIES + FINANCE_POLICIES + PRODUCT_DOCS + KB_ARTICLES
    param_generators = {
        "hr": _random_hr_params,
        "it": _random_it_params,
        "finance": _random_finance_params,
        "product": _random_product_params,
        "kb": _random_kb_params,
    }

    idx = len(generated)
    while len(generated) < count:
        template = random.choice(all_templates)
        cat = random.choice(list(param_generators.keys()))
        params = param_generators[cat]()
        title = template["title"]
        title = f"{title} — Addendum {idx}"
        content = _fill_template(template["content"], **params)
        filename = f"{cat}-addendum-{idx:03d}.md"
        path = output_dir / filename
        path.write_text(f"# {title}\n\n{content}", encoding="utf-8")
        generated.append(path)
        idx += 1

    return generated


def main():
    parser = argparse.ArgumentParser(description="Generate sample documents for RAG demo")
    parser.add_argument("--count", type=int, default=120, help="Number of documents to generate")
    parser.add_argument("--output", type=str, default="./generated", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    print(f"Generating {args.count} sample documents in {output_dir}...")

    files = generate_documents(output_dir, args.count)

    # Print summary
    total_size = sum(f.stat().st_size for f in files)
    print(f"\nGenerated {len(files)} documents ({total_size / 1024:.0f} KB total)")

    # Count by category prefix
    from collections import Counter
    prefixes = Counter(f.name.split("-")[0] for f in files)
    for prefix, cnt in sorted(prefixes.items()):
        print(f"  {prefix}: {cnt} documents")


if __name__ == "__main__":
    main()
