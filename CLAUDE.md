## Project Context

This repository contains a simple CRM MVP designed to manage client relationships with a deliberately small scope.

The product should optimize for:
- Fast contact lookup and editing
- Simple relationship/activity history
- Straightforward deal tracking
- Minimal configuration and complexity

Do not expand the scope unless explicitly requested.

## Core Domain Model

### Contact

A contact represents a person.

Required relationship:
- Every contact belongs to exactly one company.

Fields:
- name
- email
- phone
- company
- job_title
- address
- website
- tags

A company is only a field on Contact. It is NOT a separate domain entity.

Supported operations:
- Create contact
- View contact
- Edit contact
- Search by name, email, or company
- Filter by tags

### Deal

A deal represents a sales opportunity.

Required relationship:
- Every deal belongs to exactly one contact.

A deal has:
- contact
- pipeline stage

The MVP uses exactly one pipeline.

Deal stage changes are always manual.

Won and Lost are normal pipeline stages. There is no separate win/loss workflow and no reason field.

Supported operations:
- Create a deal from a contact
- View a deal
- Edit a deal
- Move a deal manually between stages
- Move a deal to Won
- Move a deal to Lost

### Activity

Activities represent interactions with contacts.

Supported types:
- call
- email
- meeting
- note

Required relationship:
- Every activity belongs to exactly one contact.

Activities are NOT directly attached to deals.

Activities should be visible in the contact's activity history.

## Main Application Sections

The primary navigation contains:

1. Contacts
2. Deals

### Contacts section

Should provide:
- Searchable contact list
- Tag filtering
- Contact detail view
- Activity history
- Associated deals

Search fields:
- name
- email
- company

Filters:
- tags

### Deals section

Should provide:
- Single pipeline view
- Deals grouped by stage
- Manual movement between stages
- Access to the associated contact

## Relationships

Conceptually:

Company (field on Contact)
    |
    v
Contact
  | \
  |  \
  v   v
Activity Deal
         |
         v
   Pipeline Stage

Rules:
- Company is not a separate entity.
- A contact has exactly one company.
- A contact can have many activities.
- A contact can have many deals.
- A deal belongs to exactly one contact.
- An activity belongs to exactly one contact.
- An activity cannot belong directly to a deal.

## Pipeline

There is one pipeline.

Pipeline stages should be simple and manually managed.

The original MVP decision was:
- Manual stage changes
- No automatic actions
- Won/Lost represented as stages

If implementation requires choosing initial default stage names, keep them conventional and minimal (for example: Lead, Qualified, Proposal, Won, Lost). Do not introduce multiple pipelines or workflow automation without an explicit product decision.

## Explicitly Out of Scope

Do NOT implement these as part of the MVP:

- Multiple pipelines
- Automated stage transitions
- Automatic follow-ups
- Tasks/reminders
- Deal win/loss reasons
- Separate Company entity
- Company pages
- Saved contact views
- Custom contact fields
- Dashboard as a primary section
- Direct Activity → Deal relationships
- Email synchronization
- Calendar synchronization
- Marketing automation
- Reporting/analytics
- Complex workflow automation

## Expected MVP User Flows

### Create a contact
1. User opens Contacts.
2. User creates a contact.
3. User provides required contact information including company.
4. Contact is saved.

### Record an interaction
1. User opens a contact.
2. User creates an activity.
3. User selects Call, Email, Meeting, or Note.
4. Activity is saved to the contact history.

### Create a deal
1. User opens a contact.
2. User creates a deal.
3. Deal is automatically associated with that contact.
4. Deal appears in the pipeline.

### Move a deal
1. User opens Deals.
2. User moves a deal to another stage.
3. The new stage is persisted.
4. No automation is triggered.

### Find a contact
1. User opens Contacts.
2. User searches by name, email, or company.
3. User optionally filters by tags.
4. User opens the desired contact.

## Engineering Guidelines

Prefer simple, explicit implementations over abstractions that are not needed by the MVP.

When adding functionality:
1. Check whether it is explicitly part of this scope.
2. Preserve the domain relationships above.
3. Avoid introducing new entities when a field is sufficient.
4. Avoid automation unless explicitly requested.
5. Keep UI flows short and CRUD-oriented.
6. Validate relationships at the data/model boundary, not only in the UI.
7. Keep business logic independent from presentation where practical.
8. Favor predictable APIs and clear naming.

## Scope Control

If a requested feature conflicts with this document or expands the MVP, do not silently add it.

Instead:
- Identify the scope change.
- Explain the smallest implementation needed.
- Ask for explicit confirmation if the change affects the core domain model or introduces a new major workflow.

The source of truth for the MVP is this document plus explicit subsequent product decisions made by the project owner.

## Product Philosophy

The CRM should feel like a lightweight operational tool, not a full enterprise CRM.

The central workflow is:

Contact -> Activities
Contact -> Deals -> Pipeline Stage

Optimize for simplicity, speed, and clarity.