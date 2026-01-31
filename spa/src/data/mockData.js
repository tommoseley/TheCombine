/**
 * Mock project data for development
 * Will be replaced with API calls in production
 */
import { createDocument, createStations, createQuestions, createEpic } from './factories';

// Mock project for "The Combine" (existing, in-progress)
export const combineProjectData = [
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
            createEpic('epic1', 'User Auth', 'stabilized', 'mandatory', ['Login Flow', 'OAuth Integration', '2FA Setup', 'Password Reset', 'Session Mgmt', 'Remember Me', 'Account Lockout', 'Audit Log']),
            createEpic('epic2', 'Math Engine', 'active', 'mandatory', ['Basic Ops', 'Expression Parser', 'Variables', 'Functions', 'Units', 'Matrix Ops', 'Statistics']),
            createEpic('epic3', 'Dashboard', 'queued', 'mandatory', ['Metrics Cards', 'Charts', 'Realtime Updates', 'Widgets', 'PDF Export', 'Reports', 'Alerts', 'Sharing', 'Mobile View']),
            createEpic('epic4', 'API Gateway', 'queued', 'mandatory', ['Rate Limiting', 'Validation', 'Caching', 'Versioning', 'Docs Gen', 'Webhooks', 'GraphQL', 'Health Check', 'Circuit Breaker', 'Tracing']),
            createEpic('epic5', 'Data Pipeline', 'queued', 'mandatory', ['ETL Jobs', 'Validation', 'Schema Registry', 'Batch Processing', 'Stream Processing', 'Dead Letter Queue', 'Lineage', 'Quality Checks']),
            createEpic('epic6', 'Notifications', 'queued', 'mandatory', ['Email', 'Push', 'SMS', 'In-App', 'Preferences', 'Tracking', 'Templates', 'Scheduling', 'A/B Testing', 'Analytics', 'Unsubscribe']),
            createEpic('epic7', 'Search', 'queued', 'optional', ['Full-text', 'Faceted', 'Autocomplete', 'Analytics', 'Synonyms', 'Relevance Tuning', 'Saved Searches']),
            createEpic('epic8', 'File Mgmt', 'queued', 'mandatory', ['Upload', 'Image Processing', 'Video Transcoding', 'CDN', 'Antivirus', 'Quotas', 'Folders', 'Sharing', 'Versioning', 'Thumbnails', 'Bulk Ops', 'Trash']),
            createEpic('epic9', 'Billing', 'queued', 'mandatory', ['Stripe Integration', 'Invoicing', 'Subscriptions', 'Usage Metering', 'Tax Calc', 'Payment History', 'Refunds', 'Dunning', 'Revenue Reports']),
            createEpic('epic10', 'Admin Panel', 'queued', 'optional', ['User Management', 'Role Management', 'Audit Logs', 'System Config', 'Feature Flags', 'Data Import', 'Bulk Actions', 'Activity Logs']),
            createEpic('epic11', 'i18n', 'queued', 'optional', ['Translation Mgmt', 'RTL Support', 'Date Formats', 'Currency', 'Language Switch', 'Pluralization', 'String Extraction']),
            createEpic('epic12', 'Analytics', 'queued', 'mandatory', ['Event Tracking', 'User Segments', 'Funnels', 'Cohorts', 'Custom Dimensions', 'Data Export', 'Goals', 'Attribution', 'Realtime', 'Anomaly Detection']),
            createEpic('epic13', 'Integrations', 'queued', 'optional', ['Salesforce', 'Slack', 'Jira', 'Zapier', 'OAuth Apps', 'Webhooks', 'Field Mapping', 'Sync Engine', 'Error Handling'])
        ]
    }
];

// Mock project list
export const MOCK_PROJECTS = {
    'combine': {
        id: 'combine',
        name: 'The Combine',
        description: 'Industrial AI for knowledge work',
        status: 'active',
        data: combineProjectData
    },
    'website': {
        id: 'website',
        name: 'Marketing Website',
        description: 'Company website redesign',
        status: 'complete',
        data: [
            createDocument('concierge', 'Concierge Intake', 'Initial requirements', 'stabilized'),
            createDocument('discovery', 'Project Discovery', 'Scope definition', 'stabilized'),
            createDocument('architecture', 'Technical Architecture', 'Tech stack decisions', 'stabilized'),
        ]
    },
    'mobile': {
        id: 'mobile',
        name: 'Mobile App',
        description: 'iOS and Android companion app',
        status: 'queued',
        data: [
            createDocument('concierge', 'Concierge Intake', 'Initial requirements', 'queued'),
        ]
    }
};
