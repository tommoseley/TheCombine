// data/projectData.js
// Sample project data using factory functions

import { createDocument, createEpic, createStations, createQuestions } from './factories.js';

export const initialData = [
    // L1 Spine Documents
    createDocument('concierge', 'Concierge Intake', 'Initial project intake', 'stabilized'),
    createDocument('discovery', 'Project Discovery', 'Deep dive into scope', 'stabilized'),
    createDocument('architecture', 'Technical Architecture', 'System design decisions', 'active', 'mandatory', {
        stations: createStations('pgc'),
        questions: createQuestions([
            'What is the primary deployment target?',
            'Are there any existing systems to integrate with?',
            { text: 'Preferred cloud provider?', required: false }
        ])
    }),
    {
        ...createDocument('backlog', 'Epic Backlog', 'High-level feature breakdown', 'queued'),
        children: [
            // Row 1
            createEpic('epic1', 'User Auth', 'stabilized', 'mandatory', 
                ['Login Flow', 'OAuth Integration', '2FA Setup', 'Password Reset', 'Session Mgmt', 'Remember Me', 'Account Lockout', 'Audit Log']),
            createEpic('epic2', 'Math Engine', 'active', 'mandatory',
                ['Basic Ops', 'Expression Parser', 'Variables', 'Functions', 'Units', 'Matrix Ops', 'Statistics']),
            createEpic('epic3', 'Dashboard', 'queued', 'mandatory',
                ['Metrics Cards', 'Charts', 'Realtime Updates', 'Widgets', 'PDF Export', 'Reports', 'Alerts', 'Sharing', 'Mobile View']),
            
            // Row 2
            createEpic('epic4', 'API Gateway', 'queued', 'mandatory',
                ['Rate Limiting', 'Validation', 'Caching', 'Versioning', 'Docs Gen', 'Webhooks', 'GraphQL', 'Health Check', 'Circuit Breaker', 'Tracing']),
            createEpic('epic5', 'Data Pipeline', 'queued', 'mandatory',
                ['ETL Jobs', 'Validation', 'Schema Registry', 'Batch Processing', 'Stream Processing', 'Dead Letter Queue', 'Lineage', 'Quality Checks']),
            createEpic('epic6', 'Notifications', 'queued', 'mandatory',
                ['Email', 'Push', 'SMS', 'In-App', 'Preferences', 'Tracking', 'Templates', 'Scheduling', 'A/B Testing', 'Analytics', 'Unsubscribe']),
            
            // Row 3
            createEpic('epic7', 'Search', 'queued', 'optional',
                ['Full-text', 'Faceted', 'Autocomplete', 'Analytics', 'Synonyms', 'Relevance Tuning', 'Saved Searches']),
            createEpic('epic8', 'File Mgmt', 'queued', 'mandatory',
                ['Upload', 'Image Processing', 'Video Transcoding', 'CDN', 'Antivirus', 'Quotas', 'Folders', 'Sharing', 'Versioning', 'Thumbnails', 'Bulk Ops', 'Trash']),
            createEpic('epic9', 'Billing', 'queued', 'mandatory',
                ['Stripe Integration', 'Invoicing', 'Subscriptions', 'Usage Metering', 'Tax Calc', 'Payment History', 'Refunds', 'Dunning', 'Revenue Reports']),
            
            // Row 4
            createEpic('epic10', 'Admin Panel', 'queued', 'optional',
                ['User Management', 'Role Management', 'Audit Logs', 'System Config', 'Feature Flags', 'Data Import', 'Bulk Actions', 'Activity Logs']),
            createEpic('epic11', 'i18n', 'queued', 'optional',
                ['Translation Mgmt', 'RTL Support', 'Date Formats', 'Currency', 'Language Switch', 'Pluralization', 'String Extraction']),
            createEpic('epic12', 'Analytics', 'queued', 'mandatory',
                ['Event Tracking', 'User Segments', 'Funnels', 'Cohorts', 'Custom Dimensions', 'Data Export', 'Goals', 'Attribution', 'Realtime', 'Anomaly Detection']),
            
            // Row 5
            createEpic('epic13', 'Integrations', 'queued', 'optional',
                ['Salesforce', 'Slack', 'Jira', 'Zapier', 'OAuth Apps', 'Webhooks', 'Field Mapping', 'Sync Engine', 'Error Handling'])
        ]
    }
];