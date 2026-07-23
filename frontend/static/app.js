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
        if (pid) { this.loadProject(pid); this.view = 'board'; }
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
      const mr = await fetch(`/api/projects/${pid}/members`, { headers: this.authHeaders() });
      this.members = mr.ok ? await mr.json() : [];
    },

    async triggerOverdue() {
      await fetch(`/api/replan/${this.project.id}/trigger_overdue`, { method: 'POST' });
      await this.loadProject(this.project.id);
    },

    // —— 重规划（直接放在 app 根，避免组件挂载时序问题）——
    replanOpen: false,
    replanLoading: false,
    replanProposal: null,
    replanGapDays: null,
    replanApplying: false,
    replanResult: null,

    async proposeReplan() {
      this.replanOpen = true;
      this.replanLoading = true;
      this.replanProposal = null;
      try {
        const r = await fetch(`/api/replan/${this.project.id}/propose`, { method: 'POST' });
        const data = await r.json();
        this.replanGapDays = data.gap_days;
        this.replanProposal = data.proposal;
      } finally { this.replanLoading = false; }
    },

    async applyReplan() {
      if (!this.replanProposal) return;
      this.replanApplying = true;
      try {
        const r = await fetch(`/api/replan/${this.project.id}/apply`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ proposal: this.replanProposal })
        });
        this.replanResult = await r.json();
        await this.refresh();
        this.replanOpen = false;
      } finally { this.replanApplying = false; }
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

    // —— 队长手动增删任务节点 ——
    addTaskOpen: false,
    addTaskMilestoneId: null,
    addTaskTitle: '',
    addTaskLoading: false,
    deleteTaskTarget: null,
    deleteTaskLoading: false,

    openAddTask(milestoneId) {
      this.addTaskMilestoneId = milestoneId;
      this.addTaskTitle = '';
      this.addTaskOpen = true;
    },

    async submitAddTask() {
      if (!this.addTaskTitle.trim()) return;
      this.addTaskLoading = true;
      try {
        await fetch(`/api/milestones/${this.addTaskMilestoneId}/tasks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...this.authHeaders() },
          body: JSON.stringify({ title: this.addTaskTitle.trim() })
        });
        this.addTaskOpen = false;
        await this.loadProject(this.project.id);
      } finally { this.addTaskLoading = false; }
    },

    askDeleteTask(task) {
      this.deleteTaskTarget = task;
    },

    async doDeleteTask() {
      if (!this.deleteTaskTarget) return;
      this.deleteTaskLoading = true;
      try {
        await fetch(`/api/tasks/${this.deleteTaskTarget.id}`, {
          method: 'DELETE',
          headers: this.authHeaders()
        });
        this.deleteTaskTarget = null;
        await this.loadProject(this.project.id);
      } finally { this.deleteTaskLoading = false; }
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
