function app() {
  return {
    view: 'create',
    project: null, milestones: [], tasks: [], notifications: [], usedReferences: null,

    async createProject(form) {
      const r = await fetch('/api/projects', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      });
      const data = await r.json();
      this.project = data.detail.project;
      this.milestones = data.detail.milestones;
      this.tasks = data.detail.tasks;
      this.usedReferences = data.detail.used_references || null;
      this.view = 'board';
    },

    async loadProject(pid) {
      const r = await fetch(`/api/projects/${pid}`);
      const data = await r.json();
      this.project = data.project;
      this.milestones = data.milestones;
      this.tasks = data.tasks;
      this.usedReferences = data.used_references || null;
      this.view = 'board';
    },

    async triggerOverdue() {
      await fetch(`/api/replan/${this.project.id}/trigger_overdue`, { method: 'POST' });
      await this.loadProject(this.project.id);
    },

    async refresh() {
      if (this.project) await this.loadProject(this.project.id);
    },

    async updateTaskStatus(taskId, event) {
      await fetch(`/api/tasks/${taskId}/status`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event })
      });
      await this.loadProject(this.project.id);
    },

    // —— 罗盘仪表辅助方法 ——
    needleAngle() {
      // 指针随当前里程碑进度旋转：M1→45°, M2→90°... 满额 360°
      if (!this.milestones.length) return 0;
      const done = this.milestones.filter(m => m.status === 'done').length;
      return Math.round((done / this.milestones.length) * 360);
    },

    currentHeading() {
      if (!this.milestones.length) return '待启航';
      const current = this.milestones.find(m => m.status !== 'done') || this.milestones[0];
      const idx = this.milestones.indexOf(current) + 1;
      return `M${String(idx).padStart(2, '0')} · ${current.name}`;
    },

    progressText() {
      if (!this.milestones.length) return '';
      const done = this.milestones.filter(m => m.status === 'done').length;
      return `${done} / ${this.milestones.length} 里程碑`;
    },

    milestonePct() {
      if (!this.milestones.length) return 0;
      const done = this.milestones.filter(m => m.status === 'done').length;
      return Math.round((done / this.milestones.length) * 100);
    },

    taskProgressText() {
      if (!this.tasks.length) return '0 / 0 任务';
      const done = this.tasks.filter(t => t.status === 'done').length;
      return `${done} / ${this.tasks.length} 任务`;
    },

    taskPct() {
      if (!this.tasks.length) return 0;
      const done = this.tasks.filter(t => t.status === 'done').length;
      return Math.round((done / this.tasks.length) * 100);
    },

    coordsLabel() {
      if (!this.project) return '— · —';
      const days = Math.max(0, Math.ceil((new Date(this.project.deadline) - new Date()) / 86400000));
      return `${days}d 到岸 · ${this.project.team_size}p`;
    },

    scrollTo(id) {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    },

    formatDate(s) {
      if (!s) return '';
      return s.slice(0, 10);
    },

    formatTime(s) {
      if (!s) return '';
      return s.replace('T', ' ').slice(0, 16);
    }
  }
}
