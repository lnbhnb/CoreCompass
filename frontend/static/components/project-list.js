function projectList(parent) {
  return {
    projects: [],
    loading: true,

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

    roleLabel(p) {
      return p.creator_id === parent.currentUser?.id ? '队长' : '队员';
    },
    progressSummary(p) {
      return `${p.team_size} 人团队`;
    }
  }
}
