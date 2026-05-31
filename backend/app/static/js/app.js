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

  function updatePromptPreview(card, text) {
    const promptElement = card.querySelector('[data-question-prompt]');
    if (!promptElement) {
      return;
    }
    const promptLine = text
      .split('\n')
      .map((line) => line.trim().replace(/^[-*]\s*/, ''))
      .find((line) => /^题干[：:]/.test(line) || /^题目[：:]/.test(line) || /^问题[：:]/.test(line));
    if (promptLine) {
      promptElement.textContent = promptLine.replace(/^[^：:]+[：:]\s*/, '').trim() || '题干未解析';
    }
  }

  function replaceQuestionMarkdown(fullTextarea, oldText, newText) {
    if (!fullTextarea || !oldText) {
      return false;
    }
    const currentValue = fullTextarea.value;
    if (!currentValue.includes(oldText)) {
      return false;
    }
    fullTextarea.value = currentValue.replace(oldText, newText);
    fullTextarea.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  }

  function rebuildDiagnosticMarkdown(fullTextarea) {
    if (!fullTextarea) {
      return;
    }
    const blocks = Array.from(document.querySelectorAll('[data-diagnostic-question-card] [data-question-editor]'))
      .map((textarea) => textarea.value.trim())
      .filter(Boolean);
    if (blocks.length) {
      fullTextarea.value = blocks.join('\n\n');
      fullTextarea.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }

  function submitDiagnosticDraft(diagnosticRoot) {
    const saveForm = diagnosticRoot.querySelector('[data-diagnostic-save-form]');
    if (!saveForm) {
      return;
    }
    if (typeof saveForm.requestSubmit === 'function') {
      saveForm.requestSubmit();
    } else {
      saveForm.submit();
    }
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

    const diagnosticRoot = document.querySelector('[data-diagnostic-v2]');
    if (diagnosticRoot) {
      const fullTextarea = diagnosticRoot.querySelector('[data-diagnostic-full-content]');
      diagnosticRoot.querySelectorAll('[data-apply-question-edit]').forEach((button) => {
        button.addEventListener('click', () => {
          const card = button.closest('[data-diagnostic-question-card]');
          if (!card) {
            return;
          }
          const rawInput = card.querySelector('[data-question-raw]');
          const editor = card.querySelector('[data-question-editor]');
          if (!rawInput || !editor) {
            return;
          }
          const updated = editor.value.trim();
          if (replaceQuestionMarkdown(fullTextarea, rawInput.value, updated)) {
            rawInput.value = updated;
          } else {
            rebuildDiagnosticMarkdown(fullTextarea);
          }
          updatePromptPreview(card, updated);
          submitDiagnosticDraft(diagnosticRoot);
        });
      });

      diagnosticRoot.querySelectorAll('[data-delete-question]').forEach((button) => {
        button.addEventListener('click', () => {
          if (!window.confirm('确认删除这道题吗？删除后将立即保存到当前草稿。')) {
            return;
          }
          const card = button.closest('[data-diagnostic-question-card]');
          if (!card) {
            return;
          }
          const rawInput = card.querySelector('[data-question-raw]');
          if (rawInput && !replaceQuestionMarkdown(fullTextarea, rawInput.value, '')) {
            card.remove();
            rebuildDiagnosticMarkdown(fullTextarea);
            submitDiagnosticDraft(diagnosticRoot);
            return;
          }
          card.remove();
          submitDiagnosticDraft(diagnosticRoot);
        });
      });
    }
  });
}());
