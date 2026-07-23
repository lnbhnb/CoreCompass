function app() {
  return {
    view: 'login',
    currentUser: null,
    token: localStorage.getItem('cc_token') || null,
    project: null, milestones: [], tasks: [], notifications: [],
    usedReferences: null, currentRole: null,

    init() {
      if (this.token) {
        this.fetchUser();
      } else {
        this.navigate('login');
      }
      window.addEventListener('hashchange', () => this.handleHash());
      this.handleHash();
    },

    handleHash() {
      const h = location.hash.slice(1);
      if (!this.token) { this.view = 'login'; return; }
      if (h.startsWith('/projects/new')) this.view = 'create';
      else if (h.startsWith('/projects/') && h.endsWith('/members')) {
        const pid = h.match(/\/projects\/(\d+)/)?.[1];
        if (pid) { this.loadProject(pid); this.view = 'members'; }
      } else if (h.startsWith('/projects/')) {
        const pid = h.match(/\/projects\/(\d+)/)?.[1];
        if (pid) this.loadProject(pid);
      } else {
        this.view = 'projects';
      }
    },

    navigate(path) {
      location.hash = path;
      this.handleHash();
    },

    async fetchUser() {
      try {
        const r = await fetch('/api/auth/me', { headers: this.authHeaders() });
        if (r.ok) {
          this.currentUser = await r.json();
        } else {
          this.logout();
        }
      } catch { this.logout(); }
    },

    authHeaders() {
      return this.token ? { 'Authorization': 'Bearer ' + this.token } : {};
    },

    setToken(token) {
      this.token = token;
      localStorage.setItem('cc_token', token);
    },

    logout() {
      fetch('/api/auth/logout', { method: 'POST', headers: this.authHeaders() });
      this.token = null;
      this.currentUser = null;
      localStorage.removeItem('cc_token');
      this.navigate('login');
    },

    async createProject(form) {
      const r = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...this.authHeaders() },
        body: JSON.stringify(form)
      });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      this.navigate('/projects/' + data.project_id);
    },

    async loadProject(pid) {
      const r = await fetch(`/api/projects/${pid}`, { headers: this.authHeaders() });
      if (!r.ok) { this.navigate('projects'); return; }
      const data = await r.json();
      this.project = data.project;
      this.milestones = data.milestones;
      this.tasks = data.tasks;
      this.usedReferences = data.used_references || null;
      this.currentRole = data.current_role;
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
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...this.authHeaders() },
        body: JSON.stringify({ event })
      });
      await this.loadProject(this.project.id);
    },

    // —— 罗盘仪表辅助方法 ——
    needleAngle() {
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
