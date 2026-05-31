(function () {
  function showElement(element) {
    if (element) {
      element.style.display = 'block';
    }
  }

  window.handleAiGenerationSubmit = function handleAiGenerationSubmit(event, form) {
    const targetId = form.getAttribute('data-status-target') || form.getAttribute('data-loading-target');
    const localStatus = targetId ? document.getElementById(targetId) : null;
    const globalStatus = document.querySelector('[data-global-generation-status]');
    const buttons = form.querySelectorAll('[data-ai-generation-button], [data-draft-generation-button], [data-outline-generation-button], button[type="submit"]');
    const clickedButton = event && event.submitter
      ? event.submitter
      : form.querySelector('[data-ai-generation-button], [data-draft-generation-button], [data-outline-generation-button], button[type="submit"]');

    showElement(localStatus);
    showElement(globalStatus);

    buttons.forEach((button) => {
      button.disabled = true;
    });

    if (localStatus && form.getAttribute('data-loading-message')) {
      localStatus.textContent = form.getAttribute('data-loading-message');
    }
    if (clickedButton) {
      clickedButton.textContent = form.getAttribute('data-loading-label') || 'AI 正在生成，请稍候...';
    }
    return true;
  };

  window.handleLessonDraftGenerationSubmit = function handleLessonDraftGenerationSubmit(event, form) {
    return window.handleAiGenerationSubmit(event, form);
  };

  window.handleOutlineGenerationSubmit = function handleOutlineGenerationSubmit(form) {
    return window.handleAiGenerationSubmit(null, form);
  };

  function activateDraftTab(tab) {
    const targetId = tab.getAttribute('data-draft-tab-target');
    if (!targetId) {
      return;
    }
    document.querySelectorAll('[data-draft-tab-target]').forEach((button) => {
      button.classList.toggle('is-active', button === tab);
      button.setAttribute('aria-selected', button === tab ? 'true' : 'false');
    });
    document.querySelectorAll('[data-draft-editor-panel]').forEach((panel) => {
      panel.classList.toggle('is-active', panel.id === targetId);
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('[data-draft-tab-target]');
    tabs.forEach((tab) => {
      tab.addEventListener('click', () => activateDraftTab(tab));
    });
    const activeTab = document.querySelector('[data-draft-tab-target].is-active') || tabs[0];
    if (activeTab) {
      activateDraftTab(activeTab);
    }
  });
}());
