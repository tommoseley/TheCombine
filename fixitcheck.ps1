cd "C:\dev\The Combine\app\web\templates\pages"

# Create project_detail.html (wrapper with base)
@"
{% extends "layout/base.html" %}

{% block title %}{{ project.name }} - The Combine{% endblock %}

{% block content %}
    {% include "pages/partials/_project_overview.html" %}
{% endblock %}
"@ | Out-File -Encoding UTF8 project_detail.html

# Create project_discovery.html
@"
{% extends "layout/base.html" %}

{% block title %}{{ project.name }} - Discovery - The Combine{% endblock %}

{% block content %}
    {% include "pages/partials/_project_discovery_content.html" %}
{% endblock %}
"@ | Out-File -Encoding UTF8 project_discovery.html

# Create project_new.html
@"
{% extends "layout/base.html" %}

{% block title %}New Project - The Combine{% endblock %}

{% block content %}
    {% include "pages/partials/_project_new_content.html" %}
{% endblock %}
"@ | Out-File -Encoding UTF8 project_new.html

# Create epic_backlog.html
@"
{% extends "layout/base.html" %}

{% block title %}Epic Backlog - The Combine{% endblock %}

{% block content %}
    {% include "pages/partials/_epic_backlog_content.html" %}
{% endblock %}
"@ | Out-File -Encoding UTF8 epic_backlog.html

# Create story_backlog.html
@"
{% extends "layout/base.html" %}

{% block title %}Story Backlog - The Combine{% endblock %}

{% block content %}
    {% include "pages/partials/_story_backlog_content.html" %}
{% endblock %}
"@ | Out-File -Encoding UTF8 story_backlog.html

# Create technical_architecture.html
@"
{% extends "layout/base.html" %}

{% block title %}Technical Architecture - The Combine{% endblock %}

{% block content %}
    {% include "pages/partials/_technical_architecture_content.html" %}
{% endblock %}
"@ | Out-File -Encoding UTF8 technical_architecture.html

Write-Host "✅ Created all wrapper templates"