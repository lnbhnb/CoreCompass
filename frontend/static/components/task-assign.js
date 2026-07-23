function taskAssign(parent, task) {
  return {
    showAssignPicker: false,
    reviewComment: '',
    submitting: false,

    async assignTo(userId) {
      const r = await fetch(`/api/tasks/${task.id}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...parent.authHeaders() },
        body: JSON.stringify({ assignee_id: userId })
      });
      if (!r.ok) { alert('分配失败'); return; }
      this.showAssignPicker = false;
      await parent.loadProject(parent.project.id);
    },

    async claim() {
      const r = await fetch(`/api/tasks/${task.id}/claim`, {
        method: 'POST',
        headers: parent.authHeaders()
      });
      if (!r.ok) { alert((await r.json()).detail || '认领失败'); return; }
      await parent.loadProject(parent.project.id);
    },

    async submitFile(fileInput) {
      const file = fileInput.files[0];
      if (!file) return;
      this.submitting = true;
      try {
        const fd = new FormData();
        fd.append('file', file);
        const r = await fetch(`/api/tasks/${task.id}/submit`, {
          method: 'POST',
          headers: parent.authHeaders(),
          body: fd
        });
        if (!r.ok) { alert((await r.json()).detail || '提交失败'); return; }
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
      if (!r.ok) { alert('审阅失败'); return; }
      this.reviewComment = '';
      await parent.loadProject(parent.project.id);
    },

    downloadUrl() {
      return `/api/tasks/${task.id}/submission`;
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
