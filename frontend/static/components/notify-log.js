function notifyLog(parent) {
  return {
    logs: [],
    schedulerStatus: null,
    scanning: false,
    scanResult: null,

    async load() {
      const pid = parent.project?.id || '';
      const r = await fetch(`/api/notifications?project_id=${pid}&limit=20`, { headers: parent.authHeaders() });
      this.logs = r.ok ? await r.json() : [];
      await this.loadSchedulerStatus();
    },

    async loadSchedulerStatus() {
      try {
        const r = await fetch('/api/notify/scheduler/status', { headers: parent.authHeaders() });
        this.schedulerStatus = r.ok ? await r.json() : null;
      } catch { this.schedulerStatus = null; }
    },

    async testPush() {
      await fetch(`/api/notify/test?project_id=${parent.project?.id || ''}`, {
        method: 'POST', headers: parent.authHeaders()
      });
      await this.load();
    },

    async scanNow() {
      this.scanning = true;
      this.scanResult = null;
      try {
        const r = await fetch('/api/notify/scan', { method: 'POST', headers: parent.authHeaders() });
        this.scanResult = r.ok ? await r.json() : { error: '扫描失败' };
        await this.load();
      } finally { this.scanning = false; }
    },

    typeMeta(type) {
      return {
        task_submit: { label: '提交', cls: 'nt-submit' },
        task_review: { label: '审阅', cls: 'nt-review' },
        manual_test: { label: '测试', cls: 'nt-test' },
        overdue: { label: '逾期', cls: 'nt-overdue' },
        replan: { label: '重规划', cls: 'nt-replan' },
        milestone: { label: '里程碑', cls: 'nt-milestone' }
      }[type] || { label: type || '通知', cls: '' };
    },

    statusLabel(s) {
      return { sent: '已推送', failed: '失败' }[s] || s || '';
    },

    formatNextRun(s) {
      if (!s) return '—';
      return s.replace('T', ' ').slice(0, 16);
    },

    init() { this.load(); }
  }
}
