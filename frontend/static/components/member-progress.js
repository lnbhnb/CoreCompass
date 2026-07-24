function memberProgress(parent) {
  return {
    data: { members: [], pending_review: [] },
    loading: true,
    reviewComment: '',
    invite: null,
    inviteCopied: false,
    inviteList: [],
    joinCode: '',
    joinError: null,

    get currentRole() { return parent.currentRole; },
    get projectId() { return parent.project ? parent.project.id : null; },

    async init() {
      await this.load();
      await this.loadInviteList();
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

    async loadInviteList() {
      if (!parent.project || parent.currentRole !== 'leader') return;
      try {
        const r = await fetch(`/api/projects/${parent.project.id}/invites`, {
          headers: parent.authHeaders()
        });
        this.inviteList = r.ok ? await r.json() : [];
      } catch { this.inviteList = []; }
    },

    async generateInvite() {
      const r = await fetch(`/api/projects/${parent.project.id}/invites`, {
        method: 'POST',
        headers: parent.authHeaders()
      });
      if (!r.ok) { alert('生成失败'); return; }
      this.invite = await r.json();
      this.inviteCopied = false;
      await this.loadInviteList();
    },

    copyCode(code) {
      if (!code) return;
      navigator.clipboard.writeText(code);
      this.inviteCopied = true;
      setTimeout(() => { this.inviteCopied = false; }, 1500);
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
    },
    go(path) { parent.navigate(path); }
  }
}
