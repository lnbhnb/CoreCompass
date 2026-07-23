function app() {
  return {
    view: 'create',
    project: null, milestones: [], tasks: [], notifications: [],

    async createProject(form) {
      const r = await fetch('/api/projects', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      });
      const data = await r.json();
      this.project = data.detail.project;
      this.milestones = data.detail.milestones;
      this.tasks = data.detail.tasks;
      this.view = 'board';
    },

    async loadProject(pid) {
      const r = await fetch(`/api/projects/${pid}`);
      const data = await r.json();
      this.project = data.project;
      this.milestones = data.milestones;
      this.tasks = data.tasks;
      this.view = 'board';
    },

    async triggerOverdue() {
      await fetch(`/api/replan/${this.project.id}/trigger_overdue`, { method: 'POST' });
      await this.loadProject(this.project.id);
    },

    async refresh() {
      if (this.project) await this.loadProject(this.project.id);
    }
  }
}
