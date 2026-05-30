(function () {
  function showElement(element) {
    if (element) {
      element.style.display = 'block';
    }
  }

  window.handleLessonDraftGenerationSubmit = function handleLessonDraftGenerationSubmit(event, form) {
    const targetId = form.getAttribute('data-loading-target');
    const localStatus = targetId ? document.getElementById(targetId) : null;
    const globalStatus = document.querySelector('[data-global-generation-status]');
    const buttons = document.querySelectorAll('[data-draft-generation-button]');
    const clickedButton = event && event.submitter ? event.submitter : form.querySelector('[data-draft-generation-button]');

    showElement(localStatus);
    showElement(globalStatus);

    buttons.forEach((button) => {
      button.disabled = true;
      if (button !== clickedButton) {
        button.title = '当前已有生成任务进行中，请稍候';
      }
    });

    if (clickedButton) {
      clickedButton.textContent = 'AI 正在生成，请稍候...';
    }
    return true;
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
