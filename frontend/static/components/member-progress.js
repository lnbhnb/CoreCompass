function memberProgress(parent) {
  return {
    data: { members: [], pending_review: [] },
    loading: true,
    reviewComment: '',

    async init() {
      await this.load();
    },

    async load() {
      if (!parent.project) return;
      this.loading = true;
      try {
        const r = await fetch(`/api/projects/${parent.project.id}/progress`, {
          headers: parent.authHeaders()
        });
        if (!r.ok) return;
        this.data = await r.json();
      } finally {
        this.loading = false;
      }
    },

    async review(taskId, decision) {
      const r = await fetch(`/api/tasks/${taskId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...parent.authHeaders() },
        body: JSON.stringify({ decision, comment: this.reviewComment })
      });
      if (!r.ok) { alert('审阅失败'); return; }
      this.reviewComment = '';
      await this.load();
    },

    downloadUrl(taskId) {
      return `/api/tasks/${taskId}/submission`;
    }
  }
}
