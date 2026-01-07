UPDATE fragment_artifacts 
SET fragment_markup = '<div class="flex items-start" data-question-id="{{ item.id }}">
    {% if item.blocking %}
    <i data-lucide="alert-circle" class="w-4 h-4 mr-2 text-red-600 dark:text-red-500 flex-shrink-0 mt-0.5"></i>
    {% else %}
    <i data-lucide="help-circle" class="w-4 h-4 mr-2 text-amber-600 dark:text-amber-500 flex-shrink-0 mt-0.5"></i>
    {% endif %}
    <div class="flex-1">
        <span class="text-gray-900 dark:text-gray-50 text-sm">{{ item.text }}</span>
        {% if item.blocking %}
        <span class="ml-2 px-1.5 py-0.5 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded text-xs">Blocking</span>
        {% endif %}
        {% if item.priority %}
        <span class="ml-1 px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded text-xs">{{ item.priority | capitalize }}</span>
        {% endif %}
        {% if item.why_it_matters %}
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ item.why_it_matters }}</p>
        {% endif %}
    </div>
</div>'
WHERE fragment_id = 'OpenQuestionV1Fragment';