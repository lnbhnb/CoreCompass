function projectList(parent) {
  return {
    projects: [],
    loading: true,
    joinOpen: false,
    joinCode: '',
    joinLoading: false,
    joinError: null,

    async init() {
      await this.load();
    },

    async load() {
      this.loading = true;
      try {
        const r = await fetch('/api/projects', { headers: parent.authHeaders() });
        if (!r.ok) { parent.logout(); return; }
        this.projects = await r.json();
      } finally {
        this.loading = false;
      }
    },

    openJoin() {
      this.joinCode = '';
      this.joinError = null;
      this.joinOpen = true;
    },

    async submitJoin() {
      if (!this.joinCode.trim()) return;
      this.joinLoading = true;
      this.joinError = null;
      try {
        const r = await fetch('/api/auth/join', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...parent.authHeaders() },
          body: JSON.stringify({ invite_code: this.joinCode.trim() })
        });
        if (!r.ok) {
          const e = await r.json();
          throw new Error(e.detail || '加入失败');
        }
        const data = await r.json();
        this.joinOpen = false;
        await this.load();
        parent.navigate('/projects/' + data.project_id);
      } catch (e) {
        this.joinError = e.message;
      } finally {
        this.joinLoading = false;
      }
    },

    roleLabel(p) {
      return p.creator_id === parent.currentUser?.id ? '队长' : '队员';
    },
    progressSummary(p) {
      return `${p.team_size} 人团队`;
    },
    go(path) { parent.navigate(path); }
  }
}
