# Simple CRM — MVP Specification

## 1. Scope

A simple CRM focused on the most common client relationship workflows:

- Manage contacts
- Manage deals through a single sales pipeline
- Record contact activities
- Search and filter contacts

The MVP intentionally excludes automation, dashboards, separate company management, and advanced customization.

## 2. Core entities

### Contact

Every contact belongs to exactly one company.

Fields:

- Name
- Email
- Phone
- Company
- Job title
- Address
- Website
- Tags

Supported operations:

- Create contact
- View contact
- Edit contact
- Search contacts by name, email, or company
- Filter contacts by tags

### Deal

Every deal must belong to a contact.

A deal is managed through a single pipeline.

The MVP supports:

- Create deal from a contact
- View deal
- Edit deal
- Manually move a deal between pipeline stages
- Mark a deal as Won or Lost by moving it to the corresponding stage

There is no separate Won/Lost action or reason field.

### Activity

Activities belong to contacts only.

Supported activity types:

- Call
- Email
- Meeting
- Note

Activities should be recorded against a contact and visible as part of that contact's activity history.

## 3. Pipeline

The CRM has one sales pipeline.

Deal stages are managed manually by the user.

The MVP requires only:

- A deal belongs to one contact
- A deal has one current pipeline stage
- Users can manually move deals between stages
- Won and Lost are represented as pipeline stages

No automatic actions are triggered by stage changes.

## 4. Main navigation

The application has two primary sections:

### Contacts

Provides:

- Contact list
- Search
- Tag filters
- Contact details
- Contact activities
- Associated deals

### Deals

Provides:

- Pipeline view
- Deals grouped by stage
- Manual deal movement between stages
- Access to the associated contact

## 5. Relationships

```text
Company (field only)
        |
        | 1
        v
     Contact
      /    \\
     /      \\
    v        v
 Activity   Deal
              |
              v
        Pipeline Stage