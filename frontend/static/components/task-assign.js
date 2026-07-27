function taskAssign(parent, task) {
  return {
    reviewComment: '',
    submitting: false,
    showSubmitBox: false,

    async submitFile(taskId) {
      const fileInput = document.getElementById('submit-file-' + taskId);
      const file = fileInput && fileInput.files && fileInput.files[0];
      if (!file) { alert('请先选择文件'); return; }
      this.submitting = true;
      try {
        const fd = new FormData();
        fd.append('file', file);
        const r = await fetch(`/api/tasks/${taskId}/submit`, {
          method: 'POST',
          headers: parent.authHeaders(),
          body: fd
        });
        if (!r.ok) { const e = await r.json().catch(() => ({})); alert(e.detail || '提交失败'); return; }
        this.showSubmitBox = false;
        await parent.loadProject(parent.project.id);
      } finally {
        this.submitting = false;
      }
    },

    async review(decision) {
      const r = await fetch(`/api/tasks/${task.id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...parent.authHeaders() },
        body: JSON.stringify({ decision, comment: this.reviewComment })
      });
      if (!r.ok) { const e = await r.json().catch(() => ({})); alert(e.detail || '审阅失败'); return; }
      this.reviewComment = '';
      await parent.loadProject(parent.project.id);
    },

    download() {
      return parent.downloadSubmission(task.id, task.submission_filename);
    },

    reviewStatusLabel(status) {
      return {
        pending_review: '待审阅',
        approved: '已通过',
        rejected: '需修改'
      }[status] || '';
    },
    reviewStatusClass(status) {
      return {
        pending_review: 'rv-pending',
        approved: 'rv-approved',
        rejected: 'rv-rejected'
      }[status] || '';
    }
  }
}
